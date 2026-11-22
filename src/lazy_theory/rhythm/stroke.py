"""Strokes: what each note of a rhythm sounds like, as two drum heads, each silent, damped or open.

Why: before any clock, a rhythm's meaning was carried by its sounds, not only its timing. A
tabla player hears where the cycle is because the bass drum drops out in its khali section;
a darbuka's dum and tak are the rhythm. Nearly every hand drum is a low head and a high head
(or one head struck low and high), each either left to ring or damped, so one pair of small
numbers describes a stroke on any of them, and the sound follows from physics: size gives the
pitch, damping the decay.

Theory it speaks to: Rohit & Rao (2021) sort tabla strokes into damped, resonant treble,
resonant bass and resonant both: exactly `Stroke(low, high)` with each head silent, damped or
open. The default voicing follows the khali principle (the bass marks the structure of the
cycle): the player's own accents get the bass when given. Otherwise the meter's grouping
reaches inside the beat: a note that starts a group above the count gets the bass, a note on a
count or on an inner group's start (the 3 of a five felt 2+3) the open high head, and any other
note a damped one. Only notes sound, so a rhythm is heard as its notes, never as its grid.

Could grow into: a hand per stroke (alternation and sticking), and dynamics. Bols typed as
text map to strokes in the catalog (`rhythm.names.spell`), so a rhythm can be spoken as
the drum would play it.
"""

from typing import NamedTuple

from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.rhythm.meter import Meter

SILENT, DAMPED, OPEN = 0, 1, 2


class Stroke(NamedTuple):
    """One stroke: what each of the two heads does, SILENT, DAMPED or OPEN."""

    low: int  # the bass head (bayan, thoppi, dum): SILENT, DAMPED or OPEN
    high: int  # the treble head (dayan, valanthalai, tak)


REST = Stroke(SILENT, SILENT)
BOTH = Stroke(OPEN, OPEN)
HIGH = Stroke(SILENT, OPEN)
LIGHT = Stroke(SILENT, DAMPED)


def voicing(
    onsets: PitchClassSet, meter: Meter, accents: PitchClassSet | None = None
) -> tuple[Stroke, ...]:
    """A stroke for each grid point of `meter`: rest where there is no note. With `accents`
    (the player's chosen notes, in pulses), those get both heads and every other note the open
    high head alone, so the accents always stand out. Without, the meter decides: both heads
    on a note that starts a group stronger than a plain count (the 1, the groups of 3+2+2), the
    open high head on a count or an inner group's start, the damped high head on any other
    point. So a five felt 2+3 sounds 2+3, and sixteenths are lighter than eighths."""
    notes = meter.to_grid(onsets)  # raises for a note off the grid
    if accents is not None:
        return tuple(
            (BOTH if pulse in accents else HIGH) if point in notes else REST
            for point, pulse in enumerate(meter.starts(-1))
        )
    weight = meter.weights()
    plain = min(weight[count] for count in meter.starts(meter.beat))
    finest = min(weight[point] for point in meter.starts(-1))
    return tuple(
        REST
        if point not in notes
        else BOTH
        if weight[pulse] > plain
        else HIGH
        if weight[pulse] == plain or weight[pulse] > finest
        else LIGHT
        for point, pulse in enumerate(meter.starts(-1))
    )
