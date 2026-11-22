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

from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from itertools import accumulate
from numbers import Integral
from operator import index
from typing import Self, overload


def shortest[N: (int, float)](steps: N, size: int) -> N:
    """`steps` round a circle of `size` taken the shorter way, so signed: 11 up in 12 is -1.
    Half way round counts as up. Works for times too: 7.5 pulses on a cycle of 8 is -0.5."""
    if size < 1:
        raise ValueError(f"a circle has at least one step, got {size}")
    steps %= size
    return steps - size if steps > size / 2 else steps


def group_starts(lengths: Sequence[int]) -> tuple[int, ...]:
    """Where each of a run of `lengths` starts, the first at 0: (3, 2, 2) starts at 0, 3 and 5.
    The inverse of `rhythm.meter.gaps`: meters, phrases and step patterns all lay groups end to
    end. No lengths, no starts."""
    return tuple(accumulate(lengths[:-1], initial=0)) if lengths else ()


@dataclass(frozen=True, eq=False)
class PitchClassSet:
    """Pitch classes in a system of `size` steps per period.

    Members are reduced mod `size` and stored sorted without duplicates, so (12, 7, 4, 0) and
    (0, 4, 7) are the same set. Sets compare by their members and size alone: a Scale equals
    the plain set of its notes. A set may be empty: a bar of silence is a rhythm too.
    """

    pitch_classes: tuple[int, ...]
    size: int = 12

    def __post_init__(self) -> None:
        if isinstance(self.size, bool) or index(self.size) < 1:
            raise ValueError(f"size must be a positive whole number, got {self.size}")
        if isinstance(self.pitch_classes, PitchClassSet) and self.pitch_classes.size != self.size:
            raise ValueError(  # reducing mod another size would make a different set
                f"a {self.pitch_classes.size}-step set given size {self.size}: pass its size"
            )
        normalised = tuple(sorted({index(pc) % self.size for pc in self.pitch_classes}))
        object.__setattr__(self, "pitch_classes", normalised)

    @classmethod
    def from_steps(cls, steps: Iterable[int]) -> Self:
        """Build from a step pattern starting on 0. The steps sum to `size`.

        (2, 2, 1, 2, 2, 2, 1) gives (0, 2, 4, 5, 7, 9, 11) with size 12.
        """
        steps = tuple(steps)
        if not steps or any(step < 1 for step in steps):
            raise ValueError(f"steps must be positive, got {steps}")
        return cls(group_starts(steps), sum(steps))

    @classmethod
    def maximally_even(cls, notes: int, size: int = 12) -> Self:
        """`notes` pitch classes spread as evenly as possible through `size` steps.

        4 in 12 is the diminished seventh, 6 in 12 the whole-tone scale, 7 in 12 a diatonic mode.
        """
        if not 0 <= notes <= size:
            raise ValueError(f"notes must be between 0 and {size}, got {notes}")
        return cls(tuple(i * size // notes for i in range(notes)), size)

    def rotate(self, degree: int) -> Self:
        """Re-root on the member at `degree` (0-based, wraps). For a scale, this gives its modes.
        Raises ValueError for an empty set, which has no member to re-root on."""
        if not self.pitch_classes:
            raise ValueError("an empty set has no member to re-root on")
        root = self.pitch_classes[degree % len(self)]
        return type(self)(tuple(pc - root for pc in self.pitch_classes), self.size)

    def necklace(self) -> Self:
        """The rotation with the lowest members, the same for every rotation and transposition:
        compare two sets with it to ask whether one is a mode or displacement of the other.
        An empty set is its own necklace."""
        rotations = (self.rotate(degree) for degree in range(len(self)))
        return min(rotations, key=lambda s: s.pitch_classes, default=self)

    def complement(self) -> PitchClassSet:
        """Every pitch class the set leaves out: the notes outside a scale, or the gaps a second
        rhythm part fills. Empty for a full set."""
        return PitchClassSet(tuple(set(range(self.size)) - set(self.pitch_classes)), self.size)

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

    @overload
    def __getitem__(self, index: int) -> int: ...
    @overload
    def __getitem__(self, index: slice) -> tuple[int, ...]: ...
    def __getitem__(self, index: int | slice) -> int | tuple[int, ...]:
        """Members in rising order, so a set reads like the sorted sequence it is: the first
        onset of a rhythm is `onsets[0]`."""
        return self.pitch_classes[index]

    def __iter__(self) -> Iterator[int]:
        return iter(self.pitch_classes)
