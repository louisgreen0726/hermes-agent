# Louis Hermes Agent 0.19.0.3

Release date: 2026-07-27

Louis Hermes Agent 0.19.0.3 is based on Nous Research Hermes Agent 0.19.0
(upstream release 2026.7.20). It is an independently maintained Louis release,
not an official Nous Research release. The upstream license and attribution
are preserved.

## Protected updater correctness

- The Louis regression list now lives in the candidate-owned
  `scripts/louis-release-tests.txt` manifest.
- A production updater loaded from an older release therefore validates a new
  candidate with the candidate's current gate on both test passes, rather than
  using the test list embedded in the older worker.
- The existing worker remains responsible for locking, fast-forward checks,
  backup bundles, dependency rollback, worktree cleanup, and Gateway service
  switching. Candidate updater code is not executed in the middle of an
  activation transaction.

## Manifest and runtime safety

- Manifest entries must be unique, whitespace-free relative `tests/...` paths
  that resolve to regular files inside the candidate worktree. Missing, empty,
  duplicate, absolute, traversing, and escaping entries fail before tests or
  dependency changes begin.
- An already-current checkout now verifies its editable source before being
  reported healthy, while continuing to repair the management launcher.
- Newly activated and already-current installations run non-network smoke
  checks for CLI and Gateway imports, editable source ownership, and the Louis
  version command. These checks do not call a model endpoint or consume tokens.

## Version and User-Agent consistency

- `model.default_headers` and per-provider `extra_headers` support
  `User-Agent: Hermes-Agent/{hermes_version}`. The placeholder resolves from
  `hermes_cli.__version__` for both main-agent and auxiliary model clients, so
  the header follows each Louis update without rewriting `config.yaml`.
- Placeholder expansion is limited to `User-Agent`; credential-bearing and
  provider-specific headers remain byte-for-byte under user control.
- The Desktop package and workspace lock now derive their SemVer-compatible
  version from the Python package release instead of remaining at `0.17.0`.

## Verification

- The updater integration suite exercises candidate-manifest ownership,
  invalid-manifest rejection, no-op editable verification, successful
  activation, and rollback after Gateway startup failure.
- The release gate passed 1,026 tests across 32 files covering provider routing,
  versioned request headers, distribution and packaging, protected updates,
  Gateway behavior, Telegram delivery, and model catalog integrity.

## Install and update

Existing installations can run `hermes update`. Managed Linux production hosts
can use `hermes-update-louis` for isolated candidate validation, rollback
backups, activation, runtime smoke checks, and Gateway health checks.
