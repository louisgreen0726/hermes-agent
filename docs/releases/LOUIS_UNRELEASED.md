# Louis Hermes Agent - Unreleased

Changes merged after `Louis-0.20.0.1` will be recorded here. The versioned
release record is [LOUIS_0.20.0.1.md](LOUIS_0.20.0.1.md).

## Pending

- Fixed the remaining same-relay isolation gaps for named custom providers.
  Model catalogs, learned context limits, endpoint metadata, and disk caches
  are now scoped by the canonical provider route plus its credentials and
  transport instead of by `base_url` alone. Credential-pool selection fails
  closed when a shared URL is ambiguous, and fallback, model switching, and
  session restore keep the named route's API key, headers, request options,
  and transport. Model lists therefore remain correct after reopening the
  picker without a refresh, and later calls cannot drift into a sibling route.
