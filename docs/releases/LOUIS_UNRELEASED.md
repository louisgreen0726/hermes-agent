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
- Gateway context pins survive a named custom provider being resolved to the
  generic `custom` runtime id when `model.base_url` is omitted. Reset banners,
  message context checks, and session hygiene use the named runtime identity
  when available so the pin does not leak to another same-URL provider.
- Selectively backported upstream PR #133615 by @liuhao1024, adapted to the
  Louis route guard with regression coverage for pin retention and isolation.
