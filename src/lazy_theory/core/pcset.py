"""Pitch-class sets: the one piece of maths every scale, chord and key is made of.

Why: hearing treats notes a period (usually an octave) apart as the same note, so harmony
lives on a circle of `size` steps, not on a line. A set of points on that circle is all a
scale or a chord is; everything else (modes, inversions, transposition) is an operation on it.
Twelve steps is the default, never an assumption: `size` travels with every set, so 19- or
31-step tunings and the Bohlen-Pierce scale use the same code.

Theory it speaks to: pitch-class set theory (Forte; Rahn), and maximal evenness (Clough &
Douthett 1991), which derives the diatonic scale, the whole-tone scale and the diminished
seventh from one formula instead of listing them.

Could grow into: interval vectors (how many of each interval a set holds: its colour),
set classes under transposition and inversion, and subset search ("every key holding this
chord"), each a few lines on top of `rotate`, `transpose` and `in`.
"""

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from itertools import accumulate
from numbers import Integral
from typing import Self


def shortest(steps: int, size: int) -> int:
    """`steps` round a circle of `size` taken the shorter way, so signed: 11 up in 12 is -1.
    Half way round counts as up."""
    steps %= size
    return steps - size if steps > size / 2 else steps


@dataclass(frozen=True, eq=False)
class PitchClassSet:
    """Pitch classes in a system of `size` steps per period.

    Members are reduced mod `size` and stored sorted without duplicates, so (12, 7, 4, 0) and
    (0, 4, 7) are the same set. Sets compare by their members and size alone: a Scale equals
    the plain set of its notes.
    """

    pitch_classes: tuple[int, ...]
    size: int = 12

    def __post_init__(self) -> None:
        if self.size < 1:
            raise ValueError(f"size must be positive, got {self.size}")
        normalised = tuple(sorted({pc % self.size for pc in self.pitch_classes}))
        if not normalised:
            raise ValueError("a pitch-class set needs at least one member")
        object.__setattr__(self, "pitch_classes", normalised)

    @classmethod
    def from_steps(cls, steps: Iterable[int]) -> Self:
        """Build from a step pattern starting on 0. The steps sum to `size`.

        (2, 2, 1, 2, 2, 2, 1) gives (0, 2, 4, 5, 7, 9, 11) with size 12.
        """
        steps = tuple(steps)
        if not steps or any(step < 1 for step in steps):
            raise ValueError(f"steps must be positive, got {steps}")
        return cls(tuple(accumulate(steps[:-1], initial=0)), sum(steps))

    @classmethod
    def maximally_even(cls, notes: int, size: int = 12) -> Self:
        """`notes` pitch classes spread as evenly as possible through `size` steps.

        4 in 12 is the diminished seventh, 6 in 12 the whole-tone scale, 7 in 12 a diatonic mode.
        """
        if not 0 < notes <= size:
            raise ValueError(f"notes must be between 1 and {size}, got {notes}")
        return cls(tuple(i * size // notes for i in range(notes)), size)

    def rotate(self, degree: int) -> Self:
        """Re-root on the member at `degree` (0-based, wraps). For a scale, this gives its modes."""
        root = self.pitch_classes[degree % len(self)]
        return type(self)(tuple(pc - root for pc in self.pitch_classes), self.size)

    def transpose(self, steps: int) -> PitchClassSet:
        """Move every member up by `steps`. A moved scale no longer starts on its root, so the
        result is always a plain PitchClassSet."""
        return PitchClassSet(tuple(pc + steps for pc in self.pitch_classes), self.size)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PitchClassSet):
            return NotImplemented
        return self.pitch_classes == other.pitch_classes and self.size == other.size

    def __hash__(self) -> int:
        return hash((self.pitch_classes, self.size))

    def __contains__(self, pitch: object) -> bool:
        """Whether a pitch, in any period, is one of the set's pitch classes."""
        return isinstance(pitch, Integral) and pitch % self.size in self.pitch_classes

    def __len__(self) -> int:
        return len(self.pitch_classes)

    def __iter__(self) -> Iterator[int]:
        return iter(self.pitch_classes)
