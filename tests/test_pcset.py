import unittest

from lazy_theory.core.pcset import PitchClassSet

IONIAN_STEPS = (2, 2, 1, 2, 2, 2, 1)
IONIAN = PitchClassSet((0, 2, 4, 5, 7, 9, 11))


class PitchClassSetTest(unittest.TestCase):
    def test_members_are_reduced_sorted_and_unique(self):
        self.assertEqual(PitchClassSet((12, 7, 4, 0, 19)).pitch_classes, (0, 4, 7))
        self.assertEqual(PitchClassSet((-1,)).pitch_classes, (11,))

    def test_equal_sets_are_equal_and_hashable(self):
        self.assertEqual(PitchClassSet((7, 0, 4)), PitchClassSet((0, 4, 7)))
        self.assertEqual(len({PitchClassSet((7, 0, 4)), PitchClassSet((0, 4, 7))}), 1)
        self.assertNotEqual(PitchClassSet((0, 4, 7)), PitchClassSet((0, 4, 7), 31))

    def test_rejects_empty_set_and_bad_size(self):
        with self.assertRaises(ValueError):
            PitchClassSet(())
        with self.assertRaises(ValueError):
            PitchClassSet((0,), 0)

    def test_from_steps(self):
        self.assertEqual(PitchClassSet.from_steps(IONIAN_STEPS), IONIAN)

    def test_from_steps_infers_size(self):
        self.assertEqual(PitchClassSet.from_steps([1] * 31).size, 31)

    def test_from_steps_rejects_non_positive_steps(self):
        for steps in [(), (2, 0, 10), (13, -1)]:
            with self.assertRaises(ValueError, msg=steps):
                PitchClassSet.from_steps(steps)

    def test_steps_round_trip(self):
        self.assertEqual(IONIAN.steps, IONIAN_STEPS)
        self.assertEqual(PitchClassSet.from_steps(IONIAN.steps), IONIAN)

    def test_rotate_is_a_mode(self):
        self.assertEqual(IONIAN.rotate(5).pitch_classes, (0, 2, 3, 5, 7, 8, 10))
        self.assertEqual(IONIAN.rotate(5).steps, (2, 1, 2, 2, 1, 2, 2))

    def test_rotate_wraps(self):
        self.assertEqual(IONIAN.rotate(7), IONIAN)
        self.assertEqual(IONIAN.rotate(-2), IONIAN.rotate(5))

    def test_symmetric_set_rotates_onto_itself(self):
        whole_tone = PitchClassSet((0, 2, 4, 6, 8, 10))
        self.assertEqual(whole_tone.rotate(1), whole_tone)

    def test_transpose(self):
        self.assertEqual(PitchClassSet((0, 4, 7)).transpose(7).pitch_classes, (2, 7, 11))
        self.assertEqual(PitchClassSet((0, 4, 7)).transpose(-1).pitch_classes, (3, 6, 11))

    def test_maximally_even(self):
        expected = {
            3: (0, 4, 8),
            4: (0, 3, 6, 9),
            5: (0, 2, 4, 7, 9),
            6: (0, 2, 4, 6, 8, 10),
            7: (0, 1, 3, 5, 6, 8, 10),
            8: (0, 1, 3, 4, 6, 7, 9, 10),
        }
        for notes, pitch_classes in expected.items():
            self.assertEqual(PitchClassSet.maximally_even(notes).pitch_classes, pitch_classes)

    def test_maximally_even_in_other_temperaments(self):
        self.assertEqual(PitchClassSet.maximally_even(3, 31).pitch_classes, (0, 10, 20))

    def test_maximally_even_rejects_impossible_counts(self):
        for notes in (0, 13):
            with self.assertRaises(ValueError, msg=notes):
                PitchClassSet.maximally_even(notes)

    def test_contains_wraps(self):
        self.assertIn(12, IONIAN)
        self.assertNotIn(1, IONIAN)
        self.assertNotIn("C", IONIAN)


if __name__ == "__main__":
    unittest.main()
