"""Performances: a rhythm as it was played, kept exactly, before anyone decides what it means.

Why: a tapped rhythm carries its feel in its timing: a note a little early, swing, a push. An
onset set or a phrase can only hold whole pulses, so storing taps in one would round them to a
grid and lose that for good. A Performance keeps every onset at the time it was played within
the cycle, in counts from its first count: only the lap a tap fell in and the order taps were
made are dropped (the cycle repeats, so they say nothing about the rhythm). Reading it onto a
grid (`placed`) is a separate, explicit step that returns a new value beside it, with how far
each onset was from its grid point, so the reading can always be redone with another grid or
another swing and the playing is never lost.

Theory it speaks to: expressive timing as deviation from a metrical grid (the onset is the
data; the grid is an interpretation of it), and swing as a timing map (`Meter.timing`), whose
inverse is what `placed` applies.

Could grow into: choosing the grid itself from the timing (the simplest grid that explains
the onsets within the player's own spread, Cemgil & Kappen's rhythm quantisation), a player's
habitual lead or lag subtracted before reading, and tempo drift across laps.
"""

from dataclasses import dataclass
from math import isfinite
from operator import index
from typing import NamedTuple

from lazy_theory.core.pcset import PitchClassSet, shortest
from lazy_theory.rhythm.meter import Meter


class Placement(NamedTuple):
    """A grid reading of a performance: each onset's grid point (pulses of the meter, in the
    performance's order: two onsets on one point show up as a repeat, so a caller can tell the
    grid was too coarse) and how far the onset was from it, in counts (negative: early)."""

    points: tuple[int, ...]
    offsets: tuple[float, ...]

    def onsets(self, pulses: int) -> PitchClassSet:
        """The points as an onset set on a cycle of `pulses`, repeats merged."""
        return PitchClassSet(self.points, pulses)


@dataclass(frozen=True)
class Performance:
    """Onsets as played: `times` in counts from the cycle's first count, over a cycle of
    `counts` counts. A time from another lap is folded into the cycle and times are sorted, so
    they are kept in the order they sound within it, not the order they were tapped. No onsets
    at all is a performance of silence."""

    times: tuple[float, ...]
    counts: int

    def __post_init__(self) -> None:
        if index(self.counts) < 1:
            raise ValueError(f"a cycle needs at least one count, got {self.counts}")
        if not all(isfinite(time) for time in self.times):
            raise ValueError(f"times must be finite, got {self.times}")
        object.__setattr__(self, "times", tuple(sorted(_fold(t, self.counts) for t in self.times)))

    def placed(self, meter: Meter, swing: float = 1.0) -> Placement:
        """Each onset on the grid point of `meter` that sounds nearest to it when the grid is
        played with `swing` (`Meter.timing`), the shorter way round the cycle, and how far off
        it was. The meter must have one beat per count; a beat split differently from the
        others (a quintuplet among sixteenths) is measured in its own points."""
        beats: tuple[int, ...] = (*meter.starts(meter.beat), meter.pulses)
        if len(beats) - 1 != self.counts:
            raise ValueError(f"the meter has {len(beats) - 1} beats, the cycle {self.counts}")
        sounds = meter.timing(swing)
        grid = tuple(meter.starts(-1))

        def pulses(time: float) -> float:  # counts into pulses, beat by beat
            count = int(time)
            return beats[count] + (time - count) * (beats[count + 1] - beats[count])

        points, offsets = [], []
        for time in self.times:
            where = pulses(time)
            point = min(grid, key=lambda p: abs(shortest(sounds[p] - where, meter.pulses)))
            missed = shortest(where - sounds[point], meter.pulses)
            beat = beats[int(time) + 1] - beats[int(time)]
            points.append(point)
            offsets.append(missed / beat)
        return Placement(tuple(points), tuple(offsets))


def _fold(time: float, counts: int) -> float:
    """`time` folded into one cycle, [0, counts). Floating point can round a time just before
    the 1 (-1e-17 % 4) up to `counts` itself, which is the 1 of the next lap: that is 0."""
    folded = time % counts
    return 0.0 if folded >= counts else folded
