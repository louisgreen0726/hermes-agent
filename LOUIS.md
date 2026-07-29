# Louis Hermes Agent

This repository is the production source for Louis Hermes Agent, an
independently maintained derivative of Hermes Agent.

## Identity

- Product repository: `https://github.com/louisgreen0726/hermes-agent`
- Release branch: `main`
- User-facing version: `Louis-0.19.0.4`
- Python package version: `0.19.0+Louis.4`
- Source project: `https://github.com/NousResearch/hermes-agent`

The independent Louis line began from Nous Research Hermes Agent commit
`41f2196c530b3359d9a7fc9c7bd41e9ddd7882c5` and remains distributed under the
MIT License. GitHub retains the fork-network relationship for provenance, but
Louis has its own roadmap, release process, production branch, and update
source. It is not an official Nous Research release.

## Current channel

- The versioned baseline is `Louis-0.19.0.4`.
- `main` is the production update channel and may contain validated unreleased
  changes after that baseline.
- Pending changes and immutable versioned records are separated in the
  [release-notes index](LOUIS_RELEASE_NOTES.md).
- The protected update and Gateway restart workflow has been exercised on the
  production installation. This document intentionally does not pin a
  deployment SHA, which would become stale after the next update.

## Release policy

`origin/main` is the only automatic update source. The `upstream` remote may be retained for manual review, but ordinary `hermes update`, `hermes-update-louis`, and the gateway `/update` command never merge, rebase, pull, or synchronize from it.

Upstream changes are adopted only through an explicit integration branch, code review, and the Louis regression suite. They are then committed to this repository as a new Louis release.

## Capabilities

The versioned 0.19.0.4 baseline carries:

- Telegram Native Guest Mode.
- Native Rich Markdown table delivery in Telegram Guest Mode.
- CJK Rich Message delivery for ordinary replies.
- Rich table consistency for cron and standalone sends.
- Regression coverage for Telegram routing, authorization, rich delivery, threads, proxy mode, and delivery ledger behavior.
- A native management center for models, providers, Gateway services,
  diagnostics, logs, and protected Louis updates.
- Safe migration away from the legacy one-provider-per-model layout.
- Correct provider grouping and routing in `/model` for multi-model custom
  endpoints.
- Stable systemd service generation across operator-shell and Gateway runtime
  environments.
- Named custom-provider activation that preserves the provider-owned Responses,
  Chat Completions, or Anthropic transport at runtime.
- Candidate-owned protected-update test gates, strict manifest validation, and
  non-network runtime smoke checks before a release is accepted as healthy.
- Version-aware custom `User-Agent` headers and synchronized Python, CLI, and
  Desktop release metadata.
- Complete WebDAV backup, per-device retention, no-agent daily scheduling, and
  rollback-protected restore from both the CLI and `hermes manage`.
- `Hermes Light (Large)` as the readable default Dashboard theme while
  preserving every explicit existing theme preference and the Teal themes.
- Complete Simplified Chinese Dashboard interaction coverage, locale-aware
  formatting, translated configuration metadata, and a static English-string
  regression gate.
- Bounded models.dev offline probes so model pickers remain responsive when the
  registry and local cache are unavailable.

## Management center

Use either `hermes manage` or the dedicated `hermes-manage` command. Linux and
macOS installers create the shortcut explicitly; Windows receives
`hermes-manage.exe` from the packaged console entry points already placed on
`PATH` by the installer.

To add a custom endpoint interactively:

1. Run `hermes manage` and choose **Model and provider management**.
2. Choose **Custom endpoint (enter URL manually)**.
3. Enter the API base URL, API key, compatibility mode, exact model ID,
   optional context length, and a provider display name.
4. Restart the Gateway when the running messaging service must pick up the new
   default configuration.

Use one provider name per distinct credential and routing identity. Different
named providers may share an endpoint when a relay assigns different API keys,
models, or API modes; their credentials and runtime pools remain isolated.
Reusing the same provider name edits that configuration. Multiple credentials
inside one provider pool are appropriate only when they are interchangeable
for that same named provider. A model ID such as `gpt-5.6-sol` must remain a
model ID; do not turn it into a provider name such as `Louis/gpt-5.6-sol`. API
keys entered by this flow are stored in `.env`, while `config.yaml` retains an
environment reference.

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

Production machines use `hermes-update-louis`. The updater validates `origin/main` in an isolated worktree, loads the regression manifest from that candidate, runs the suite, updates dependencies, verifies the candidate again, activates the validated commit, and restarts the gateway only after integrity checks pass. Candidate manifest entries are restricted to existing test files inside the candidate worktree.

Before a newly activated release is accepted, the updater verifies the editable
source, imports both the CLI and Gateway runtime, and checks the Louis version
command without making a model API request. The same smoke check runs when the
checkout is already current, so a broken editable install is not reported as
healthy merely because no Git update is available.

The gateway launches updates in an independent transient user service so the updater survives the intentional Gateway stop/restart window. Progress and the final exit code are delivered through durable marker files.

Do not use `git pull upstream main` on a production checkout.

## Documentation policy

The root project overview is maintained in exactly two language editions:
`README.md` (English) and `README.zh-CN.md` (Simplified Chinese). Their facts,
versions, commands, warnings, and project status must remain aligned.

Before every commit, contributors and coding agents review documentation impact
and update all affected project, release, user, reference, and developer docs in
the same change. Pure internal or test-only changes may require no documentation
edit, but the impact review is still mandatory. The detailed checklist lives in
`AGENTS.md`.

## Release notes

- [Louis release-notes index](LOUIS_RELEASE_NOTES.md)
- [Unreleased changes](docs/releases/LOUIS_UNRELEASED.md)
- [Louis Hermes Agent 0.19.0.4](docs/releases/LOUIS_0.19.0.4.md)
- [Louis Hermes Agent 0.19.0.3](docs/releases/LOUIS_0.19.0.3.md)
- [Louis Hermes Agent 0.19.0.2](docs/releases/LOUIS_0.19.0.2.md)
- [Louis Hermes Agent 0.19.0.1 baseline](docs/releases/LOUIS_0.19.0.1.md)
