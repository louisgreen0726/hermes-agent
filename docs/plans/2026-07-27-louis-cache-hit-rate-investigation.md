# Louis Cache Hit Rate Investigation

Status: Unconfirmed investigation backlog

This plan was extracted from the archived 2026-07-27 WIP handoff. It records a
reported possibility that cache hit rate degraded, but no current reproduction
or root cause has been established. Do not treat it as a confirmed regression.

## Question To Answer

Determine whether the observed change is:

1. a real provider-side prompt-cache miss,
2. loss or mistranslation of cache usage fields,
3. a dashboard calculation issue, or
4. expected cold-cache or request-prefix churn.

## Evidence To Record

- Provider, exact model ID, API mode, and base URL identity.
- Before/after time window and representative session IDs.
- Redacted raw usage JSON from the provider or relay.
- Request-prefix hashes for controlled repeated requests.
- Hermes usage rows and the UI or dashboard where the rate was observed.

Never preserve API keys, authorization headers, cookies, access tokens, or
other reusable credentials in investigation artifacts.

## Controlled Reproduction

1. Use the same provider, model, API mode, credentials, system prompt, tools,
   and user payload for two requests with a sufficiently large identical
   prefix.
2. Capture raw usage from both responses.
3. Repeat the pair directly against the relay and through Hermes.
4. Compare OpenAI-compatible
   `usage.prompt_tokens_details.cached_tokens`, Anthropic-compatible
   `cache_read_input_tokens`, and `cache_creation_input_tokens` with Hermes
   `cache_read_tokens` and `cache_write_tokens` accounting.
5. Repeat after a Gateway restart to distinguish cold-cache effects from
   persistent behavior.

## Prefix Stability Checks

- System-prompt or date/environment block changes.
- Dynamic tool-schema content or ordering changes.
- Memory, skill, persona, and project-context changes.
- Context compression or session resume.
- Provider, credential-pool, model, or API-mode rotation.
- Relay behavior that rewrites requests or omits usage details.

## Primary Code Paths

- `run_agent.py::_anthropic_prompt_cache_policy()`
- `agent/agent_runtime_helpers.py::anthropic_prompt_cache_policy()`
- Cache-control injection around the prepared system message.
- Usage normalization and persistence paths discoverable with:

```bash
rg -n "cached_tokens|cache_read|cache_write|cache_control|prompt_cache" \
  run_agent.py agent hermes_state.py providers.py tests
```

Discover the current SQLite schema before querying state; do not assume table
or column names from an older build.

## Required Regression Coverage

- A test for each relevant raw provider usage-field normalization path.
- A test proving stable cache-control placement and request-prefix construction
  across repeated turns.
- A separate test for the displayed cache-rate formula if raw accounting is
  correct but the UI result is not.

Close this investigation only with a current reproduction and an evidenced
root cause, or with controlled results showing that Hermes behavior is correct.
