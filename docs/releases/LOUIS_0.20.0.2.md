# Louis Hermes Agent 0.20.0.2

Release date: 2026-08-07

Louis Hermes Agent 0.20.0.2 completes the isolation of named custom providers
that share one relay URL. It is an independently maintained Louis release, not
an official Nous Research release. The selectively integrated upstream baseline
remains Hermes Agent 0.20.0 (upstream release 2026.8.3).

## Named custom provider isolation

- A configured name such as `custom:relay-a` is now retained as the canonical
  route identity even when the runtime billing class is the generic `custom`
  provider.
- Model discovery, in-memory catalogs, disk caches, learned context limits, and
  endpoint metadata are scoped by that route together with its credential and
  transport fingerprint. Reopening a model picker therefore cannot show a
  sibling provider's list merely because both providers use the same URL.
- Credential-pool lookup fails closed when URL-only matching would be ambiguous.
  Named pools continue to rotate only credentials belonging to that route.
- Model switching, fallback, compression, session restore, background review,
  cron, Gateway, TUI, ACP, Feishu, and MoA paths preserve the selected route's
  API key, headers, request overrides, TLS policy, API mode, and transport.
- Provider-generated `extra_body` values are rebound during a live switch while
  caller-supplied request overrides remain intact. Failed switches restore the
  complete prior runtime state.

## Compatibility and scope

- No configuration migration is required. Existing named provider entries keep
  their current `custom_providers` or `providers` representation.
- Legacy unnamed callers retain URL-based matching when the endpoint resolves
  unambiguously; ambiguous shared URLs no longer guess between credentials.
- The fix does not change model tool schemas, conversation history, or the
  system prompt, so per-conversation prompt caching remains stable.

## Release metadata

- CLI version: `Louis-0.20.0.2`
- Python package version: `0.20.0+Louis.2`
- Desktop package version: `0.20.0-louis.2`
- Selectively integrated upstream baseline: Hermes Agent `0.20.0`, release
  `2026.8.3`

## Verification

- All changed Python modules passed bytecode compilation.
- The focused named-provider suite passed 87 tests.
- A multi-path regression batch covering provider resolution, model switching,
  credential pools, fallback, Gateway, TUI, ACP, cron, context engines, caches,
  and MoA passed 227 tests.
- The Louis release gate passed all 2,827 tests across 79 files with no
  failures, including the newly protected same-relay provider paths.

## Install and update

Existing installations can run `hermes update`. Managed Linux production hosts
can run `hermes-update-louis --dry-run` before an explicit
`hermes-update-louis` activation. The updater remains Louis-owned and ff-only;
it does not synchronize from the upstream remote.
