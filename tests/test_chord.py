import unittest

import numpy as np

from lazy_theory.core.chord import Chord, identify
from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.core.scale import Scale

MAJOR, AUGMENTED = PitchClassSet((0, 4, 7)), PitchClassSet((0, 4, 8))
SUS2, SUS4 = PitchClassSet((0, 2, 7)), PitchClassSet((0, 5, 7))
PATTERNS = {MAJOR, AUGMENTED, SUS2, SUS4}
E, G, A = 4, 7, 9


class ChordTest(unittest.TestCase):
    def test_pattern_on_a_root(self):
        e_minor = Chord(PitchClassSet((0, 3, 7)), E)
        self.assertEqual(e_minor.pitch_classes.pitch_classes, (4, 7, 11))

    def test_the_root_is_a_pitch_class(self):
        self.assertEqual(Chord(MAJOR, 12 + A), Chord(MAJOR, A))

    def test_holds_its_notes_in_any_octave(self):
        e_minor = Chord(PitchClassSet((0, 3, 7)), E)
        self.assertTrue(G in e_minor and G + 24 in e_minor)
        self.assertNotIn(A, e_minor)
        self.assertEqual(e_minor.interval(G + 12), 3)

    def test_a_bass_is_one_of_its_notes(self):
        self.assertEqual(Chord(MAJOR, 0, bass=E + 12).bass, E)
        self.assertNotEqual(Chord(MAJOR, 0, bass=E), Chord(MAJOR, 0))
        with self.assertRaises(ValueError):
            Chord(MAJOR, 0, bass=2)

    def test_with_note_adds_only_new_notes(self):
        c = Chord(MAJOR, 0, bass=E)
        self.assertIs(c.with_note(E), c)
        added = c.with_note(2)
        self.assertEqual((added.pattern.pitch_classes, added.bass), ((0, 2, 4, 7), E))


class IdentifyTest(unittest.TestCase):
    def test_root_position(self):
        self.assertEqual(identify(MAJOR, PATTERNS), [Chord(MAJOR, 0)])

    def test_inversion_finds_the_root(self):
        first_inversion = PitchClassSet((0, 3, 8))
        self.assertEqual(identify(first_inversion, PATTERNS), [Chord(MAJOR, 8)])

    def test_ambiguous_set_returns_every_reading(self):
        self.assertEqual(identify(SUS2, PATTERNS), [Chord(SUS2, 0), Chord(SUS4, 7)])

    def test_symmetric_chord_matches_on_every_member(self):
        self.assertEqual([chord.root for chord in identify(AUGMENTED, PATTERNS)], [0, 4, 8])

    def test_unknown_set(self):
        self.assertEqual(identify(PitchClassSet((0, 1, 2)), PATTERNS), [])

    def test_different_temperament_does_not_match(self):
        self.assertEqual(identify(PitchClassSet((0, 4, 7), 31), PATTERNS), [])

    def test_a_scale_reads_like_the_set_of_its_notes(self):
        self.assertEqual(Scale((0, 4, 7)), MAJOR)
        self.assertEqual(identify(Scale((0, 4, 7)), PATTERNS), [Chord(MAJOR, 0)])

    def test_membership_takes_any_integer(self):
        # pitches read off a neck are numpy integers, not int
        for pitch in (16, np.int16(16), np.int64(-8)):
            self.assertIn(pitch, MAJOR)
            self.assertIn(pitch, Chord(MAJOR, 0))
        self.assertNotIn("E", MAJOR)
        self.assertNotIn(np.int16(5), Chord(MAJOR, 0))


if __name__ == "__main__":
    unittest.main()
