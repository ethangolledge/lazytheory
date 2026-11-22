"""Chords one finger away, and the shapes that pass between two chords.

Why: the laziest voice leading is one note moving while the rest stay where they are. From any
shape, the chords a single finger can reach are the ones a player finds by accident and keeps:
they cost nothing to play and always sound connected. And between two shapes, the fingers need
not all move at once, so the in-between shapes are chords too.

Theory it speaks to: parsimonious voice leading. Two triads that keep two notes and move the
third by step are exactly those joined by Cohn's P, L and R (Cohn 1997); on the neck that is
one finger moving along its string while the others stay down, guitar teachers' "guide" and
"anchor" fingers. Chains of such moves give line cliches (Am, Am(maj7), Am7) and walking
basses (C, Cmaj7/B, Am7) without listing either. A voice that moves late is a suspension; one
that moves early, an anticipation: `passing` is every mix of moved and not yet.

Could grow into: the shortest chain of one-finger moves between any two shapes (a breadth-
first search over `one_finger`), two-finger neighbours, and the same idea per voice on a
keyboard. Optional, like the rest of this layer: names come from the catalog's chord patterns.
"""

from collections.abc import Collection
from itertools import combinations
from typing import NamedTuple

import numpy as np

from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.instruments.arrays import MUTED, Grid
from lazy_theory.instruments.fretboard import Fretboard
from lazy_theory.instruments.taste import Taste
from lazy_theory.pitch.attraction import anchoring
from lazy_theory.pitch.chord import Chord
from lazy_theory.pitch.key import Key


class Neighbour(NamedTuple):
    """A nearby shape, the chord it plays, and how far the fingers moved to reach it."""

    frets: Grid  # one row: a fret or MUTED per string
    chord: Chord  # with the shape's bass written, unless it is the root
    steps: int  # steps of the temperament moved in all, from the shape it was found from


def named(
    board: Fretboard, voicings: Grid, patterns: Collection[PitchClassSet], key: Key | None = None
) -> list[Chord | None]:
    """The chord each voicing plays, read as one of `patterns` (`pitch.catalog.chord_names()`
    for the catalog's); None where no pattern fits. Of several readings (F A B D is Bm7b5 or
    Dm6), the one rooted on the bass; failing that, with `key`, the one whose root is steadiest
    in the key (`pitch.attraction.anchoring`: tonic, then the rest of the home chord, then the
    scale); else the first."""
    if key is not None and key.size != board.size:
        raise ValueError(f"a {key.size}-step key on a {board.size}-step neck")
    steady = anchoring(key) if key else None
    chords: list[Chord | None] = []
    for found in board.readings(voicings, patterns):
        on_bass = next((chord for chord in found if chord.bass is None), None)
        if on_bass or not found:
            chords.append(on_bass)
        else:
            chords.append(max(found, key=lambda c: steady[c.root]) if steady else found[0])
    return chords


def one_finger(
    board: Fretboard,
    taste: Taste,
    frets: Grid,
    patterns: Collection[PitchClassSet],
    key: Key | None = None,
) -> list[Neighbour]:
    """Every other chord or inversion this hand reaches from the shape `frets` by moving one
    finger along its string, to an open string or another fret in reach, while every other
    string stays as it is. Smallest move first, then from the lowest string up."""
    strings = np.flatnonzero(frets != MUTED)
    string = np.repeat(strings, board.frets + 1)
    fret = np.tile(np.arange(board.frets + 1, dtype=frets.dtype), len(strings))
    rows = np.repeat(frets[None, :], len(string), axis=0)
    rows[np.arange(len(rows)), string] = fret
    moved = np.abs(fret - frets[string])
    found = _neighbours(board, taste, rows, moved, patterns, key, frets[None, :])
    return sorted(found, key=lambda one: one.steps)  # stable: lowest string first


def passing(
    board: Fretboard,
    taste: Taste,
    before: Grid,
    after: Grid,
    patterns: Collection[PitchClassSet],
    key: Key | None = None,
) -> list[Neighbour]:
    """The shapes on the way from `before` to `after` that play a third chord or inversion:
    each string either already at its new fret or still at its old one. Fewest strings moved
    first; `steps` counts from `before`."""
    differ = np.flatnonzero(before != after)
    both = (before != MUTED) & (after != MUTED)
    rows, steps = [], []
    for count in range(1, len(differ)):
        for moved in map(list, combinations(differ, count)):
            row = before.copy()
            row[moved] = after[moved]
            rows.append(row)
            steps.append(np.abs(after[moved] - before[moved])[both[moved]].sum())
    grid = np.array(rows, dtype=before.dtype).reshape(-1, len(before))
    known = np.stack([before, after])
    return _neighbours(board, taste, grid, np.array(steps), patterns, key, known)


def _neighbours(
    board: Fretboard,
    taste: Taste,
    rows: Grid,
    steps: Grid,
    patterns: Collection[PitchClassSet],
    key: Key | None,
    known: Grid,
) -> list[Neighbour]:
    """The rows this hand allows that play one of `patterns`, other than what the `known` shapes
    already sound (the same notes over the same bass)."""

    def sound(grid: Grid) -> Grid:  # what a symbol shows: [row, pitch classes then bass]
        return np.column_stack([board.chroma(grid), board.bass(grid) % board.size])

    keep = (rows != MUTED).any(axis=1) & taste.allows(board, rows)
    keep &= (sound(rows)[:, None, :] != sound(known)[None, :, :]).any(axis=2).all(axis=1)
    return [
        Neighbour(row, chord, int(step))
        for row, chord, step in zip(
            rows[keep], named(board, rows[keep], patterns, key), steps[keep], strict=True
        )
        if chord is not None
    ]
