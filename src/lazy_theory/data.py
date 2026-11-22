"""Data files: the one reader every domain's catalog loads its TOML through.

Why: names are data, not code (docs/theory.md), and each domain keeps its own files next to its
code (pitch/scales.toml, rhythm/rhythm.toml, instruments/tunings.toml). Reading and checking
them is the same job everywhere, so it is written once here.

Pass a path to a catalog's loader to read your own file instead of the bundled one: you get
its values (scales, chords, tunings, talas) to use directly. The names modules always speak
the bundled files: to change how chords or syllables are written, edit the bundled file.
"""

import tomllib
from collections.abc import Mapping
from functools import cache
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
from types import MappingProxyType
from typing import Any


@cache
def read(module: str, bundled: str, path: Path | None = None) -> Mapping[str, Any]:
    """The TOML file at `path`, or else the file `bundled` beside `module` (the caller's
    `__name__`), in its package: parsed once and shared
    by every loader that reads it, so it is frozen (tables read-only, lists tuples) and no
    caller can change what the next one reads."""
    source: Path | Traversable = path or files(module.rpartition(".")[0]) / bundled
    with source.open("rb") as file:
        frozen: Mapping[str, Any] = _frozen(tomllib.load(file))
        return frozen


def _frozen(value: Any) -> Any:
    """`value` with every table made a read-only mapping and every list a tuple, all the way
    down."""
    if isinstance(value, dict):
        return MappingProxyType({key: _frozen(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_frozen(item) for item in value)
    return value


def add[T](named: dict[str, T], name: str, value: T) -> None:
    """Add `value` under `name`, rejecting a repeated name or a repeated value under a new name."""
    if name in named:
        raise ValueError(f"duplicate name {name!r}")
    for existing_name, existing in named.items():
        if existing == value:
            raise ValueError(f"{name!r} is the same as {existing_name!r}")
    named[name] = value
