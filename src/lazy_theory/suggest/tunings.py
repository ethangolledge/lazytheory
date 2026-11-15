"""Suggest a tuning and capo for a progression.

A tuning is just its open strings' pitches, so candidates are generated, not looked up: every
way to retune each string within safe tension. Names come afterwards, from the catalog.

Two passes. A cheap screen scores every retuning at every capo at once by how many open strings
are chord tones, without building a voicing. Only the shortlist gets the full search: the
player's cheapest path through the progression, plus what the retuning costs and how well the
key's other chords sit on the same neck.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import replace
from itertools import product
from typing import NamedTuple

import numpy as np

from lazy_theory.catalog import Tuning
from lazy_theory.core.scale import Scale
from lazy_theory.instruments.fretboard import Floats, Fretboard, Grid
from lazy_theory.instruments.taste import Chords, Taste

# Tension rises with the square of frequency: 4 steps down leaves 63% of it, 2 up adds 26%.
SAFE_STEPS = range(-4, 3)


class Suggestion(NamedTuple):
    retuning: tuple[int, ...]  # steps each string moves from the base tuning
    capo: int
    path: Grid  # one voicing per chord, frets counted from the capo
    cost: float


def retunings(strings: int, steps: Sequence[int]) -> Grid:
    """Every way to move each of `strings` strings by one of `steps`, one row each."""
    moves: Grid = np.array(list(product(steps, repeat=strings)), dtype=np.int16)
    return moves.reshape(-1, strings)


def key(scale: Scale, root: int, notes: int = 3) -> Chords:
    """The chord on each degree of `scale` from `root`, stacked in thirds."""
    degrees = range(len(scale))
    return [(scale.chord(degree, notes), root + scale.pitch_classes[degree]) for degree in degrees]


def screen(open_strings: Grid, chords: Chords, size: int) -> Floats:
    """Share of open strings that are chord tones, averaged over the chords, for each row of
    open-string pitches (strings on the last axis)."""
    tones = np.zeros((len(chords), size), dtype=bool)
    for index, (chord, root) in enumerate(chords):
        tones[index, (np.array(chord.pitch_classes) + root) % size] = True
    share: Floats = tones[:, open_strings % size].mean(axis=(0, -1))
    return share


def suggest(
    base: Fretboard,
    chords: Chords,
    taste: Taste,
    steps: Sequence[int] = SAFE_STEPS,
    capos: Sequence[int] = range(8),
    retune: float = 1.0,
    context: Chords = (),
    context_weight: float = 0.25,
    shortlist: int = 20,
    top: int = 5,
) -> list[Suggestion]:
    """The `top` retunings of `base` and capos for `chords`, cheapest first.

    Cost is the cheapest path through `chords`, plus `retune` per step of retuning, plus
    `context_weight` times the cheapest voicing of each `context` chord (e.g. the rest of the
    key), so a neck that suits these chords but not the next one ranks lower. Every chord must
    be playable. The screen keeps `shortlist` retuning and capo pairs, and always `base` with
    no capo. Equal costs rank the smaller retuning first, and a path playing the same pitches
    as a better one is dropped. Roots stay measured from the base tuning's first open string.
    """
    moves = retunings(len(base.open_strings), steps)
    capo = np.array(capos, dtype=np.int16)
    open_strings = base.open_strings + moves[:, None, :] + capo[:, None]  # [move, capo, string]
    score = screen(open_strings, chords, base.size).ravel()
    effort = np.repeat(np.abs(moves).sum(axis=1), len(capo))
    pairs = [divmod(int(i), len(capo)) for i in np.lexsort((effort, -score))[:shortlist]]
    unchanged = int(np.flatnonzero((moves == 0).all(axis=1))[0])

    found = []
    for move_index, capo_index in dict.fromkeys([(unchanged, 0), *pairs]):
        move, fret = moves[move_index], int(capo[capo_index])
        board = replace(base, open_strings=base.open_strings + move).capo(fret)
        try:  # ValueError: some chord has no voicing this player allows
            path, cost = taste.path(board, chords)
            near = [taste.standing(board, taste.voicings(board, *chord)).min() for chord in context]
        except ValueError:
            continue
        effort_here = int(np.abs(move).sum())
        total = cost + retune * effort_here + context_weight * sum(near)
        sound = np.nan_to_num(board.notes(path), nan=-1).tobytes()
        found.append((total, effort_here, sound, fret, move, path))

    suggestions, heard = [], set()
    for total, _, sound, fret, move, path in sorted(found, key=lambda one: one[:2]):
        if sound not in heard:  # the same pitches from another tuning sound the same
            heard.add(sound)
            suggestions.append(Suggestion(tuple(move.tolist()), fret, path, float(total)))
    return suggestions[:top]


def name(open_strings: Grid, base: Fretboard, tunings: Mapping[str, Tuning]) -> str | None:
    """The catalog's name for these open strings (pitch 0 being `base`'s first open string),
    or a named tuning moved by whole steps, e.g. "guitar open D +2"; the smallest move wins."""
    period = float(base.temperament.period)
    moved = {}
    for tuning_name, tuning in tunings.items():
        named = Fretboard.from_tuning(tuning)
        if len(named.open_strings) != len(open_strings):
            continue
        offset = round(base.size * math.log(tuning.hertz / base.hertz, period))
        shift = np.asarray(open_strings) - named.open_strings - offset
        if (shift == shift[0]).all():
            moved[tuning_name] = int(shift[0])
    if not moved:
        return None
    nearest = min(moved, key=lambda one: abs(moved[one]))
    return nearest if moved[nearest] == 0 else f"{nearest} {moved[nearest]:+d}"
