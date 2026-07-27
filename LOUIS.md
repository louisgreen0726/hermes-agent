# Louis Hermes Agent

This repository is the production source for the Louis distribution of Hermes Agent.

## Identity

- Product repository: `https://github.com/louisgreen0726/hermes-agent`
- Release branch: `main`
- User-facing version: `Louis-0.19.0.1`
- Python package version: `0.19.0+Louis.1`
- Upstream project: `https://github.com/NousResearch/hermes-agent`

The project is based on Hermes Agent by Nous Research and remains distributed under the MIT License. It is an independently maintained fork and is not an official Nous Research release.

## Release policy

`origin/main` is the only automatic update source. The `upstream` remote may be retained for manual review, but ordinary `hermes update`, `hermes-update-louis`, and the gateway `/update` command never merge, rebase, pull, or synchronize from it.

Upstream changes are adopted only through an explicit integration branch, code review, and the Louis regression suite. They are then committed to this repository as a new Louis release.

## Local capabilities

The first Louis release carries:

- Telegram Native Guest Mode.
- Native Rich Markdown table delivery in Telegram Guest Mode.
- CJK Rich Message delivery for ordinary replies.
- Rich table consistency for cron and standalone sends.
- Regression coverage for Telegram routing, authorization, rich delivery, threads, proxy mode, and delivery ledger behavior.
- A native management center for models, providers, Gateway services, diagnostics, logs, and protected Louis updates.

## Management center

Use either `hermes manage` or the dedicated `hermes-manage` command. Linux and
macOS installers create the shortcut explicitly; Windows receives
`hermes-manage.exe` from the packaged console entry points already placed on
`PATH` by the installer.

Legacy versions of `hermes_manager.sh` stored every discovered model as a
separate `custom_providers` entry named `Provider/model-id`. Hermes-Louis can
inspect and consolidate that layout without exposing credentials:

```bash
hermes-manage --check
hermes-manage --repair
```

Use `--repair --yes` for a non-interactive deployment. Named profiles are
supported, for example `hermes-manage -p production --check`. A repair is
written only when endpoint, credential, protocol, TLS, header, and other
routing settings agree. Hermes-Louis refuses malformed YAML, managed profiles,
and ambiguous groups, and creates a mode-`0600` backup before any write.

## Updating

Production machines use `hermes-update-louis`. The updater validates `origin/main` in an isolated worktree, runs the Louis regression suite, updates dependencies, verifies the candidate again, activates the validated commit, and restarts the gateway only after integrity checks pass.

The gateway launches updates in an independent transient user service so the updater survives the intentional Gateway stop/restart window. Progress and the final exit code are delivered through durable marker files.

Do not use `git pull upstream main` on a production checkout.

## Release notes

- [Louis Hermes Agent 0.19.0.1](LOUIS_RELEASE_NOTES.md)
