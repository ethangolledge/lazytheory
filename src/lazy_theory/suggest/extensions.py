"""Extended chords, derived from the key rather than listed.

Stacking a seven-note scale in thirds from any degree gives 1 3 5 7 9 11 13; the 13th chord is
the whole scale. An extended chord keeps a core, the root and third that give its quality, and
adds any of the rest: every add9, seventh, ninth, eleventh and thirteenth is one of those.
`catalog.names.stack_spelling` names their notes by place in the stack ("1 b3 5 b9").
"""

from itertools import combinations

from lazy_theory.core.chord import Chord
from lazy_theory.core.key import Key
from lazy_theory.core.pcset import PitchClassSet


def extended(key: Key, degree: int, core: int = 2, most: int = 5) -> list[Chord]:
    """Every chord on `degree` of `key`: the first `core` notes of its stack of thirds plus any
    of the rest, at most `most` notes in all."""
    order = key.scale.stacked(degree, len(key.scale))
    root = key.chord(degree).root
    return [
        Chord(PitchClassSet((*order[:core], *extra), key.scale.size), root)
        for count in range(most - core + 1)
        for extra in combinations(order[core:], count)
    ]
