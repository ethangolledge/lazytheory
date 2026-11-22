"""Extended chords, derived from the key rather than listed.

Why: add9, 11th and 13th chords look like a long list to learn, but they are one idea: keep
stacking thirds past the seventh. Derived from the key, each one automatically has the right
notes for where it sits (the ninth on E in E Phrygian is flat, because F is in the key).

Could grow into: quartal and other stacks (`stride` on `Scale.stacked`), upper-structure
triads (three neighbouring notes of the stack), and which extensions a melody note allows.

Stacking a seven-note scale in thirds from any degree gives 1 3 5 7 9 11 13; the 13th chord is
the whole scale. An extended chord keeps a core, the root and third that give its quality, and
adds any of the rest: every add9, seventh, ninth, eleventh and thirteenth is one of those.
`pitch.names.stack_spelling` names their notes by place in the stack ("1 b3 5 b9").
"""

from itertools import combinations

from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.pitch.chord import Chord
from lazy_theory.pitch.key import Key


def extended(key: Key, degree: int, core: int = 2, most: int = 5) -> list[Chord]:
    """Every chord on `degree` of `key`: the first `core` notes of its stack of thirds plus any
    of the rest, at most `most` notes in all. The stack is every note before one repeats
    (`Scale.stack`), so a whole-tone scale stacks three."""
    if core < 1:
        raise ValueError(f"a core of at least one note, not {core}")
    order = key.scale.stack(degree)
    if core > len(order):
        raise ValueError(f"thirds on degree {degree} stack {len(order)} notes, not {core}")
    root = key.root + key.scale[degree]
    return [
        Chord(PitchClassSet((*order[:core], *extra), key.size), root)
        for count in range(most - core + 1)
        for extra in combinations(order[core:], count)
    ]
