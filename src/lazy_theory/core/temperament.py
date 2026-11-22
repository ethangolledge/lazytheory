"""Temperament: how integer steps map to frequency ratios.

Why: the rest of the library counts steps, because music is written and fingered in steps. A
string and an ear deal in frequency. This module is the one bridge between the two, so fret
positions, roughness and anything else physical asks it and nothing else guesses.

Theory it speaks to: equal temperament, where every step multiplies frequency by the same
ratio (the `size`th root of the period), and cents, the logarithmic unit in which intervals
add. The period is a parameter because the octave is a convention (docs/theory.md, section 2):
Bohlen-Pierce divides 3:1 into 13.

Could grow into: unequal temperaments and just intonation (a `ratio` looked up per step
instead of computed), and stretched tunings for stiff strings.
"""

from dataclasses import dataclass
from fractions import Fraction
from math import log, log2
from operator import index
from typing import Any, Protocol, overload


def ratio_to_cents(ratio: float) -> float:
    """Size of a frequency ratio in cents: 1200 per 2:1 octave."""
    return 1200 * log2(ratio)


class _Steps(Protocol):
    """An array of steps: anything that divides by a number."""

    def __truediv__(self, other: int, /) -> Any: ...


@dataclass(frozen=True)
class EqualTemperament:
    """`size` equal steps per `period`, a frequency ratio. 12-TET is EqualTemperament(12)."""

    size: int = 12
    period: Fraction = Fraction(2)

    def __post_init__(self) -> None:
        if index(self.size) < 1:
            raise ValueError(f"size must be positive, got {self.size}")
        if self.period <= 1:
            raise ValueError(f"period must be greater than 1, got {self.period}")

    @overload
    def ratio(self, step: float) -> float: ...
    @overload
    def ratio(self, step: _Steps) -> Any: ...
    def ratio(self, step: Any) -> Any:
        """Frequency ratio `step` steps above the root: any step, negative or fractional, or
        an array of them at once. The one place steps become frequency."""
        return float(self.period) ** (step / self.size)

    def steps(self, ratio: float) -> float:
        """Steps a frequency ratio spans, the inverse of `ratio`: 3:2 is 7.02 in twelve."""
        return self.size * log(ratio, float(self.period))

    def cents(self, step: float) -> float:
        """Size of `step` steps in cents: 100 a step in twelve to the octave."""
        return ratio_to_cents(self.ratio(step))
