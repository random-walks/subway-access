See the [Scientific Python Developer Guide][spc-dev-intro] for broader
background on Python package maintenance.

[spc-dev-intro]: https://learn.scientific-python.org/development/

# Quick development

The fastest way to start with development is to use the repo Makefile:

```bash
make install-dev
make test
make lint
make docs-build
make ci
```

`nox` is still available for repository hygiene hooks and focused sessions, but
`make` is the primary local interface so it matches CI.

# Setting up a development environment manually

You can set up a development environment by running:

```bash
uv sync
```

# Pre-commit

Install `pre-commit` to run the same hygiene checks used in CI:

```bash
uv tool install pre-commit # or brew install pre-commit on macOS
pre-commit install
```

You can also run `pre-commit run --all-files`.

# Testing

Use pytest to run the unit checks:

```bash
make test
```

# Coverage

Use pytest-cov to generate coverage reports:

```bash
uv run pytest --cov=subway_access
```

# Building docs

You can build and serve the docs using:

```bash
make docs
```

You can build the docs only with:

```bash
make docs-build
```
