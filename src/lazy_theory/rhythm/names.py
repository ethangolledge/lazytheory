"""Numbers into words and back for rhythm: phrases as text, spoken systems, counting, time
signatures, tala marks and Krebs' labels. The one place the library writes or reads them.

Why: a phrase is numbers (lengths, sound ids, groups); how it is said depends on the
tradition. Konnakol says the group, Takadimi the place in the beat, bols the stroke, a
guitarist counts "1 e & a". One phrase, many spellings, each written and read here only.
"""

import re
from collections.abc import Callable, Sequence
from functools import cache, reduce
from itertools import pairwise
from operator import add

from lazy_theory.core.pcset import PitchClassSet, group_starts
from lazy_theory.rhythm.catalog import load_spoken, syllable_id
from lazy_theory.rhythm.layers import Dissonance
from lazy_theory.rhythm.meter import CLAP, WAVE, Meter, grouping
from lazy_theory.rhythm.phrase import NOTE, REST, Phrase
from lazy_theory.rhythm.stroke import voicing


def counting(meter: Meter, bar: int) -> tuple[str, ...]:
    """A word per grid point, as a guitarist counts: each count's number (1 to `bar`, the
    counts in a bar), then the catalog's words for how it is split ("1 & 2 &", "1 trip let",
    "1 e & a"); a split the catalog doesn't count is said in its konnakol word ("1 ka ta ki ta")."""
    said = load_spoken().counting
    return tuple(
        str(count % bar + 1) if not index else (said.get(split) or _word(split)[1:])[index - 1]
        for count, split, index in _places(meter)
    )


def counted(phrase: Phrase, meter: Meter, bar: int) -> str:
    """`phrase` (on `meter`'s grid) written in `counting`'s words: each note the word for
    where it falls ("1 & a"), holds and rests as `phrase_text` writes them."""
    words = counting(meter, bar)
    if phrase.pulses != len(words):
        raise ValueError(f"the phrase has {phrase.pulses} pulses, the meter's grid {len(words)}")
    positions = phrase.positions
    return _text(phrase, lambda token: words[positions[token]])


def spell(phrase: Phrase, system: str, meter: Meter | None = None) -> Phrase:
    """`phrase` with a syllable for each note whose sound isn't chosen (NOTE), in a spoken
    `system`; chosen sounds are kept. Systems say three different things:

    - "konnakol" says the group: each word's notes are the catalog's word for that many
      ("ta-ki-ta" for three), so the syllable tells you where you are in the word;
    - "takadimi" says the position in the beat ("di" is always its middle), from `meter`;
    - "bols" says the sound: each note's stroke (`rhythm.stroke.voicing`, the first syllable of
      each word accented), as the first bol the catalog lists for that stroke.

    The position and sound systems need `meter`, with the phrase on its grid."""
    spoken = load_spoken()
    sounds = list(phrase.sounds)
    chosen: list[str | None] = [None] * len(phrase)
    if system == "konnakol":
        words = phrase.groups[-1]
        for start, size in zip(group_starts(words), words, strict=True):
            notes = [t for t in range(start, start + size) if sounds[t] != REST]
            for token, name in zip(notes, _word(len(notes)) if notes else (), strict=True):
                chosen[token] = name
    elif system in ("takadimi", "bols"):
        if meter is None or phrase.pulses != len(meter.starts(-1)):
            raise ValueError(f"{system} needs a meter whose grid has the phrase's pulses")
        positions = phrase.positions
        if system == "takadimi":
            places = _places(meter)
            for token, position in enumerate(positions):
                _, split, index = places[position]
                if split not in spoken.takadimi:
                    raise ValueError(f"takadimi has no syllables for {split} to a beat")
                chosen[token] = spoken.takadimi[split][index]
        else:
            bols = {stroke: bol for bol, stroke in reversed(list(spoken.strokes.items()))}
            try:
                accents: PitchClassSet | None = meter.from_grid(phrase.accents())
            except ValueError:
                accents = None
            strokes = voicing(meter.from_grid(phrase.onsets()), meter, accents)
            for token, position in enumerate(positions):
                if sounds[token] != REST:
                    chosen[token] = bols.get(strokes[position])
    else:
        raise ValueError(f"unknown system {system!r}: konnakol, takadimi or bols")
    for token, said in enumerate(chosen):
        if sounds[token] == NOTE:
            if said is None:
                raise ValueError(f"{system} has no syllable for token {token}")
            sounds[token] = syllable_id(said)
    return Phrase(phrase.lengths, tuple(sounds), phrase.groups)


