"""Keys: a scale on a root, and the chords built on its degrees.

Why: a key is the context that turns notes into functions. The same C major chord is home in C,
the pull away from home in F and the pull towards it in G. Everything that names or ranks
(numerals, spelling, stability, which chords "belong") asks a Key.

Theory it speaks to: tertian harmony (chords as every other scale note, `stride` 2) and its
relatives (quartal harmony is `stride` 3); modes as the same notes on another root.

Could grow into: modulation (keys ranked by shared notes or by voice-leading distance between
their scales), modal interchange (the same degree in a parallel key: see tests/test_tension.py),
and secondary dominants as `Key(scale, chord.root).chord(4)`.
"""

from dataclasses import dataclass

from lazy_theory.pitch.chord import Chord, Rooted
from lazy_theory.pitch.scale import Scale


@dataclass(frozen=True)
class Key(Rooted[Scale]):
    """`scale` (a mode, measured from 0) on `root`, a pitch class: E Phrygian is
    Key(phrygian, 4)."""

    @property
    def scale(self) -> Scale:
        """The key's pattern, by the name musicians use."""
        return self.pattern

    def chord(self, degree: int, notes: int = 3, stride: int = 2) -> Chord:
        """The chord stacked on `degree` (0-based, wrapping as the scale's degrees do), on
        that degree's note."""
        root = self.root + self.scale[degree % len(self.scale)]
        return Chord(self.scale.chord(degree, notes, stride), root)

    def chords(self, notes: int = 3, stride: int = 2) -> list[Chord]:
        """The chord on every degree, in order."""
        return [self.chord(degree, notes, stride) for degree in range(len(self.scale))]
