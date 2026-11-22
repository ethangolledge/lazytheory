"""Suggest a tuning and capo for a progression.

Why: players reach for drop D or a capo by habit, but a tuning is a choice like any other: the
right one puts the song's notes on open strings and its shapes under the hand. Since every
other search already scores a neck, the best neck is one more search over that score.

Theory it speaks to: scordatura and the capo as the same act (moving the open strings), and
string tension, which rises with the square of frequency and bounds how far a string may move.

Could grow into: partial capos, one tuning for a whole set of songs, and string gauges chosen
for a tuning.

A tuning is just its open strings' pitches, so candidates are generated, not looked up: every
way to retune each string within safe tension. Names come afterwards
(`instruments.names.tuning_name`).

Two passes. A cheap screen scores every retuning at every capo at once by how many open strings
are chord tones, without building a voicing. Only the shortlist gets the full search: the
player's cheapest path through the progression, plus what the retuning costs and how well the
key's other chords sit on the same neck.
"""

from collections.abc import Sequence
from dataclasses import replace
from typing import NamedTuple

import numpy as np

from lazy_theory.instruments.arrays import Grid
from lazy_theory.instruments.fretboard import Fretboard
from lazy_theory.instruments.taste import Taste
from lazy_theory.pitch.chord import Chords

# Tension rises with the square of frequency: 4 steps down leaves 63% of it, 2 up adds 26%.
SAFE_STEPS = range(-4, 3)


class Suggestion(NamedTuple):
    """A retuning and capo, with the cheapest way to play the progression on that neck."""

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
    no capo when `steps` and `capos` both include 0. Equal costs rank the smaller retuning
    first, and a path playing the same pitches as a better one is dropped.
    """
    strings, step = len(base.open_strings), np.array(steps, dtype=np.int16)
    score = screen(base.open_strings, steps, capos, chords, base.size).astype(np.int32)
    effort = _by_string(np.broadcast_to(np.abs(step)[:, None], (strings, len(step), 1)))
    rank = ((score.max() - score) * (effort.max() + 1) + effort).ravel()  # tones, then effort
    kth = min(shortlist, rank.size) - 1
    tied = np.flatnonzero(rank <= np.partition(rank, kth)[kth])  # in order, as a stable sort
    shortlisted = tied[np.argsort(rank[tied], kind="stable")][:shortlist].tolist()
    if 0 in steps and 0 in capos:
        unchanged = (*(list(steps).index(0),) * strings, list(capos).index(0))
        shortlisted.insert(0, int(np.ravel_multi_index(unchanged, score.shape)))

    found = []
    for index in dict.fromkeys(shortlisted):
        *choice, capo_index = np.unravel_index(index, score.shape)
        move, fret = step[choice], int(capos[capo_index])
        board = replace(base, open_strings=base.open_strings + move).capo(fret)
        options = taste.options(board, [*chords, *context])
        if any(len(voicings) == 0 for voicings in options):
            continue  # some chord has no voicing this player allows
        route = taste.trellis(board, options[: len(chords)]).shortest()
        effort_here = int(np.abs(move).sum())
        nearby = taste.costs(board, options[len(chords) :]) if context else []
        near = sum(chord_costs.min() for chord_costs in nearby)
        total = float(route.cost + retune * effort_here + context_weight * near)
        sound = np.nan_to_num(board.notes(route.path), nan=-1).tobytes()
        suggestion = Suggestion(tuple(move.tolist()), fret, route.path, total)
        found.append((total, effort_here, sound, suggestion))

    heard: dict[bytes, Suggestion] = {}
    for _, _, sound, suggestion in sorted(found, key=lambda one: one[:2]):
        heard.setdefault(sound, suggestion)  # the same pitches from another tuning sound the same
    return list(heard.values())[:top]
