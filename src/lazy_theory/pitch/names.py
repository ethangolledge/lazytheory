"""Numbers into words and back for pitch: note names, interval names, chord symbols, Roman
numerals. The one place the library writes them, and reads chord symbols; reading a single
note name ("F#", "E2") is `pitch.catalog`'s, where the letters themselves are defined.

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

import re
from functools import cache, lru_cache
from typing import NamedTuple

from lazy_theory.core.pcset import PitchClassSet, shortest
from lazy_theory.pitch.catalog import (
    LETTERS,
    TWELVE,
    accidentals,
    alteration,
    chord_names,
    load_aliases,
    load_chords,
    load_scales,
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
    if number < 1:
        raise ValueError(f"interval numbers start at 1 (the unison), not {number}")
    return accidentals(shortest(step - _natural(number), TWELVE)) + str(number)


@lru_cache(maxsize=256)  # keys a session uses, not every key ever asked
def step_names(key: Key) -> tuple[str, ...]:
    """Every step above the tonic as an interval: the key's own notes numbered in order (in a
    seven-note key, so Lydian's fourth is "#4"), every other step flat against the major scale
    (b2 b3 b5 b6 b7). What a note is in the key, wherever a chord puts it. A seven-note key
    whose notes can't be numbered 1 to 7 with at most two accidentals each (C C# D D# E F F#)
    is named as the steps of no key are."""
    if key.size != TWELVE:
        return tuple(map(str, range(key.size)))
    names = [  # each step on the first major-scale note at or above it, so flat
        interval_name(step, next(n for n in range(1, 8) if _natural(n) >= step))
        for step in range(TWELVE)
    ]
    if _numbered(key):
        for degree, step in enumerate(key.scale):
            names[step] = interval_name(step, degree + 1)
    return tuple(names)


def _numbered(key: Key) -> bool:
    """Whether a twelve-step key's notes can be numbered 1 to 7 in order, each at most two
    steps from its major-scale degree: what degree names, spelling and numerals need."""
    return len(key.scale) == 7 and all(
        abs(shortest(step - _natural(degree + 1), TWELVE)) <= 2
        for degree, step in enumerate(key.scale)
    )


def degree_names(key: Key) -> tuple[str, ...]:
    """Each key note as an interval above the tonic: ("1", "b2", "b3", "4", "5", "b6", "b7")
    for Phrygian."""
    names = step_names(key)
    return tuple(names[step] for step in key.scale)


def note_name(pitch: int, key: Key | None = None, size: int = TWELVE) -> str:
    """A pitch or pitch class (C = 0) as a note name. A seven-note `key` spells it: its own
    notes one letter each, any other on the letter its interval in the key names (the b6 of D
    is Bb, not A#). Without one, natural or sharp. In a key or `size` of other than twelve
    steps the pitch class is written as a number."""
    size = key.size if key is not None else size
    if size < 1:
        raise ValueError(f"a period has at least one step, not {size}")
    if size != TWELVE:
        return str(pitch % size)
    return _spelling(key)[pitch % TWELVE]


def note_names(key: Key) -> tuple[str, ...]:
    """The key's notes spelled, tonic first: ("E", "F", "G", "A", "B", "C", "D") for E
    Phrygian."""
    return tuple(note_name(key.root + step, key) for step in key.scale)


def pitch_name(pitch: int, key: Key | None = None) -> str:
    """A pitch (steps above C0) in scientific notation, e.g. "E2"; B#3 and Cb4 keep the octave
    of their letter. Scientific notation is for twelve steps only: other keys raise ValueError
    (`note_name` still writes their pitch classes as numbers)."""
    if key is not None and key.size != TWELVE:
        raise ValueError(f"scientific pitch names need twelve steps, not {key.size}")
    name = note_name(pitch, key)
    return f"{name}{(pitch - pitch_class(name)) // TWELVE}"


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
    if pattern.size != TWELVE:
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
    """The chord as written over a staff: "Em7", or "Em7/G" with a bass ("Em7/E" asks for the root
    in the bass, where "Em7" leaves the inversion free). A pattern the catalog doesn't name is its
    largest named core plus its other notes as `chord_tone_names` calls them, "Em7(b9)" (a major
    seventh is written "maj7" there, since "(7)" would read as the flat one); with no named core at
    all, every note, "E(1,b9,2)". Without a `key`, the chord is spelled in its own: the major or
    minor key on its root with the fewest accidentals, so Bb minor is "Bbm", not "A#m", and its bass
    follows."""
    if key is not None and key.size != chord.size:
        raise ValueError(f"a {chord.size}-step chord in a {key.size}-step key")
    spelling = key if key is not None else _own_key(chord)
    symbol = note_name(chord.root, spelling, chord.size) + _suffix(chord.pattern)
    if chord.bass is not None:  # on its own root too: "C/C" asks for root position
        symbol += "/" + note_name(chord.bass, spelling, chord.size)
    return symbol


def _own_key(chord: Chord) -> Key | None:
    """The key a chord is spelled in when none is given: minor on its root with a minor third
    and no major one, otherwise major. None outside twelve steps, where notes are numbers."""
    if chord.size != TWELVE:
        return None
    minor = 3 in chord.pattern and 4 not in chord.pattern
    return Key(load_scales()["Aeolian" if minor else "Ionian"], chord.root)


def parse_chord(text: str, key: Key | None = None) -> Chord:
    """A written chord back into numbers, the inverse of `chord_symbol`: "Fmaj7/A", "Em7(b9)",
    "Bb". Other common spellings read too ("CM7", "C-7", "Cø7", "C7#9", "C6/9"; the catalog's
    aliases). With a seven-note `key`, its numerals ("bII", "iv") work too. Raises ValueError
    saying what's wrong."""
    text = text.strip()
    if key is not None and key.size == TWELVE and _numbered(key):
        for degree in range(7):
            if text == numeral(key, degree):
                return key.chord(degree)
    if not text or text[0] not in LETTERS:
        raise ValueError("a chord starts with its root, A to G")
    length = 1 + len(text[1:]) - len(text[1:].lstrip("#b"))
    rest, slash, bass = text[length:].rpartition("/")
    if not slash or not bass or bass[0] not in LETTERS:  # no bass: "6/9" is part of the type
        rest, slash = text[length:], ""
    chord = Chord(_pattern(rest), pitch_class(text[:length]))
    if not slash:
        return chord
    if pitch_class(bass) not in chord:
        raise ValueError(f"{bass} is not a note of the chord")
    return Chord(chord.pattern, chord.root, pitch_class(bass))


def quality(scale: Scale) -> str | None:
    """Whether a mode sounds major or minor: the catalog's name for the chord stacked in
    thirds on its first note ("major", "minor", "diminished", "augmented"). Where that stacking
    makes no named chord, the third it contains decides; with both thirds or neither, None.
    None outside twelve steps, where the names don't apply."""
    if scale.size != TWELVE:
        return None
    if len(scale) >= 5:
        name = chord_names().get(scale.chord(0))
        if name in ("major", "minor", "diminished", "augmented"):
            return name
    return {(False, True): "major", (True, False): "minor"}.get((3 in scale, 4 in scale))


def numeral(key: Key, degree: int) -> str:
    """The Roman numeral of the triad on `degree` (0-based): upper case with a major third,
    lower case with a minor one, ° diminished, + augmented, flat or sharp as the degree is.
    E Phrygian's second degree is "bII". Degrees wrap, as `Key.chord`'s do."""
    if key.size != TWELVE or not _numbered(key):
        raise ValueError("Roman numerals need a seven-note key in twelve steps, numbered 1 to 7")
    degree %= 7
    triad = key.scale.chord(degree)
    text = degree_names(key)[degree][:-1] + _NUMERALS[degree]
    if 3 in triad:
        return text.lower() + ("°" if 6 in triad else "")
    return text + ("+" if 8 in triad else "")


def stack_spelling(scale: Scale, degree: int, pattern: PitchClassSet) -> str:
    """The pattern's notes that are in the stack of thirds on `degree`, by their place in it,
    in stack order: "1 b3 5 b9" for E minor with E Phrygian's F. Notes outside the stack (not in
    the scale, or past where thirds repeat) are left out. Unlike `chord_tone_names`, the number
    is the note's place in the scale's own stack, whatever else the chord holds; in a scale of other
    than seven notes, where a place isn't a number, each note is named as `chord_tone_names`
    names it. Outside twelve steps each note is its number of steps above the root."""
    if pattern.size != scale.size:
        raise ValueError(f"a {pattern.size}-step chord in a {scale.size}-step scale")
    stack = scale.stack(degree)
    if scale.size != TWELVE:
        return " ".join(str(note) for note in stack if note in pattern)
    if len(scale) != 7:  # thirds aren't scale steps two apart: name each as a chord tone
        names = dict(zip(pattern, chord_tone_names(pattern), strict=True))
        return " ".join(names[note] for note in stack if note in pattern)
    return " ".join(
        interval_name(note, 2 * place + 1) for place, note in enumerate(stack) if note in pattern
    )


def _natural(number: int) -> int:
    """Steps from a root up to the `number`th note of its major scale: the 3rd is 4, and the
    9th, a period up, is the 2nd's 2."""
    return major().pitch_classes[(number - 1) % 7]


def _interval_step(name: str) -> int:
    """`interval_name` read back: "b3" is 3, "#11" is 6; "maj7" is how a symbol writes 7."""
    number = _number(name)
    if number not in (1, 2, 3, 4, 5, 6, 7, 9, 11, 13):
        raise ValueError(f"unknown extension {name!r}")
    return (_natural(number) + alteration(name)) % TWELVE


@lru_cache(maxsize=256)
def _spelling(key: Key | None) -> tuple[str, ...]:
    """The name of each of the twelve pitch classes, as `key` spells them: each note on the
    letter its interval names (C minor pentatonic's b3 is Eb). A seven-note key whose notes
    can't each take their own letter with at most two accidentals (C C# D D# E F F# can't) is
    spelled as no key is."""
    usable = key is not None and (len(key.scale) != 7 or _numbered(key))
    if key is not None and usable and (spellings := _key_spellings(key)):
        by_step = min(spellings)[-1]
        return tuple(by_step[key.interval(note)] for note in range(TWELVE))
    return tuple(  # natural, or the sharp of the letter below
        _spelled([letter for letter in LETTERS if pitch_class(letter) <= note][-1], note)
        for note in range(TWELVE)
    )


def _key_spellings(key: Key) -> list[tuple[int, int, int, list[str]]]:
    """Each way to put a key's notes on the letters their intervals name, with at most two
    accidentals on any note, ranked for `_spelling`: the plainest tonic (C Ultralocrian starts
    on C, not B#), then the fewest accidentals (Bb major, not A#), then flats (Ebm, not D#m)."""
    numbers = [_number(name) for name in step_names(key)]
    spellings = []
    for tonic in range(7):  # each letter the tonic could take; the rest follow in order
        names = [
            _spelled(LETTERS[(tonic + number - 1) % 7], key.root + step)
            for step, number in enumerate(numbers)
        ]
        altered = [len(names[step]) - 1 for step in key.scale]
        if max(altered) <= 2:
            sharps = sum(names[step].count("#") for step in key.scale)
            for step in set(range(TWELVE)) - set(key.scale):  # outside the key: plainest name
                names[step] = _plainest(key.root + step, names[step])
            spellings.append((altered[0], sum(altered), sharps, names))
    return spellings


def _plainest(pitch: int, named: str) -> str:
    """`pitch` on whichever letter takes the fewest accidentals, `named` (its interval's
    letter, a flattened degree) when that is as plain: Gb major's C is C, not Dbb, while C
    major's F#/Gb stays Gb, the b5."""
    names = [named, *(_spelled(letter, pitch) for letter in LETTERS)]
    return min(names, key=lambda name: len(name))  # ties: the first, `named`


def _spelled(letter: str, pitch: int) -> str:
    """`pitch` written on `letter`, with the sharps or flats that takes."""
    return letter + accidentals(shortest(pitch - pitch_class(letter), TWELVE))


@lru_cache(maxsize=4096)  # a song repeats its chords
def _suffix(pattern: PitchClassSet) -> str:
    """What follows the root in a chord symbol: "m7", or a named core with what's added and
    what's left out ("m7(b9)", "7(no5)"); failing both, every note, "(1,b3,b9)"."""
    symbols = _symbols()
    if pattern in symbols:
        return symbols[pattern]
    tones = dict(zip(pattern, chord_tone_names(pattern), strict=True))
    found = (
        []
        if pattern.size != TWELVE
        else [reading for core in symbols if (reading := _core(core, pattern, tones)) is not None]
    )
    if not found:
        return f"({','.join(tones.values())})"
    best = max(found, key=lambda reading: reading.rank)  # ties: catalog order
    labels = [f"no{number}" for number in best.omitted]
    labels += ["maj7" if tones[step] == "7" else tones[step] for step in best.added]
    return f"{symbols[best.core]}({','.join(labels)})"


_WRITTEN = re.compile(r"(?:bb|b|#)?[1-9]\d*|maj7|no[1-9]\d*")  # a tone as `_suffix` writes it
_OMITTABLE = {3, 5}  # the tones a lead sheet leaves out of a seventh chord: "7(no3)", "m7(no5)"


class _Reading(NamedTuple):
    """A chord read as a named core with notes added or left out, as `_core` ranks it."""

    rank: tuple[int, bool, bool, int]  # the larger reads better: see `_core`
    core: PitchClassSet
    omitted: tuple[int, ...]  # degree numbers left out: 3, 5
    added: tuple[int, ...]  # steps above the root, in written order


def _core(core: PitchClassSet, pattern: PitchClassSet, tones: dict[int, str]) -> _Reading | None:
    """`pattern` read as the named `core` with notes added and its 3rd or 5th left out, ranked
    for `_suffix` (the largest is chosen), or None if it can't be. Ranked by the most of the
    core kept; then nothing left out; then a core that reads the same inside the chord as
    alone (with a seventh the 6 of a 6 chord is a 13, with a third the 2 of a sus2 is a 9);
    then the most of the chord's own 1 to 7 in the core, so extensions sit on a seventh chord:
    "Am(maj7)(9)", not "Amadd9(maj7)". An added note may not share a degree with the core's
    own, or it would read as altering it (`_pattern`). Only a chord with a seventh is written
    with a note left out, and only when its other notes keep their names."""
    names = dict(zip(core, chord_tone_names(core), strict=True))
    kept = [step for step in core if step in pattern]
    omitted = sorted({_number(names[step]) for step in core if step not in pattern})
    added = sorted(set(pattern) - set(core), key=lambda step: _written_order(tones[step]))
    own = {_number(name) for name in names.values()}
    reads_same = all(names[step] == tones[step] for step in kept)
    if omitted and (7 not in own or not reads_same):  # a seventh chord, its other notes as named
        return None
    if len(kept) < 2 or set(omitted) - _OMITTABLE or any(_number(tones[s]) in own for s in added):
        return None
    within_seventh = sum(_number(tones[step]) <= 7 for step in kept)
    rank = (len(kept), not omitted, reads_same, within_seventh)
    return _Reading(rank, core, tuple(omitted), tuple(added))


def _written_order(tone: str) -> tuple[bool, int, int]:
    """Extensions as symbols list them: 9ths, 11ths and 13ths rising, then the rest; flats
    before naturals before sharps."""
    number = _number(tone)
    return number < 8, number, alteration(tone)


def _pattern(text: str) -> PitchClassSet:
    """The part of a symbol after its root, back into a pattern: "m7(b9)". A bracketed note
    with the same number as one of the core's alters it rather than joining it: "m7(b5)" is
    the half-diminished chord, its fifth lowered, not a minor 7th with two fifths. "no5"
    leaves the core's fifth out."""
    types = _types()
    core, added = text, ""
    if text not in types and text.endswith(")"):  # "m(maj7)" is a type; only split what isn't
        core, _, added = text[:-1].rpartition("(")
    if text.endswith("()"):
        raise ValueError(f"empty brackets in {text!r}")
    labels = [label.strip() for label in added.split(",")] if added else []
    if core not in types:  # alterations written straight after the type: "7#9", "maj7#11"
        for end in range(len(core) - 1, -1, -1):
            if core[:end] in types and re.fullmatch(r"(?:[b#]\d+)+", core[end:]):
                core, labels = core[:end], [*re.findall(r"[b#]\d+", core[end:]), *labels]
                break
        else:
            raise ValueError(f"unknown chord type {core!r}")
    if len(set(labels)) < len(labels):
        raise ValueError(f"a note is written twice in {text!r}")
    if bad := [label for label in labels if not _WRITTEN.fullmatch(label)]:
        raise ValueError(f"not a chord tone: {', '.join(bad)} in {text!r}")
    if not core and "1" in labels:  # "(1,b9,9)": every note is listed, there is no core
        return PitchClassSet(tuple(map(_interval_step, labels)), TWELVE)
    if "1" in labels:
        raise ValueError(f"the root is written only when every note is: {text!r}")
    if "7" in labels:  # after a named core "(7)" would read as the flat one, so it is never written
        raise ValueError(f"after a chord type, write b7 or maj7, not 7: {text!r}")
    pattern = types[core]
    omitted = {_number(label[2:]) for label in labels if label.startswith("no")}
    own = {_number(name) for name in chord_tone_names(pattern)}
    if omitted and (omitted - _OMITTABLE or omitted - own or 7 not in own):
        raise ValueError(f"only a seventh chord's own 3rd or 5th is left out, not {text!r}")
    notes = [label for label in labels if not label.startswith("no")]
    if omitted & {_number(label) for label in notes}:
        raise ValueError(f"a degree both left out and written in {text!r}")
    altered = {_number(label) for label in notes} | omitted
    kept = [
        step
        for step, name in zip(pattern, chord_tone_names(pattern), strict=True)
        if _number(name) not in altered
    ]
    written = [_interval_step(label) for label in notes]
    if len(set(written)) < len(written) or set(written) & set(kept):  # "C(##9)" is the C's own 3rd
        raise ValueError(f"a written tone is a note the chord already has: {text!r}")
    return PitchClassSet((*kept, *written), TWELVE)


def _number(name: str) -> int:
    """The degree an interval name counts: "b5" and "#5" are both 5, "maj7" is 7. Raises
    ValueError if there is no number."""
    number = name.strip().removeprefix("maj").lstrip("b#")
    if not number.isdigit():
        raise ValueError(f"not an interval: {name!r}")
    return int(number)


@cache
def _types() -> dict[str, PitchClassSet]:
    """Each written chord type, aliases too, back to its pattern: `_symbols` turned round."""
    types = {symbol: chord for chord, symbol in _symbols().items()}
    return types | {alias: types[symbol] for alias, symbol in load_aliases().items()}


@cache
def _symbols() -> dict[PitchClassSet, str]:
    """What follows the root for each chord the catalog names: (0, 3, 7, 10) is "m7"."""
    symbols = load_symbols()
    return {pattern: symbols[name] for name, pattern in load_chords().items()}
