"""Rules for choosing voicings: each takes a voicing grid (one row per voicing, one fret or MUTED
per string) and returns a value per row. Combine them with `&`, swap any of them out.
"""

from collections.abc import Sequence
from itertools import pairwise

import numpy as np
from numpy.typing import NDArray

from lazy_theory.instruments.fretboard import MUTED, Grid

Mask = NDArray[np.bool_]
Costs = NDArray[np.int64]


def fingers(frets: Grid) -> Costs:
    """Fretting fingers needed. One finger can barre every note on the lowest fret, unless an
    open string lies under the barre; every other fretted note needs its own finger."""
    fretted = frets > 0
    lowest = np.where(fretted, frets, np.iinfo(frets.dtype).max).min(axis=1, keepdims=True)
    barred = fretted & (frets == lowest)
    under_barre = (
        np.maximum.accumulate(barred, axis=1)
        & np.maximum.accumulate(barred[:, ::-1], axis=1)[:, ::-1]
    )
    can_barre = ~(under_barre & (frets == 0)).any(axis=1)
    with_barre = barred.any(axis=1) + (fretted & ~barred).sum(axis=1)
    return np.where(can_barre, with_barre, fretted.sum(axis=1)).astype(np.int64)


def contiguous(frets: Grid) -> Mask:
    """Sounding strings sit next to each other, with no muted string between them."""
    sounding = frets != MUTED
    first = sounding.argmax(axis=1)
    last = sounding.shape[1] - 1 - sounding[:, ::-1].argmax(axis=1)
    joined: Mask = sounding.sum(axis=1) == last - first + 1
    return joined


def within(frets: Grid, lowest: int, highest: int) -> Mask:
    """Every fretted note lies between frets `lowest` and `highest`. Open strings are allowed."""
    inside: Mask = ((frets <= 0) | ((frets >= lowest) & (frets <= highest))).all(axis=1)
    return inside


def transition_cost(previous: Grid, following: Grid, string_change: int) -> Costs:
    """Cost of every change from a row of `previous` to a row of `following`.

    Frets moved on strings that sound in both, plus `string_change` for every string that starts
    or stops. Setting `string_change` to the hand's width in frets makes changing strings cost
    more than any move within one position. Shape is (len(previous), len(following)).
    """
    before, after = previous[:, None, :], following[None, :, :]
    shared = (before != MUTED) & (after != MUTED)
    changed = ((before != MUTED) != (after != MUTED)).sum(axis=2)
    moved = np.where(shared, np.abs(before - after), 0).sum(axis=2)
    costs: Costs = moved + string_change * changed
    return costs


def smoothest(options: Sequence[Grid], string_change: int) -> Grid:
    """One voicing per chord, chosen so the total transition cost over the whole progression is
    as small as possible. Every path is considered, by keeping only the cheapest way to reach
    each voicing of each chord. Pass a single row as a chord's options to fix that voicing.
    """
    for index, voicings in enumerate(options):
        if len(voicings) == 0:
            raise ValueError(f"no voicing of chord {index} satisfies the rules")
    total = np.zeros(len(options[0]), dtype=np.int64)
    best_previous = []
    for previous, following in pairwise(options):
        reach = total[:, None] + transition_cost(previous, following, string_change)
        best_previous.append(reach.argmin(axis=0))
        total = reach.min(axis=0)
    path = [int(total.argmin())]
    for pointers in reversed(best_previous):
        path.append(int(pointers[path[-1]]))
    path.reverse()
    chosen: Grid = np.stack([voicings[row] for voicings, row in zip(options, path, strict=True)])
    return chosen
