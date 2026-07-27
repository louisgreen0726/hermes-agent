# Louis Hermes Agent 0.19.0.2

Release date: 2026-07-27

Louis Hermes Agent 0.19.0.2 is based on Nous Research Hermes Agent 0.19.0
(upstream release 2026.7.20). It is an independently maintained Louis release,
not an official Nous Research release. The upstream license and attribution
are preserved.

## Highlights

- Added the native `hermes manage` / `hermes-manage` management center for
  models, providers, Gateway operations, diagnostics, logs, setup, terminal
  chat, and protected Louis updates.
- Added safe inspection and consolidation of legacy one-provider-per-model
  custom endpoint layouts, including named-profile support and mode-`0600`
  backups.
- Stabilized generated systemd service PATH values across operator shells and
  Gateway runtime environments.

## Custom provider transport fix

- Custom endpoints created through the management flow now activate as
  `custom:<provider-slug>` instead of bare `custom`.
- Selecting an existing custom provider follows the same rule, including
  terminal-menu fallback paths.
- Endpoint URL, credentials, and `api_mode` remain owned by the named provider
  entry instead of being duplicated under `model`.
- Responses-compatible endpoints therefore retain `codex_responses` during
  runtime resolution, allowing stable request prefixes to use upstream prompt
  caching as intended.
- URL deduplication returns the canonical existing provider name, so activation
  cannot accidentally point at a different display-name slug.

## Verification

- The custom-provider management and runtime-resolution suites passed 223
  focused tests.
- The expanded Louis protected-update gate passed 982 tests across 29 files,
  including provider persistence, runtime resolution, distribution, packaging,
  updater rollback, Gateway, Telegram, and model-catalog coverage.
- A production-config Responses tool-call flow was validated before release at
  approximately 94.5% cached input tokens.

## Install and update

Existing installations can run `hermes update`. Managed Linux production hosts
can use `hermes-update-louis` for isolated candidate validation, rollback
backups, activation, and Gateway health checks.
