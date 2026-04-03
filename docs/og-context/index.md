# subway-access

`subway-access` is a Python-first toolkit for measuring how accessible NYC
subway service really is once you account for walking distance and neighborhood
need.

## Implemented in v0.1

The current release includes one real, deterministic happy path:

- load a small packaged station dataset plus ADA status rows
- generate first-pass Euclidean catchments from a fixed walking-speed assumption
- load tract-level demographic fixture data
- compute tract-level need and accessibility gap outputs
- export catchments to GeoJSON and gaps to CSV
- run the full flow from the `subway-access demo` CLI command

## Planned later

The project still aims to move beyond binary ADA labels toward reliability-aware
analysis, but the following surfaces remain intentionally unimplemented
placeholders:

- outage loading
- pedestrian network loading
- reliability scoring
- advanced routing and travel-time modeling
- broader station metrics exports

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
