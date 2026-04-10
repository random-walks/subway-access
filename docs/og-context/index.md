# subway-access

> This section contains internal project context and agent-oriented notes. It is
> kept in the repo for maintainers and automation, not as stable user-facing
> documentation.

`subway-access` is a Python-first toolkit for measuring how accessible NYC
subway service really is once you account for walking distance and neighborhood
need.

## Implemented

The package now includes a full pipeline from live data through research-grade
analysis:

- fetch official MTA station, ADA status, elevator availability, equipment,
  entrance, and GTFS-Pathways data from public APIs
- fetch ACS 5-year tract-level demographics
- cache reusable local snapshot bundles per study area
- generate Euclidean and OSM-network walk catchments
- compute tract-level need and accessibility gap outputs via factor pipeline
- compute rolling station reliability from outage history
- build station-level metrics combining coverage, need, and reliability
- export catchments to GeoJSON, gaps to CSV, and station metrics to CSV/GeoJSON
- temporal panel infrastructure for longitudinal causal analysis
- run the full flow from `subway-access fetch-snapshot` and
  `subway-access analyze-snapshot` CLI commands

## Still planned

- public-facing notebook and dashboard reporting
- fully polished public dashboard UX

## Project Focus

- move past binary ADA labels toward reliability-aware analysis
- connect station accessibility with who lives nearby
- keep outputs useful for both policy work and reproducible research
- make borough-scale workflows easy before expanding to richer dashboards

## Read Next

- [Project brief](project-brief.md)
- [Data sources](data-sources.md)
- [MVP roadmap](mvp-roadmap.md)
- [Python API](api.md)
- [Agent kickoff TODO](agent-kickoff-todo.md)
- [Agent handoff prompt](agent-handoff-prompt.md)
- [Original seed spec](notes/original-spec.md)
- [Gap explination](notes/gap-explination.md)
