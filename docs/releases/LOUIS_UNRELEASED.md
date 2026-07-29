# Louis Hermes Agent - Unreleased

## Independent project documentation

- The root project overview now presents Louis Hermes Agent as an independent
  derivative with its own roadmap, release process, production branch, and
  update source while preserving Nous Research attribution and the MIT license.
- Root README maintenance is intentionally limited to English and Simplified
  Chinese editions, with semantic parity required between them.
- Repository Codex guidance now requires a documentation-impact review before
  every commit and maps behavior, release, configuration, and contributor
  changes to their authoritative documentation surfaces.
- The tracked Codex project configuration raises the project-instruction limit
  so the root and Desktop `AGENTS.md` files load together instead of being
  truncated at the default limit.

## Named custom provider isolation

- Custom provider names are now durable identities. Different names keep
  separate models, API modes, `.env` key references, and credential pools even
  when they share one relay `base_url`.
- Re-saving the same name updates that provider, including endpoint, model, and
  credentials. URL-only matching remains for unnamed and legacy callers.
- Credential-pool validation now carries the requested custom provider through
  agent initialization, 401/429 recovery, and cross-turn fallback restoration.
  Both legacy `custom_providers:` names and `providers:` mapping keys resolve to
  the exact configured pool and URL before a credential can be used.

## Verification

- End-to-end CLI coverage configures two model-specific keys on one relay and
  verifies independent persistence and runtime resolution.
- Custom-provider, runtime, credential-pool, fallback, Dashboard, and
  delegation regression suites pass with the new identity invariant.
