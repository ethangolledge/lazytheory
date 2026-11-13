"""Temperaments: how integer steps map to frequency ratios.

The rest of the library works in steps. This module is where steps meet physics.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from fractions import Fraction
from itertools import pairwise
from math import log2


def ratio_to_cents(ratio: float) -> float:
    """Size of a frequency ratio in cents: 1200 per 2:1 octave."""
    return 1200 * log2(ratio)


class Temperament(ABC):
    """A system of `size` steps per `period`, where `period` is a frequency ratio (2 for octaves)."""

    period: Fraction

    @property
    @abstractmethod
    def size(self) -> int:
        """Number of steps per period."""

    @abstractmethod
    def ratio(self, step: int) -> float:
        """Frequency ratio `step` steps above the root. Any integer step, including negative."""

    def cents(self, step: int) -> float:
        return ratio_to_cents(self.ratio(step))


@dataclass(frozen=True)
class EqualTemperament(Temperament):
    """`size` equal steps per period. 12-TET is EqualTemperament(12)."""

    size: int = 12
    period: Fraction = Fraction(2)

    def __post_init__(self) -> None:
        if self.size < 1:
            raise ValueError(f"size must be positive, got {self.size}")
        if self.period <= 1:
            raise ValueError(f"period must be greater than 1, got {self.period}")

    def ratio(self, step: int) -> float:
        return float(self.period) ** (step / self.size)


@dataclass(frozen=True)
class JustIntonation(Temperament):
    """Steps tuned to exact ratios: `ratios` lists one period, starting at 1/1."""

    ratios: tuple[Fraction, ...]
    period: Fraction = Fraction(2)

    def __post_init__(self) -> None:
        if not self.ratios or self.ratios[0] != 1:
            raise ValueError("the first ratio must be 1/1 (the root)")
        if any(low >= high for low, high in pairwise(self.ratios)):
            raise ValueError("ratios must be strictly increasing")
        if self.ratios[-1] >= self.period:
            raise ValueError("ratios must be smaller than the period")

    @property
    def size(self) -> int:
        return len(self.ratios)

    def ratio(self, step: int) -> float:
        periods, step = divmod(step, self.size)
        return float(self.period**periods * self.ratios[step])
