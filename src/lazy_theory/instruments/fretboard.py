"""Fretted instruments: every position on the neck as arrays of steps.

Everything is relative. A tuning is the gaps in steps between neighbouring open strings, the
first open string is pitch 0, and a key's root is a step count from that string. Grids have one
row per string (in tuning order) and one column per fret (0 = open).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from functools import cached_property

import numpy as np
from numpy.typing import NDArray

from lazy_theory.core.pcset import PitchClassSet

MUTED = -1
Grid = NDArray[np.int16]


@dataclass(frozen=True, eq=False)
class Fretboard:
    """Open-string pitches plus a fret count. One fret per step, `size` steps per period."""

    open_strings: Grid
    frets: int = 24
    size: int = 12

    def __post_init__(self) -> None:
        open_strings = np.array(self.open_strings, dtype=np.int16)
        open_strings.flags.writeable = False
        object.__setattr__(self, "open_strings", open_strings)

    @classmethod
    def from_gaps(cls, gaps: Sequence[int], frets: int = 24, size: int = 12) -> Fretboard:
        """Build from the step gaps between neighbouring strings. Negative gaps are allowed, for
        re-entrant tunings like the ukulele's."""
        return cls(np.cumsum([0, *gaps], dtype=np.int16), frets, size)

    @cached_property
    def pitches(self) -> Grid:
        """Pitch at every position, in steps above the first open string."""
        frets = np.arange(self.frets + 1, dtype=np.int16)
        pitches: Grid = self.open_strings[:, None] + frets
        return pitches

    def intervals(self, root: int) -> Grid:
        """Pitch class at every position, measured from `root`."""
        return (self.pitches - root) % self.size

    def positions(self, pitch_classes: PitchClassSet, root: int) -> NDArray[np.bool_]:
        """Where a scale or chord, measured from `root`, can be played."""
        if pitch_classes.size != self.size:
            raise ValueError(f"set has {pitch_classes.size} steps per period, not {self.size}")
        return np.isin(self.intervals(root), pitch_classes.pitch_classes)

    def voicings(self, chord: PitchClassSet, root: int, max_span: int = 4) -> Grid:
        """Every way to play `chord` on `root`, one row per voicing, one fret or MUTED per string.

        Every chord tone sounds, and fretted notes lie within `max_span` frets of each other
        (open strings are free). Rows are ordered by their lowest fretted note, up the neck.
        """
        playable = self.positions(chord, root)
        tones = np.array(chord.pitch_classes, dtype=np.int16)
        return np.concatenate(
            [
                self._voicings_from(playable, tones, root, lowest, max_span)
                for lowest in range(self.frets + 1)
            ]
        )

    def _voicings_from(
        self, playable: NDArray[np.bool_], tones: Grid, root: int, lowest: int, max_span: int
    ) -> Grid:
        """Voicings whose lowest fretted note is at fret `lowest` (0 means open strings only).

        Every combination of each string's options in the window is built as one array, then
        filtered with vector operations.
        """
        highest = lowest + max_span if lowest else 0
        options = []
        for string in playable:
            frets = np.flatnonzero(string)
            in_window = frets[(frets == 0) | ((frets >= lowest) & (frets <= highest))]
            options.append(np.append(in_window, MUTED))
        grid = np.stack(np.meshgrid(*options, indexing="ij"), axis=-1)
        grid = grid.reshape(-1, len(options)).astype(np.int16)

        no_fret = self.frets + 1
        lowest_fretted = np.where(grid > 0, grid, no_fret).min(axis=1)
        starts_here = lowest_fretted == (lowest or no_fret)

        sounding = np.where(grid != MUTED, (self.open_strings + grid - root) % self.size, MUTED)
        every_tone = (sounding[:, :, None] == tones).any(axis=1).all(axis=1)
        voicings: Grid = grid[starts_here & every_tone]
        return voicings

    def bass(self, frets: Grid, root: int) -> Grid:
        """Interval above `root` of each voicing's lowest-sounding pitch: 0 is root position,
        and any other chord tone names the inversion. Found by pitch, so re-entrant strings
        are handled."""
        pitches = np.where(frets != MUTED, self.open_strings + frets, np.iinfo(np.int16).max)
        bass: Grid = (pitches.min(axis=1) - root) % self.size
        return bass
