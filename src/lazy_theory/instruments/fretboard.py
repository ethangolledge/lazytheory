"""Fretted instruments: every position on the neck as arrays of steps.

Pitches are steps above C0 and roots are pitch classes (C = 0), as the catalog defines them, so
any two necks compare by subtraction. Grids have one row per string (in tuning order) and one
column per fret (0 = open).
A voicing grid has one row per voicing and one fret, or MUTED, per string.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from functools import cached_property

import numpy as np
from numpy.typing import NDArray

from lazy_theory.catalog import Tuning
from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.core.temperament import EqualTemperament

MUTED = -1
Grid = NDArray[np.int16]
Floats = NDArray[np.float64]
Chords = Sequence[tuple[PitchClassSet, int]]  # (chord, root) in order


@dataclass(frozen=True, eq=False)
class Fretboard:
    """Open-string pitches (steps above C0) on a neck `scale_length` mm long, pitch 0 sounding
    at `hertz`. Each fret raises a string one step of `temperament`."""

    open_strings: Grid
    scale_length: float
    hertz: float
    frets: int = 24
    temperament: EqualTemperament = field(default_factory=EqualTemperament)

    def __post_init__(self) -> None:
        open_strings = np.array(self.open_strings, dtype=np.int16)
        open_strings.flags.writeable = False
        object.__setattr__(self, "open_strings", open_strings)

    @classmethod
    def from_tuning(cls, tuning: Tuning, frets: int = 24) -> Fretboard:
        return cls(np.array(tuning.open_strings), tuning.scale_length, tuning.hertz, frets)

    def capo(self, fret: int) -> Fretboard:
        """The neck with a capo at `fret`: a movable nut. The open strings sound `fret` steps
        higher, the vibrating length shrinks to 1/ratio of the scale length, and fret numbers
        count from the capo, as tab written for a capo does."""
        if not 0 <= fret < self.frets:
            raise ValueError(f"capo must sit between frets 0 and {self.frets - 1}, not {fret}")
        return Fretboard(
            self.open_strings + fret,
            self.scale_length / self.temperament.ratio(fret),
            self.hertz,
            self.frets - fret,
            self.temperament,
        )

    @property
    def size(self) -> int:
        return self.temperament.size

    @cached_property
    def pitches(self) -> Grid:
        """Pitch at every position, in steps above C0."""
        frets = np.arange(self.frets + 1, dtype=np.int16)
        pitches: Grid = self.open_strings[:, None] + frets
        return pitches

    @cached_property
    def fret_distance(self) -> Floats:
        """Millimetres from the nut to each fret. Frequency is inversely proportional to the
        vibrating length, so a fret leaves 1/ratio of the string sounding and frets get closer
        together up the neck."""
        ratios = np.array([self.temperament.ratio(fret) for fret in range(self.frets + 1)])
        distance: Floats = self.scale_length * (1 - 1 / ratios)
        return distance

    def intervals(self, root: int) -> Grid:
        """Pitch class at every position, measured from `root`."""
        return (self.pitches - root) % self.size

    def positions(self, pitch_classes: PitchClassSet, root: int) -> NDArray[np.bool_]:
        """Where a scale or chord, measured from `root`, can be played."""
        if pitch_classes.size != self.size:
            raise ValueError(f"set has {pitch_classes.size} steps per period, not {self.size}")
        return np.isin(self.intervals(root), pitch_classes.pitch_classes)

    def voicings(self, chord: PitchClassSet, root: int, reach: float) -> Grid:
        """Every way to play `chord` on `root` with a hand that reaches `reach` mm.

        Every chord tone sounds, and every fretted note lies within `reach` mm of the lowest one
        (open strings are free), so more frets fit in the hand up the neck. Rows are ordered by
        their lowest fretted note, up the neck.
        """
        voicings, _ = self.voicings_of([(chord, root)], reach)
        return voicings

    def voicings_of(
        self, chords: Chords, reach: float, contiguous: bool = False
    ) -> tuple[Grid, NDArray[np.intp]]:
        """`voicings` of every chord at once, grouped by chord in order, and which chord each
        row plays. One pass over the strings serves the whole progression. `contiguous` keeps
        only voicings whose sounding strings are neighbours (rules.contiguous), never building
        the rest."""
        playable = np.stack([self.positions(chord, root) for chord, root in chords])
        tones = np.zeros((len(chords), self.size), dtype=bool)  # [chord, interval]
        for index, (chord, _) in enumerate(chords):
            tones[index, chord.pitch_classes] = True
        roots = np.array([root for _, root in chords])

        which = np.arange(len(chords))
        grid = np.zeros((len(chords), 0), dtype=np.int16)
        lowest = np.full(len(chords), self.frets)  # lowest and highest fretted note so far
        highest = np.zeros(len(chords), dtype=np.int16)
        sounded = ended = np.zeros(len(chords), dtype=bool)  # a string sounded; then one muted
        for string in range(len(self.open_strings)):  # add a string, keep what the hand can span
            options, valid = _options(playable[:, string])  # [chord, option], up the neck
            parent = np.repeat(np.arange(len(grid)), options.shape[1])
            slot = np.tile(np.arange(options.shape[1]), len(grid))
            fret = options[which[parent], slot]
            low = np.where(fret > 0, np.minimum(lowest[parent], fret), lowest[parent])
            high = np.maximum(highest[parent], fret)
            keep = valid[which[parent], slot]
            keep &= self.fret_distance[high] <= self.fret_distance[low] + reach
            sounds = fret != MUTED
            if contiguous:
                keep &= ~(sounds & ended[parent])
            ended = (ended[parent] | (sounded[parent] & ~sounds))[keep]
            sounded = (sounded[parent] | sounds)[keep]
            parent, lowest, highest = parent[keep], low[keep], high[keep]
            grid, which = np.column_stack([grid[parent], fret[keep]]), which[parent]

        row, string = np.nonzero(grid != MUTED)
        heard = np.zeros((len(grid), self.size), dtype=bool)
        heard[
            row, (self.open_strings[string] + grid[row, string] - roots[which[row]]) % self.size
        ] = True
        every_tone = ~(tones[which] & ~heard).any(axis=1)
        start = np.where(highest > 0, lowest, 0)[every_tone]  # open strings only come first
        grid, which = grid[every_tone], which[every_tone]
        order = np.lexsort((start, which))
        return grid[order], which[order]

    def notes(self, frets: Grid) -> Floats:
        """Pitch of each string in each voicing, in steps above C0; NaN where
        muted."""
        notes: Floats = np.where(frets != MUTED, self.open_strings + frets, np.nan)
        return notes

    def frequencies(self, frets: Grid) -> Floats:
        """Frequency of each string in each voicing, in hertz; NaN where muted."""
        period = float(self.temperament.period)
        frequencies: Floats = self.hertz * period ** (self.notes(frets) / self.size)
        return frequencies

    def stack(self, frets: Grid, root: int) -> Grid:
        """Intervals above `root` of each voicing's notes, lowest pitch first, then MUTED.

        Column 0 is the bass, so it names the inversion: 0 is root position. Sorted by pitch,
        not string, so re-entrant tunings are handled.
        """
        notes = np.sort(self.notes(frets), axis=1)
        intervals = np.where(np.isnan(notes), MUTED, (notes - root) % self.size)
        stack: Grid = intervals.astype(np.int16)
        return stack

    def hand(self, frets: Grid) -> Floats:
        """Where the hand sits for each voicing: millimetres from the nut to its lowest fretted
        note, where the index finger goes. NaN when nothing is fretted."""
        lowest = np.where(frets > 0, frets, self.frets + 1).min(axis=1)
        hand: Floats = np.append(self.fret_distance, np.nan)[lowest]
        return hand


def _options(playable: NDArray[np.bool_]) -> tuple[Grid, NDArray[np.bool_]]:
    """Each chord's playable frets on one string, lowest first, then MUTED; padded to the chord
    with the most, with a mask of the real ones. `playable` is [chord, fret]."""
    count = playable.sum(axis=1)
    frets = np.argsort(~playable, axis=1, kind="stable")[:, : count.max()]
    muted = np.full((len(playable), 1), MUTED)
    options = np.column_stack([frets, muted]).astype(np.int16)
    valid = np.column_stack([np.arange(frets.shape[1]) < count[:, None], muted == MUTED])
    return options, valid
