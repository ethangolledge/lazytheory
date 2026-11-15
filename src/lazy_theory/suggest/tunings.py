"""Suggest a tuning and capo for a progression.

A tuning is just its open strings' pitches, so candidates are generated, not looked up: every
way to retune each string within safe tension. Names come afterwards, from the catalog.

Two passes. A cheap screen scores every retuning at every capo at once by how many open strings
are chord tones, without building a voicing. Only the shortlist gets the full search: the
player's cheapest path through the progression, plus what the retuning costs and how well the
key's other chords sit on the same neck.
"""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from functools import partial
from typing import NamedTuple

import numpy as np

from lazy_theory.catalog import Tuning
from lazy_theory.core.chord import Chords
from lazy_theory.instruments.arrays import Grid
from lazy_theory.instruments.fretboard import Fretboard
from lazy_theory.instruments.rules import smoothest
from lazy_theory.instruments.taste import Taste

# Tension rises with the square of frequency: 4 steps down leaves 63% of it, 2 up adds 26%.
SAFE_STEPS = range(-4, 3)


class Suggestion(NamedTuple):
    retuning: tuple[int, ...]  # steps each string moves from the base tuning
    capo: int
    path: Grid  # one voicing per chord, frets counted from the capo
    cost: float


def screen(
    open_strings: Grid, steps: Sequence[int], capos: Sequence[int], chords: Chords, size: int
) -> Grid:
    """Open strings that are chord tones, summed over the chords, for every retuning by `steps`
    at every capo: shape (len(steps),) * strings + (len(capos),).

    A string's count depends only on its own step and the capo, so each string gets a small
    [step, capo] table and the tables are broadcast together, never enumerated one by one.
    """
    hits = np.zeros(size, dtype=np.int16)  # chords each pitch class belongs to
    for chord in chords:
        hits[list(chord.pitch_classes)] += 1
    pitch = np.add.outer(np.add.outer(open_strings, steps), capos) % size  # [string, step, capo]
    return _by_string(hits[pitch])


def _by_string(tables: Grid) -> Grid:
    """Sum of one [step, capo] table per string, for every retuning and capo: each string's
    table broadcast along its own axis, shape (steps,) * strings + (capos,)."""
    strings, steps, capos = tables.shape
    total: Grid = sum(
        table.reshape([steps if axis == string else 1 for axis in range(strings)] + [capos])
        for string, table in enumerate(tables)
    )
    return total


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
    as a better one is dropped.
    """
    strings, step = len(base.open_strings), np.array(steps, dtype=np.int16)
    score = screen(base.open_strings, steps, capos, chords, base.size).astype(np.int32)
    effort = _by_string(np.broadcast_to(np.abs(step)[:, None], (strings, len(step), 1)))
    rank = ((score.max() - score) * (effort.max() + 1) + effort).ravel()  # tones, then effort
    kth = min(shortlist, rank.size) - 1
    tied = np.flatnonzero(rank <= np.partition(rank, kth)[kth])  # in order, as a stable sort
    best = tied[np.argsort(rank[tied], kind="stable")][:shortlist]
    unchanged = np.ravel_multi_index((*(steps.index(0),) * strings, 0), score.shape)

    found = []
    for index in dict.fromkeys([int(unchanged), *best.tolist()]):
        *choice, capo_index = np.unravel_index(index, score.shape)
        move, fret = step[choice], int(capos[capo_index])
        board = replace(base, open_strings=base.open_strings + move).capo(fret)
        options = taste.options(board, [*chords, *context])
        if any(len(voicings) == 0 for voicings in options):
            continue  # some chord has no voicing this player allows
        costs = taste.costs(board, options)
        path, cost = smoothest(
            options[: len(chords)], partial(taste.transition, board), costs[: len(chords)]
        )
        near = [chord_costs.min() for chord_costs in costs[len(chords) :]]
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


def name(open_strings: Grid, tunings: Mapping[str, Tuning]) -> str | None:
    """The catalog's name for these open strings, or a named tuning moved by whole steps, e.g.
    "guitar open D +2"; the smallest move wins."""
    moved = {}
    for tuning_name, tuning in tunings.items():
        if len(tuning.open_strings) == len(open_strings):
            shift = np.subtract(open_strings, tuning.open_strings)
            if (shift == shift[0]).all():
                moved[tuning_name] = int(shift[0])
    if not moved:
        return None
    nearest = min(moved, key=lambda one: abs(moved[one]))
    return nearest if moved[nearest] == 0 else f"{nearest} {moved[nearest]:+d}"
