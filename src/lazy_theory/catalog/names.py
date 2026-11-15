"""Numbers into words: the one place the library writes note names, chord symbols, Roman
numerals and tab. Everything else works in the integer frame and calls this at the edge.

Spelling is derived, not listed. In a seven-note key each letter is used once, so the notes
take the letters in order from the tonic's, with whichever tonic letter needs the fewest
accidentals (Bb major, not A# major). Names are for twelve steps per period; other temperaments
are written as step numbers.
"""

from collections.abc import Sequence
from functools import cache

from lazy_theory.catalog import _LETTERS, load_chords, load_scales, load_symbols, pitch_class
from lazy_theory.core.chord import Chord
from lazy_theory.core.key import Key
from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.core.scale import Scale

_NUMERALS = ("I", "II", "III", "IV", "V", "VI", "VII")


@cache
def note_names(key: Key) -> tuple[str, ...]:
    """The key's notes spelled, tonic first: ("E", "F", "G", "A", "B", "C", "D") for E
    Phrygian. Keys that aren't seven notes are named note by note."""
    notes = [(key.root + step) % key.scale.size for step in key.scale]
    if key.scale.size != 12 or len(notes) != 7:
        return tuple(note_name(note) for note in notes)
    spellings = []
    for tonic in range(7):
        names = [_spelled(_LETTERS[(tonic + i) % 7], note) for i, note in enumerate(notes)]
        accidentals = [len(name) - 1 for name in names]
        if max(accidentals) <= 2:
            sharps = sum(name.count("#") for name in names)
            spellings.append((sum(accidentals), accidentals[0], -sharps, tuple(names)))
    return min(spellings)[-1]


def note_name(pitch_class: int, key: Key | None = None) -> str:
    """A pitch class (C = 0) as a note name: as `key` spells it when it's one of the key's notes;
    otherwise natural, or sharp (flat in a key spelled with flats)."""
    size = key.scale.size if key else 12
    if size != 12:
        return str(pitch_class % size)
    pitch_class %= 12
    flats = False
    if key is not None:
        names = note_names(key)
        for step, name in zip(key.scale, names, strict=True):
            if (key.root + step) % 12 == pitch_class:
                return name
        flats = any("b" in name for name in names)
    for letter in _LETTERS:
        if _natural(letter) == pitch_class:
            return letter
    neighbour = pitch_class + 1 if flats else pitch_class - 1
    letter = next(one for one in _LETTERS if _natural(one) == neighbour % 12)
    return letter + ("b" if flats else "#")


def pitch_name(pitch: int, key: Key | None = None) -> str:
    """A pitch (steps above C0) in scientific notation, e.g. "E2"; B#3 and Cb4 keep the octave
    of their letter."""
    name = note_name(pitch, key)
    return f"{name}{(pitch - pitch_class(name)) // 12}"


def chord_symbol(chord: Chord, key: Key | None = None, bass: int | None = None) -> str:
    """The chord as written over a staff, e.g. "Em7", or "Em7/G" with `bass` (a pitch class)
    under it. A pattern the catalog doesn't name is written by its intervals, "E(0 1 3 7)"."""
    root = note_name(chord.root, key)
    name = _chord_names().get(chord.pattern)
    if name is None:
        symbol = root + "(" + " ".join(map(str, chord.pattern)) + ")"
    else:
        symbol = root + load_symbols().get(name, f" {name}")
    if bass is not None and (bass - chord.root) % chord.pattern.size:
        symbol += "/" + note_name(bass, key)
    return symbol


def numeral(key: Key, degree: int) -> str:
    """The Roman numeral of the triad on `degree` (0-based): upper case with a major third,
    lower case with a minor one, ° diminished, + augmented, flat or sharp against the major
    scale. E Phrygian's second degree is "bII"."""
    if key.scale.size != 12 or len(key.scale) != 7:
        raise ValueError("Roman numerals need a seven-note key in twelve steps")
    triad = set(key.chord(degree).pattern)
    major = load_scales()["Ionian"].pitch_classes[degree]
    shift = key.scale.pitch_classes[degree] - major
    text = "b" * -shift + "#" * shift + _NUMERALS[degree]
    if 3 in triad:
        text = text.lower() + ("°" if 6 in triad else "")
    elif 8 in triad:
        text += "+"
    return text


def stack_spelling(scale: Scale, degree: int, pattern: PitchClassSet) -> str:
    """The pattern's notes by their place in the stack of thirds on `degree`, flat or sharp
    against the major scale, in stack order: "1 b3 5 b9" for E minor with E Phrygian's F."""
    major = load_scales()["Ionian"].pitch_classes
    names = []
    for place, note in enumerate(scale.stacked(degree, len(scale))):
        if note in pattern:
            number = 2 * place + 1
            difference = (note - major[(number - 1) % len(major)] + 6) % 12 - 6
            names.append("b" * -difference + "#" * difference + str(number))
    return " ".join(names)


def tab(
    open_strings: Sequence[int],
    voicings: Sequence[Sequence[int]],
    titles: Sequence[str] = (),
    key: Key | None = None,
) -> str:
    """Voicings as guitar tab: one line per string, the highest string on top, labelled with
    its open note; one column per voicing under its title. A negative fret is a muted "x"."""
    columns = [[str(fret) if fret >= 0 else "x" for fret in voicing] for voicing in voicings]
    titles = list(titles) + [""] * (len(columns) - len(titles))
    widths = [
        max(len(title), *map(len, column)) for title, column in zip(titles, columns, strict=True)
    ]
    labels = [note_name(string, key) for string in open_strings]
    pad = max(map(len, labels))
    lines = [" " * (pad + 2) + "  ".join(t.ljust(w) for t, w in zip(titles, widths, strict=True))]
    for string in reversed(range(len(open_strings))):
        cells = "  ".join(
            column[string].ljust(w) for column, w in zip(columns, widths, strict=True)
        )
        lines.append(f"{labels[string].ljust(pad)} |{cells}")
    return "\n".join(line.rstrip() for line in lines)


def _spelled(letter: str, pitch_class: int) -> str:
    accidental = (pitch_class - _natural(letter) + 6) % 12 - 6
    return letter + "#" * accidental + "b" * -accidental


def _natural(letter: str) -> int:
    return pitch_class(letter)


@cache
def _chord_names() -> dict[PitchClassSet, str]:
    return {pattern: name for name, pattern in load_chords().items()}
