"""Named scales and chords, loaded from TOML data files.

Names are convention (docs/theory.md), so they live here as data rather than in core. Pass a
path to load your own file instead of the bundled one.
"""

import tomllib
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path

from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.core.scale import Scale

_BUNDLED = files(__package__)


def load_scales(path: Path | None = None) -> dict[str, Scale]:
    """Every named mode, keyed by name."""
    scales: dict[str, Scale] = {}
    for family, entry in _read(path or _BUNDLED / "scales.toml").items():
        scale = Scale.from_steps(entry["steps"])
        if not 0 < len(entry["modes"]) <= len(scale):
            raise ValueError(f"{family}: name between 1 and {len(scale)} modes")
        for degree, name in enumerate(entry["modes"]):
            _add(scales, name, scale.rotate(degree))
    return scales


def load_chords(path: Path | None = None) -> dict[str, PitchClassSet]:
    """Every named chord pattern, keyed by name."""
    data = _read(path or _BUNDLED / "chords.toml")
    chords: dict[str, PitchClassSet] = {}
    for name, members in data["chords"].items():
        _add(chords, name, PitchClassSet(tuple(members), data["size"]))
    return chords


def _read(path: Path | Traversable) -> dict:
    with path.open("rb") as file:
        return tomllib.load(file)


def _add[T](named: dict[str, T], name: str, value: T) -> None:
    """Add `value` under `name`, rejecting a repeated name or a repeated value under a new name."""
    if name in named:
        raise ValueError(f"duplicate name {name!r}")
    for existing_name, existing in named.items():
        if existing == value:
            raise ValueError(f"{name!r} is the same as {existing_name!r}")
    named[name] = value
