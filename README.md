<p align="center">
  <img src="assets/banner.png" alt="Louis Hermes Agent" width="100%">
</p>

# Louis Hermes Agent

<p align="center">
  <strong>An independently maintained AI agent project derived from Hermes Agent.</strong>
</p>

<p align="center">
  <a href="README.md">English</a> |
  <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <a href="https://github.com/louisgreen0726/hermes-agent/releases"><img src="https://img.shields.io/badge/stable-Louis--0.19.0.4-2563eb" alt="Stable release: Louis-0.19.0.4"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-16a34a" alt="MIT License"></a>
  <a href="https://github.com/louisgreen0726/hermes-agent/issues"><img src="https://img.shields.io/badge/issues-Louis%20project-7c3aed" alt="Louis project issues"></a>
</p>

> [!IMPORTANT]
> Louis Hermes Agent is an independent derivative of
> [Nous Research's Hermes Agent](https://github.com/NousResearch/hermes-agent).
> It is not an official Nous Research product or release. The original project,
> contributors, copyright notices, and MIT license remain fully attributed.

## What this project is

Louis Hermes Agent is a personal AI agent that runs across a CLI, terminal UI,
Electron desktop app, web dashboard, and messaging gateway. It retains the
Hermes foundation for tools, memory, skills, plugins, scheduled jobs,
subagents, model providers, terminal backends, and browser automation, while
developing its own product direction and release process.

This repository is still connected to the upstream project in GitHub's fork
network for provenance. Operationally, however, it is maintained as a separate
project:

- Releases are produced from `louisgreen0726/hermes-agent`.
- `origin/main` is the only automatic update source for Louis installations.
- Upstream commits are reviewed and adopted selectively; they are not merged or
  rebased automatically.
- Compatibility with every future upstream change is not guaranteed.
- A large GitHub "behind upstream" count is expected and is not a Louis release
  health indicator.

## Origin

The independent Louis line started on July 27, 2026 (UTC+8), from upstream
Hermes Agent commit
[`41f2196c`](https://github.com/NousResearch/hermes-agent/commit/41f2196c530b3359d9a7fc9c7bd41e9ddd7882c5).
The inherited codebase was Hermes Agent `0.19.0`.

Nous Research created the original Hermes Agent architecture and the majority
of the inherited implementation. Louis development builds on that work under
the MIT License. References to Nous Research that remain in source history,
documentation, assets, or integration names describe that provenance or an
upstream service; they do not imply that this independent project is an
official Nous Research release.

## Current status

| Item | Status |
| --- | --- |
| Maintenance | Active, independently maintained |
| Production branch | `main` |
| Stable baseline | [`Louis-0.19.0.4`](docs/releases/LOUIS_0.19.0.4.md) |
| Python package version | `0.19.0+Louis.4` |
| Current `main` | Stable baseline plus reviewed, unreleased changes |
| Upstream relationship | Selective review and backporting only |
| Automatic updates | Louis `origin/main` only |

The current `main` branch includes an unreleased provider-isolation fix: named
custom providers can use the same relay URL while retaining separate API keys,
models, API modes, and credential pools.

Release history and pending changes are tracked in
[`LOUIS_RELEASE_NOTES.md`](LOUIS_RELEASE_NOTES.md) and
[`docs/releases/LOUIS_UNRELEASED.md`](docs/releases/LOUIS_UNRELEASED.md).

## Main capabilities

The inherited Hermes foundation includes:

- Interactive CLI, Ink-based TUI, Electron desktop app, and web dashboard.
- Messaging gateways for Telegram, Discord, Slack, WhatsApp, Signal, and other
  platforms.
- Persistent sessions, memory, skills, plugins, MCP support, cron jobs, and
  subagent delegation.
- Local, Docker, SSH, Singularity, Modal, and Daytona terminal environments.
- Multiple model providers plus custom OpenAI-, Anthropic-, and
  Responses-compatible endpoints.

Louis-specific work currently includes:

- Telegram Native Guest Mode and rich Markdown/CJK delivery.
- A native management center for models, providers, Gateway services,
  diagnostics, logs, backups, and protected updates.
- Provider grouping, API-mode preservation, and isolated credentials for named
  custom providers sharing one relay endpoint.
- Candidate-owned update validation, regression gates, rollback protection,
  and Gateway-safe restart handling.
- WebDAV backup and restore with per-device retention and scheduled execution.
- A Simplified Chinese dashboard, localized configuration metadata, and Louis
  dashboard themes.

See [`LOUIS.md`](LOUIS.md) for the detailed project and release policy.

## Installation

### Linux, macOS, WSL2, and Termux

```bash
curl -fsSL https://raw.githubusercontent.com/louisgreen0726/hermes-agent/main/scripts/install.sh | bash
```

### Native Windows PowerShell

```powershell
iex (irm https://raw.githubusercontent.com/louisgreen0726/hermes-agent/main/scripts/install.ps1)
```

After installation:

```bash
hermes setup          # Configure providers, tools, and integrations
hermes                # Start the interactive agent
hermes-manage         # Open the Louis management center
hermes gateway        # Manage messaging platforms
hermes doctor         # Diagnose the installation
```

## Updates

Louis installations update from this repository, not directly from upstream:

```bash
hermes update
```

Production installations can validate the candidate before activation:

```bash
hermes-update-louis --dry-run
hermes-update-louis
```

Do not run `git pull upstream main` in a production checkout. Upstream adoption
belongs on an explicit integration branch with code review and the Louis
regression suite.

## Documentation and support

- [Project and release policy](LOUIS.md)
- [Louis release notes](LOUIS_RELEASE_NOTES.md)
- [Documentation source](website/docs)
- [Louis issue tracker](https://github.com/louisgreen0726/hermes-agent/issues)
- [Original Hermes Agent project](https://github.com/NousResearch/hermes-agent)
- [Original upstream documentation](https://hermes-agent.nousresearch.com/docs/)

Upstream documentation remains useful for inherited Hermes functionality, but
Louis-specific behavior and commands in this repository take precedence when
the two differ.

## License and attribution

This project is distributed under the [MIT License](LICENSE).

Hermes Agent was originally created by
[Nous Research](https://nousresearch.com) and its contributors. Louis Hermes
Agent is independently maintained by the Louis project and is not affiliated
with or endorsed by Nous Research.
