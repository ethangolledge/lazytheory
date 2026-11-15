import unittest

from lazy_theory.catalog import load_scales
from lazy_theory.core.chord import Chord
from lazy_theory.core.key import Key
from lazy_theory.core.pcset import PitchClassSet

SCALES = load_scales()
E, F, A = 4, 5, 9


class ChordTest(unittest.TestCase):
    def test_pattern_on_a_root(self):
        e_minor = Chord(PitchClassSet((0, 3, 7)), E)
        self.assertEqual(e_minor.pitch_classes.pitch_classes, (4, 7, 11))

    def test_unpacks_as_pattern_then_root(self):
        pattern, root = Chord(PitchClassSet((0, 4, 7)), A)
        self.assertEqual((pattern.pitch_classes, root), ((0, 4, 7), A))


class KeyTest(unittest.TestCase):
    def test_degree_chords_sit_on_their_notes(self):
        e_phrygian = Key(SCALES["Phrygian"], E)
        chords = e_phrygian.chords()
        self.assertEqual([chord.root for chord in chords], [4, 5, 7, 9, 11, 0, 2])  # E F G A B C D
        self.assertEqual(chords[1], Chord(PitchClassSet((0, 4, 7)), F))  # the flat II

    def test_chords_are_made_of_the_key_notes(self):
        key = Key(SCALES["Dorian"], 2)
        for chord in key.chords(notes=4):
            self.assertLessEqual(set(chord.pitch_classes), set(key.pitch_classes))

    def test_stacking_in_thirds_reaches_the_thirteenth(self):
        self.assertEqual(SCALES["Ionian"].stacked(0, 7), (0, 4, 7, 11, 2, 5, 9))


if __name__ == "__main__":
    unittest.main()
