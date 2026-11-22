"""A pattern on a root: what a chord and a key both are, and reading a set back as chords.

Why: "E minor" and "E Phrygian" are the same kind of thing, a pattern of intervals placed on
a root, and differ only in which pattern. Stack a seven-note scale in thirds and the seven-note
chord you reach (the 13th) is the scale itself. So `Rooted` holds the shared arithmetic once:
which notes it has, what interval a note makes with the root, whether a note belongs. `Chord`
adds only what is a chord's own: a bass written under a slash. (`Key`, next door, adds the
chords on its degrees.)

Theory it speaks to: chords as transposition classes of pitch-class sets; inversion as a
choice of bass, not a different chord (Rameau's basse fondamentale); and the fact that one set
can be read on several roots (C6 is Am7), which `identify` returns in full instead of guessing.

Could grow into: negative harmony and other inversions (`Rooted` mirrored about an axis),
chord-scale matching (`all(note in key for note in chord.pitch_classes)`), and polychords.
Names stay out: `identify` is handed its patterns, so core never learns a naming convention.
"""

from collections.abc import Collection, Sequence
from dataclasses import dataclass, replace
from functools import cached_property
from numbers import Integral
from operator import index

from lazy_theory.core.pcset import PitchClassSet


@dataclass(frozen=True)
class Rooted[Pattern: PitchClassSet]:
    """`pattern` (intervals above the root, e.g. (0, 3, 7)) on `root`, a pitch class. The
    pattern holds its root, 0: a chord is named from a note it has. The root is a whole step
    reduced mod the pattern's size, so equal things compare equal."""

    pattern: Pattern
    root: int

    def __post_init__(self) -> None:
        if 0 not in self.pattern.pitch_classes:
            raise ValueError(f"a {type(self).__name__}'s pattern holds its root, 0: {self.pattern}")
        object.__setattr__(self, "root", index(self.root) % self.size)

    @property
    def size(self) -> int:
        """Steps per period."""
        return self.pattern.size

    @cached_property
    def pitch_classes(self) -> PitchClassSet:
        """Its notes as pitch classes, e.g. (4, 7, 11) for E minor."""
        return self.pattern.transpose(self.root)

    def interval(self, pitch: int) -> int:
        """Steps from the root up to `pitch`, within one period: G in E minor is 3."""
        return (pitch - self.root) % self.size

    def __contains__(self, pitch: object) -> bool:
        """Whether a pitch, in any period, is one of its notes."""
        return isinstance(pitch, Integral) and self.interval(int(pitch)) in self.pattern


@dataclass(frozen=True)
class Chord(Rooted[PitchClassSet]):
    """A chord, and optionally the note written under it: `bass` is the pitch class that must
    sound lowest (the E of C/E, one of the chord's own notes), or None to leave the inversion
    to whoever voices it."""

    bass: int | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.bass is not None:
            object.__setattr__(self, "bass", index(self.bass) % self.size)
            if self.bass not in self:
                raise ValueError(f"bass {self.bass} is not a note of the chord")

    def with_note(self, pitch: int) -> Chord:
        """The chord with `pitch` added: C with D is C(9). Unchanged if it's already there."""
        if pitch in self:
            return self
        added = PitchClassSet((*self.pattern, self.interval(pitch)), self.size)
        return replace(self, pattern=added)


Chords = Sequence[Chord]  # a progression, in order


def identify(notes: PitchClassSet, patterns: Collection[PitchClassSet]) -> list[Chord]:
    """Every way to read `notes` as one of `patterns`, trying each note as the root.

    One set can have several readings: (0, 2, 7) is sus2 on 0 and sus4 on 7. Choosing between
    them depends on context (the bass, the key), so all are returned, in order of root.
    """
    readings = []
    for degree, root in enumerate(notes):
        pattern = notes.rotate(degree)
        if pattern in patterns:
            readings.append(Chord(pattern, root))
    return readings
