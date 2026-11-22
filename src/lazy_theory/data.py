"""Data files: the one reader every domain's catalog loads its TOML through.

Why: names are data, not code (docs/theory.md), and each domain keeps its own files next to its
code (pitch/scales.toml, rhythm/rhythm.toml, instruments/tunings.toml). Reading and checking
them is the same job everywhere, so it is written once here.

Pass a path to a catalog's loader to read your own file instead of the bundled one: you get
its values (scales, chords, tunings, talas) to use directly. The names modules always speak
the bundled files: to change how chords or syllables are written, edit the bundled file.
"""

import tomllib
from collections.abc import Callable, Mapping
from functools import cache, wraps
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
from types import MappingProxyType
from typing import Any, Protocol


def read(module: str, bundled: str, path: Path | None = None) -> Mapping[str, Any]:
    """The TOML file at `path`, read afresh each time so an edited file is seen, or else the
    file `bundled` beside `module` (the caller's `__name__`), parsed once and shared by every
    loader that reads it. Either way it is frozen (tables read-only, lists tuples), so no
    caller can change what the next one reads."""
    if path is not None:
        return _parsed(path)
    return _bundled(module.rpartition(".")[0], bundled)


@cache
def _bundled(package: str, name: str) -> Mapping[str, Any]:
    return _parsed(files(package) / name)


def _parsed(source: Path | Traversable) -> Mapping[str, Any]:
    with source.open("rb") as file:
        frozen: Mapping[str, Any] = _frozen(tomllib.load(file))
        return frozen


class Loader[T](Protocol):
    """A catalog loader: the bundled file's values, or those of the file at `path`."""

    def __call__(self, path: Path | None = None) -> T: ...


def bundled_once[T](load: Callable[[Path | None], T]) -> Loader[T]:
    """A catalog loader that runs once for the bundled file and every time for a file of your
    own (`path`), so an edited file is read again. What it returns is frozen like the data it
    is built from, so the one shared copy can't be changed by any caller."""

    def frozen(path: Path | None) -> T:
        built: T = _frozen(load(path))
        return built

    once = cache(frozen)

    @wraps(load)
    def loader(path: Path | None = None) -> T:
        return once(None) if path is None else frozen(path)

    return loader


def _frozen(value: Any) -> Any:
    """`value` with every table made a read-only mapping and every list a tuple, all the way
    down."""
    if isinstance(value, dict):
        return MappingProxyType({key: _frozen(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_frozen(item) for item in value)
    if isinstance(value, tuple) and hasattr(value, "_fields"):  # a NamedTuple: freeze its fields
        return type(value)(*map(_frozen, value))
    return value


def add[T](named: dict[str, T], name: str, value: T) -> None:
    """Add `value` under `name`, rejecting a repeated name or a repeated value under a new name."""
    if name in named:
        raise ValueError(f"duplicate name {name!r}")
    for existing_name, existing in named.items():
        if existing == value:
            raise ValueError(f"{name!r} is the same as {existing_name!r}")
    named[name] = value
