# Louis Hermes Agent - Unreleased

These changes are merged into `main` after the versioned 0.19.0.1 baseline.
No next version number, release date, tag, or GitHub Release has been assigned.

## Native Management Center

- Added the interactive `hermes manage` command and the `hermes-manage`
  shortcut.
- Added one management surface for models and providers, Gateway operations,
  diagnostics, logs, setup, terminal chat, and protected Louis updates.
- Added `--check`, `--repair`, and `--repair --yes` modes for deployments that
  used the legacy `hermes_manager.sh` script.
- Added named-profile support, including `hermes-manage -p <profile>`.

## Custom Providers And Models

- Custom endpoints are stored as one provider with one or more model IDs,
  rather than one provider record per model.
- The interactive flow probes the endpoint model catalog when possible and
  otherwise accepts an exact model ID manually.
- API compatibility can be selected explicitly: Chat Completions, Responses /
  Codex, Anthropic Messages, or automatic detection.
- API keys entered through the custom-endpoint flow are stored in `.env`; the
  YAML configuration keeps an environment reference instead of duplicating the
  secret.
- `/model` now groups legacy `Provider/model-id` records correctly, preserves
  the active-model marker, and routes switches through the matching endpoint,
  credential, protocol, TLS, and header identity.
- Legitimate single provider names containing `/` are not treated as legacy
  per-model records. Ambiguous same-name groups are left unchanged.

## Migration Safety

- Legacy consolidation creates a mode-`0600` backup before writing.
- Malformed YAML, package-manager-managed profiles, conflicting settings, and
  ambiguous provider groups fail closed without rewriting the configuration.
- Existing normalized configurations require no migration.

## Distribution And Updates

- Linux and macOS installers create the `hermes-manage` launcher; Windows uses
  the packaged console entry point.
- `hermes-update-louis` repairs a missing launcher even when production is
  already running the current `origin/main` commit.
- The protected updater includes management-center, distribution, packaging,
  model-catalog, Gateway, and Telegram regressions in its activation gate.

## Reliability

- Stabilized generated systemd service PATH values when an operator shell and
  the Gateway runtime discover `node` from different standard locations. This
  prevents a current unit from being reported and rewritten as outdated on
  every restart.

## Verification Snapshot

- The management-center and model-routing changes passed focused CLI,
  packaging, installer, updater, and model-switch regression suites.
- The 2026-07-27 production activation ran 759 tests before dependency
  activation and the same 759 tests afterward, with no failures.
- The deployed Gateway passed deep status checks, configuration inspection,
  launcher verification, and post-start error-log inspection.

This verification count describes that snapshot only; the gate may grow as new
tests are added.
