Open the `subway-access` repo and treat the seeded docs as the source of truth,
especially `docs/notes/original-spec.md`, `docs/notes/gap-explination.md`,
`docs/mvp-roadmap.md`, and `docs/agent-kickoff-todo.md`. The repo already has a
typed placeholder package surface in `src/subway_access/` that marks planned
features as not implemented; preserve that pattern for anything you do not fully
build. Your goal is to move the project from scaffold to a credible v0.1
foundation by implementing the narrowest real happy path first: station plus ADA
status loading, first-pass catchment generation, tract-level demographic joins,
and a basic accessibility gap output, with tests and docs that clearly
distinguish what is implemented now from what remains planned.
