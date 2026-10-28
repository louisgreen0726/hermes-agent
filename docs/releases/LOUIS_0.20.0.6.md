# Louis Hermes Agent 0.20.0.6

Release date: 2026-10-28

Louis Hermes Agent 0.20.0.6 fixes duplicate continuation tails in long Telegram
streaming replies. It is an independently maintained Louis release, not an
official Nous Research release. The selectively integrated upstream baseline
remains Hermes Agent 0.20.0 (upstream release 2026.8.3).

## Telegram final delivery

- A final first send no longer forces the editable preview path. Native DM
  drafts have no message id, so their durable final can use rich rendering
  directly for tables and other eligible content.
- When that final send splits into multiple messages, the stream consumer
  recognizes both continuation-result contracts and skips the redundant
  finalize edit. The first chunk is no longer replaced with the full reply
  while already-delivered tail chunks remain visible.
- Ordinary text still splits at the legacy 4,096-character limit when needed.
  Eligible rich content can use the existing 32,768-character rich limit;
  rejected or unavailable rich delivery still falls back to MarkdownV2
  chunking without a duplicate tail.
- Progressive streaming previews, rich table rendering, reply routing, and
  final-delivery notification behavior remain available. No Telegram adapter
  limits were changed, and neither streaming nor rich messages was disabled.

## Compatibility

- No configuration, session-data, or dependency migration is required.
- Existing prompt-cache and tool-schema behavior is unchanged.
- The protected-update gate manifest remains unchanged; Telegram product
  regressions stay in focused validation and normal CI.
- CLI, Python, and Desktop release metadata advance only the Louis revision
  from 5 to 6. The selectively integrated upstream baseline is unchanged.

## Release metadata

- CLI version: `Louis-0.20.0.6`
- Python package version: `0.20.0+Louis.6`
- Desktop package version: `0.20.0-louis.6`
- Selectively integrated upstream baseline: Hermes Agent `0.20.0`, release
  `2026.8.3`

## Verification

- Focused Telegram and streaming regression validation: 363 tests across
  13 files, including real adapter rich delivery, native draft finalization,
  ordinary-text splitting, and rejected-rich fallback under an isolated
  `HERMES_HOME`. Bot API network calls are mocked; no live Telegram client
  acceptance test was performed.
- Protected-update gate plus CLI/Gateway version validation: 161 tests across
  11 files. JavaScript release-version validation: 2 tests.
- Isolated CLI version and Gateway/Telegram adapter import smoke checks passed.
  Ruff, README local file links, `git diff --check`, and offline lockfile
  consistency checks passed; dependency versions did not change.
- The changed Telegram guide passed MDX compilation. A full Docusaurus build
  and the full Python suite were not run.
- Production activation remains a separate protected-update step; publishing
  this source release does not restart an installed Gateway or Dashboard.

## Install and update

Existing installations can run `hermes update`. Managed Linux production hosts
can run `hermes-update-louis` to validate and activate Louis `origin/main`; the
updater restores previously running Gateway and Dashboard services. It never
synchronizes upstream directly into production. After activation, long Telegram
replies should appear as one eligible rich message or complete legacy chunks
without repeated tail content.
