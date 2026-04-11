# Enhanced Seeds

This directory holds researched ADA upgrade data and per-station research files
for 157 currently accessible NYC subway stations.

## Current coverage

**100 of 157 stations (63.7%)** have sourced upgrade years traced to MTA press
releases, Governor's announcements, MTA Capital Program records, Wikipedia
station articles, and news coverage. The remaining 57 stations — primarily Key
Station Program stations from the 1990s--2010s — have null upgrade years because
per-station completion dates were not publicly documented. A FOIL request to the
MTA for the complete Key Station Program schedule would close this gap.

## What's here

### `upgrade_templates/`

Per-borough CSV files listing every currently ADA-accessible subway station.
Each row has:

- **Populated columns** — station ID, name, borough, coordinates, routes, line,
  division, structure, current ADA status (from the MTA station catalog API),
  and researched fields where available: `upgrade_year`, `upgrade_source`,
  `capital_program`, and others.
- **Empty columns** — fields still awaiting data for the 57 unresolved stations.

### `research/`

Per-station research folders (`{station_id:03d}-{slug}/`) each containing:

- **`data.json`** — structured data matching the CSV schema (upgrade year,
  source, capital program, cost, contractor, features, notes).
- **`research.md`** — citations, links to MTA press releases, Wikipedia
  articles, and news coverage documenting how each upgrade year was determined.

### How to fill them in

1. **FOIL request** — File a Freedom of Information Law request with the MTA for
   Capital Program project completion records related to ADA station
   accessibility upgrades.
2. **MTA Capital Program dashboard** — Cross-reference the MTA's published
   capital program reports and board materials.
3. **News / public documents** — Search press releases, news articles, and NYC
   Council hearing transcripts for station opening dates.
4. **AI-driven enhancement** — Use the empty templates as a structured starting
   point for LLM-assisted research, filling in rows one at a time from public
   sources.

### How the pipeline uses them

The library's `build_upgrade_timeline()` function (in
`src/subway_access/temporal/_upgrade_timeline.py`) already accepts a
`known_upgrades` parameter — a `dict[str, int]` mapping station IDs to upgrade
years. To use enhanced seeds:

1. Read the CSV(s) from this directory.
2. Filter to rows where `upgrade_year` is filled in.
3. Build a `{station_id: upgrade_year}` dict.
4. Pass it as `known_upgrades` to `build_upgrade_timeline()`.

This replaces the MD5-hash-based synthetic timeline with real dates, producing a
more accurate treatment/control assignment for the difference-in-differences
analysis.

## Regenerating templates

```bash
python scripts/real_upgrade_years_template.py
```

This fetches the latest MTA station catalog and regenerates the template CSVs
with current station metadata (preserving any empty FOIA columns).
