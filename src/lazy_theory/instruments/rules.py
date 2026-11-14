"""Rules for choosing voicings. Each takes voicing grids (one row per voicing, one fret or MUTED
per string) and returns a value per row, or per pair of rows for a change between chords.
Combine them with `&` and `+`; swap any of them out.
"""

from collections.abc import Callable, Sequence
from itertools import pairwise

import numpy as np
from numpy.typing import NDArray

from lazy_theory.instruments.fretboard import MUTED, Floats, Grid

Mask = NDArray[np.bool_]
Counts = NDArray[np.int64]


def fingers(frets: Grid) -> Counts:
    """Fewest fretting fingers each voicing needs.

    One finger can barre notes at the same fret across the strings between them, as long as
    none of those strings is open, muted or fretted lower: the barre would sound over them.
    Every other fretted note needs its own finger.
    """
    index = np.arange(frets.shape[1])
    between = (index[:, None, None] <= index) & (
        index <= index[None, :, None]
    )  # [from, to, string]
    lowest_between = np.where(between, frets[:, None, None, :], np.iinfo(frets.dtype).max).min(-1)
    same_fret = frets[:, :, None] == frets[:, None, :]
    barred = same_fret & (lowest_between >= frets[:, None, :]) & (index[:, None] < index)
    joins_a_barre = barred.any(axis=1)
    needed: Counts = ((frets > 0) & ~joins_a_barre).sum(axis=1)
    return needed


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


def motion(previous: Floats, following: Floats) -> Floats:
    """How far a value moves from each previous voicing to each following one, e.g. the bass
    (lowest note) or the hand. Shape (len(previous), len(following)); NaN counts as no move."""
    moved: Floats = np.nan_to_num(np.abs(following[None, :] - previous[:, None]))
    return moved


def moved(previous: Grid, following: Grid) -> Counts:
    """Steps moved on each string that sounds in both voicings: voice leading, with each string
    a voice. Shape (len(previous), len(following))."""
    before, after = previous[:, None, :], following[None, :, :]
    shared = (before != MUTED) & (after != MUTED)
    steps: Counts = np.where(shared, np.abs(before - after), 0).sum(axis=2)
    return steps


def strings_changed(previous: Grid, following: Grid) -> Counts:
    """Strings that start or stop sounding between voicings. Shape (len(previous),
    len(following))."""
    before, after = previous[:, None, :] != MUTED, following[None, :, :] != MUTED
    changed: Counts = (before != after).sum(axis=2)
    return changed


def smoothest(
    options: Sequence[Grid],
    transition: Callable[[Grid, Grid], NDArray[np.floating] | NDArray[np.integer]],
    cost: Callable[[Grid], NDArray[np.floating] | NDArray[np.integer]] | None = None,
) -> Grid:
    """One voicing per chord, with the lowest total `cost` of each voicing plus `transition`
    of each change, over the whole progression.

    Every path is considered, by keeping only the cheapest way to reach each voicing of each
    chord (the Viterbi algorithm). Pass a single row as a chord's options to fix that voicing.
    """
    for index, voicings in enumerate(options):
        if len(voicings) == 0:
            raise ValueError(f"no voicing of chord {index} satisfies the rules")
    standing = cost or (lambda voicings: np.zeros(len(voicings)))
    total = np.asarray(standing(options[0]), dtype=np.float64)
    best_previous = []
    for previous, following in pairwise(options):
        reach = total[:, None] + transition(previous, following)
        best_previous.append(reach.argmin(axis=0))
        total = reach.min(axis=0) + standing(following)
    path = [int(total.argmin())]
    for pointers in reversed(best_previous):
        path.append(int(pointers[path[-1]]))
    path.reverse()
    chosen: Grid = np.stack([voicings[row] for voicings, row in zip(options, path, strict=True)])
    return chosen
