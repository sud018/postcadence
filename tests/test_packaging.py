"""Packaging: a new template or script must not silently go missing from an install."""
from __future__ import annotations

import importlib
from fnmatch import fnmatch
from pathlib import Path

import pytest

tomllib = pytest.importorskip("tomllib")     # standard library from Python 3.11

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_every_template_and_static_file_is_packaged():
    patterns = PYPROJECT["tool"]["setuptools"]["package-data"]["web"]
    web = ROOT / "web"
    files = [p.relative_to(web).as_posix()
             for folder in ("templates", "static") for p in (web / folder).rglob("*") if p.is_file()]

    missing = [f for f in files if not any(fnmatch(f, pattern) for pattern in patterns)]
    assert missing == [], f"add these to [tool.setuptools.package-data]: {missing}"


def test_every_python_package_is_listed():
    listed = set(PYPROJECT["tool"]["setuptools"]["packages"])
    found = {p.parent.relative_to(ROOT).as_posix().replace("/", ".")
             for top in ("agent", "web") for p in (ROOT / top).rglob("__init__.py")}
    assert found - listed == set(), "a new package folder is missing from pyproject.toml"


def test_version_has_one_source():
    assert "version" in PYPROJECT["project"]["dynamic"]
    assert PYPROJECT["tool"]["setuptools"]["dynamic"]["version"]["attr"] == "agent.__version__"


@pytest.mark.parametrize("name", ["postcadence", "postcadence-web"])
def test_commands_point_at_real_functions(name):
    module, func = PYPROJECT["project"]["scripts"][name].split(":")
    assert callable(getattr(importlib.import_module(module), func))
