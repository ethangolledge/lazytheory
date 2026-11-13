"""Voice leading: how far the notes of one pitch-class set move to reach another."""

from dataclasses import dataclass
from itertools import product
from typing import NamedTuple

from lazy_theory.core.pcset import PitchClassSet


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
    seventh chord resolving to a triad sends two voices to one note. Every pairing is tried,
    which suits chords; ties go to the first pairing in pitch-class order.
    """
    if source.size != target.size:
        raise ValueError(f"sets have different sizes: {source.size} and {target.size}")
    if len(source) >= len(target):
        pairs = _cheapest_pairs(source, target)
    else:
        pairs = [(note, other) for other, note in _cheapest_pairs(target, source)]
    size = source.size
    return VoiceLeading(tuple(sorted(Move(s, t, _shortest(s, t, size)) for s, t in pairs)))


def _cheapest_pairs(larger: PitchClassSet, smaller: PitchClassSet) -> list[tuple[int, int]]:
    """Pair each note of `larger` with a note of `smaller`, using all of `smaller`."""
    every_note = set(smaller)
    best = min(
        (choice for choice in product(smaller, repeat=len(larger)) if set(choice) == every_note),
        key=lambda choice: sum(
            abs(_shortest(s, t, larger.size)) for s, t in zip(larger, choice, strict=True)
        ),
    )
    return list(zip(larger, best, strict=True))


def _shortest(source: int, target: int, size: int) -> int:
    steps = (target - source) % size
    return steps - size if steps > size / 2 else steps
