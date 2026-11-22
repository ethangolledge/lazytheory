"""Fretted instruments: every position on the neck as arrays of steps.

Why: a guitar, a bass and a ukulele are the same object with different numbers: some open
strings, a scale length, frets that each raise a string one step. Nothing here knows a chord
shape or a scale box. It maps every way a set of notes can be played, in one pass, and then
reads any shape back: its pitches, bass, top, which notes it sounds, which chords it could be.
A capo, a retuning or a 31-step neck is the same code with another number.

Theory it speaks to: Mersenne's law (a fret leaves 1/ratio of the string sounding, so frets
get closer up the neck and reach is measured in millimetres, not frets), and the two
directions of harmony on an instrument: voicing (a chord into shapes) and reading (a shape
back into chords, by `pitch.chord.identify`).

Could grow into: fingerings (which finger on which note: `rules.placeable` already finds one
to prove a shape fits), fanned frets and per-string scale lengths, harmonics and bends as
other ways to raise a string, and keyboards as a one-string neck.

Pitches are steps above C0 and roots are pitch classes (C = 0), as the catalog defines them, so
any two necks compare by subtraction. Grids have one row per string (in tuning order) and one
column per fret (0 = open). A voicing grid has one row per voicing and one fret, or MUTED, per
string.
"""

from collections.abc import Collection, Sequence
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, NamedTuple

import numpy as np
from numpy.typing import NDArray

from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.core.temperament import EqualTemperament
from lazy_theory.instruments.arrays import MUTED, Floats, Grid, Mask
from lazy_theory.pitch.chord import Chord, Chords, Rooted, identify


