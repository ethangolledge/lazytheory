"""Scales: pitch-class sets measured from a root, and the chords stacked from them."""

from lazy_theory.core.pcset import PitchClassSet


class Scale(PitchClassSet):
    """A pitch-class set measured from its root, so it always contains 0."""

    def __post_init__(self) -> None:
        super().__post_init__()
        if 0 not in self.pitch_classes:
            raise ValueError(f"a scale must contain its root (0), got {self.pitch_classes}")

    def chord(self, degree: int, notes: int = 3, stride: int = 2) -> PitchClassSet:
        """Stack `notes` scale members `stride` degrees apart, starting on `degree` (0-based).

        In a seven-note scale, stride 2 stacks thirds and stride 3 stacks fourths. The result
        is measured from its own root, the member at `degree`.
        """
        members = [self.pitch_classes[(degree + i * stride) % len(self)] for i in range(notes)]
        if len(set(members)) < notes:
            raise ValueError(
                f"stacking {notes} notes with stride {stride} repeats a pitch class "
                f"in this {len(self)}-note scale"
            )
        root = members[0]
        return PitchClassSet(tuple(member - root for member in members), self.size)
