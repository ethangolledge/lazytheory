"""Melodic attraction: how strongly one pitch pulls towards another in a key.

Why: voice leading says how far notes move; this says which moves the ear expects. A leading
tone a semitone below the tonic wants to rise; the tonic wants to stay. It lets a search
describe a line ("the top voice resolves here") rather than only cost it.

Theory it speaks to: tonal pitch space (Lerdahl, "Tonal Pitch Space", 2001), tested against
listeners in Lerdahl & Krumhansl, "Modeling Tonal Tension" (2007), building on Bharucha's
melodic anchoring (1984, 1996): an unstable note anchors to a near, more stable one. The pull
grows with how much more stable the target is, and falls with the square of the steps between
them. The authors call this the least tested part of their model: the inverse square may fall
too steeply, and a held note gets no value.

Could grow into: the rest of the model (chord distance and surface tension, for a tension
curve over a progression), and attraction measured against the current chord instead of the
tonic, by passing a Key built on that chord's root.
"""

from functools import cache
from math import gcd

from lazy_theory.pitch.key import Key


@cache
def anchoring(key: Key) -> tuple[int, ...]:
    """How stable each pitch class is in `key`, indexed by pitch class: Lerdahl's basic space
    without its fifths level. 4 the tonic, 3 the rest of the tonic triad, 2 the rest of the
    scale, 1 any other note. In a key too small to stack three notes in thirds (a scale of
    two or four notes), the tonic chord is the notes stacked before one repeats."""
    notes = len(key.scale) // gcd(len(key.scale), 2)  # distinct notes stacked in thirds
    tonic = key.chord(0, min(3, notes))
    return tuple(
        4 if note == key.root else 3 if note in tonic else 2 if note in key else 1
        for note in range(key.size)
    )


def attraction(key: Key, source: int, target: int) -> float:
    """Pull of pitch `source` towards pitch `target` (any frame in steps, e.g. above C0):
    the ratio of their anchoring over the steps between them squared. 0 when they are the
    same pitch, which the rule leaves out."""
    steps = abs(target - source)
    if steps == 0:
        return 0.0
    stable = anchoring(key)
    return stable[target % key.size] / stable[source % key.size] / steps**2
