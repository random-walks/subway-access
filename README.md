# subway-access

[![Actions Status][actions-badge]][actions-link]
[![Documentation Status][rtd-badge]][rtd-link]
[![PyPI version][pypi-version]][pypi-link]
[![PyPI platforms][pypi-platforms]][pypi-link]

Spatial analysis toolkit for evaluating NYC subway accessibility, reliability, and equity gaps.

## Status

This repository has been scaffolded as a public-ready package repo before implementation starts and now includes the exact seed docs that define the product target.

- Packaging, docs, CI, and release plumbing are present.
- The package is still in the planning and seeding phase.
- The target API surface is scaffolded with typed placeholders that raise `NotImplementedError`.

## Why This Exists

Official MTA and NYC data can tell you whether a station is accessible, and live feeds can tell you when equipment is out of service. What is much harder to answer is whether the system is reliably accessible in practice for the people who need it most.

`subway-access` is intended to combine:

- station accessibility status
- elevator and escalator outage data
- walk-distance catchments
- neighborhood demographics

into a reusable analysis toolkit rather than a one-off notebook.

## Planned Outputs

- station-level accessibility and reliability metrics
- tract-level accessibility gap outputs
- GeoJSON for maps
- CSV tables for policy analysis
- notebook-friendly borough walkthroughs

## Seeded Sources Of Truth

- `docs/notes/original-spec.md`: exact copied seed spec for `subway-access`
- `docs/notes/gap-explination.md`: exact copied gap analysis that explains why this project is still worth building
- `docs/agent-kickoff-todo.md`: kickoff plan for follow-on implementation agents
- `docs/agent-handoff-prompt.md`: paste-ready prompt for the next agent session

## Initial Scope

- ingest station and accessibility data
- build first-pass catchments
- join tract-level demographic variables
- produce a basic accessibility gap score
- document methodology clearly enough for external review

## Scaffolded Package Surface

The package now exposes planned-but-unimplemented modules so contributors can see the intended shape before building:

- `subway_access.loaders`
- `subway_access.processors`
- `subway_access.exporters`
- `subway_access.models`
- `subway_access.cli`

## Development

```bash
uv sync --group docs
uv run pytest
uv run mkdocs serve
```

## License

MIT.

<!-- prettier-ignore-start -->
[actions-badge]:            https://github.com/random-walks/subway-access/actions/workflows/ci.yml/badge.svg
[actions-link]:             https://github.com/random-walks/subway-access/actions
[github-discussions-badge]: https://img.shields.io/static/v1?label=Discussions&message=Ask&color=blue&logo=github
[github-discussions-link]:  https://github.com/random-walks/subway-access/discussions
[pypi-link]:                https://pypi.org/project/subway-access/
[pypi-platforms]:           https://img.shields.io/pypi/pyversions/subway-access
[pypi-version]:             https://img.shields.io/pypi/v/subway-access
[rtd-badge]:                https://readthedocs.org/projects/subway-access/badge/?version=latest
[rtd-link]:                 https://subway-access.readthedocs.io/en/latest/?badge=latest
<!-- prettier-ignore-end -->
