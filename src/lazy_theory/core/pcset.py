"""Pitch-class sets: the maths shared by scales and chords."""

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from itertools import accumulate
from typing import Self


@dataclass(frozen=True)
class PitchClassSet:
    """Pitch classes in a system of `size` steps per period.

    Members are reduced mod `size` and stored sorted without duplicates, so (12, 7, 4, 0) and
    (0, 4, 7) are the same set.
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

    def __len__(self) -> int:
        return len(self.pitch_classes)

    def __iter__(self) -> Iterator[int]:
        return iter(self.pitch_classes)
