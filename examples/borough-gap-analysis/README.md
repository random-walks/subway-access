# Borough Gap Analysis

This example turns the packaged sample data into a borough-level tearsheet.

It keeps the workflow small and deterministic while showing how to filter the
analysis story to one geography.

## Run

```bash
uv sync
uv run python main.py
```

## Outputs

- `artifacts/manhattan-accessibility-gaps.csv`
- `reports/borough-gap-analysis-tearsheet.md`
