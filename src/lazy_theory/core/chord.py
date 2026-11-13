"""Chord identification: matching a pitch-class set against named patterns.

A chord is a PitchClassSet. The names come from whoever calls `identify` (usually the catalog),
so core never depends on naming conventions.
"""

from collections.abc import Mapping
from typing import NamedTuple

from lazy_theory.core.pcset import PitchClassSet


class ChordMatch(NamedTuple):
    name: str
    root: int  # pitch class within the identified set that the named pattern is built on


def identify(chord: PitchClassSet, patterns: Mapping[str, PitchClassSet]) -> list[ChordMatch]:
    """Every way to read `chord` as a named pattern, trying each member as the root.

    One set can have several readings: (0, 2, 7) is sus2 on 0 and sus4 on 7. Choosing between
    them depends on context, so all matches are returned, in order of root.
    """
    names = {(pattern.pitch_classes, pattern.size): name for name, pattern in patterns.items()}
    matches = []
    for degree, root in enumerate(chord):
        rotated = chord.rotate(degree)
        name = names.get((rotated.pitch_classes, rotated.size))
        if name is not None:
            matches.append(ChordMatch(name, root))
    return matches
