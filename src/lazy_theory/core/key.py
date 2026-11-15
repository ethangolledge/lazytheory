"""Keys: a scale on a root, and the chords built on its degrees."""

from typing import NamedTuple

from lazy_theory.core.chord import Chord
from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.core.scale import Scale


class Key(NamedTuple):
    """`scale` (a mode, measured from 0) on `root`, a pitch class: E Phrygian is
    Key(phrygian, 4)."""

    scale: Scale
    root: int

    @property
    def pitch_classes(self) -> PitchClassSet:
        """The key's notes as pitch classes."""
        return self.scale.transpose(self.root)

    def chord(self, degree: int, notes: int = 3, stride: int = 2) -> Chord:
        """The chord stacked on `degree` (0-based), on that degree's note."""
        root = (self.root + self.scale.pitch_classes[degree]) % self.scale.size
        return Chord(self.scale.chord(degree, notes, stride), root)

    def chords(self, notes: int = 3, stride: int = 2) -> list[Chord]:
        """The chord on every degree, in order."""
        return [self.chord(degree, notes, stride) for degree in range(len(self.scale))]
