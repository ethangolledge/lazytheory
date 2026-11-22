"""Phrases: rhythm as it is spoken, syllables in words in larger groups.

Why: an onset set says where notes start and nothing else. Say "ta-ka-di-mi ta-ki-ta" and
there are three things at once: a steady pulse, seven syllables that sound, and two words whose
first syllables are the accents. Leave a gap ("ta , di mi") or hold a syllable ("ta _ ki ta")
and the onsets change but the words don't. A Phrase keeps all of it: each token (a syllable or
a silence) with how many pulses it lasts and what it sounds like, and the groups the tokens
form, words inside bigger groups, the same nesting a meter has. Every measure that works on an
onset set still works, on `onsets` or `accents`, so a phrase adds to the library rather than
replacing anything.

Theory it speaks to: konnakol and solkattu, where a group of n pulses is a word of n
syllables and a rhythm is changed by regrouping the same stream (gati bhedam); tabla bols,
where the syllable names the stroke; the moves traditions vary a phrase by: repetition,
retrograde, speed change (kalam, layakari: the same phrase twice as fast is every length
halved), substitution (khali: the same bols without the bass), permutation of its parts
(the palta of a qa'ida, Kippen & Bel), and the cadences built from it (tihai, yati), whose
lengths `rhythm.cadence` solves.

Could grow into: phrases whose sounds carry dynamics, a hand per stroke (sticking), and a
grammar of variations: every phrase reachable from a theme by these moves.

Sounds are numbers: REST, NOTE (a note whose sound isn't chosen yet), or an id the catalog
gives a syllable. This module never learns a syllable's name; `rhythm.names` reads and writes text.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import reduce
from itertools import pairwise
from math import lcm
from operator import add

from lazy_theory.core.pcset import PitchClassSet, group_starts
from lazy_theory.rhythm.meter import Levels, check_nesting

REST, NOTE = -1, 0  # a silence; a note whose sound isn't chosen. Above 0: the catalog's sounds


@dataclass(frozen=True)
class Phrase:
    """Tokens, each lasting `lengths[i]` pulses (to the next token) and sounding `sounds[i]`,
    grouped by `groups`: levels over the tokens, coarsest first, each splitting the one above,
    the finest being words. A held syllable is a longer length; a silence is a REST token.
    Without `groups`, the whole phrase is one word."""

    lengths: tuple[int, ...]
    sounds: tuple[int, ...]
    groups: Levels = ()

    def __post_init__(self) -> None:
        lengths, sounds = tuple(self.lengths), tuple(self.sounds)
        if not lengths or len(lengths) != len(sounds):
            raise ValueError(f"need one sound per length, got {lengths} and {sounds}")
        if min(lengths) < 1 or min(sounds) < REST:
            raise ValueError(f"lengths must be positive and sounds REST or more, got {self}")
        groups = tuple(tuple(level) for level in self.groups) or ((len(lengths),),)
        check_nesting(groups)
        if sum(groups[0]) != len(lengths):
            raise ValueError(f"groups cover {sum(groups[0])} tokens, the phrase has {len(lengths)}")
        words = set(group_starts(groups[-1]))
        for i in range(1, len(sounds)):
            if sounds[i] == sounds[i - 1] == REST and i not in words:
                raise ValueError("two rests in a row inside a word: make them one longer rest")
        object.__setattr__(self, "lengths", lengths)
        object.__setattr__(self, "sounds", sounds)
        object.__setattr__(self, "groups", groups)

    @classmethod
    def notes(cls, onsets: PitchClassSet) -> Phrase:
        """One note per onset, held until the next (the last until the cycle ends), after a
        rest if the first pulse is silent: the onset set as a single word."""
        lead, held = _spans(onsets)
        return cls((*lead, *held), (REST,) * len(lead) + (NOTE,) * len(held))

    @classmethod
    def stream(cls, accents: PitchClassSet) -> Phrase:
        """A syllable on every pulse, a word starting at each accent: how konnakol speaks a
        rhythm ("ta-ki-ta ta-ka ta-ka" is 7/8 accented on 1, 4 and 6). Pulses before the first
        accent are one rest."""
        lead, words = _spans(accents)
        spoken = sum(words)
        return cls(
            (*lead, *(1,) * spoken),
            (REST,) * len(lead) + (NOTE,) * spoken,
            ((1,) * len(lead) + words,),
        )

    @classmethod
    def beats(cls, per_beat: Sequence[Sequence[int]]) -> Phrase:
        """Each beat's sounds dividing it evenly, one word per beat: a theka, where "dha-ge"
        is two strokes in one beat beside "dhin", one. The beats share a grid of the least
        common multiple of their divisions, so every length stays a whole number."""
        if not per_beat or not all(per_beat):
            raise ValueError("every beat needs at least one sound")
        grid = lcm(*map(len, per_beat))
        lengths: list[int] = []
        sounds: list[int] = []
        words = []
        for beat in per_beat:
            step, count = grid // len(beat), 0
            for sound in beat:
                if sound == REST and count and sounds[-1] == REST:
                    lengths[-1] += step  # rests in one beat are one rest
                else:
                    lengths.append(step)
                    sounds.append(sound)
                    count += 1
            words.append(count)
        return cls(tuple(lengths), tuple(sounds), (tuple(words),))

    @property
    def pulses(self) -> int:
        """How many pulses the phrase lasts."""
        return sum(self.lengths)

    @property
    def positions(self) -> tuple[int, ...]:
        """The pulse each token starts on."""
        return group_starts(self.lengths)

    def __len__(self) -> int:
        return len(self.lengths)

    def onsets(self, start: int = 0, size: int | None = None) -> PitchClassSet:
        """Where the phrase's sounding tokens start, placed from pulse `start` on a cycle of
        `size` pulses (its own length by default): the onset set every measure works on."""
        struck = [start + p for p, s in zip(self.positions, self.sounds, strict=True) if s != REST]
        return PitchClassSet(tuple(struck), size or self.pulses)

    def starts(self, level: int = -1) -> tuple[int, ...]:
        """The pulse each group of `level` starts on (-1: the words)."""
        positions = self.positions
        return tuple(positions[token] for token in group_starts(self.groups[level]))

    def accents(self, level: int = -1, start: int = 0, size: int | None = None) -> PitchClassSet:
        """The groups of `level` that start on a sounding token, as onsets: what a listener
        hears as accented when the first syllable of each word is stressed."""
        tokens = group_starts(self.groups[level])
        heard = [
            start + pulse
            for token, pulse in zip(tokens, self.starts(level), strict=True)
            if self.sounds[token] != REST
        ]
        return PitchClassSet(tuple(heard), size or self.pulses)

    # Moves: each a pure function, named as players name them.

    def __add__(self, other: Phrase) -> Phrase:
        """One phrase then the other. A phrase with fewer levels of groups repeats its
        coarsest, so joining is associative and every group of each survives."""
        depth = max(len(self.groups), len(other.groups))
        first, second = self._padded(depth), other._padded(depth)
        return Phrase(
            self.lengths + other.lengths,
            self.sounds + other.sounds,
            tuple(a + b for a, b in zip(first, second, strict=True)),
        )

    def __mul__(self, times: int) -> Phrase:
        """The phrase `times` times in a row."""
        if times < 1:
            raise ValueError(f"repeat at least once, got {times}")
        return reduce(add, [self] * times)

    def grouped(self) -> Phrase:
        """The whole phrase as one group above its own: a statement to repeat or to cut."""
        return Phrase(self.lengths, self.sounds, ((len(self),), *self.groups))

    def regrouped(self, sizes: Sequence[int]) -> Phrase:
        """The same tokens in new words of `sizes` tokens, every other level dropped: gati
        bhedam, a stream of 4s heard in 3s."""
        return Phrase(self.lengths, self.sounds, (tuple(sizes),))

    def rotated(self, groups: int) -> Phrase:
        """Started from its group `groups` of the top level, wrapping round."""
        cut = group_starts(self.groups[0])[groups % len(self.groups[0])]
        if not cut:
            return self
        return self._cut(cut, len(self)) + self._cut(0, cut)

    def reversed(self) -> Phrase:
        """Retrograde: the tokens in reverse order, each keeping its length."""
        return Phrase(
            self.lengths[::-1], self.sounds[::-1], tuple(level[::-1] for level in self.groups)
        )

    def scaled(self, factor: int) -> Phrase:
        """Every length times `factor`: the phrase at 1/`factor` of the speed, or the same
        phrase counted on a grid `factor` times finer (to join one twice as fast)."""
        if factor < 1:
            raise ValueError(f"factor must be positive, got {factor}")
        return Phrase(tuple(n * factor for n in self.lengths), self.sounds, self.groups)

    def faster(self, factor: int) -> Phrase:
        """Every length divided by `factor`: `factor` times the speed. Raises if a length
        doesn't divide; `scaled` the rest of the music instead."""
        if factor < 1 or any(n % factor for n in self.lengths):
            raise ValueError(f"lengths {self.lengths} don't all divide by {factor}")
        return Phrase(tuple(n // factor for n in self.lengths), self.sounds, self.groups)

    def substituted(self, sounds: Mapping[int, int]) -> Phrase:
        """Each sound replaced by its entry in `sounds`, others kept: khali, the same bols
        without the bass (dha to ta)."""
        return Phrase(self.lengths, tuple(sounds.get(s, s) for s in self.sounds), self.groups)

    def permuted(self, order: Sequence[int]) -> Phrase:
        """The groups of the top level in a new `order` (each index once): the palta of a
        qa'ida, its parts rearranged."""
        top = self.groups[0]
        if sorted(order) != list(range(len(top))):
            raise ValueError(f"order must use each of the {len(top)} groups once, got {order}")
        bounds = (*group_starts(top), len(self))
        return reduce(add, [self._cut(bounds[i], bounds[i + 1]) for i in order])

    def tihai(self, gap: int, times: int = 3, hold: bool = False) -> Phrase:
        """The phrase `times` times with `gap` pulses after each but the last, each statement a
        group: a tihai (mora). The gap is a rest, or with `hold` the last syllable held.
        `rhythm.cadence.tihais` gives the lengths that land."""
        if gap < 0:
            raise ValueError(f"gap must not be negative, got {gap}")
        statement = self.grouped()
        if not gap:
            body = statement
        elif hold:
            body = Phrase(
                (*self.lengths[:-1], self.lengths[-1] + gap), self.sounds, statement.groups
            )
        else:
            body = (self + Phrase((gap,), (REST,))).grouped()
        return body * (times - 1) + statement if times > 1 else statement

    def yati(self, sizes: Sequence[int], keep: str = "end") -> Phrase:
        """Statements of the phrase cut to `sizes` tokens each, keeping its `end` (or its
        `start`), each a group: growing sizes are srotovaha, shrinking gopuccha.
        `rhythm.cadence.yatis` gives sizes that fill a span."""
        if keep not in ("end", "start") or not sizes:
            raise ValueError(f"keep the 'end' or the 'start' of at least one size, got {keep}")
        if not all(1 <= size <= len(self) for size in sizes):
            raise ValueError(f"sizes must be between 1 and {len(self)}, got {sizes}")
        n = len(self)
        cut = [self._cut(n - s, n) if keep == "end" else self._cut(0, s) for s in sizes]
        return reduce(add, [statement.grouped() for statement in cut])

    def _padded(self, depth: int) -> Levels:
        return (self.groups[0],) * (depth - len(self.groups)) + self.groups

    def _cut(self, first: int, stop: int) -> Phrase:
        """Tokens `first` to `stop`, with each group cut where it crosses an end."""
        levels = []
        for level in self.groups:
            marks = sorted({first, stop} | {s for s in group_starts(level) if first < s < stop})
            levels.append(tuple(b - a for a, b in pairwise(marks)))
        return Phrase(self.lengths[first:stop], self.sounds[first:stop], tuple(levels))


def _spans(points: PitchClassSet) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """The silence before the first point (empty if it is on 0), then the pulses from each point
    to the next, the last running to the end of the cycle rather than round to the first. With
    no points, the whole cycle is silence."""
    if not points.pitch_classes:
        return (points.size,), ()
    first = points.pitch_classes[0]
    return (first,) if first else (), tuple(b - a for a, b in pairwise((*points, points.size)))
