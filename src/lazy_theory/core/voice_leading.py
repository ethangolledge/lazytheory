"""Voice leading: how far the notes of one pitch-class set move to reach another.

Why: two chords sound connected when their notes are close, whatever their roots. C major to
A minor moves one note by two steps; C major to F# major moves all three. That distance is a
measure of harmonic nearness that needs no theory of function, and it is what a player's hand
and a listener's ear both follow.

Theory it speaks to: voice-leading geometry (Tymoczko, "The Geometry of Musical Chords", 2006;
"A Geometry of Music", 2011) with the taxicab measure: total steps moved. Neo-Riemannian P, L
and R (Cohn 1997) are the triad pairs that hold two notes and move the third by one or two
steps: distance 1 or 2 here.

Could grow into: other measures (largest single move; squared moves, which punish leaps),
keys ranked by the distance between their scales (smooth modulations), and chord maps drawn by
distance. Distances here are between pitch-class sets; on an instrument, where each note is a
real pitch on a real string, see `instruments.rules.moved`.
"""

from dataclasses import dataclass
from functools import cache
from math import inf
from typing import NamedTuple

from lazy_theory.core.pcset import PitchClassSet, shortest


class Move(NamedTuple):
    source: int
    target: int
    steps: int  # signed, the shorter way round; a half-period move counts as upwards


@dataclass(frozen=True)
class VoiceLeading:
    moves: tuple[Move, ...]

    @property
    def distance(self) -> int:
        return sum(abs(move.steps) for move in self.moves)


def voice_leading(source: PitchClassSet, target: PitchClassSet) -> VoiceLeading:
    """The smallest total movement taking `source` to `target`.

    Every note of both sets takes part, so when the sizes differ some notes split or merge: a
    seventh chord resolving to a triad sends two voices to one note. Among equally small
    movements, the larger set's lowest notes take the other's lowest notes first.
    """
    if source.size != target.size:
        raise ValueError(f"sets have different sizes: {source.size} and {target.size}")
    if len(source) >= len(target):
        pairs = _cheapest_pairs(source, target)
    else:
        pairs = [(note, other) for other, note in _cheapest_pairs(target, source)]
    size = source.size
    return VoiceLeading(tuple(sorted(Move(s, t, shortest(t - s, size)) for s, t in pairs)))


def _cheapest_pairs(larger: PitchClassSet, smaller: PitchClassSet) -> list[tuple[int, int]]:
    """Pair each note of `larger` with a note of `smaller`, using all of `smaller`, for the
    least total movement.

    Exact, without trying every pairing: the cheapest finish for the notes still to pair
    depends only on which notes of `smaller` are used so far, so each such state is solved
    once (notes x 2 ** len(smaller) states).
    shortcut: fine to about 16 notes in the smaller set; past that, pair in circular order.
    """
    cost = [[abs(shortest(t - s, larger.size)) for t in smaller] for s in larger]
    targets = range(len(smaller))
    every = (1 << len(smaller)) - 1

    @cache
    def finish(note: int, used: int) -> float:
        if note == len(larger):
            return 0 if used == every else inf
        return min(cost[note][t] + finish(note + 1, used | 1 << t) for t in targets)

    pairs, used = [], 0
    for note, source in enumerate(larger):  # `min` keeps the first of equals: the lowest target
        chosen = min(targets, key=lambda t: cost[note][t] + finish(note + 1, used | 1 << t))
        pairs.append((source, smaller.pitch_classes[chosen]))
        used |= 1 << chosen
    return pairs
