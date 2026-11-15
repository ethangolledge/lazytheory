"""Scales: pitch-class sets measured from a root, and the chords stacked from them."""

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
