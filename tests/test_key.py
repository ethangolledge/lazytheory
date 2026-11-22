import unittest

from fixtures import SCALES

from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.pitch.chord import Chord
from lazy_theory.pitch.key import Key

E, F = 4, 5


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

    def test_a_key_is_its_scale_on_a_root(self):
        key = Key(SCALES["Dorian"], 14)
        self.assertEqual((key.root, key.scale), (2, SCALES["Dorian"]))
        self.assertIn(11, key)  # B, the note that makes D Dorian
        self.assertNotIn(10, key)
        self.assertNotEqual(key, Chord(SCALES["Dorian"], 2))  # same notes, not the same thing

    def test_degrees_wrap_as_the_scales_do(self):
        c_major = Key(SCALES["Ionian"], 0)
        self.assertEqual(c_major.chord(7), c_major.chord(0))
        self.assertEqual(c_major.chord(-1), c_major.chord(6))

    def test_stacking_in_thirds_reaches_the_thirteenth(self):
        self.assertEqual(SCALES["Ionian"].stacked(0, 7), (0, 4, 7, 11, 2, 5, 9))


if __name__ == "__main__":
    unittest.main()
