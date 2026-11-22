import unittest
from itertools import combinations

from lazy_theory.core.pcset import PitchClassSet, group_starts, shortest

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

    def test_rejects_a_bad_size(self):
        with self.assertRaises(ValueError):
            PitchClassSet((0,), 0)

    def test_reads_like_its_sorted_members(self):
        tresillo = PitchClassSet((6, 0, 3), 8)
        self.assertEqual((tresillo[0], tresillo[-1], tresillo[1:]), (0, 6, (3, 6)))

    def test_the_empty_set_is_silence(self):
        silence = PitchClassSet((), 16)
        self.assertEqual(len(silence), 0)
        self.assertEqual(silence.complement(), PitchClassSet(tuple(range(16)), 16))
        self.assertEqual(silence.transpose(3), silence)
        self.assertEqual(silence.necklace(), silence)
        self.assertEqual(PitchClassSet.maximally_even(0, 16), silence)
        with self.assertRaises(ValueError):
            silence.rotate(0)

    def test_from_steps(self):
        self.assertEqual(PitchClassSet.from_steps(IONIAN_STEPS), IONIAN)

    def test_from_steps_infers_size(self):
        self.assertEqual(PitchClassSet.from_steps([1] * 31).size, 31)

    def test_from_steps_rejects_non_positive_steps(self):
        for steps in [(), (2, 0, 10), (13, -1)]:
            with self.assertRaises(ValueError, msg=steps):
                PitchClassSet.from_steps(steps)

    def test_rotate_is_a_mode(self):
        self.assertEqual(IONIAN.rotate(5).pitch_classes, (0, 2, 3, 5, 7, 8, 10))

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
        for notes in (-1, 13):
            with self.assertRaises(ValueError, msg=notes):
                PitchClassSet.maximally_even(notes)

    def test_shortest_way_round(self):
        self.assertEqual(
            [shortest(steps, 12) for steps in (0, 1, 5, 6, 7, 11, 13, -1)],
            [0, 1, 5, 6, -5, -1, 1, -1],
        )
        self.assertEqual(shortest(10, 19), -9)


class SetClassTest(unittest.TestCase):
    """Published counts of pitch-class set classes in twelve steps: every subset, the empty and
    the full set included, falls into 352 classes under transposition and 224 under
    transposition and inversion (OEIS A000031 and A000029 at 12), and Forte's table lists
    12 trichords, 29 tetrachords, 38 pentachords and 50 hexachords (Forte 1973)."""

    @staticmethod
    def classes(size: int, inversion: bool) -> set[PitchClassSet]:
        found = set()
        for members in combinations(range(12), size):
            pcs = PitchClassSet(members)
            forms = [pcs, PitchClassSet(tuple(-p for p in members))] if inversion else [pcs]
            found.add(min((form.necklace() for form in forms), key=lambda f: f.pitch_classes))
        return found

    def test_all_subsets_under_transposition(self):
        self.assertEqual(sum(len(self.classes(n, False)) for n in range(13)), 352)

    def test_all_subsets_under_transposition_and_inversion(self):
        self.assertEqual(sum(len(self.classes(n, True)) for n in range(13)), 224)

    def test_fortes_table(self):
        counts = {n: len(self.classes(n, True)) for n in (3, 4, 5, 6)}
        self.assertEqual(counts, {3: 12, 4: 29, 5: 38, 6: 50})


class GroupStartsTest(unittest.TestCase):
    def test_starts(self):
        self.assertEqual(group_starts((3, 2, 2)), (0, 3, 5))
        self.assertEqual(group_starts(()), ())  # no groups, no starts


class FromAnotherSetTest(unittest.TestCase):
    def test_keeps_its_size_or_refuses(self):
        nineteen = PitchClassSet((0, 3, 17), 19)
        self.assertEqual(PitchClassSet(nineteen, 19), nineteen)
        with self.assertRaises(ValueError):
            PitchClassSet(nineteen)  # 12 by default: 17 would quietly become 5


if __name__ == "__main__":
    unittest.main()
