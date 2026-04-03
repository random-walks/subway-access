# Contributing

## Development Setup

Install the default contributor environment:

```bash
make install-dev
```

Install the fuller environment, including docs and test extras:

```bash
make install
```

## Common Commands

```bash
make test
make lint
make docs
make docs-build
make ci
```

## Repository standards

- keep implemented behavior honest and small rather than speculative
- preserve explicit `NotImplementedError` placeholders for planned surfaces
- update docs alongside package exports
- keep fixture-backed tests deterministic and local by default

## Docs and API surface

- `docs/api.md` is generated from the top-level `subway_access` namespace
- `scripts/audit_public_api.py` checks that the documented public namespace and
  `__all__` exports stay aligned
- archived planning material lives under `docs/og-context/` and should not be
  used as the public docs navigation
