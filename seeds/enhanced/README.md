# Enhanced Seeds

This directory holds research-grade data templates and enhanced seed files
for replacing the synthetic (MD5-hashed) ADA upgrade timeline with real
historical data.

## What's here

### `upgrade_templates/`

Per-borough CSV templates listing every currently ADA-accessible subway
station. Each row has:

- **Populated columns** — station ID, name, borough, coordinates, routes,
  line, division, structure, and current ADA status (all sourced from the
  live MTA station catalog API).
- **Empty columns** — fields that would come from a FOIL request, MTA
  Capital Program reports, or manual research:
  `upgrade_year`, `upgrade_source`, `capital_program`, `project_id`,
  `contract_number`, `construction_start_date`, `construction_end_date`,
  `project_cost_millions`, `contractor`, `accessibility_features`, `notes`.

### How to fill them in

1. **FOIL request** — File a Freedom of Information Law request with the
   MTA for Capital Program project completion records related to ADA
   station accessibility upgrades.
2. **MTA Capital Program dashboard** — Cross-reference the MTA's published
   capital program reports and board materials.
3. **News / public documents** — Search press releases, news articles, and
   NYC Council hearing transcripts for station opening dates.
4. **AI-driven enhancement** — Use the empty templates as a structured
   starting point for LLM-assisted research, filling in rows one at a time
   from public sources.

### How the pipeline uses them

The library's `build_upgrade_timeline()` function (in
`src/subway_access/temporal/_upgrade_timeline.py`) already accepts a
`known_upgrades` parameter — a `dict[str, int]` mapping station IDs to
upgrade years. To use enhanced seeds:

1. Read the CSV(s) from this directory.
2. Filter to rows where `upgrade_year` is filled in.
3. Build a `{station_id: upgrade_year}` dict.
4. Pass it as `known_upgrades` to `build_upgrade_timeline()`.

This replaces the MD5-hash-based synthetic timeline with real dates,
producing a more accurate treatment/control assignment for the
difference-in-differences analysis.

## Regenerating templates

```bash
python scripts/real_upgrade_years_template.py
```

This fetches the latest MTA station catalog and regenerates the template
CSVs with current station metadata (preserving any empty FOIA columns).
