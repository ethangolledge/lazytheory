import unittest

from lazy_theory.catalog import load_scales
from lazy_theory.catalog.names import stack_spelling as spell
from lazy_theory.core.key import Key
from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.suggest.extensions import extended

SCALES = load_scales()
PHRYGIAN, DORIAN, IONIAN = SCALES["Phrygian"], SCALES["Dorian"], SCALES["Ionian"]


class StackTest(unittest.TestCase):
    def test_thirds_up_to_the_thirteenth(self):
        self.assertEqual(PHRYGIAN.stacked(0, 7), (0, 3, 7, 10, 1, 5, 8))

    def test_spelled_against_the_major_scale(self):
        whole = PitchClassSet(tuple(range(12)))
        self.assertEqual(spell(IONIAN, 0, whole), "1 3 5 7 9 11 13")
        self.assertEqual(spell(DORIAN, 0, whole), "1 b3 5 b7 9 11 13")
        self.assertEqual(spell(PHRYGIAN, 0, PitchClassSet((0, 3, 7, 1))), "1 b3 5 b9")


class ExtendedTest(unittest.TestCase):
    def test_core_plus_any_of_the_rest(self):
        chords = extended(Key(PHRYGIAN, 4), degree=0)  # E Phrygian
        sets = {chord.pitch_classes for chord, _ in chords}
        self.assertEqual(len(chords), 1 + 5 + 10 + 10)  # up to 3 of 5, 5 notes at most
        self.assertIn((0, 3, 7), sets)  # Em itself
        self.assertIn((0, 1, 3, 7), sets)  # Em(b9): the Phrygian F as a colour
        self.assertTrue(all({0, 3} <= set(chord) for chord in sets))

    def test_rooted_on_the_degree(self):
        (_, root), *_ = extended(Key(PHRYGIAN, 4), degree=1)
        self.assertEqual(root, 5)  # F in E Phrygian


if __name__ == "__main__":
    unittest.main()
