# Example Template

This folder is the canonical bootstrap template for new `subway-access`
examples.

Copy it to a new semantic slug, then replace the placeholders in `main.py`,
`pyproject.toml`, and this README with the story for your new example.

## Folder Contract

Every well-formed example should include:

- `pyproject.toml`
- `.gitignore`
- `README.md`
- `main.py`
- optional tracked `reports/`
- optional ignored `cache/`
- optional ignored `artifacts/`

## Shipping Checklist

- the example imports only `subway_access.*`
- `uv sync` and `uv run python main.py` work from the example folder
- the example fetches or reuses official public-data cache files rather than
  packaged synthetic fixtures
- ignored outputs stay in `cache/` or `artifacts/`
- tracked outputs stay under `reports/`
- markdown links use explicit relative paths that render on GitHub
