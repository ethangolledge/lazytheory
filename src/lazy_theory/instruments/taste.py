"""A player's taste: what their hand can play and what they listen for, as one set of rules and
weights. Every search scores voicings through a Taste, so changing a preference is one edit.
"""

from dataclasses import dataclass, replace
from functools import partial

import numpy as np
from numpy.typing import NDArray

from lazy_theory.core.chord import Chord, Chords
from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.instruments.acoustics import tempered_roughness
from lazy_theory.instruments.arrays import Floats, Grid
from lazy_theory.instruments.fretboard import Fretboard
from lazy_theory.instruments.rules import (
    motion,
    moved,
    open_within,
    placeable,
    ringing,
    smoothest,
    sounding,
    strings_changed,
    within,
)


@dataclass(frozen=True)
class Taste:
    """Rules a voicing must pass, then weights on what it costs. Frets count from the capo."""

    # mm between fingers 1, 2 and 3 apart: one finger per fret at frets 1-4 of a 648 mm neck,
    # the widest frets, rounded up
    spans: tuple[float, ...] = (34.4, 66.8, 97.4)
    fingers: int = 4  # fretting fingers, index first; at most len(spans) + 1
    lowest: int = 0  # fretted notes between these frets; open strings always allowed
    highest: int = 7
    open_within: int | None = None  # open strings only with fretted notes this low
    contiguous: bool = True
    roughness: float = 10.0
    sounding: float = 0.0  # reward per string that sounds: a fuller chord
    ringing: float = 0.0  # reward per open string: it sustains undamped
    moved: float = 1.0  # per step moved on a string
    strings_changed: float = 5.0  # per string that starts or stops
    bass: float = 1.0  # per step the lowest note moves

    @property
    def reach(self) -> float:
        """mm the whole hand spans, index to pinky."""
        return self.spans[-1]

    def voicings(self, board: Fretboard, chord: PitchClassSet, root: int) -> Grid:
        """Every voicing of `chord` this hand can play and this player allows."""
        (allowed,) = self.options(board, [Chord(chord, root)])
        return allowed

    def options(self, board: Fretboard, chords: Chords) -> list[Grid]:
        """`voicings` of each chord, built and filtered for all of them at once."""
        neck = replace(board, frets=min(board.frets, self.highest))  # never build what's cut
        voicings, which = neck.voicings_of(chords, self.reach, self.contiguous)
        keep = within(voicings, self.lowest, self.highest)
        if self.open_within is not None:
            keep &= open_within(voicings, self.open_within)
        voicings, which = voicings[keep], which[keep]  # the hand check is costly, so it's last
        keep = placeable(voicings, neck.fret_distance, self.spans[: self.fingers - 1])
        return _by_chord(voicings[keep], which[keep], len(chords))

    def costs(self, board: Fretboard, options: list[Grid]) -> list[Floats]:
        """`standing` of each chord's options, scored together."""
        every = self.standing(board, np.concatenate(options))
        return np.split(every, np.cumsum([len(voicings) for voicings in options])[:-1])

    def standing(self, board: Fretboard, voicings: Grid) -> Floats:
        """Cost of each voicing on its own."""
        rough = tempered_roughness(board.notes(voicings), board.hertz, board.temperament)
        reward = self.sounding * sounding(voicings) + self.ringing * ringing(voicings)
        cost: Floats = self.roughness * rough - reward
        return cost

    def transition(self, board: Fretboard, previous: Grid, following: Grid) -> Floats:
        """Cost of each change from a previous voicing to a following one."""
        bass = [board.bass(voicings) for voicings in (previous, following)]
        cost: Floats = (
            self.moved * moved(previous, following)
            + self.strings_changed * strings_changed(previous, following)
            + self.bass * motion(*bass)
        )
        return cost

    def path(self, board: Fretboard, chords: Chords) -> tuple[Grid, float]:
        """The cheapest voicing of each chord through the progression, and its total cost."""
        options = self.options(board, chords)
        return smoothest(options, partial(self.transition, board), self.costs(board, options))


def _by_chord(rows: Grid, which: NDArray[np.intp], chords: int) -> list[Grid]:
    """Rows grouped by chord (already in chord order) into one array per chord."""
    return np.split(rows, np.cumsum(np.bincount(which, minlength=chords))[:-1])
