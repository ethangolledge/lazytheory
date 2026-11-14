"""Fretted instruments: every position on the neck as arrays of steps.

Everything is relative. The first open string is pitch 0, and a key's root is a step count from
that string. Grids have one row per string (in tuning order) and one column per fret (0 = open).
A voicing grid has one row per voicing and one fret, or MUTED, per string.
"""

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


@dataclass(frozen=True, eq=False)
class Fretboard:
    """Open-string pitches on a neck `scale_length` mm long, pitch 0 sounding at `hertz`. Each
    fret raises a string one step of `temperament`."""

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
        """Open strings from the tuning's gaps. Negative gaps are re-entrant strings."""
        open_strings = np.cumsum([0, *tuning.gaps], dtype=np.int16)
        return cls(open_strings, tuning.scale_length, tuning.hertz, frets)

    @property
    def size(self) -> int:
        return self.temperament.size

    @cached_property
    def pitches(self) -> Grid:
        """Pitch at every position, in steps above the first open string."""
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
        playable = self.positions(chord, root)
        tones = np.array(chord.pitch_classes, dtype=np.int16)
        return np.concatenate(
            [
                self._voicings_from(playable, tones, root, lowest, reach)
                for lowest in range(self.frets + 1)
            ]
        )

    def _voicings_from(
        self, playable: NDArray[np.bool_], tones: Grid, root: int, lowest: int, reach: float
    ) -> Grid:
        """Voicings whose lowest fretted note is at fret `lowest` (0 means open strings only).

        Every combination of each string's options in the window is built as one array, then
        filtered with vector operations.
        """
        fret = np.arange(self.frets + 1)
        in_hand = (fret >= lowest) & (self.fret_distance <= self.fret_distance[lowest] + reach)
        window = (fret == 0) | (in_hand & (lowest > 0))
        options = [np.append(np.flatnonzero(string & window), MUTED) for string in playable]
        grid = np.stack(np.meshgrid(*options, indexing="ij"), axis=-1)
        grid = grid.reshape(-1, len(options)).astype(np.int16)

        no_fret = self.frets + 1
        lowest_fretted = np.where(grid > 0, grid, no_fret).min(axis=1)
        starts_here = lowest_fretted == (lowest or no_fret)

        sounding = np.where(grid != MUTED, (self.open_strings + grid - root) % self.size, MUTED)
        every_tone = (sounding[:, :, None] == tones).any(axis=1).all(axis=1)
        voicings: Grid = grid[starts_here & every_tone]
        return voicings

    def notes(self, frets: Grid) -> Floats:
        """Pitch of each string in each voicing, in steps above the first open string; NaN where
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
