# Examples

`examples/` contains self-contained consumer projects instead of one-off repo
scripts or notebooks.

## Contract

Every example lives in its own semantic-slug folder such as
`examples/quickstart-demo/`.

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
- run from packaged sample data by default unless the README documents a live
  dependency clearly

Examples are intentionally not part of the main CI runtime path. They are
consumer references, not package fixtures.

## Start Here

- `examples/quickstart-demo/`: smallest end-to-end walkthrough
- `examples/borough-gap-analysis/`: report-focused tract gap story
- `examples/catchment-map/`: mapping-oriented GeoJSON export workflow
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
