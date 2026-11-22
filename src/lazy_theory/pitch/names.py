"""Numbers into words and back for pitch: note names, interval names, chord symbols, Roman
numerals. The one place the library writes or reads them.

Why: everything else works in integers, where a mistake is impossible to hide; names are how
a musician reads the result. Keeping every pitch name in one module means a symbol and the
labels on its notes are built by the same rule and cannot disagree.

Theory it speaks to: names are relative to the major scale, by long convention. An interval
is "the Nth note of the major scale, flattened or sharpened to fit" (`interval_name`), and
that one rule gives scale degrees (b3), chord tones (#9, b13), extensions in a symbol
(Em7(b9)) and the accidental on a Roman numeral (bII). Which N a note gets depends on context,
and that is the only judgement here: a note two steps up is a 9th over a chord with a third
and a 2nd in a sus chord. Spelling is derived the same way: in a seven-note key each letter is
used once, starting from whichever tonic letter needs the fewest accidentals (Bb major, not
A# major), and notes outside the key take the letter their interval names (the b6 of D is Bb).

Could grow into: other naming traditions as data (solfege, Nashville numbers, figured bass,
German H), enharmonic choice by direction of travel. Names are for twelve steps per period;
other systems are written as numbers.
"""

from functools import cache
from itertools import combinations

from lazy_theory.core.pcset import PitchClassSet, shortest
from lazy_theory.pitch.catalog import (
    LETTERS,
    accidentals,
    alteration,
    chord_names,
    load_chords,
    load_symbols,
    major,
    pitch_class,
)
from lazy_theory.pitch.chord import Chord
from lazy_theory.pitch.key import Key
from lazy_theory.pitch.scale import Scale

_NUMERALS = ("I", "II", "III", "IV", "V", "VI", "VII")


def interval_name(step: int, number: int) -> str:
    """`step` (steps above a root) written as the `number`th note of the major scale, flat or
    sharp to fit: (3, 3) is "b3", (3, 9) is "#9", (9, 7) is "bb7". Numbers past 7 are the same
    notes a period up."""
    return accidentals(shortest(step - _natural(number), 12)) + str(number)


@cache
def step_names(key: Key) -> tuple[str, ...]:
    """Every step above the tonic as an interval: the key's own notes numbered in order (in a
    seven-note key, so Lydian's fourth is "#4"), every other step flat against the major scale
    (b2 b3 b5 b6 b7). What a note is in the key, wherever a chord puts it."""
    if key.size != 12:
        return tuple(map(str, range(key.size)))
    names = [  # each step on the first major-scale note at or above it, so flat
        interval_name(step, next(n for n in range(1, 8) if _natural(n) >= step))
        for step in range(12)
    ]
    if len(key.scale) == 7:
        for degree, step in enumerate(key.scale):
            names[step] = interval_name(step, degree + 1)
    return tuple(names)


def degree_names(key: Key) -> tuple[str, ...]:
    """Each key note as an interval above the tonic: ("1", "b2", "b3", "4", "5", "b6", "b7")
    for Phrygian."""
    names = step_names(key)
    return tuple(names[step] for step in key.scale)


def note_name(pitch: int, key: Key | None = None) -> str:
    """A pitch or pitch class (C = 0) as a note name. A seven-note `key` spells it: its own
    notes one letter each, any other on the letter its interval in the key names (the b6 of D
    is Bb, not A#). Without one, natural or sharp."""
    if key is not None and key.size != 12:
        return str(pitch % key.size)
    return _spelling(key)[pitch % 12]


def note_names(key: Key) -> tuple[str, ...]:
    """The key's notes spelled, tonic first: ("E", "F", "G", "A", "B", "C", "D") for E
    Phrygian."""
    return tuple(note_name(key.root + step, key) for step in key.scale)


def pitch_name(pitch: int, key: Key | None = None) -> str:
    """A pitch (steps above C0) in scientific notation, e.g. "E2"; B#3 and Cb4 keep the octave
    of their letter."""
    name = note_name(pitch, key)
    return f"{name}{(pitch - pitch_class(name)) // 12}"


