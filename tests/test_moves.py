import unittest

from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.rhythm.meter import Meter, unevenness
from lazy_theory.rhythm.moves import (
    even,
    filled,
    jam,
    merged,
    moves,
    nudged,
    shifted,
    split,
)

TRESILLO = PitchClassSet((0, 3, 6), 8)


class MoveTest(unittest.TestCase):
    def test_nudge_moves_one_note_to_a_free_neighbour(self):
        found = nudged(PitchClassSet((0, 1), 4))
        self.assertEqual(
            found, [PitchClassSet((1, 3), 4), PitchClassSet((0, 2), 4)]
        )  # 0 back to 3 (0 forward is taken), 1 forward to 2

    def test_split_follows_the_halving_rule(self):
        self.assertEqual(split(PitchClassSet((0,), 5)), [PitchClassSet((0, 2), 5)])  # 2+3
        self.assertEqual(split(PitchClassSet((0,), 4)), [PitchClassSet((0, 2), 4)])  # 2+2
        self.assertEqual(split(PitchClassSet((0, 1), 2)), [])  # nothing to split

    def test_merge_keeps_the_first_note(self):
        self.assertEqual(merged(TRESILLO), [PitchClassSet((0, 6), 8), PitchClassSet((0, 3), 8)])
        self.assertEqual(merged(PitchClassSet((0,), 8)), [])

    def test_shift_is_displacement(self):
        self.assertEqual(shifted(TRESILLO), [TRESILLO.transpose(-1), TRESILLO.transpose(1)])

    def test_even_is_euclidean_from_the_first_note(self):
        (found,) = even(PitchClassSet((0, 1, 2), 8))
        self.assertEqual(unevenness(found), 0)
        self.assertIn(0, found)
        self.assertEqual(even(TRESILLO), [])  # the tresillo is already even


class MovesTest(unittest.TestCase):
    def test_each_rhythm_once_never_the_original(self):
        meter = Meter.of((2, 2), 2)
        found = moves(TRESILLO, meter)
        flat = [rhythm for rhythms in found.values() for rhythm in rhythms]
        self.assertEqual(len(flat), len(set(flat)))
        self.assertNotIn(TRESILLO, flat)
        self.assertEqual(list(found), ["nudge", "split", "merge", "shift", "even"])

    def test_counted_on_the_grid_returned_in_pulses(self):
        meter = Meter.of((2, 2), (4, 5, 4, 4))  # 80 pulses, 17 grid points
        onsets = meter.starts(meter.beat)
        for rhythms in moves(onsets, meter).values():
            for rhythm in rhythms:
                self.assertEqual(rhythm.size, 80)
                self.assertTrue(set(rhythm) <= set(meter.starts(-1)))


class JamTest(unittest.TestCase):
    def test_gaps_land_on_the_next_accent(self):
        spine = PitchClassSet((0, 3), 4)  # accents on counts 1 and 4: gaps of 3 and 1
        notes = filled(spine, 4, 3)  # 16ths in 3s
        self.assertEqual(tuple(notes), (0, 3, 6, 9, 12, 14))  # 3+3+3+3, then 2+2
        self.assertIn(12, notes)  # the second accent sounds

    def test_one_idea_varies_with_the_gaps(self):
        notes = filled(PitchClassSet((0, 2), 4), 4, 3)  # two gaps of 2 counts: 8 points each
        self.assertEqual(tuple(notes), (0, 3, 6, 8, 11, 14))  # 3+3+2 twice

    def test_a_single_point_gap_has_no_fill(self):
        self.assertIsNone(filled(PitchClassSet((0,), 1), 1, 2))  # no StopIteration

    def test_a_group_that_never_fits_is_not_an_idea(self):
        spine = PitchClassSet((0, 3), 4)
        self.assertIsNone(filled(spine, 2, 5))  # gaps of 6 and 2 eighths: no room for a 5
        self.assertNotIn((2, 5), [(per_count, group) for per_count, group, _ in jam(spine)])

    def test_every_idea_keeps_the_accents_and_sounds_different(self):
        spine = PitchClassSet((0, 3, 5), 7)
        ideas = jam(spine)
        for per_count, _, notes in ideas:
            self.assertTrue(all(accent * per_count in notes for accent in spine))
        sounds = [frozenset(p / per_count for p in notes) for per_count, _, notes in ideas]
        self.assertEqual(len(sounds), len(set(sounds)))
        self.assertEqual([len(n) for _, _, n in ideas], sorted(len(n) for _, _, n in ideas))


if __name__ == "__main__":
    unittest.main()
