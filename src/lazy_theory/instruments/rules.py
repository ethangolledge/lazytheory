"""Rules for choosing voicings. Each takes voicing grids (one row per voicing, one fret or MUTED
per string) and returns a value per row, or per pair of rows for a change between chords.
Combine them with `&` and `+`; swap any of them out.
"""

from collections.abc import Callable, Sequence
from itertools import combinations, pairwise

import numpy as np
from numpy.typing import NDArray

from lazy_theory.instruments.fretboard import MUTED, Floats, Grid

Mask = NDArray[np.bool_]
Counts = NDArray[np.int64]


def barres(frets: Grid) -> Mask:
    """Whether one finger can barre the notes on strings `first` and `last` (first < last), as
    [voicing, first, last].

    Fingers reach over the neck from the highest string's side, so a barre lies from its first
    note all the way to that edge. Every string under it must be fretted at the barre's fret or
    higher: an open string would be damped and a lower note couldn't sound. Past the barre's
    last note, a muted string is fine (it isn't played); between its notes, it would sound.
    """
    index = np.arange(frets.shape[1])
    first, last, string = index[:, None, None], index[None, :, None], index[None, None, :]
    fret, barre = frets[:, None, None, :], frets[:, :, None, None]  # [voicing, first, last, string]
    blocks = (string >= first) & (fret < barre) & ((string <= last) | (fret != MUTED))
    same_fret = frets[:, :, None] == frets[:, None, :]
    barred: Mask = same_fret & (first[..., 0] < last[..., 0]) & ~blocks.any(axis=-1)
    return barred


def _own_finger(frets: Grid) -> Mask:
    """Fretted notes that need their own finger: those not joining a barre from a lower string."""
    joins: Mask = barres(frets).any(axis=1)
    return (frets > 0) & ~joins


def fingers(frets: Grid) -> Counts:
    """Fewest fretting fingers each voicing needs: one per note, except notes that join a
    barre."""
    needed: Counts = _own_finger(frets).sum(axis=1)
    return needed


def placeable(frets: Grid, distance: Floats, spans: Sequence[float]) -> Mask:
    """Each voicing's fingers fit the hand, given `distance`, mm from the nut to each fret.

    Fingers go index first in fret order, one per note or barre, so a finger never sits behind
    a lower-numbered one; any of them may be skipped. Two fingers `k` apart reach at most
    `spans[k - 1]` mm, so `len(spans) + 1` fingers are available. A barre lies along its whole
    fret, so no other finger can share that fret.
    """
    own = _own_finger(frets)
    count = own.sum(axis=1)
    fret = np.where(own, frets, MUTED)
    barre = own & barres(frets).any(axis=2)
    others = ~np.eye(frets.shape[1], dtype=bool)
    shared = (fret[:, :, None] == fret[:, None, :]) & own[:, None, :] & others
    crowded = (barre[:, :, None] & shared).any(axis=(1, 2))

    hand = len(spans) + 1
    in_order = np.sort(np.where(own, frets, len(distance)), axis=1)[:, :hand]
    position = np.append(distance, np.nan)[in_order]  # mm of each finger's fret, lowest first
    fits = count == 0
    for used in range(1, hand + 1):
        rows = count == used
        for chosen in combinations(range(hand), used):  # which fingers, index first
            reach = np.ones(rows.sum(), dtype=bool)
            for (a, finger_a), (b, finger_b) in combinations(enumerate(chosen), 2):
                spread = position[rows, b] - position[rows, a]
                reach &= spread <= spans[finger_b - finger_a - 1]
            fits[rows] |= reach
    placed: Mask = fits & ~crowded
    return placed


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


def open_within(frets: Grid, highest: int) -> Mask:
    """Open strings sound only with fretted notes no higher than fret `highest`, so an open
    string never rings far below the hand. Voicings without open strings always pass. On a
    capoed neck, frets and open strings count from the capo."""
    has_open = (frets == 0).any(axis=1)
    near: Mask = ~has_open | (frets <= highest).all(axis=1)
    return near


def sounding(frets: Grid) -> Counts:
    """Strings that sound in each voicing."""
    count: Counts = (frets != MUTED).sum(axis=1)
    return count


def ringing(frets: Grid) -> Counts:
    """Open strings in each voicing. Nothing damps them, so they sustain longest."""
    count: Counts = (frets == 0).sum(axis=1)
    return count


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
) -> tuple[Grid, float]:
    """One voicing per chord, with the lowest total `cost` of each voicing plus `transition`
    of each change, over the whole progression; and that total.

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
    return chosen, float(total.min())