def chord_tone_names(pattern: PitchClassSet) -> tuple[str, ...]:
    """Each note of a chord as an interval above its root: ("1", "b3", "5", "b7") for a minor
    7th. The number a step gets follows the rest of the chord, as its symbol does:

    - two or five steps up is a 9th or 11th over a third, a 2nd or 4th without one (sus)
    - three steps is a #9 beside a major third, otherwise the minor third
    - six or eight steps is a #11 or b13 beside a perfect fifth, otherwise the fifth itself,
      flat or sharp (dim, aug)
    - nine steps is a 13th over a seventh, the diminished seventh on a diminished triad,
      otherwise a 6th
    """
    if pattern.size != 12:
        return tuple(map(str, pattern))
    third, fifth = 3 in pattern or 4 in pattern, 7 in pattern
    seventh, diminished = 10 in pattern or 11 in pattern, 3 in pattern and 6 in pattern
    number = {
        0: 1,
        1: 9,
        2: 9 if third else 2,
        3: 9 if 4 in pattern else 3,
        4: 3,
        5: 11 if third else 4,
        6: 11 if fifth else 5,
        7: 5,
        8: 13 if fifth else 5,
        9: 13 if seventh else 7 if diminished and not fifth else 6,
        10: 7,
        11: 7,
    }
    return tuple(interval_name(step, number[step]) for step in pattern)


def chord_symbol(chord: Chord, key: Key | None = None) -> str:
    """The chord as written over a staff: "Em7", or "Em7/G" with a bass that isn't its root.
    A pattern the catalog doesn't name is its largest named core plus its other notes as
    `chord_tone_names` calls them, "Em7(b9)" (a major seventh is written "maj7" there, since
    "(7)" would read as the flat one); with no named core at all, every note, "E(1,b9,9)"."""
    symbol = note_name(chord.root, key) + _suffix(chord.pattern)
    if chord.bass is not None and chord.bass != chord.root:
        symbol += "/" + note_name(chord.bass, key)
    return symbol


def parse_chord(text: str, key: Key | None = None) -> Chord:
    """A written chord back into numbers, the inverse of `chord_symbol`: "Fmaj7/A", "Em7(b9)",
    "Bb". With a seven-note `key`, its numerals ("bII", "iv") work too. Raises ValueError
    saying what's wrong."""
    text = text.strip()
    if key is not None and key.size == 12 and len(key.scale) == 7:
        for degree in range(7):
            if text == numeral(key, degree):
                return key.chord(degree)
    if not text or text[0] not in LETTERS:
        raise ValueError("a chord starts with its root, A to G")
    length = 1 + len(text[1:]) - len(text[1:].lstrip("#b"))
    rest, slash, bass = text[length:].partition("/")
    chord = Chord(_pattern(rest), pitch_class(text[:length]))
    if not slash:
        return chord
    if pitch_class(bass) not in chord:
        raise ValueError(f"{bass} is not a note of the chord")
    return Chord(chord.pattern, chord.root, pitch_class(bass))


def quality(scale: Scale) -> str | None:
    """Whether a mode sounds major or minor: the catalog's name for the chord stacked in
    thirds on its first note ("major", "minor", "diminished", "augmented"). Where that stacking
    makes no named chord, the third it contains decides; with both thirds or neither, None."""
    if len(scale) >= 5 and scale.size == 12:
        name = chord_names().get(scale.chord(0))
        if name in ("major", "minor", "diminished", "augmented"):
            return name
    return {(False, True): "major", (True, False): "minor"}.get((3 in scale, 4 in scale))


def numeral(key: Key, degree: int) -> str:
    """The Roman numeral of the triad on `degree` (0-based): upper case with a major third,
    lower case with a minor one, ° diminished, + augmented, flat or sharp as the degree is.
    E Phrygian's second degree is "bII"."""
    if key.size != 12 or len(key.scale) != 7:
        raise ValueError("Roman numerals need a seven-note key in twelve steps")
    triad = key.scale.chord(degree)
    text = degree_names(key)[degree][:-1] + _NUMERALS[degree]
    if 3 in triad:
        return text.lower() + ("°" if 6 in triad else "")
    return text + ("+" if 8 in triad else "")


def stack_spelling(scale: Scale, degree: int, pattern: PitchClassSet) -> str:
    """The pattern's notes by their place in the stack of thirds on `degree`, in stack order:
    "1 b3 5 b9" for E minor with E Phrygian's F. Unlike `chord_tone_names`, the number is the
    note's place in the scale's own stack, whatever else the chord holds."""
    stack = enumerate(scale.stacked(degree, len(scale)))
    return " ".join(interval_name(note, 2 * place + 1) for place, note in stack if note in pattern)


def _natural(number: int) -> int:
    """Steps from a root up to the `number`th note of its major scale: the 3rd is 4, and the
    9th, a period up, is the 2nd's 2."""
    return major().pitch_classes[(number - 1) % 7]


def _interval_step(name: str) -> int:
    """`interval_name` read back: "b3" is 3, "#11" is 6; "maj7" is how a symbol writes 7."""
    name = name.strip().removeprefix("maj")
    number = name.lstrip("b#")
    if number not in ("1", "2", "3", "4", "5", "6", "7", "9", "11", "13"):
        raise ValueError(f"unknown extension {name!r}")
    return (_natural(int(number)) + alteration(name)) % 12


