"""Named scales and chords, loaded from TOML, and note names into numbers.

Why: "Dorian" and "m7" are conventions, not maths (docs/theory.md), so they are data here and
never code in the maths modules. Edit a file and the library speaks another tradition's
names, or your own. This is also where note names become numbers, once: pitch is steps above C0 and
pitch class is pitch mod the steps per period, C being 0 (`pitch`, `pitch_class`). Everything
after this is integers in that one frame, so any two things compare by subtraction.

Theory it speaks to: scientific pitch notation; the letters A to G as the Ionian scale on C
(so they are read from the scales file, not typed in twice); modes as rotations, so a family
is one step pattern and a list of names.

Could grow into: maqam or raga families, 19- or 31-step scales: more data, no code.

Your own files load as `lazy_theory.data` describes.
"""

from collections.abc import Mapping
from functools import cache
from pathlib import Path

from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.data import add, read
from lazy_theory.pitch.scale import Scale

LETTERS = tuple("CDEFGAB")  # the Ionian scale on C, in order

_DIGITS = "0123456789"


@cache
def load_scales(path: Path | None = None) -> Mapping[str, Scale]:
    """Every named mode, keyed by name."""
    scales: dict[str, Scale] = {}
    for family, entry in read(__name__, "scales.toml", path).items():
        scale = Scale.from_steps(entry["steps"])
        if not 0 < len(entry["modes"]) <= len(scale):
            raise ValueError(f"{family}: name between 1 and {len(scale)} modes")
        for degree, name in enumerate(entry["modes"]):
            add(scales, name, scale.rotate(degree))
    return scales


@cache
def load_chords(path: Path | None = None) -> Mapping[str, PitchClassSet]:
    """Every named chord pattern, keyed by name."""
    data = read(__name__, "chords.toml", path)
    chords: dict[str, PitchClassSet] = {}
    for name, members in data["chords"].items():
        add(chords, name, PitchClassSet(tuple(members), data["size"]))
    return chords


@cache
def chord_names() -> Mapping[PitchClassSet, str]:
    """The name of each bundled chord pattern: `load_chords` turned round. It names what
    `pitch.chord.identify` finds, and serves as the patterns it looks for."""
    return {pattern: name for name, pattern in load_chords().items()}


@cache
def load_symbols(path: Path | None = None) -> Mapping[str, str]:
    """How each named chord is written after its root, e.g. "m7" for "minor 7th"."""
    data = read(__name__, "chords.toml", path)
    symbols: Mapping[str, str] = data.get("symbols", {})
    if mismatched := set(symbols) ^ set(data["chords"]):  # so every chord can be written
        raise ValueError(f"chords and symbols differ: {sorted(mismatched)}")
    return symbols


@cache
def load_aliases(path: Path | None = None) -> Mapping[str, str]:
    """Other ways each chord symbol is written, read but never written: "M7" for "maj7"."""
    data = read(__name__, "chords.toml", path)
    aliases: Mapping[str, str] = data.get("aliases", {})
    symbols = set(data.get("symbols", {}).values())
    if unknown := set(aliases.values()) - symbols:
        raise ValueError(f"aliases for symbols that don't exist: {sorted(unknown)}")
    if shadowed := set(aliases) & symbols:
        raise ValueError(f"aliases that are already symbols: {sorted(shadowed)}")
    return aliases


def pitch(note: str) -> int:
    """Steps above C0: a note name, then its octave, which starts on C (scientific pitch
    notation, so E2 is 28 and A4 is 57)."""
    name = note.rstrip(_DIGITS)
    if name == note:
        raise ValueError(f"no octave in {note!r}")
    return major().size * int(note[len(name) :]) + pitch_class(name)


def pitch_class(note: str) -> int:
    """Steps above C, so C is 0 and E is 4. The letters are the Ionian scale on C, upper
    case; then sharps, each raising a step, or flats, each lowering one, never both (B# is 12:
    reduce it mod the period where needed)."""
    letter, altered = note[:1], note[1:]
    if letter not in LETTERS or altered.strip("#") and altered.strip("b"):
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