def phrase_text(phrase: Phrase) -> str:
    """A spelled phrase as text: syllables of a word joined by "-", a held pulse "_", a silent
    pulse ",", words separated by spaces, and each group above the words in brackets:
    "[ta-ka-di-mi ta ,] [ta-ka-di-mi ta ,] [ta-ka-di-mi ta]". `parse_phrase` reads it back
    exactly. Raises for a note with no syllable: `spell` it first."""
    names = load_spoken().names

    def name(token: int) -> str:
        if phrase.sounds[token] == NOTE:
            raise ValueError("a note has no syllable yet: spell the phrase first")
        return names[phrase.sounds[token] - 1]

    return _text(phrase, name)


def parse_phrase(text: str) -> Phrase:
    """Text back into a phrase, the inverse of `phrase_text`. Words are separated by spaces;
    inside one, syllables are joined by "-" or run together ("takita" is ta-ki-ta), "_" holds
    the syllable before one more pulse and "," is a silent pulse. "[ ... ]" makes a group of
    words (or of groups), and "[ ... ]x3" plays it three times: "[ta-ka-di-mi ta ,]x2
    [ta-ka-di-mi ta]" is a tihai. Raises ValueError saying what's wrong, including text that
    splits into syllables two ways."""
    stack: list[list[Phrase]] = [[]]
    for piece in re.findall(r"\[|\](?:x\d+)?|[^\s\[\]]+", text.lower()):
        if piece == "[":
            stack.append([])
        elif piece.startswith("]"):
            if len(stack) == 1 or not stack[-1]:
                raise ValueError("brackets must open before they close and hold something")
            group = reduce(add, stack.pop()).grouped()
            stack[-1].append(group * int(piece[2:] or 1))
        else:
            stack[-1].append(_parse_word(piece))
    if len(stack) != 1:
        raise ValueError("a bracket is never closed")
    if not stack[0]:
        raise ValueError("a phrase needs at least one syllable")
    return reduce(add, stack[0])


def tala_marks(meter: Meter) -> tuple[str, ...]:
    """The mark under each beat of a cycle kept by hand, as Hindustani notation writes them:
    claps numbered in order, the first "X" when it falls on sam, a wave "0"; fingers and
    beats without a gesture "". Teentaal's sections read X 2 0 3."""
    marks, claps = [], 0
    for beat, hand in enumerate(meter.hands):
        if hand == CLAP:
            claps += 1
            marks.append("X" if beat == 0 else str(claps))
        else:
            marks.append("0" if hand == WAVE else "")
    return tuple(marks)


def khali(phrase: Phrase) -> Phrase:
    """The phrase's bols without their bass, as a theka's khali section plays them."""
    swaps = load_spoken().khali.items()
    return phrase.substituted({syllable_id(a): syllable_id(b) for a, b in swaps})


def jam_name(split: int, group: int) -> str:
    """An idea said plainly: "16ths in 3s", the subdivision and the group size it runs in."""
    return f"{load_spoken().subdivisions.get(split, f'{split} per count')} in {group}s"


def parse_meter(text: str, division: int | Sequence[int] = 1, bars: int = 1) -> Meter:
    """A time signature into a meter: "7/8" groups its 7 counts by `grouping` (3+2+2);
    "2+2+3/8" says how. The lower number names the count's note value and doesn't change the
    grid. `division` splits each count further, as in `Meter.of`; the cycle is `bars` bars."""
    top, slash, bottom = text.replace(" ", "").partition("/")
    groups = top.split("+")
    if not slash or not bottom.isdigit() or not all(group.isdigit() for group in groups):
        raise ValueError(f"write a meter as 7/8 or 2+2+3/8, got {text!r}")
    if int(bottom) < 1 or any(int(group) < 1 for group in groups) or bars < 1:
        raise ValueError(f"a meter's numbers must be positive, got {text!r} x {bars}")
    return Meter.of([int(group) for group in groups], division, bars)


