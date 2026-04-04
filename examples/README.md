# Examples

`examples/` contains self-contained consumer projects built around official
public data, local cache reuse, and tracked reports.

## Contract

Every example lives in its own semantic-slug folder such as
`examples/fetch-borough-snapshot/`.

The canonical starting point for new work is `examples/example-template/`.

Each example must:

- include its own `pyproject.toml`
- include its own `README.md`
- include its own `.gitignore`
- provide a single `main.py` entrypoint
- import only `subway_access.*` as an installed package
- keep caches under `cache/`
- keep scratch and intermediate outputs under ignored `artifacts/`
- use an optional tracked `reports/` folder for markdown and report figures that
  should stay in git
- avoid shared cross-example `utils/`, `data/`, or `output/` directories
- fetch or reuse official-data cache snapshots instead of relying on packaged
  synthetic fixtures

Examples are intentionally not part of the main CI runtime path. They are
consumer references, not package fixtures.

## Start Here

- `examples/fetch-borough-snapshot/`: first live/official cache-building example
- `examples/borough-gap-analysis/`: borough-scale tract gap story on real public
  data
- `examples/outage-reliability-report/`: real monthly availability and
  reliability story
- `examples/network-access-comparison/`: Euclidean vs network comparison
  workflow
- `examples/example-template/`: scaffold for future examples

## Local Repo Usage

Each example is its own `uv` project. From an example folder:

```bash
uv sync
uv run python main.py
```

The local `pyproject.toml` points to the repo root as an editable path
dependency so the example imports `subway_access` exactly the way an external
consumer would while still tracking local source edits.
