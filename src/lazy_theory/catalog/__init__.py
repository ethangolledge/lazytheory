"""Named scales, chords and string tunings, loaded from TOML data files.

Names are convention (docs/theory.md), so they live here as data rather than in core. Pass a
path to load your own file instead of the bundled one.
"""

import tomllib
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any, NamedTuple

from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.core.scale import Scale
from lazy_theory.core.temperament import EqualTemperament

_BUNDLED = files(__package__)
_LETTERS = tuple("CDEFGAB")
_DIGITS = "0123456789"


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


class Tuning(NamedTuple):
    first: str  # first open string with its octave, e.g. "E2"
    gaps: tuple[int, ...]  # steps between neighbouring open strings
    scale_length: float  # millimetres from nut to bridge
    hertz: float  # frequency of the first open string

    def root(self, note: str) -> int:
        """Steps from the first open string up to `note`, e.g. 5 for "A" in standard tuning."""
        return (_pitch_class(note) - _pitch_class(self.first.rstrip(_DIGITS))) % _ionian().size


def load_tunings(path: Path | None = None) -> dict[str, Tuning]:
    """Every named tuning, keyed by instrument and name, e.g. "guitar standard"."""
    data = _read(path or _BUNDLED / "tunings.toml")
    reference = data.pop("reference")
    temperament = EqualTemperament(_ionian().size)
    tunings: dict[str, Tuning] = {}
    for instrument, entry in data.items():
        for name, tuning in entry["tunings"].items():
            steps = _pitch(tuning["first"]) - _pitch(reference["note"])
            hertz = reference["hertz"] * temperament.ratio(steps)
            values = Tuning(tuning["first"], tuple(tuning["gaps"]), entry["scale_length"], hertz)
            _add(tunings, f"{instrument} {name}", values)
    return tunings


def _pitch(note: str) -> int:
    """Steps above C0: a note name, then its octave, which starts on C (scientific pitch
    notation, so A4 is 57)."""
    name = note.rstrip(_DIGITS)
    if name == note:
        raise ValueError(f"no octave in {note!r}")
    return _ionian().size * int(note[len(name) :]) + _pitch_class(name)


def _pitch_class(note: str) -> int:
    """C is 0. The letters are the Ionian scale on C; each # raises and each b lowers a step."""
    letter, accidentals = note[:1].upper(), note[1:]
    if letter not in _LETTERS or set(accidentals) - {"#", "b"}:
        raise ValueError(f"not a note name: {note!r}")
    natural = _ionian().pitch_classes[_LETTERS.index(letter)]
    return natural + accidentals.count("#") - accidentals.count("b")


def _ionian() -> Scale:
    return load_scales()["Ionian"]


def _read(path: Path | Traversable) -> dict[str, Any]:
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
