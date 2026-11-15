"""Extended chords, derived from the key rather than listed.

Stacking a seven-note scale in thirds from any degree gives 1 3 5 7 9 11 13; the 13th chord is
the whole scale. An extended chord keeps a core, the root and third that give its quality, and
adds any of the rest: every add9, seventh, ninth, eleventh and thirteenth is one of those. Notes
are named by their place in the stack, flat or sharp against the major scale.
"""

from itertools import combinations

from lazy_theory.catalog import load_scales
from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.core.scale import Scale
from lazy_theory.instruments.fretboard import Chords


def stack(scale: Scale, degree: int) -> list[int]:
    """The notes stacked in thirds on `degree`, in order (root, 3rd, 5th, 7th, 9th, 11th, 13th
    in a seven-note scale), measured from the chord's root."""
    order: list[int] = []
    for notes in range(1, len(scale) + 1):
        (added,) = set(scale.chord(degree, notes)) - set(order)
        order.append(added)
    return order


def extended(scale: Scale, root: int, degree: int, core: int = 2, most: int = 5) -> Chords:
    """Every chord on `degree` of `scale` from `root`: the first `core` notes of its stack plus
    any of the rest, at most `most` notes in all, each with its root."""
    order = stack(scale, degree)
    chord_root = root + scale.pitch_classes[degree]
    return [
        (PitchClassSet((*order[:core], *extra), scale.size), chord_root)
        for count in range(most - core + 1)
        for extra in combinations(order[core:], count)
    ]


def spell(scale: Scale, degree: int, chord: PitchClassSet) -> str:
    """The chord's notes as stack numbers, flat or sharp against the major scale, in stack
    order: e.g. "1 b3 5 b9" for E minor with the F of E Phrygian."""
    major = load_scales()["Ionian"].pitch_classes
    names = []
    for place, note in enumerate(stack(scale, degree)):
        if note in chord:
            number = 2 * place + 1
            difference = (note - major[(number - 1) % len(major)] + 6) % 12 - 6
            names.append("b" * -difference + "#" * difference + str(number))
    return " ".join(names)
