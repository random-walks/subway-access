# Releasing

This guide covers the current PyPI release workflow for `subway-access`.

## Release discipline

- Version source: git tags via Hatch VCS
- Preferred publish trigger: GitHub Release publication (fires
  `release: published` → PyPI)

Patch releases in the `0.1.x` line should stay backward-compatible. Cut a new
minor release when the documented workflow, dependency expectations, or public
analysis surface expands in a meaningful way.

## Pre-release checks

Before tagging a release, run:

```bash
make ci
make audit
make docs-build
make smoke-dist
```

That covers:

- lint, typing, and public API checks
- docs build validation
- source and wheel builds
- installed-wheel smoke testing for the CLI and cached real-data workflow

### README / PyPI hero image

The project README and [docs home](index.md) show a wide map at
`docs/images/subway-access-hero.png`. PyPI renders the image via a **raw GitHub
URL** in `README.md` (pointing at `main`); after you change the PNG, merge to
`main` so the link matches. To refresh the graphic, run the
`examples/about-the-data` example and copy
`reports/figures/map-library-header-horizontal.png` over
`docs/images/subway-access-hero.png`.

## Publishing configuration

This repo publishes through `.github/workflows/cd.yml` using GitHub trusted
publishing and the `pypi` environment.

Repository-admin setup such as PyPI project creation, trusted publisher
registration, and Read the Docs project linking is managed manually outside the
repo and is intentionally not duplicated here.

## Release path

The standard production path is:

1. create the final release tag on `main`, for example `0.3.0`
2. `git push origin <tag>`
3. publish the GitHub Release for that tag (this triggers CD → PyPI when trusted
   publishing is enabled)

**CLI (same outcome as the Releases UI):** with the
[GitHub CLI](https://cli.github.com/) authenticated (`gh auth login`),

```bash
gh release create <tag> --verify-tag --title "<tag>" --generate-notes
```

Example after pushing tag `0.3.0`:

```bash
git push origin 0.3.0
gh release create 0.3.0 --verify-tag --title "0.3.0" --generate-notes
```

Optionally run the `CD` workflow against TestPyPI first (workflow dispatch).
Then confirm the `release.published` workflow run finished and the artifact is
on PyPI.

If you prefer publishing without `gh release`, run the `CD` workflow from the
same tag with:

- `publish=true`
- `repository=pypi`

## Post-release verification

After the release lands on PyPI:

1. Install `subway-access` from PyPI in a clean environment.
2. Run `subway-access --help`.
3. Run
   `subway-access fetch-snapshot --geography borough --value Manhattan --cache-dir cache/manhattan`.
4. Run
   `subway-access analyze-snapshot --cache-dir cache/manhattan --output-dir artifacts/manhattan`.
5. Confirm the PyPI project page renders the README correctly.
6. Confirm the docs site, GitHub release notes, and repo sidebar links reflect
   the release.