def dissonance_label(dissonance: Dissonance) -> str:
    """Krebs' label: "G3/4" for a grouping dissonance, "D3+1" or "D3-1" for a displacement,
    "aligned" when the guest sits inside the host."""
    if dissonance.grouping:
        return "G{}/{}".format(*dissonance.grouping)
    if dissonance.displacement:
        return "D{}{:+d}".format(*dissonance.displacement)
    return "aligned"


def _word(size: int) -> tuple[str, ...]:
    """The syllables of a group of `size` pulses: the catalog's word, or the words of its two
    halves by `grouping`."""
    words = load_spoken().words
    if size in words:
        return words[size]
    return tuple(syllable for part in grouping(size) for syllable in _word(part))


def _places(meter: Meter) -> list[tuple[int, int, int]]:
    """For each grid point: its count, how many points that count is split into, and which
    of them it is."""
    grid = meter.starts(-1).pitch_classes
    counts = (*meter.starts(meter.beat).pitch_classes, meter.pulses)
    places = []
    for count, (start, end) in enumerate(pairwise(counts)):
        split = sum(1 for point in grid if start <= point < end)
        places += [(count, split, index) for index in range(split)]
    return places


def _text(phrase: Phrase, name: Callable[[int], str]) -> str:
    """`phrase` written with `name` for each sounding token: see `phrase_text`."""
    spoken = load_spoken()

    def word(first: int, stop: int) -> str:
        items = []
        for token in range(first, stop):
            length = phrase.lengths[token]
            if phrase.sounds[token] == REST:
                items += [spoken.rest] * length
            else:
                items += [name(token), *[spoken.hold] * (length - 1)]
        return "-".join(items)

    def groups(level: int, first: int, stop: int) -> str:
        starts = [s for s in group_starts(phrase.groups[level]) if first <= s < stop]
        bounds = pairwise((*starts, stop))
        if level == len(phrase.groups) - 1:
            return " ".join(word(a, b) for a, b in bounds)
        return " ".join(f"[{groups(level + 1, a, b)}]" for a, b in bounds)

    return groups(0, 0, len(phrase))


def _parse_word(piece: str) -> Phrase:
    """One word of `parse_phrase`: its syllables, rests and holds as tokens."""
    spoken = load_spoken()
    lengths: list[int] = []
    sounds: list[int] = []
    for item in (item for part in piece.split("-") if part for item in _syllables(part)):
        if item == spoken.hold:
            if not sounds or sounds[-1] == REST:
                raise ValueError(f"{piece!r}: a hold must follow a syllable in its word")
            lengths[-1] += 1
        elif item == spoken.rest and sounds and sounds[-1] == REST:
            lengths[-1] += 1
        else:
            lengths.append(1)
            sounds.append(REST if item == spoken.rest else syllable_id(item))
    if not lengths:
        raise ValueError(f"{piece!r} has no syllables")
    return Phrase(tuple(lengths), tuple(sounds))


@cache
def _syllables(piece: str) -> tuple[str, ...]:
    """`piece` ("takita", ",") split into the catalog's syllables, rests and holds. Raises
    ValueError if no split works, or if two do."""
    spoken = load_spoken()
    known = sorted(spoken.syllables | {spoken.rest, spoken.hold})
    ways: list[list[tuple[str, ...]]] = [[] for _ in piece] + [[()]]
    for start in reversed(range(len(piece))):
        for syllable in known:
            if piece.startswith(syllable, start):
                ways[start] += [(syllable, *rest) for rest in ways[start + len(syllable)]]
        del ways[start][2:]  # two readings are already too many
    if not ways[0]:
        raise ValueError(f"{piece!r} isn't made of known syllables")
    if len(ways[0]) > 1:
        raise ValueError(f"{piece!r} reads as {' or '.join('-'.join(w) for w in ways[0])}")
    return ways[0][0]
