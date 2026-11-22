import unittest

from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.pitch.scale import Scale

IONIAN = Scale.from_steps((2, 2, 1, 2, 2, 2, 1))


class ScaleTest(unittest.TestCase):
    def test_must_contain_root(self):
        with self.assertRaises(ValueError):
            Scale((2, 4, 7))

    def test_modes_are_scales(self):
        self.assertIsInstance(IONIAN.rotate(1), Scale)

    def test_seven_stacked_fifths_give_the_diatonic_scale(self):
        fifths = Scale(tuple(7 * i for i in range(7)))
        self.assertEqual(fifths, IONIAN.rotate(3))  # Lydian

    def test_seven_maximally_even_notes_give_the_diatonic_scale(self):
        self.assertEqual(Scale.maximally_even(7), IONIAN.rotate(6))  # Locrian

    def test_transposed_scale_is_a_plain_set(self):
        self.assertIs(type(IONIAN.transpose(2)), PitchClassSet)

    def test_every_diatonic_stride_comes_in_exactly_two_sizes(self):
        # Myhill's property: why stacked diatonic thirds are only ever major or minor.
        notes = IONIAN.pitch_classes
        for stride in range(1, 7):
            sizes = {(notes[(i + stride) % 7] - notes[i]) % 12 for i in range(7)}
            self.assertEqual(len(sizes), 2, stride)

    def test_diatonic_triads(self):
        triads = [IONIAN.chord(degree).pitch_classes for degree in range(7)]
        major, minor, diminished = (0, 4, 7), (0, 3, 7), (0, 3, 6)
        self.assertEqual(triads, [major, minor, minor, major, major, minor, diminished])

    def test_seventh_chord(self):
        self.assertEqual(IONIAN.chord(0, notes=4).pitch_classes, (0, 4, 7, 11))

    def test_chord_is_measured_from_its_own_root(self):
        self.assertEqual(IONIAN.chord(4, notes=4).pitch_classes, (0, 4, 7, 10))

    def test_quartal_stacking(self):
        self.assertEqual(IONIAN.chord(0, stride=3).pitch_classes, (0, 5, 11))

    def test_chord_is_a_plain_pitch_class_set(self):
        self.assertIs(type(IONIAN.chord(0)), PitchClassSet)

    def test_stacking_that_repeats_a_pitch_class_is_rejected(self):
        whole_tone = Scale.from_steps([2] * 6)
        self.assertEqual(whole_tone.chord(0).pitch_classes, (0, 4, 8))
        with self.assertRaises(ValueError):
            whole_tone.chord(0, notes=4)

    def test_works_in_other_temperaments(self):
        meantone_major_31 = Scale.from_steps((5, 5, 3, 5, 5, 5, 3))
        self.assertEqual(meantone_major_31.size, 31)
        self.assertEqual(meantone_major_31.chord(0).pitch_classes, (0, 10, 18))


if __name__ == "__main__":
    unittest.main()
