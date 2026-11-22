"""Harmonise a melody: one chord per melody note, the note on top, the chords chosen from those
allowed in each slot (one fixed chord, or any chord of a key), with smooth voice leading.

Why: chord-melody playing, a tune and its harmony from one instrument, is the hardest thing to
work out by hand: every melody note limits the voicings, and every voicing limits the next. As
a search it is the usual graph with one more rule: the top note of each chord is given.

Theory it speaks to: the outer voices carry a texture (the top is heard as the tune, the bass
as the foundation), and independence between them: contrary motion keeps two lines distinct,
while voices moving in parallel perfect fifths or octaves fuse into one (Huron, "Tone and
Voice", 2001). Avoiding parallels is classical taste: on guitar, where a barre shape slid up
the neck is all parallel fifths, it is a choice, which is why it lives in a Taste subclass.

Could grow into: a bass line given the same way, melodies with passing notes between chords,
and a rhythm that lets one chord carry several melody notes.

Optional, like the rest of this layer. A MelodicTaste is a Taste that also listens to how the
voices move against each other; everything else it inherits.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import combinations
from typing import NamedTuple

import numpy as np

from lazy_theory.instruments.arrays import Floats, Grid
from lazy_theory.instruments.fretboard import Fretboard
from lazy_theory.instruments.taste import Taste
from lazy_theory.pitch.chord import Chords


def parallels(board: Fretboard, previous: Grid, following: Grid) -> Floats:
    """Pairs of strings moving the same way from a perfect fifth or octave (unisons included)
    to the same interval, for each change. Shape (len(previous), len(following)).

    Voices in parallel perfect intervals fuse and are heard as one (Huron 2001)."""
    fifth = round(board.temperament.steps(3 / 2))
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
    tops = [board.top(voicings) for voicings in (previous, following)]
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
        """`Taste.transition`, plus parallels as a cost and contrary motion as a reward."""
        cost: Floats = (
            super().transition(board, previous, following)
            + self.parallels * parallels(board, previous, following)
            - self.contrary * contrary(board, previous, following)
        )
        return cost


class Harmony(NamedTuple):
    """A harmonised melody: the chord chosen in each slot and how to play them all."""

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
            grids = [grid[board.top(grid) % board.size == note % board.size] for grid in grids]
        options.append(np.concatenate(grids))
        owners.append(np.repeat(np.arange(len(grids)), [len(grid) for grid in grids]))
    route = taste.trellis(board, options).shortest()
    chosen = tuple(int(owner[pick]) for owner, pick in zip(owners, route.picks, strict=True))
    return Harmony(chosen, route.path, route.cost)
