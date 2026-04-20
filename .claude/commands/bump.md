---
description:
  Roll CHANGELOG [Unreleased] → new version section + stage. Arg = patch | minor
  | major (default patch). Version is derived from git tags via hatch-vcs, so
  only CHANGELOG needs editing.
---

Run these in order:

1. Parse `$ARGUMENTS`. Valid values: `patch` (default if omitted), `minor`,
   `major`.
2. Read the latest version from
   `git tag --list 'v*' --sort=-v:refname | head -1` (strip the leading `v`). If
   no tag exists, use `0.0.0`.
3. Compute the new version per SemVer:
   - patch → `X.Y.(Z+1)`
   - minor → `X.(Y+1).0`
   - major → `(X+1).0.0`
4. In `CHANGELOG.md`:
   - Find the `## [Unreleased]` section.
   - Rename it to `## [<new-version>] — <today's date in YYYY-MM-DD>`.
   - Insert a fresh empty `## [Unreleased]` block above it with subheadings:
     `### Added / ### Changed / ### Fixed / ### Deprecated / ### Security`.
   - Update the compare-link footer:
     `[unreleased]: https://github.com/random-walks/subway-access/compare/v<new>...HEAD`
     and `[<new>]: ...compare/v<prev>...v<new>`.
5. Stage `CHANGELOG.md` with `git add CHANGELOG.md`.
6. Print a summary: old version, new version, number of entries carried over,
   next steps (`git commit -m "release: v<new>"`, then `git tag v<new>`, then
   push the tag to trigger the CD workflow).

Do NOT commit or tag — leave both to the human.

The package version is derived at build time from git tags via `hatch-vcs`;
`src/subway_access/_version.py` is auto-generated. Do not hand-edit
`_version.py`.

If `$ARGUMENTS` is invalid, print usage and exit.
