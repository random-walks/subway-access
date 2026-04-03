# Releasing

This guide covers the current PyPI release workflow for `subway-access`.

## Release discipline

- Current release line: `0.1.x`
- Version source: git tags via Hatch VCS
- Preferred publish trigger: GitHub Release publication

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

## Trusted publishing setup

This repo uses trusted publishing through `.github/workflows/cd.yml` and the
`pypi` GitHub environment.

Before the first public release, complete these one-time steps:

1. Create or verify the PyPI account that will own `subway-access`, and enable
   2FA.
2. Create or verify a TestPyPI account if you want a dry run first.
3. Add a pending trusted publisher for project `subway-access` on TestPyPI and
   PyPI using:

- Owner: `random-walks`
- Repository: `subway-access`
- Workflow: `.github/workflows/cd.yml`
- Environment: `pypi`

4. Create the `pypi` environment in GitHub.
5. Set `PYPI_PUBLISH_ENABLED=true` when you are ready to allow publishing.

## Release path

The standard production path is:

1. create the final release tag, for example `0.1.0`
2. push the tag
3. optionally run the `CD` workflow against TestPyPI first
4. publish the matching GitHub Release
5. let the `release.published` trigger publish to real PyPI
