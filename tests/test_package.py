from __future__ import annotations

import importlib.metadata

import subway_access as m


def test_version() -> None:
    assert importlib.metadata.version("subway_access") == m.__version__
