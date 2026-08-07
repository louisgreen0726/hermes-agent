# Louis Hermes Agent 0.20.0.3

Release date: 2026-08-07

Louis Hermes Agent 0.20.0.3 makes protected production updates restart the
Dashboard automatically when it was running before activation. It is an
independently maintained Louis release, not an official Nous Research release.
The selectively integrated upstream baseline remains Hermes Agent 0.20.0
(upstream release 2026.8.3).

## Managed service restoration

- The updater records the running state of both Gateway and Dashboard before
  changing dependencies or the production checkout.
- Services that were running are stopped for activation, then restarted from
  the validated release. Gateway starts first and Dashboard follows after the
  Gateway has passed its PID stability window.
- A service that was inactive before the update remains inactive afterward.
- If activation or service startup fails, the updater rolls back the source and
  Python environment, then restores both services to their prior running state.
- Dry runs continue to leave the production checkout, dependencies, Gateway,
  and Dashboard unchanged.

## Compatibility and scope

- No configuration migration or systemd unit change is required.
- Existing `hermes-dashboard.service` and `hermes-gateway.service` units remain
  the managed service boundary.
- The updater does not start services that operators intentionally left
  inactive.

## Release metadata

- CLI version: `Louis-0.20.0.3`
- Python package version: `0.20.0+Louis.3`
- Desktop package version: `0.20.0-louis.3`
- Selectively integrated upstream baseline: Hermes Agent `0.20.0`, release
  `2026.8.3`

## Verification

- The updater passed shell syntax validation.
- The focused updater suite passed 11 tests, including active and inactive
  Dashboard paths, startup ordering, PID stability, failure rollback, and
  restoration of both managed services.
- The related protected-update suite passed 140 tests across seven files.
- The Louis release gate passed all 2,828 tests across 79 files with no
  failures.

## Install and update

Existing installations can run `hermes update`. Managed Linux production hosts
can run `hermes-update-louis --dry-run` before an explicit
`hermes-update-louis` activation. The updater remains Louis-owned and ff-only;
it does not synchronize from the upstream remote.
