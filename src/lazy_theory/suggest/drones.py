"""Drones: one note held on one string while the chords change around it.

Why: a note that rings through a whole progression glues it together, and on a guitar it is
free: a string left open or a finger left down. It also recolours the chords it doesn't belong
to, which is where much of the sound of open tunings and "jangly" guitar parts comes from.

Theory it speaks to: the pedal point, a note held while the harmony moves, often against
chords it doesn't belong to: that clash and its release is the point. In the bass it is a
pedal, on top an inverted pedal, in between an internal one; two at once are a double pedal.
Where the held note isn't in a chord it joins it, so C under a held D becomes C(9).

Could grow into: drones outside the key's stable notes, pedals that move once (a held note
stepping at a cadence), and drones chosen by a tuning search (open strings as pedals).
Optional, like the rest of this layer.
"""

from collections.abc import Iterable, Mapping, Sequence
from typing import NamedTuple

import numpy as np

from lazy_theory.instruments.arrays import MUTED, Grid, Mask
from lazy_theory.instruments.fretboard import Fretboard
from lazy_theory.instruments.taste import Taste
from lazy_theory.pitch.chord import Chord, Chords


class Drone(NamedTuple):
    """A note held on fixed strings through a run of chords, and the route that holds it."""

    strings: tuple[int, ...]  # every string held through the run: two make a double pedal
    frets: tuple[int, ...]  # where each is held
    first: int  # the first and last chord it is held through
    last: int
    chords: tuple[Chord, ...]  # every chord of the progression, with the note added where held
    path: Grid  # one voicing per chord
    extra: float  # what holding costs, over the same chords played without holding


def drones(
    board: Fretboard,
    taste: Taste,
    chords: Chords,
    notes: Iterable[int],
    slack: float | None = None,
) -> list[Drone]:
    """Each way to hold one of `notes` (pitch classes, e.g. the key's) on one string at one fret
    through two or more chords in a row, as the cheapest route that holds it there. A drone is
    kept when holding costs at most `slack` more (default: one string starting or stopping)
    than the best route through the same chords, the note added, without holding it: so it is
    the holding that is measured, not what the added note does to the chords. Held through the
    most chords first, then cheapest to hold. A route found from several held notes is kept
    once, naming every string it holds.
    """
    slack = taste.strings_changed if slack is None else slack
    coloured = {note: [chord.with_note(note) for chord in chords] for note in sorted(set(notes))}
    every = [*chords, *(chord for added in coloured.values() for chord in added)]
    voicings = dict(zip(every, taste.options(board, every), strict=True))  # each built once
    kept: dict[tuple[bytes, int, int], Drone] = {}
    for note, added in coloured.items():
        for drone in _holding(board, taste, chords, added, note, voicings):
            if drone.extra <= slack + 1e-9:
                kept.setdefault((drone.path.tobytes(), drone.first, drone.last), drone)
    return sorted(kept.values(), key=lambda drone: (drone.first - drone.last, drone.extra))


def _holding(
    board: Fretboard,
    taste: Taste,
    chords: Chords,
    coloured: Chords,
    note: int,
    voicings: Mapping[Chord, Grid],
) -> list[Drone]:
    """Every way to hold `note` through a run of chords, whatever it costs: `coloured` are
    the chords with the note added, `voicings` each chord's options.

    One graph and one batch of searches: each chord's voicings with and without the note side
    by side, and each candidate (a string, a fret, a run of chords) a mask saying where the
    note must be added and held. Outside its run a candidate plays the chords as written.
    """
    places = range(len(chords))
    plain, added = [voicings[chord] for chord in chords], [voicings[c] for c in coloured]
    slots = [np.concatenate(pair) for pair in zip(plain, added, strict=True)]
    with_note = [np.arange(len(slots[i])) >= len(plain[i]) for i in places]

    held = []  # each candidate: its run of chords, and where it holds the note in each
    for string, fret in zip(*np.nonzero(board.intervals(note) == 0), strict=True):
        holding = [with_note[i] & (slots[i][:, string] == fret) for i in places]
        held += [(run, holding) for run in _runs([bool(h.any()) for h in holding])]
    if not held:
        return []
    runs = sorted({run for run, _ in held})
    searches = [(run, with_note) for run in runs] + held  # each run not held, then each held
    trellis = taste.trellis(board, slots)

    def allowed(i: int) -> Mask:  # per search: chord i with the note inside the run only
        return np.stack([w[i] if a <= i <= b else ~with_note[i] for (a, b), w in searches])

    picks, totals = trellis.search([allowed(i) for i in places])
    free = dict(zip(runs, totals[: len(runs)], strict=True))  # the free searches come first
    found = []
    results = zip(held, picks[len(runs) :], totals[len(runs) :], strict=True)
    for ((first, last), _), pick, total in results:
        if not np.isfinite(total):
            continue  # some chord outside the run has no voicing
        path = trellis.route(pick, float(total)).path
        shape, same = path[first], (path[first : last + 1] == path[first]).all(axis=0)
        strings = np.flatnonzero(same & (shape != MUTED))
        played = (*chords[:first], *coloured[first : last + 1], *chords[last + 1 :])
        where = tuple(strings.tolist()), tuple(shape[strings].tolist())
        found.append(Drone(*where, first, last, played, path, float(total - free[first, last])))
    return found


def _runs(holds: Sequence[bool]) -> list[tuple[int, int]]:
    """Each longest stretch of two or more True in a row, as (first, last)."""
    runs, start = [], None
    for index, holding in enumerate([*holds, False]):
        if holding and start is None:
            start = index
        elif not holding and start is not None:
            if index - start >= 2:
                runs.append((start, index - 1))
            start = None
    return runs
