"""Data files: the one reader every domain's catalog loads its TOML through.

Why: names are data, not code (docs/theory.md), and each domain keeps its own files next to its
code (pitch/scales.toml, rhythm/rhythm.toml, instruments/tunings.toml). Reading and checking
them is the same job everywhere, so it is written once here.
"""

import tomllib
from collections.abc import Mapping
from functools import cache
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any


@cache
def read(package: str, bundled: str, path: Path | None = None) -> Mapping[str, Any]:
    """The TOML file at `path`, or else the file `bundled` with `package`: parsed once and shared
    by every loader that reads it, so treat it as read-only."""
    source: Path | Traversable = path or files(package) / bundled
    with source.open("rb") as file:
        return tomllib.load(file)


def add[T](named: dict[str, T], name: str, value: T) -> None:
    """Add `value` under `name`, rejecting a repeated name or a repeated value under a new name."""
    if name in named:
        raise ValueError(f"duplicate name {name!r}")
    for existing_name, existing in named.items():
        if existing == value:
            raise ValueError(f"{name!r} is the same as {existing_name!r}")
    named[name] = value
