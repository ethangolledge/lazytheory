"""Temperament: how integer steps map to frequency ratios.

The rest of the library works in steps. This module is where steps meet physics.
"""

from dataclasses import dataclass
from fractions import Fraction
from math import log2, pow


def ratio_to_cents(ratio: float) -> float:
    """Size of a frequency ratio in cents: 1200 per 2:1 octave."""
    return 1200 * log2(ratio)


@dataclass(frozen=True)
class EqualTemperament:
    """`size` equal steps per `period`, a frequency ratio. 12-TET is EqualTemperament(12)."""

    size: int = 12
    period: Fraction = Fraction(2)

    def __post_init__(self) -> None:
        if self.size < 1:
            raise ValueError(f"size must be positive, got {self.size}")
        if self.period <= 1:
            raise ValueError(f"period must be greater than 1, got {self.period}")

    def ratio(self, step: int) -> float:
        """Frequency ratio `step` steps above the root. Any integer step, including negative."""
        return pow(self.period, step / self.size)

    def cents(self, step: int) -> float:
        return ratio_to_cents(self.ratio(step))
