# Louis Hermes Agent 0.20.0.5

Release date: 2026-10-14

Louis Hermes Agent 0.20.0.5 fixes custom endpoint model metadata parsing and
Gateway context-pin retention. It is an independently maintained Louis release,
not an official Nous Research release. The selectively integrated upstream
baseline remains Hermes Agent 0.20.0 (upstream release 2026.8.3).

## Custom endpoint metadata

- List- and mapping-valued keys such as `modalities.input` are ignored as
  pricing aliases instead of raising `TypeError` and invalidating the entire
  `/models` catalog.
- Nested scalar pricing, including zero-valued prices, remains available.
- Model discovery and main/auxiliary context resolution can use the endpoint's
  reported window rather than falling back to 256K or a model-family limit.
- `deepseek-v4.1-flash` and `deepseek-flash` have a defensive 1,000,000-token
  fallback; configured overrides and endpoint metadata retain precedence.

## Gateway context pins

- `model.context_length` survives `custom:<name>` resolving to the generic
  `custom` runtime provider when the URL lives only in `custom_providers`.
- Reset banners, message context checks, and session hygiene use the same route
  guard, preferring the requested named runtime provider when available.
- Identifiable different named providers still clear the pin, including
  providers sharing one relay URL. Explicit endpoint and model mismatches
  continue to clear it.
- This prevents these parsing and pin-loss failures from causing premature
  compression on a correctly configured large-context route.

## Compatibility and attribution

- No configuration, session-data, or dependency migration is required.
- Existing prompt-cache and tool-schema behavior is unchanged.
- Selectively backported upstream
  [PR #137990](https://github.com/NousResearch/hermes-agent/pull/137990) by
  @niyoh120 and
  [PR #133615](https://github.com/NousResearch/hermes-agent/pull/133615) by
  @liuhao1024, preserving authorship and adapting the route fix to Louis.
- The protected-update release gate remains unchanged; product regressions
  stay in focused validation and normal CI.

## Release metadata

- CLI version: `Louis-0.20.0.5`
- Python package version: `0.20.0+Louis.5`
- Desktop package version: `0.20.0-louis.5`
- Selectively integrated upstream baseline: Hermes Agent `0.20.0`, release
  `2026.8.3`

## Verification

- Focused Python validation: 169 tests across model metadata, route mismatch,
  Gateway session-info, and Louis distribution metadata.
- JavaScript release-version validation: 2 tests.
- The endpoint regression uses a real local HTTP server under an isolated
  `HERMES_HOME`, checking that reported limits and the complete model catalog
  survive modality lists without an explicit context pin.
- README local file links, `git diff --check`, and the unchanged dependency
  lock resolution were checked. The changed model guide passed MDX compilation;
  a full Docusaurus build was not run.
- Full-suite and protected-update gate runs were intentionally not part of
  this focused release validation. Production activation remains a separate
  protected-update step.

## Install and update

Existing installations can run `hermes update`. Managed Linux production hosts
can run `hermes-update-louis` to validate and activate Louis `origin/main`; the
updater restores previously running Gateway and Dashboard services. It never
synchronizes upstream directly into production. After updating, Telegram
`/reset` should report the retained context pin, for example
`Context: 1.0M tokens (config)` for a matching 1M named custom route.
