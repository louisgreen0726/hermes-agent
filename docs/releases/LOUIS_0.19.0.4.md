# Louis Hermes Agent 0.19.0.4

Release date: 2026-07-28

Louis Hermes Agent 0.19.0.4 is based on Nous Research Hermes Agent 0.19.0
(upstream release 2026.7.20). It is an independently maintained Louis release,
not an official Nous Research release. The upstream license and attribution
are preserved.

## WebDAV cloud backup and restore

- `hermes backup webdav` now provides redacted status, capability testing,
  immediate upload, cross-device listing, and rollback-protected restore.
- Backups remain the existing complete raw Hermes ZIP format. They are not
  encrypted and include `.env`, credentials, sessions, skills, and other local
  state, so the configuration flow requires an explicit first-use warning.
- Credentials stay in the base Hermes `.env`; URL, remote path, device name,
  schedule, retention, and enablement stay in `config.yaml`.
- Remote backups are isolated by device UUID, uploaded through `.part` files,
  finalized with MOVE when supported, and accepted for restore only after a
  complete size and SHA-256 manifest is present.
- The client validates TLS normally, rejects credential-bearing URLs and path
  traversal, bounds retries, limits redirects, supports anonymous WebDAV, and
  falls back to a final PUT when MOVE is unavailable.

## Automatic backup and recovery safety

- `hermes manage` includes a Chinese WebDAV configuration and recovery menu
  with hidden password entry, explicit anonymous mode, connection testing,
  immediate backup, backup browsing, and automatic-backup controls.
- The default schedule is daily at 03:00 local time with the newest 14 complete
  backups retained per device. The Gateway runs one `no_agent` Cron task, so
  scheduled backups do not call a model or consume tokens.
- Cross-process locking prevents manual and scheduled uploads from overlapping.
  Successful scheduled runs stay quiet; failures are persisted and can notify
  the configured Gateway home channel.
- Restore validates the manifest, size, digest, ZIP integrity, version, and
  member paths before modifying local data. It creates a full rollback ZIP,
  stops and restores the Gateway state, preserves the destination device's
  WebDAV identity and credentials, and automatically rolls back failed imports.
- Existing local `hermes backup` ZIPs and `hermes import` behavior remain
  compatible; their implementations now return explicit results for safe
  orchestration by the WebDAV workflow.

## Dashboard light theme and interaction fix

- `Hermes Light (Large)` is now the default only when no Dashboard theme was
  explicitly selected. Hermes Teal, Hermes Teal (Large), and all other themes
  remain available and existing preferences are preserved.
- The new theme keeps the Teal Large sidebar, spacing, 18px typography, mobile
  drawer breakpoint, and route structure while using a white canvas, dark text,
  teal actions, restrained surfaces, accessible borders, and a light terminal.
- Built-in and user themes receive matching first-paint bootstrap variables, so
  explicit dark-theme users no longer see a light flash before React mounts.
- Sidebar hover highlights now render behind icons and labels instead of
  covering them with the light accent surface. Navigation, system actions, and
  collapsed footer controls keep readable foreground contrast while hovered.

## Complete Simplified Chinese Dashboard

- Every built-in Dashboard page and shared component now routes visible labels,
  tooltips, placeholders, dialogs, toasts, ARIA labels, and error prefixes
  through the locale catalog instead of English component fallbacks.
- Configuration fields expose stable Chinese names, descriptions, and enum
  labels while retaining the original dot paths and stored values. Search
  matches both translated metadata and raw keys.
- Dates, times, relative time, and numbers follow the selected `zh-CN` locale.
  Required product, protocol, model, provider, plugin, path, and log text remains
  in its original form.
- A static i18n check rejects undeclared visible English in built-in TSX files
  and enforces complete Simplified Chinese keys with an explicit technical-term
  allowlist.

## Model picker resilience

- models.dev requests now use separate bounded connect and read timeouts.
- When the registry is offline and no disk cache exists, an empty failure is
  cached briefly so one picker render does not repeat the same network timeout
  once per provider. Explicit refresh still bypasses the backoff.

## Verification

- Focused Python regression coverage passed 753 tests for WebDAV, local
  backup/import, Dashboard APIs, the Louis manager, and models.dev behavior.
- The Dashboard check passed type checking, the static i18n gate, 112 Vitest
  tests across 19 files, ESLint with no errors, and the production build.
- The protected Louis release manifest now includes the new WebDAV, backup,
  Dashboard, models.dev, no-agent Cron, and cross-process Cron lock suites.
- The canonical per-file release gate passed 1,779 tests across all 38 manifest
  files with zero failures.

## Install and update

Existing installations can run `hermes update`. Managed Linux production hosts
can use `hermes-update-louis` for isolated candidate validation, rollback
backups, activation, runtime smoke checks, and Gateway health checks.

On a new device, install Hermes, configure WebDAV, run
`hermes backup webdav list`, and restore the selected backup. Treat every remote
ZIP as sensitive because this release intentionally does not add backup
encryption or a recovery key.
