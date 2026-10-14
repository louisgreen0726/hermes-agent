# Louis Hermes Agent - Unreleased

Changes merged after `Louis-0.20.0.4` will be recorded here. The versioned
release record is [LOUIS_0.20.0.4.md](LOUIS_0.20.0.4.md).

## Pending

- Custom endpoint model catalogs no longer fail when `modalities.input` or
  another pricing alias contains a list or mapping. Endpoint context windows
  and nested scalar pricing remain available to model discovery and auxiliary
  compression instead of falling back to an empty catalog.
- Selectively backported upstream PR #137990 by @niyoh120, with Louis regression
  coverage for container-valued aliases and a real local `/v1/models` endpoint.
