"""Guest over host: a repeating pattern laid over a meter, and how the two pull apart and meet.

Why: accent every third beat through four bars of 4/4 and the bar seems to become 3/4; put
a crash on every fourth eighth of a 7/8 and the two cycles drift past each other. The meter is
the host, the accented pattern the guest. The tension comes from where they disagree and the
release from where they land together, so both are worth computing: what kind of
disagreement it is, when they next meet, and how to finish the guest so it lands on one.
The host doesn't have to sound: one accented line is heard against the meter the listener
expects, which is why every measure here takes the host's group size, never the notes alone.

Theory it speaks to: metrical dissonance (Krebs, "Fantasy Pieces", 1999). A grouping
dissonance (G3/4) is a guest whose groups neither divide nor are divided by the host's; a
displacement dissonance (D3+1) is a guest of the same groups started late or early. Krebs
calls it subliminal when only the guest is heard. Finishing a guest to land on one is the
Indian mora and tihai, and the fills come from the same compositions as every meter. Parts
that interlock (Balinese kotekan: each of two players fills the other's gaps) are the same
arithmetic on one cycle: a second part is the complement of the first, or a note in each of its
gaps. A cadence is a tihai made from the rhythm's own opening.

Could grow into: several guests at once (a tihai of tihais), dissonance measured against every
level of a meter at once, and a guest whose pattern changes as it repeats (yati shapes: each
statement longer or shorter by a fixed step).
"""

from collections.abc import Collection, Iterator
from math import gcd
from typing import NamedTuple

from lazy_theory.core.pcset import PitchClassSet, shortest
from lazy_theory.rhythm.meter import compositions, gaps, grouping


class Dissonance(NamedTuple):
    """Krebs' label, as numbers. `grouping` (a, b) is G a/b; `displacement` (a, k) is D a+k,
    k negative when the guest is early. Both None when the guest sits inside the host."""

    grouping: tuple[int, int] | None
    displacement: tuple[int, int] | None


def dissonance(period: int, offset: int, host: int) -> Dissonance:
    """How a guest repeating every `period` pulses, starting on pulse `offset`, disagrees with
    host groups of `host` pulses, both counted in their largest common unit. A 3-beat guest
    over a 4-beat bar is G3/4; a 3-beat guest one beat late in 3/4 is D3+1."""
    if period < 1 or host < 1:
        raise ValueError(f"groups must be positive, got {period} and {host}")
    common = gcd(period, host)
    if common not in (period, host):
        return Dissonance((period // common, host // common), None)
    shift = shortest(offset, common)
    if shift == 0:
        return Dissonance(None, None)
    unit = gcd(common, shift)
    return Dissonance(None, (common // unit, shift // unit))


def meets(period: int, offset: int, host: int) -> int | None:
    """The first pulse after 0 where a guest group and a host group start together, or None if
    they never do. A 3 over a 4 meets at 12; displaced by 1 over a 3, never."""
    if offset % gcd(period, host):
        return None
    pulse = offset % period or period
    while pulse % host:
        pulse += period
    return pulse


def fills(period: int, length: int, parts: Collection[int] = (2, 3)) -> Iterator[tuple[int, ...]]:
    """Ways to fill `length` pulses with a guest of `period`, as many repeats as possible
    first, then the rest made of `parts`, so the next group lands on the cycle's first pulse.
    Each comes once: a tail never starts with another full `period`."""
    for repeats in range(length // period, -1, -1):
        tail = length - repeats * period
        for ending in compositions(tail, parts):
            if not ending or ending[0] != period:
                yield (period,) * repeats + ending


def midpoints(points: PitchClassSet) -> tuple[int, ...]:
    """A note inside each gap of two or more, where `grouping` splits it (4 as 2+2, 5 as
    2+3, 3 as 1+2): the call and response of a second part answering each note."""
    return tuple(
        point + grouping(gap)[0] for point, gap in zip(points, gaps(points), strict=True) if gap > 1
    )