@cache
def _spelling(key: Key | None) -> tuple[str, ...]:
    """The name of each of the twelve pitch classes, as `key` spells them."""
    if key is None or len(key.scale) != 7:  # natural, or the sharp of the letter below
        return tuple(
            _spelled([letter for letter in LETTERS if pitch_class(letter) <= note][-1], note)
            for note in range(12)
        )
    numbers = [int(name.lstrip("b#")) for name in step_names(key)]
    spellings = []
    for tonic in range(7):  # each letter the tonic could take; the rest follow in order
        names = [
            _spelled(LETTERS[(tonic + number - 1) % 7], key.root + step)
            for step, number in enumerate(numbers)
        ]
        altered = [len(names[step]) - 1 for step in key.scale]
        if max(altered) <= 2:
            sharps = sum(names[step].count("#") for step in key.scale)
            spellings.append((sum(altered), altered[0], -sharps, names))
    by_step = min(spellings)[-1]
    return tuple(by_step[key.interval(note)] for note in range(12))


def _spelled(letter: str, pitch: int) -> str:
    """`pitch` written on `letter`, with the sharps or flats that takes."""
    return letter + accidentals(shortest(pitch - pitch_class(letter), 12))


def _suffix(pattern: PitchClassSet) -> str:
    """What follows the root in a chord symbol: "m7", or a named core plus what's added."""
    symbols = _symbols()
    if pattern in symbols:
        return symbols[pattern]
    tones = dict(zip(pattern, chord_tone_names(pattern), strict=True))
    notes = [step for step in pattern if step]
    for size in range(len(notes) - 1, 0, -1) if pattern.size == 12 else ():  # largest core first
        cores = [PitchClassSet((0, *c)) for c in combinations(notes, size)]
        if cores := [core for core in cores if core in symbols and not _clashes(core, tones)]:
            # a core must read the same inside the chord as alone: with a seventh the 6 of a
            # 6 chord is a 13, with a third the 2 of a sus2 is a 9, so those cores lose
            core = max(cores, key=lambda c: chord_tone_names(c) == tuple(tones[s] for s in c))
            added = sorted(set(pattern) - set(core), key=lambda step: _written_order(tones[step]))
            written = ",".join("maj7" if tones[step] == "7" else tones[step] for step in added)
            return f"{symbols[core]}({written})"
    return f"({','.join(tones.values())})"


def _clashes(core: PitchClassSet, tones: dict[int, str]) -> bool:
    """Whether a note added to `core` would share a degree with one of the core's own notes:
    written in brackets it would read as altering that note (`_pattern`), so such a core can't
    be the one a symbol is built on."""
    own = {_number(name) for name in chord_tone_names(core)}
    return any(_number(tones[step]) in own for step in set(tones) - set(core))


def _written_order(tone: str) -> tuple[bool, int, int]:
    """Extensions as symbols list them: 9ths, 11ths and 13ths rising, then the rest; flats
    before naturals before sharps."""
    number = int(tone.lstrip("b#"))
    return number < 8, number, alteration(tone)


def _pattern(text: str) -> PitchClassSet:
    """The part of a symbol after its root, back into a pattern: "m7(b9)". A bracketed note
    with the same number as one of the core's alters it rather than joining it: "m7(b5)" is
    the half-diminished chord, its fifth lowered, not a minor 7th with two fifths."""
    types = {symbol: chord for chord, symbol in _symbols().items()}
    core, added = text, ""
    if text not in types and text.endswith(")"):  # "m(maj7)" is a type; only split what isn't
        core, _, added = text[:-1].rpartition("(")
    if core not in types:
        raise ValueError(f"unknown chord type {core!r}")
    labels = added.split(",") if added else []
    if not core and "1" in labels:  # "(1,b9,9)": every note is listed, there is no core
        return PitchClassSet(tuple(map(_interval_step, labels)))
    pattern = types[core]
    altered = {_number(label) for label in labels}
    kept = [
        step
        for step, name in zip(pattern, chord_tone_names(pattern), strict=True)
        if _number(name) not in altered
    ]
    return PitchClassSet((*kept, *map(_interval_step, labels)))


def _number(name: str) -> int:
    """The degree an interval name counts: "b5" and "#5" are both 5, "maj7" is 7."""
    return int(name.strip().removeprefix("maj").lstrip("b#"))


@cache
def _symbols() -> dict[PitchClassSet, str]:
    """What follows the root for each chord the catalog names: (0, 3, 7, 10) is "m7"."""
    symbols = load_symbols()
    return {pattern: symbols[name] for name, pattern in load_chords().items()}
