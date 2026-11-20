"""Named scales, chords and string tunings, loaded from TOML data files.

Why: "Dorian", "m7" and "drop D" are conventions, not maths (docs/theory.md), so they are data
here and never code in core. Swap a file and the library speaks another tradition's names, or
your own. This is also where note names become numbers, once: pitch is steps above C0 and pitch
class is pitch mod the steps per period, C being 0 (`pitch`, `pitch_class`). Everything after
this layer is integers in that one frame, so any two things compare by subtraction.

Theory it speaks to: scientific pitch notation; the letters A to G as the Ionian scale on C
(so they are read from the scales file, not typed in twice); modes as rotations, so a family
is one step pattern and a list of names.

Could grow into: more data, with no code: maqam or raga families, other instruments' tunings,
a different reference pitch (A = 432 or 415), 19- or 31-step scales.

Pass a path to load your own file instead of the bundled one. Each file is read once; the
results are shared, so treat them as read-only.
"""

import tomllib
from collections.abc import Mapping
from functools import cache
from importlib.resources import files
from importlib.resources.abc import Traversable
from itertools import accumulate
from pathlib import Path
from typing import Any, NamedTuple

from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.core.scale import Scale
from lazy_theory.core.temperament import EqualTemperament

_BUNDLED = files(__package__)
LETTERS = tuple("CDEFGAB")  # the Ionian scale on C, in order
_DIGITS = "0123456789"


@cache
def load_scales(path: Path | None = None) -> Mapping[str, Scale]:
    """Every named mode, keyed by name."""
    scales: dict[str, Scale] = {}
    for family, entry in _read(path or _BUNDLED / "scales.toml").items():
        scale = Scale.from_steps(entry["steps"])
        if not 0 < len(entry["modes"]) <= len(scale):
            raise ValueError(f"{family}: name between 1 and {len(scale)} modes")
        for degree, name in enumerate(entry["modes"]):
            _add(scales, name, scale.rotate(degree))
    return scales


@cache
def load_scale_families(path: Path | None = None) -> Mapping[str, tuple[str, ...]]:
    """Each family of modes (a table in the scales file, e.g. "harmonic_minor") with its modes'
    names in rotation order."""
    data = _read(path or _BUNDLED / "scales.toml")
    return {family: tuple(entry["modes"]) for family, entry in data.items()}


@cache
def load_chords(path: Path | None = None) -> Mapping[str, PitchClassSet]:
    """Every named chord pattern, keyed by name."""
    data = _read(path or _BUNDLED / "chords.toml")
    chords: dict[str, PitchClassSet] = {}
    for name, members in data["chords"].items():
        _add(chords, name, PitchClassSet(tuple(members), data["size"]))
    return chords


@cache
def chord_names() -> Mapping[PitchClassSet, str]:
    """The name of each bundled chord pattern: `load_chords` turned round. It names what
    `core.chord.identify` finds, and serves as the patterns it looks for."""
    return {pattern: name for name, pattern in load_chords().items()}


@cache
def load_symbols(path: Path | None = None) -> Mapping[str, str]:
    """How each named chord is written after its root, e.g. "m7" for "minor 7th"."""
    data = _read(path or _BUNDLED / "chords.toml")
    symbols: dict[str, str] = data.get("symbols", {})
    if mismatched := set(symbols) ^ set(data["chords"]):  # so every chord can be written
        raise ValueError(f"chords and symbols differ: {sorted(mismatched)}")
    return symbols


class Tuning(NamedTuple):
    open_strings: tuple[int, ...]  # pitch of each open string, steps above C0
    scale_length: float  # millimetres from nut to bridge
    hertz: float  # frequency of pitch 0 (C0), from the file's reference


@cache
def load_tunings(path: Path | None = None) -> Mapping[str, Tuning]:
    """Every named tuning, keyed by instrument and name, e.g. "guitar standard"."""
    data = _read(path or _BUNDLED / "tunings.toml")
    reference = data.pop("reference")
    temperament = EqualTemperament(major().size)
    hertz = reference["hertz"] * temperament.ratio(-pitch(reference["note"]))
    tunings: dict[str, Tuning] = {}
    for instrument, entry in data.items():
        for name, tuning in entry["tunings"].items():
            strings = accumulate(tuning["gaps"], initial=pitch(tuning["first"]))
            _add(
                tunings,
                f"{instrument} {name}",
                Tuning(tuple(strings), entry["scale_length"], hertz),
            )
    return tunings


def pitch(note: str) -> int:
    """Steps above C0: a note name, then its octave, which starts on C (scientific pitch
    notation, so E2 is 28 and A4 is 57)."""
    name = note.rstrip(_DIGITS)
    if name == note:
        raise ValueError(f"no octave in {note!r}")
    return major().size * int(note[len(name) :]) + pitch_class(name)


def pitch_class(note: str) -> int:
    """Steps above C, so C is 0 and E is 4. The letters are the Ionian scale on C; each #
    raises and each b lowers a step (B# is 12: reduce it mod the period where needed)."""
    letter, altered = note[:1].upper(), note[1:]
    if letter not in LETTERS or set(altered) - {"#", "b"}:
        raise ValueError(f"not a note name: {note!r}")
    return major().pitch_classes[LETTERS.index(letter)] + alteration(altered)


def major() -> Scale:
    """The scale names are measured against: its notes are the letters C to B, and its degrees
    the numbers every interval name counts in."""
    return load_scales()["Ionian"]


def accidentals(shift: int) -> str:
    """Sharps that raise a note `shift` steps, or flats that lower it: 1 is "#", -2 is "bb"."""
    return "#" * shift + "b" * -shift


def alteration(text: str) -> int:
    """`accidentals` read back: steps up for each "#" in `text`, down for each "b"."""
    return text.count("#") - text.count("b")


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
