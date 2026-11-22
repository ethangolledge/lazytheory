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

Two passes. A cheap screen ranks retunings and capos by how many open strings are chord tones
(`open_tones`), without building a voicing, and keeps the best few (`cheapest`). Only that
shortlist gets the full search: the
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
    unplayable: int  # context chords this neck has no allowed voicing for


def open_tones(
    open_strings: Grid, steps: Sequence[int], capos: Sequence[int], chords: Chords, size: int
) -> Grid:
    """How many of `chords` each open string is a tone of, retuned by each of `steps` at each
    of `capos`: [string, step, capo]. A string's count depends only on its own step and the
    capo, so a retuning's count is the sum of its strings', read by `cheapest` without ever
    building the len(steps) ** strings table of every retuning."""
    hits = np.zeros(size, dtype=np.int64)  # chords each pitch class belongs to
    for chord in chords:
        hits[list(chord.pitch_classes)] += 1
    pitch = np.add.outer(np.add.outer(open_strings, steps), capos) % size  # [string, step, capo]
    tables: Grid = hits[pitch]
    return tables


def cheapest(costs: Grid, count: int) -> list[tuple[tuple[int, ...], int]]:
    """The `count` cheapest (step per string, capo) choices, where a choice costs the sum of
    its strings' `costs` [string, step, capo]; cheapest first, ties in index order. Exact, as
    a choice's prefix is among the `count` best prefixes whenever the choice is among the best
    (swap in a better prefix and the whole is better), so each string keeps only `count`."""
    found = []
    for capo in range(costs.shape[2]):
        total, prefix = np.zeros(1, dtype=np.int64), np.zeros((1, 0), dtype=np.int64)
        for table in costs[:, :, capo]:
            total = (total[:, None] + table[None, :]).ravel()
            prefix = np.column_stack(
                [np.repeat(prefix, len(table), axis=0), np.tile(np.arange(len(table)), len(prefix))]
            )
            keep = np.lexsort((*prefix.T[::-1], total))[:count]  # by cost, then index order
            total, prefix = total[keep], prefix[keep]
        found += [
            (int(cost), tuple(choice.tolist()), capo)
            for cost, choice in zip(total, prefix, strict=True)
        ]
    found.sort()  # by cost, then strings, then capo: the dense table's index order
    return [(choice, capo) for _, choice, capo in found[:count]]


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
    key), so a neck that suits these chords but not the next one ranks lower. Every one of
    `chords` must be playable; a context chord that isn't is counted (`unplayable`), and necks
    that play more of the context rank first, then by cost. The screen keeps `shortlist`
    retuning and capo pairs, and always `base` with no capo when `steps` and `capos` both
    include 0. Equal costs rank the smaller retuning first, and a path playing the same
    pitches as a better one is dropped.
    """
    strings, step = len(base.open_strings), np.array(steps, dtype=np.int16)
    tones = open_tones(base.open_strings, steps, capos, chords, base.size)
    effort = np.abs(step).astype(np.int64)[None, :, None]  # per string, the same for each
    rank = effort - tones * (strings * int(effort.max()) + 1)  # most tones, then least effort
    shortlisted = cheapest(rank, shortlist)
    if 0 in steps and 0 in capos:
        shortlisted.insert(0, ((list(steps).index(0),) * strings, list(capos).index(0)))

    found = []
    for choice, capo_index in dict.fromkeys(shortlisted):
        move, fret = step[list(choice)], int(capos[capo_index])
        board = replace(base, open_strings=base.open_strings + move).capo(fret)
        options = taste.options(board, [*chords, *context])
        if any(len(voicings) == 0 for voicings in options[: len(chords)]):
            continue  # a chord of the progression has no voicing this player allows
        playable = [voicings for voicings in options[len(chords) :] if len(voicings)]
        unplayable = len(context) - len(playable)
        route = taste.trellis(board, options[: len(chords)]).shortest()
        effort_here = int(np.abs(move).sum())
        near = sum(costs.min() for costs in taste.costs(board, playable))
        total = float(route.cost + retune * effort_here + context_weight * near)
        sound = np.nan_to_num(board.notes(route.path), nan=-1).tobytes()
        suggestion = Suggestion(tuple(move.tolist()), fret, route.path, total, unplayable)
        found.append((unplayable, total, effort_here, sound, suggestion))

    heard: dict[bytes, Suggestion] = {}
    for *_, sound, suggestion in sorted(found, key=lambda one: one[:3]):
        heard.setdefault(sound, suggestion)  # the same pitches from another tuning sound the same
    return list(heard.values())[:top]
