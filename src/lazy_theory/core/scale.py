"""Scales: pitch-class sets measured from a root, and the chords stacked from them.

Why: a scale is the pool of notes a piece draws on, and its chords are not a separate list to
memorise: take every other note and you have them. One step pattern gives seven modes by
rotation and seven triads, seven sevenths, and so on by stacking.

Theory it speaks to: modes as rotations of one pattern; tertian harmony as stacked thirds
(stride 2), quartal harmony as stacked fourths (stride 3). Because the stacking counts scale
degrees, not semitones, it works unchanged on pentatonic, octatonic or microtonal scales.

Could grow into: scale families found by rotation and reflection, "brightness" orderings of
modes (the sum of a mode's steps), and chords from any stride on any scale.
"""

from lazy_theory.core.pcset import PitchClassSet


class Scale(PitchClassSet):
    """A pitch-class set measured from its root, so it always contains 0."""

    def __post_init__(self) -> None:
        super().__post_init__()
        if 0 not in self.pitch_classes:
            raise ValueError(f"a scale must contain its root (0), got {self.pitch_classes}")

    def stacked(self, degree: int, notes: int = 3, stride: int = 2) -> tuple[int, ...]:
        """`notes` scale members `stride` degrees apart, starting on `degree` (0-based), in
        stacking order and measured from the member at `degree`.

        In a seven-note scale, stride 2 stacks thirds (1 3 5 7 9 11 13 when all seven are
        stacked) and stride 3 stacks fourths.
        """
        members = [self.pitch_classes[(degree + i * stride) % len(self)] for i in range(notes)]
        if len(set(members)) < notes:
            raise ValueError(
                f"stacking {notes} notes with stride {stride} repeats a pitch class "
                f"in this {len(self)}-note scale"
            )
        return tuple((member - members[0]) % self.size for member in members)

    def chord(self, degree: int, notes: int = 3, stride: int = 2) -> PitchClassSet:
        """The `stacked` notes as a set, measured from the chord's own root."""
        return PitchClassSet(self.stacked(degree, notes, stride), self.size)
