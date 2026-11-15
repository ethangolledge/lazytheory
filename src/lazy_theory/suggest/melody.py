"""Harmonise a melody: one chord per melody note, the note on top, the chords chosen from those
allowed in each slot (one fixed chord, or any chord of a key), with smooth voice leading.

Optional, like the rest of this layer. A MelodicTaste is a Taste that also listens to how the
voices move against each other; everything else it inherits.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from functools import partial
from itertools import combinations
from typing import NamedTuple

import numpy as np

from lazy_theory.core.chord import Chords
from lazy_theory.instruments.arrays import Floats, Grid
from lazy_theory.instruments.fretboard import Fretboard
from lazy_theory.instruments.rules import smoothest
from lazy_theory.instruments.taste import Taste


def top(board: Fretboard, voicings: Grid) -> Floats:
    """Highest pitch of each voicing, where the melody is heard."""
    highest: Floats = np.nanmax(board.notes(voicings), axis=1)
    return highest


def parallels(board: Fretboard, previous: Grid, following: Grid) -> Floats:
    """Pairs of strings moving the same way from a perfect fifth or octave (unisons included)
    to the same interval, for each change. Shape (len(previous), len(following)).

    Voices in parallel perfect intervals fuse and are heard as one (Huron 2001)."""
    fifth = round(board.size * math.log(1.5, float(board.temperament.period)))
    before, after = board.notes(previous)[:, None, :], board.notes(following)[None, :, :]
    direction = np.sign(after - before)  # NaN where either is silent
    count = np.zeros((len(previous), len(following)))
    for low, high in combinations(range(before.shape[-1]), 2):
        interval = (before[..., high] - before[..., low]) % board.size
        same = interval == (after[..., high] - after[..., low]) % board.size
        perfect = (interval == 0) | (interval == fifth)
        together = (direction[..., low] == direction[..., high]) & (direction[..., low] != 0)
        count += same & perfect & together
    return count


def contrary(board: Fretboard, previous: Grid, following: Grid) -> Floats:
    """1 where the top note and the bass move in opposite directions, for each change."""
    tops = [top(board, voicings) for voicings in (previous, following)]
    basses = [board.bass(voicings) for voicings in (previous, following)]
    up = np.sign(tops[1][None, :] - tops[0][:, None])
    down = np.sign(basses[1][None, :] - basses[0][:, None])
    opposite: Floats = (up * down < 0).astype(np.float64)
    return opposite


@dataclass(frozen=True)
class MelodicTaste(Taste):
    """A Taste that also penalises parallel fifths and octaves and rewards the melody moving
    against the bass."""

    parallels: float = 5.0  # per pair of voices in parallel fifths or octaves
    contrary: float = 1.0  # reward when the top note and the bass move in opposite directions

    def transition(self, board: Fretboard, previous: Grid, following: Grid) -> Floats:
        cost: Floats = (
            super().transition(board, previous, following)
            + self.parallels * parallels(board, previous, following)
            - self.contrary * contrary(board, previous, following)
        )
        return cost


class Harmony(NamedTuple):
    chords: tuple[int, ...]  # which of each slot's chords was chosen
    path: Grid  # one voicing per slot
    cost: float


def harmonise(
    board: Fretboard, melody: Sequence[int | None], slots: Sequence[Chords], taste: Taste
) -> Harmony:
    """The cheapest chord and voicing for each melody note, with that note on top.

    `melody` holds one pitch class per slot, measured like roots (None leaves the top free);
    `slots` holds the chords allowed under each note. Raises ValueError if some note has no
    allowed voicing.
    """
    options, owners = [], []
    for note, chords in zip(melody, slots, strict=True):
        grids = taste.options(board, chords)
        if note is not None:
            grids = [grid[top(board, grid) % board.size == note % board.size] for grid in grids]
        options.append(np.concatenate(grids))
        owners.append(np.repeat(np.arange(len(grids)), [len(grid) for grid in grids]))
    path, cost = smoothest(options, partial(taste.transition, board), taste.costs(board, options))
    chosen = tuple(
        int(owner[(voicings == row).all(axis=1).argmax()])
        for owner, voicings, row in zip(owners, options, path, strict=True)
    )
    return Harmony(chosen, path, cost)
