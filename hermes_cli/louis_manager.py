"""Native Hermes-Louis management center and legacy-manager repair tools."""

from __future__ import annotations

import copy
import shutil
import subprocess
import sys
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


@dataclass(frozen=True)
class ProviderRepair:
    """One safely consolidatable provider group."""

    name: str
    source_entries: int
    model_count: int


@dataclass(frozen=True)
class RepairSummary:
    """Secret-free description of a legacy-manager repair plan or result."""

    repairs: tuple[ProviderRepair, ...] = ()
    skipped_groups: tuple[str, ...] = ()
    model_provider_updated: bool = False
    changed: bool = False
    backup_path: Path | None = None


@dataclass(frozen=True)
class _MergedProvider:
    name: str
    canonical: dict[str, Any]
    source_indices: tuple[int, ...]
    models: tuple[str, ...]


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return tuple(sorted((str(key), _freeze(item)) for key, item in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return tuple(sorted(_freeze(item) for item in value))
    return value


def _entry_name(entry: Mapping[str, Any]) -> str:
    return str(entry.get("name") or "").strip()


def _entry_default_model(entry: Mapping[str, Any]) -> str:
    return str(entry.get("model") or entry.get("default_model") or "").strip()


def _declared_models(entry: Mapping[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    result: list[tuple[str, dict[str, Any]]] = []

    def add(model_id: Any, metadata: Any = None) -> None:
        model = str(model_id or "").strip()
        if not model:
            return
        result.append((
            model,
            copy.deepcopy(metadata) if isinstance(metadata, dict) else {},
        ))

    add(entry.get("model"))
    add(entry.get("default_model"))
    models = entry.get("models")
    if isinstance(models, Mapping):
        for model_id, metadata in models.items():
            add(model_id, metadata)
    elif isinstance(models, list):
        for item in models:
            if isinstance(item, str):
                add(item)
            elif isinstance(item, Mapping):
                model_id = item.get("id") or item.get("name")
                metadata = {
                    key: value
                    for key, value in item.items()
                    if key not in {"id", "name"}
                }
                add(model_id, metadata)
    return result


def _legacy_manager_prefix(entry: Mapping[str, Any]) -> str | None:
    """Recognize ``Provider/model-id`` names emitted by hermes_manager.sh."""
    name = _entry_name(entry)
    if "/" not in name:
        return None
    prefix, suffix = name.split("/", 1)
    prefix = prefix.strip()
    suffix = suffix.strip()
    if not prefix or not suffix:
        return None

    declared = [model for model, _ in _declared_models(entry)]
    if not declared or suffix not in declared:
        return None
    return prefix


def _normalized_endpoint(entry: Mapping[str, Any]) -> str:
    endpoint = str(
        entry.get("base_url") or entry.get("url") or entry.get("api") or ""
    ).strip()
    return endpoint.rstrip("/")


def _provider_identity(entry: Mapping[str, Any]) -> Any:
    """Return the complete non-model routing identity for a custom provider."""
    settings = copy.deepcopy(dict(entry))
    for key in ("name", "model", "default_model", "models", "base_url", "url", "api"):
        settings.pop(key, None)
    return (
        _normalized_endpoint(entry),
        _freeze(settings),
    )


def _merge_metadata(
    current: dict[str, Any], incoming: dict[str, Any]
) -> dict[str, Any] | None:
    if current == incoming:
        return current
    if not current:
        return copy.deepcopy(incoming)
    if not incoming:
        return current

    merged = copy.deepcopy(current)
    for key, value in incoming.items():
        if key in merged and merged[key] != value:
            return None
        merged[key] = copy.deepcopy(value)
    return merged


def _build_merged_provider(
    name: str,
    records: Sequence[tuple[int, Mapping[str, Any]]],
) -> _MergedProvider | None:
    canonical_source = next(
        (
            entry
            for _, entry in records
            if _entry_name(entry).casefold() == name.casefold()
        ),
        records[0][1],
    )
    canonical = copy.deepcopy(dict(canonical_source))
    canonical["name"] = name

    endpoint = _normalized_endpoint(canonical_source)
    if endpoint:
        canonical["base_url"] = endpoint
    canonical.pop("url", None)
    canonical.pop("api", None)
    canonical.pop("default_model", None)

    models: dict[str, dict[str, Any]] = {}
    default_model = ""
    for _, entry in records:
        entry_default = _entry_default_model(entry)
        if not default_model and entry_default:
            default_model = entry_default
        for model_id, metadata in _declared_models(entry):
            if model_id not in models:
                models[model_id] = copy.deepcopy(metadata)
                continue
            merged = _merge_metadata(models[model_id], metadata)
            if merged is None:
                return None
            models[model_id] = merged

    if not default_model and models:
        default_model = next(iter(models))
    if default_model:
        canonical["model"] = default_model
    else:
        canonical.pop("model", None)
    if models:
        canonical["models"] = models
    else:
        canonical.pop("models", None)

    return _MergedProvider(
        name=name,
        canonical=canonical,
        source_indices=tuple(index for index, _ in records),
        models=tuple(models),
    )


def _custom_provider_slug(display_name: str) -> str:
    from hermes_cli.providers import custom_provider_slug

    return custom_provider_slug(display_name)


def _model_matches_group(model_cfg: Mapping[str, Any], group: _MergedProvider) -> bool:
    configured = str(model_cfg.get("provider") or "").strip().casefold()
    expected = _custom_provider_slug(group.name).casefold()
    expected_name = group.name.casefold()

    configured_mode = str(
        model_cfg.get("api_mode") or model_cfg.get("transport") or ""
    ).strip()
    provider_mode = str(
        group.canonical.get("api_mode") or group.canonical.get("transport") or ""
    ).strip()
    if configured_mode and provider_mode and configured_mode != provider_mode:
        return False

    if configured in {expected, expected_name}:
        return True
    if configured.startswith("custom:"):
        requested_name = configured.removeprefix("custom:").split("/", 1)[0]
        if requested_name == expected.removeprefix("custom:"):
            return True
    if configured != "custom":
        return False

    model_endpoint = str(model_cfg.get("base_url") or "").strip().rstrip("/")
    group_endpoint = _normalized_endpoint(group.canonical)
    if not model_endpoint or model_endpoint != group_endpoint:
        return False

    for key in ("api_key", "key_env"):
        configured_value = str(model_cfg.get(key) or "").strip()
        if (
            configured_value
            and configured_value != str(group.canonical.get(key) or "").strip()
        ):
            return False
    return True


def plan_legacy_manager_repair(
    config: Mapping[str, Any],
) -> tuple[dict[str, Any], RepairSummary]:
    """Build a loss-averse repair plan without touching disk.

    Only entries whose endpoint, credentials, protocol, TLS, headers, and every
    other non-model field match exactly are consolidated. Ambiguous groups are
    reported and left untouched.
    """
    repaired = copy.deepcopy(dict(config))
    raw_providers = repaired.get("custom_providers")
    if not isinstance(raw_providers, list):
        return repaired, RepairSummary()

    prefixes: dict[str, str] = {}
    for entry in raw_providers:
        if not isinstance(entry, Mapping):
            continue
        prefix = _legacy_manager_prefix(entry)
        if prefix:
            prefixes.setdefault(prefix.casefold(), prefix)

    merged_groups: list[_MergedProvider] = []
    skipped: list[str] = []
    for prefix_key, display_name in prefixes.items():
        records: list[tuple[int, Mapping[str, Any]]] = []
        identities: set[Any] = set()
        for index, entry in enumerate(raw_providers):
            if not isinstance(entry, Mapping):
                continue
            entry_name = _entry_name(entry)
            legacy_prefix = _legacy_manager_prefix(entry)
            belongs = entry_name.casefold() == prefix_key or (
                legacy_prefix is not None and legacy_prefix.casefold() == prefix_key
            )
            if not belongs:
                continue
            records.append((index, entry))
            identities.add(_provider_identity(entry))

        if len(records) < 2:
            continue
        if len(identities) != 1:
            skipped.append(display_name)
            continue
        merged = _build_merged_provider(display_name, records)
        if merged is None:
            skipped.append(display_name)
            continue
        merged_groups.append(merged)

    if not merged_groups:
        return repaired, RepairSummary(skipped_groups=tuple(skipped))

    replacements = {
        min(group.source_indices): group.canonical for group in merged_groups
    }
    removed_indices = {
        index for group in merged_groups for index in group.source_indices
    }
    consolidated: list[Any] = []
    for index, entry in enumerate(raw_providers):
        replacement = replacements.get(index)
        if replacement is not None:
            consolidated.append(replacement)
        elif index not in removed_indices:
            consolidated.append(entry)
    repaired["custom_providers"] = consolidated

    model_provider_updated = False
    model_cfg = repaired.get("model")
    if isinstance(model_cfg, dict):
        matches = [
            group for group in merged_groups if _model_matches_group(model_cfg, group)
        ]
        if len(matches) == 1:
            target = matches[0]
            target_slug = _custom_provider_slug(target.name)
            model_mode = str(
                model_cfg.get("api_mode") or model_cfg.get("transport") or ""
            ).strip()
            provider_mode = str(
                target.canonical.get("api_mode")
                or target.canonical.get("transport")
                or ""
            ).strip()
            if model_mode and not provider_mode:
                target.canonical["api_mode"] = model_mode
            stale_keys = ("base_url", "api_key", "key_env", "api_mode", "transport")
            if model_cfg.get("provider") != target_slug or any(
                key in model_cfg for key in stale_keys
            ):
                model_cfg["provider"] = target_slug
                for key in stale_keys:
                    model_cfg.pop(key, None)
                model_provider_updated = True

    summary = RepairSummary(
        repairs=tuple(
            ProviderRepair(
                name=group.name,
                source_entries=len(group.source_indices),
                model_count=len(group.models),
            )
            for group in merged_groups
        ),
        skipped_groups=tuple(skipped),
        model_provider_updated=model_provider_updated,
        changed=repaired != dict(config),
    )
    return repaired, summary


def _strict_raw_config() -> dict[str, Any]:
    """Validate YAML before using Hermes' cached raw-config reader."""
    from hermes_cli.config import get_config_path, read_raw_config
    from utils import fast_safe_load

    config_path = get_config_path()
    if not config_path.exists():
        return {}
    with config_path.open(encoding="utf-8") as handle:
        parsed = fast_safe_load(handle) or {}
    if not isinstance(parsed, dict):
        raise ValueError(f"{config_path} must contain a YAML mapping at the root")
    raw = read_raw_config()
    if raw != parsed:
        return copy.deepcopy(parsed)
    return raw


def inspect_legacy_manager_config() -> RepairSummary:
    from hermes_cli.config import _CONFIG_LOCK

    with _CONFIG_LOCK:
        _, summary = plan_legacy_manager_repair(_strict_raw_config())
        return summary


def _create_config_backup(config_path: Path) -> Path:
    from hermes_constants import get_hermes_home

    backup_dir = get_hermes_home() / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = backup_dir / f"config-before-louis-manager-{stamp}.yaml"
    suffix = 1
    while candidate.exists():
        candidate = backup_dir / f"config-before-louis-manager-{stamp}-{suffix}.yaml"
        suffix += 1
    shutil.copy2(config_path, candidate)
    candidate.chmod(0o600)
    return candidate


def repair_legacy_manager_config() -> RepairSummary:
    """Apply the current repair plan through Hermes' guarded atomic writer."""
    from hermes_cli.config import (
        _CONFIG_LOCK,
        get_config_path,
        is_managed,
        read_raw_config,
        save_config,
    )

    with _CONFIG_LOCK:
        if is_managed():
            raise RuntimeError(
                "This Hermes profile is package-manager managed; its configuration cannot be changed here."
            )
        config_path = get_config_path()
        raw = _strict_raw_config()
        repaired, summary = plan_legacy_manager_repair(raw)
        if not summary.changed:
            return summary
        if not config_path.is_file():
            raise RuntimeError(f"Configuration file not found: {config_path}")

        backup_path = _create_config_backup(config_path)
        save_config(repaired, strip_defaults=False)

        persisted = read_raw_config()
        _, remaining = plan_legacy_manager_repair(persisted)
        repaired_names = {item.name.casefold() for item in summary.repairs}
        remaining_names = {item.name.casefold() for item in remaining.repairs}
        if repaired_names & remaining_names:
            raise RuntimeError(
                f"Configuration verification failed; original backup is at {backup_path}"
            )
        return replace(summary, backup_path=backup_path)


def _print_repair_summary(summary: RepairSummary, *, applied: bool = False) -> None:
    if not summary.repairs:
        print("未发现由旧版 hermes_manager.sh 生成的逐模型供应商配置。")
    else:
        heading = (
            "已修复旧管理器配置：" if applied else "发现可安全修复的旧管理器配置："
        )
        print(heading)
        for item in summary.repairs:
            print(
                f"  - {item.name}: {item.source_entries} 条供应商记录 -> "
                f"1 个供应商，{item.model_count} 个模型"
            )
        if summary.model_provider_updated:
            print("  - 当前模型已切换到规范的 custom:<provider> 引用。")
    if summary.skipped_groups:
        names = ", ".join(summary.skipped_groups)
        print(f"为避免误合并，以下同名但设置不一致的分组未修改：{names}")
    if applied and summary.backup_path:
        print(f"修复前备份：{summary.backup_path}")


def _run_process(argv: Sequence[str]) -> int:
    print()
    try:
        return subprocess.run(list(argv), check=False).returncode
    except FileNotFoundError:
        print(f"命令不可用：{argv[0]}", file=sys.stderr)
        return 127
    except KeyboardInterrupt:
        print("\n已返回管理中心。")
        return 130


def _run_hermes(*args: str) -> int:
    return _run_process([sys.executable, "-m", "hermes_cli.main", *args])


def _pause() -> None:
    try:
        input("\n按 Enter 返回管理中心...")
    except (EOFError, KeyboardInterrupt):
        pass


def _select(
    title: str, items: Iterable[str], *, cancel_label: str = "返回"
) -> int | None:
    from hermes_cli.curses_ui import curses_single_select

    return curses_single_select(title, list(items), cancel_label=cancel_label)


def _interactive_repair() -> None:
    try:
        summary = inspect_legacy_manager_config()
        _print_repair_summary(summary)
        if not summary.changed:
            _pause()
            return
        choice = _select(
            "修复旧版管理器配置",
            ["创建备份并执行安全修复"],
        )
        if choice != 0:
            return
        applied = repair_legacy_manager_config()
        print()
        _print_repair_summary(applied, applied=True)
    except Exception as exc:
        print(f"修复失败：{exc}", file=sys.stderr)
    _pause()


def _gateway_menu() -> None:
    actions = [
        ("查看 Gateway 状态", ("gateway", "status", "--deep")),
        ("安装 Gateway 服务", ("gateway", "install")),
        ("启动 Gateway", ("gateway", "start")),
        ("重启 Gateway", ("gateway", "restart")),
        ("停止 Gateway", ("gateway", "stop")),
        ("配置消息平台", ("gateway", "setup")),
    ]
    choice = _select("Gateway 服务管理", [label for label, _ in actions])
    if choice is None:
        return
    _run_hermes(*actions[choice][1])
    _pause()


def _logs_menu() -> None:
    actions = [
        ("Gateway 日志（最近 100 行）", ("logs", "gateway", "-n", "100")),
        ("错误日志（最近 100 行）", ("logs", "errors", "-n", "100")),
        ("Agent 日志（最近 100 行）", ("logs", "agent", "-n", "100")),
        ("持续查看 Gateway 日志", ("logs", "gateway", "-f")),
        ("列出全部日志", ("logs", "list")),
    ]
    choice = _select("Hermes 日志", [label for label, _ in actions])
    if choice is None:
        return
    _run_hermes(*actions[choice][1])
    _pause()


def _run_louis_update() -> int:
    updater = shutil.which("hermes-update-louis")
    if not updater:
        candidate = (
            Path(__file__).resolve().parents[1] / "scripts" / "hermes-update-louis"
        )
        if candidate.is_file():
            updater = str(candidate)
    if not updater:
        print("未找到 hermes-update-louis。请先用 Louis 安装器修复命令入口。")
        return 127
    return _run_process([updater])


def _menu_title() -> str:
    try:
        raw = _strict_raw_config()
        model_cfg = raw.get("model") if isinstance(raw, dict) else None
        if isinstance(model_cfg, dict):
            provider = str(model_cfg.get("provider") or "未设置")
            model = str(model_cfg.get("default") or model_cfg.get("model") or "未设置")
            return f"Hermes-Louis 管理中心  |  {provider} / {model}"
    except Exception:
        pass
    return "Hermes-Louis 管理中心"


def run_interactive_manager() -> int:
    actions = [
        "状态总览",
        "模型与供应商管理",
        "刷新模型目录",
        "修复旧版管理器配置",
        "Gateway 服务管理",
        "初始化设置",
        "配置检查与 Doctor",
        "查看日志",
        "更新 Hermes-Louis",
        "启动终端聊天",
        "卸载 Hermes",
    ]

    while True:
        choice = _select(_menu_title(), actions, cancel_label="退出")
        if choice is None:
            return 0
        if choice == 0:
            _run_hermes("status", "--all")
            _pause()
        elif choice == 1:
            _run_hermes("model")
            _pause()
        elif choice == 2:
            _run_hermes("model", "--refresh")
            _pause()
        elif choice == 3:
            _interactive_repair()
        elif choice == 4:
            _gateway_menu()
        elif choice == 5:
            _run_hermes("setup")
            _pause()
        elif choice == 6:
            _run_hermes("doctor")
            _pause()
        elif choice == 7:
            _logs_menu()
        elif choice == 8:
            _run_louis_update()
            _pause()
        elif choice == 9:
            _run_hermes("chat")
            _pause()
        elif choice == 10:
            _run_hermes("uninstall")
            return 0


def run_manage_command(args: Any) -> int:
    """CLI handler shared by ``hermes manage`` and ``hermes-manage``."""
    if getattr(args, "yes", False) and not getattr(args, "repair", False):
        print("--yes 只能与 --repair 一起使用。", file=sys.stderr)
        return 2

    if getattr(args, "check", False):
        try:
            summary = inspect_legacy_manager_config()
        except Exception as exc:
            print(f"配置检查失败：{exc}", file=sys.stderr)
            return 2
        _print_repair_summary(summary)
        return 1 if summary.changed or summary.skipped_groups else 0

    if getattr(args, "repair", False):
        try:
            preview = inspect_legacy_manager_config()
        except Exception as exc:
            print(f"配置检查失败：{exc}", file=sys.stderr)
            return 2
        _print_repair_summary(preview)
        if not preview.changed:
            return 1 if preview.skipped_groups else 0

        if not getattr(args, "yes", False):
            if not sys.stdin.isatty():
                print("非交互环境请同时使用 --yes。", file=sys.stderr)
                return 2
            choice = _select(
                "确认修复旧版管理器配置",
                ["创建备份并执行安全修复"],
            )
            if choice != 0:
                print("已取消。")
                return 0
        try:
            applied = repair_legacy_manager_config()
        except Exception as exc:
            print(f"修复失败：{exc}", file=sys.stderr)
            return 2
        _print_repair_summary(applied, applied=True)
        return 1 if applied.skipped_groups else 0

    if not sys.stdin.isatty():
        print(
            "Error: 'hermes manage' requires an interactive terminal. "
            "Use --check or --repair --yes for non-interactive operation.",
            file=sys.stderr,
        )
        return 1
    return run_interactive_manager()
