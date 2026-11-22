"""Measures of how a rhythm or a meter is heard: numbers to show beside a rhythm, never weights.

Why: whether a rhythm "feels like speech", "is too fast to count" or "which beat a listener
taps" are questions listening experiments have answered, so they can be numbers with a source
rather than opinions in the code. Each is a measure to display, as `syncopation` and
`unevenness` are; none ranks anything.

Theory it speaks to:
- the nPVI, how much each duration differs from the next (Patel & Daniele 2003): English
  instrumental themes score higher than French ones, as English speech does French, so it is
  a measure of how speech-like a rhythm's durations are;
- the rate limit of synchronisation: people can keep time with events no closer than about
  100 ms (Repp 2006), so a level of a meter faster than that can't be counted, only heard as
  texture;
- London's well-formedness for meters with uneven beats (Hearing in Time, 2012; Polak &
  London 2014): the beats, measured in the grid's pulses, must be maximally even, as 3+2+2
  and 3+3+2 are and 4+1+2 isn't;
- the tactus, the level a listener taps: the one whose beats are nearest a comfortable
  period, which the caller states.

Could grow into: Povel & Essens' clock model (accents from how notes cluster, and the meter
that fits them best), once its rules are read from the paper; rhythmic categories as priors
per culture (Jacoby & McDermott 2017) for reading taps.
"""

from collections.abc import Sequence
from itertools import pairwise
from math import log

from lazy_theory.rhythm.meter import Meter, unevenness

RATE_LIMIT = 0.1  # seconds: the closest events people synchronise with (Repp 2006)


def npvi(lengths: Sequence[int]) -> float:
    """The normalised pairwise variability index of successive durations (Patel & Daniele
    2003): 100 times the mean of |a − b| / ((a + b) / 2) over each neighbouring pair. 0 for
    even durations; 66.7 for long-short alternating 2:1."""
    if len(lengths) < 2 or min(lengths) <= 0:
        raise ValueError(f"need two or more positive durations, got {lengths}")
    pairs = list(pairwise(lengths))
    return 100 * sum(abs(a - b) / ((a + b) / 2) for a, b in pairs) / len(pairs)


def too_fast(meter: Meter, pulse_seconds: float) -> list[int]:
    """The levels of `meter` with a group shorter than `RATE_LIMIT` when a pulse lasts
    `pulse_seconds`: too fast to count or tap, heard as texture."""
    if pulse_seconds <= 0:
        raise ValueError(f"a pulse must last some time, got {pulse_seconds}")
    return [
        index for index, level in enumerate(meter.levels) if min(level) * pulse_seconds < RATE_LIMIT
    ]


def even_beats(meter: Meter, level: int) -> bool:
    """Whether the groups of `level`, heard as beats, are maximally even in the grid's points:
    London's condition for a meter of uneven beats (3+2+2 and 3+3+2 pass, 4+1+2 fails). A
    tala's sections usually fail (Adi's 4+2+2): they are a count kept by hand over even beats,
    not uneven beats."""
    return unevenness(meter.to_grid(meter.starts(level))) == 0


def tactus(meter: Meter, pulse_seconds: float, preferred: float) -> int:
    """The level whose beats last nearest `preferred` seconds, compared as ratios (a beat
    twice as long is as far as one half as long), when a pulse lasts `pulse_seconds`: the
    level a listener taps. 6/8 in eighths of 0.25 s, preferring 0.6 s, is the dotted quarter.
    `preferred` is the caller's: it varies with the listener and the music."""
    if pulse_seconds <= 0 or preferred <= 0:
        raise ValueError("durations must be positive")
    return min(
        range(len(meter.levels)),
        key=lambda index: abs(
            log(meter.pulses / len(meter.levels[index]) * pulse_seconds / preferred)
        ),
    )