class Tuning(NamedTuple):
    """A named tuning: its open strings, the neck they sit on and the pitch it is tuned from."""

    open_strings: tuple[int, ...]  # pitch of each open string, steps above C0
    scale_length: float  # millimetres from nut to bridge
    hertz: float  # frequency of pitch 0 (C0), from the file's reference
    temperament: EqualTemperament = EqualTemperament()  # the steps its pitches count


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
        if self.frets < 0:
            raise ValueError(f"a neck has zero or more frets, not {self.frets}")
        given = np.asarray(self.open_strings)
        if given.ndim != 1 or len(given) == 0 or (given % 1).any():
            raise ValueError(f"open strings are whole steps above C0, got {self.open_strings}")
        if np.abs(given).max() > np.iinfo(np.int16).max // 2:  # room to fret and capo
            raise ValueError(f"open strings out of range: {self.open_strings}")
        open_strings = given.astype(np.int16)
        open_strings.flags.writeable = False
        object.__setattr__(self, "open_strings", open_strings)

    @classmethod
    def from_tuning(cls, tuning: Tuning, frets: int = 24) -> Fretboard:
        """The neck a catalog tuning describes."""
        return cls(
            np.array(tuning.open_strings),
            tuning.scale_length,
            tuning.hertz,
            frets,
            tuning.temperament,
        )

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
        """Steps per period."""
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
        ratios = self.temperament.ratio(np.arange(self.frets + 1))
        distance: Floats = self.scale_length * (1 - 1 / ratios)
        return distance

    def intervals(self, root: int) -> Grid:
        """Pitch class at every position, measured from `root`."""
        return (self.pitches - root) % self.size

    def positions(self, notes: Rooted[Any]) -> Mask:
        """Where a chord or a key can be played: its notes at every position."""
        where: Mask = self._tones([notes])[0][self.intervals(0)]
        return where

    def voicings(self, chord: Chord, reach: float) -> Grid:
        """Every way to play `chord` with a hand that reaches `reach` mm.

        Every chord tone sounds, and every fretted note lies within `reach` mm of the lowest one
        (open strings are free), so more frets fit in the hand up the neck. A chord written
        over a bass (C/E) keeps only the voicings with that note lowest. Rows are ordered by
        their lowest fretted note, up the neck.
        """
        voicings, _ = self.voicings_of([chord], reach)
        return voicings

    def voicings_of(
        self, chords: Chords, reach: float, contiguous: bool = False
    ) -> tuple[Grid, NDArray[np.intp]]:
        """`voicings` of every chord at once, grouped by chord in order, and which chord each
        row plays. One pass over the strings serves the whole progression. `contiguous` keeps
        only voicings whose sounding strings are neighbours (rules.contiguous), never building
        the rest. No chords, no voicings."""
        if not chords:
            return np.zeros((0, len(self.open_strings)), dtype=np.int16), np.zeros(0, np.intp)
        tones = self._tones(chords)  # [chord, pitch class]
        playable = tones[:, self.intervals(0)]  # [chord, string, fret]
        which = np.arange(len(chords))
        grid = np.zeros((len(chords), 0), dtype=np.int16)
        lowest = np.full(len(chords), self.frets)  # lowest and highest fretted note so far
        highest = np.zeros(len(chords), dtype=np.int16)
        sounded = np.zeros(len(chords), dtype=bool)  # a string has sounded
        ended = np.zeros(len(chords), dtype=bool)  # then one was muted
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

        keep = ~(tones[which] & ~self.chroma(grid)).any(axis=1)  # every chord tone sounds
        written = np.array([MUTED if chord.bass is None else chord.bass for chord in chords])
        keep &= (written[which] == MUTED) | (self.bass(grid) % self.size == written[which])
        start = np.where(highest > 0, lowest, 0)[keep]  # open strings only come first
        grid, which = grid[keep], which[keep]
        order = np.lexsort((start, which))
        return grid[order], which[order]

    def readings(self, frets: Grid, patterns: Collection[PitchClassSet]) -> list[list[Chord]]:
        """Every chord each voicing could be, the inverse of `voicings`: its notes read as
        each of `patterns` on each of its own notes as root (`pitch.chord.identify`), with the
        voicing's lowest note written as the bass unless that is the root. Choosing between
        readings is the caller's: the one with no bass written sits on its root."""
        read: dict[tuple[bytes, float], list[Chord]] = {}
        readings = []
        for sounded, low in zip(self.chroma(frets), self.bass(frets) % self.size, strict=True):
            if (sounded.tobytes(), low) not in read and sounded.any():
                notes = PitchClassSet(tuple(np.flatnonzero(sounded).tolist()), self.size)
                read[sounded.tobytes(), low] = [
                    Chord(chord.pattern, chord.root, None if chord.root == low else int(low))
                    for chord in identify(notes, patterns)
                ]
            readings.append(read.get((sounded.tobytes(), low), []))
        return readings

    def chroma(self, frets: Grid) -> Mask:
        """Which pitch classes each voicing sounds, as [voicing, pitch class]: the form every
        set compares in (a chord, a key or another voicing is one such row)."""
        row, string = np.nonzero(frets != MUTED)
        chroma = np.zeros((len(frets), self.size), dtype=bool)
        chroma[row, (self.open_strings[string] + frets[row, string]) % self.size] = True
        return chroma

    def notes(self, frets: Grid) -> Floats:
        """Pitch of each string in each voicing, in steps above C0; NaN where muted."""
        notes: Floats = np.where(frets != MUTED, self.open_strings + frets, np.nan)
        return notes

    def bass(self, frets: Grid) -> Floats:
        """Lowest pitch of each voicing, the note that names its inversion; NaN if silent."""
        notes = self.notes(frets)
        bass: Floats = np.fmin.reduce(notes, axis=1, initial=np.nan)
        return bass

    def top(self, frets: Grid) -> Floats:
        """Highest pitch of each voicing, where a melody is heard; NaN if silent."""
        notes = self.notes(frets)
        top: Floats = np.fmax.reduce(notes, axis=1, initial=np.nan)
        return top

    def stack(self, frets: Grid, root: int) -> Grid:
        """Intervals above `root` of each voicing's notes, lowest pitch first, then MUTED.

        Column 0 is the bass, so it names the inversion: 0 is root position. Sorted by pitch,
        not string, so re-entrant tunings are handled.
        """
        notes = np.sort(self.notes(frets), axis=1)
        intervals = np.where(np.isnan(notes), MUTED, (notes - root) % self.size)
        stack: Grid = intervals.astype(np.int16)
        return stack

    def _tones(self, sets: Sequence[Rooted[Any]]) -> Mask:
        """Which pitch classes each chord or key holds, as [set, pitch class]: the same form
        as `chroma`, so a voicing is checked against its chord by comparing rows."""
        tones = np.zeros((len(sets), self.size), dtype=bool)
        for index, notes in enumerate(sets):
            if notes.size != self.size:
                raise ValueError(f"set has {notes.size} steps per period, not {self.size}")
            tones[index, list(notes.pitch_classes)] = True
        return tones


def _options(playable: NDArray[np.bool_]) -> tuple[Grid, NDArray[np.bool_]]:
    """Each chord's playable frets on one string, lowest first, then MUTED; padded to the chord
    with the most, with a mask of the real ones. `playable` is [chord, fret]."""
    count = playable.sum(axis=1)
    frets = np.argsort(~playable, axis=1, kind="stable")[:, : count.max()]
    muted = np.full((len(playable), 1), MUTED)
    options = np.column_stack([frets, muted]).astype(np.int16)
    valid = np.column_stack([np.arange(frets.shape[1]) < count[:, None], muted == MUTED])
    return options, valid
