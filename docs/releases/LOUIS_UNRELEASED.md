# Louis Hermes Agent - Unreleased

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
