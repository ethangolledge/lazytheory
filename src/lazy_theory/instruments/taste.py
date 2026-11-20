"""A player's taste: what their hand can play and what they listen for, as one set of rules and
weights.

Why: there is no best voicing, only best for someone: a hand of a certain size, on a part of
the neck, who minds a muted string more or less than a stretch. Putting every such choice in
one frozen value means every search (the smoothest path, a tuning suggestion, a harmonised
melody) judges voicings the same way, a preference is changed in one place, and a different
player is a different Taste, not different code.

Theory it speaks to: sensory roughness for how a voicing sounds (`acoustics`), and voice
leading for how one follows another: steps moved on each string, strings entering or leaving,
motion of the bass. The weights are the open question of the whole library: they are stated
here, not hidden, because they are choices, not measurements.

Could grow into: weights fitted to how people actually play (tabs give thousands of real
chord changes to rank), tastes per style, and costs on the outer voices or on fingering
changes. To add a rule or a cost, subclass and extend `allows`, `standing` or `transition`
with `super()`: every search that takes a Taste then uses it (`suggest.melody.MelodicTaste`).
"""

from collections.abc import Callable
from dataclasses import dataclass, replace
from functools import partial

import numpy as np

from lazy_theory.core.chord import Chord, Chords
from lazy_theory.instruments.acoustics import tempered_roughness
from lazy_theory.instruments.arrays import Floats, Grid, Mask
from lazy_theory.instruments.fretboard import Fretboard
from lazy_theory.instruments.rules import (
    contiguous,
    motion,
    moved,
    open_within,
    placeable,
    ringing,
    sounding,
    strings_changed,
    within,
)
from lazy_theory.instruments.trellis import Route, Trellis


@dataclass(frozen=True)
class Taste:
    """Rules a voicing must pass, then weights on what it costs. Frets count from the capo."""

    # the hand: mm between fingers 1, 2 and 3 apart, so four fingers. One finger per fret at
    # frets 1-4 of a 648 mm neck, the widest frets, rounded up. A shorter tuple is fewer fingers.
    spans: tuple[float, ...] = (34.4, 66.8, 97.4)
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
        """mm the whole hand spans, first finger to last."""
        return self.spans[-1]

    def voicings(self, board: Fretboard, chord: Chord) -> Grid:
        """Every voicing of `chord` this hand can play and this player allows."""
        (allowed,) = self.options(board, [chord])
        return allowed

    def options(self, board: Fretboard, chords: Chords) -> list[Grid]:
        """`voicings` of each chord, built and filtered for all of them at once. A chord that
        comes round again is built once and shares its grid, so treat the grids as read-only."""
        unique = list(dict.fromkeys(chords))
        if not unique:
            return []
        neck = replace(board, frets=min(board.frets, self.highest))  # never build what's cut
        voicings, which = neck.voicings_of(unique, self.reach, self.contiguous)
        keep = self.allows(neck, voicings)
        counts = np.bincount(which[keep], minlength=len(unique))  # rows are in chord order
        built = dict(zip(unique, np.split(voicings[keep], np.cumsum(counts)[:-1]), strict=True))
        return [built[chord] for chord in chords]

    def allows(self, board: Fretboard, voicings: Grid) -> Mask:
        """Which voicings this player allows and this hand can play, however they were made:
        the rules `options` builds with, checked on any grid."""
        keep = within(voicings, self.lowest, self.highest) & (voicings <= board.frets).all(axis=1)
        if self.contiguous:
            keep &= contiguous(voicings)
        if self.open_within is not None:
            keep &= open_within(voicings, self.open_within)
        keep[keep] = placeable(voicings[keep], board.fret_distance, self.spans)  # costly: last
        return keep

    def standing(self, board: Fretboard, voicings: Grid) -> Floats:
        """Cost of each voicing on its own."""
        rough = tempered_roughness(board.notes(voicings), board.hertz, board.temperament)
        reward = self.sounding * sounding(voicings) + self.ringing * ringing(voicings)
        cost: Floats = self.roughness * rough - reward
        return cost

    def costs(self, board: Fretboard, options: list[Grid]) -> list[Floats]:
        """`standing` of each chord's options, scored together."""
        if not options:
            return []
        every = self.standing(board, np.concatenate(options))
        return np.split(every, np.cumsum([len(voicings) for voicings in options])[:-1])

    def transition(self, board: Fretboard, previous: Grid, following: Grid) -> Floats:
        """Cost of each change from a previous voicing to a following one."""
        cost: Floats = (
            self.moved * moved(previous, following)
            + self.strings_changed * strings_changed(previous, following)
            + self.bass * motion(board.bass(previous), board.bass(following))
        )
        return cost

    def trellis(self, board: Fretboard, options: list[Grid]) -> Trellis:
        """The progression as this player hears and plays it: `options` as a graph weighted by
        `standing` and `transition`, ready for any search (`trellis.Trellis`)."""
        return Trellis.build(options, partial(self.transition, board), self.costs(board, options))

    def path(self, board: Fretboard, chords: Chords) -> Route:
        """The cheapest voicing of each chord through the progression."""
        return self.trellis(board, self.options(board, chords)).shortest()

    def lines(
        self,
        board: Fretboard,
        chords: Chords,
        voice: Callable[[Fretboard, Grid], Floats] = Fretboard.top,
        slack: float | None = None,
    ) -> list[Route]:
        """The cheapest route for each line one voice can take, cheapest first: `voice` gives
        that voice's pitch in each voicing (`Fretboard.top` for the top line, `Fretboard.bass`
        for the bass line), and each route's `labels` are its line. Only lines whose route
        costs at most `slack` more than `path` are kept; `slack` defaults to the cost of one
        string starting or stopping, so every line is about as easy as the best."""
        options = self.options(board, chords)
        labels = [voice(board, voicings) for voicings in options]
        slack = self.strings_changed if slack is None else slack
        return self.trellis(board, options).each(labels, slack)
