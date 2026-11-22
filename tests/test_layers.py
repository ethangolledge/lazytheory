import unittest

from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.rhythm.layers import Dissonance, dissonance, fills, meets, midpoints


class DissonanceTest(unittest.TestCase):
    def test_three_beats_over_a_four_four_bar(self):
        self.assertEqual(dissonance(3, 0, 4), Dissonance((3, 4), None))

    def test_counted_in_the_largest_common_unit(self):
        self.assertEqual(dissonance(12, 0, 16), Dissonance((3, 4), None))  # in sixteenths
        self.assertEqual(dissonance(6, 0, 4), Dissonance((3, 2), None))  # hemiola, in eighths

    def test_displacement(self):
        self.assertEqual(dissonance(3, 1, 3), Dissonance(None, (3, 1)))
        self.assertEqual(dissonance(3, 2, 3), Dissonance(None, (3, -1)))  # early, not late by 2
        self.assertEqual(dissonance(12, 4, 12), Dissonance(None, (3, 1)))

    def test_nested_groups_are_aligned(self):
        for period, offset, host in [(3, 0, 3), (6, 3, 3), (3, 3, 6), (2, 0, 4), (8, 4, 4)]:
            self.assertEqual(dissonance(period, offset, host), Dissonance(None, None))

    def test_off_beat_eighths(self):
        self.assertEqual(dissonance(2, 1, 4), Dissonance(None, (2, 1)))


class MeetsTest(unittest.TestCase):
    def test_three_over_four_meets_after_three_bars(self):
        self.assertEqual(meets(3, 0, 4), 12)

    def test_over_four_bars_of_four_four(self):
        self.assertEqual(meets(3, 0, 16), 48)

    def test_displaced_guest_never_meets(self):
        self.assertIsNone(meets(3, 1, 3))
        self.assertIsNone(meets(2, 1, 4))

    def test_offset_guest_meets_on_a_bar_line(self):
        self.assertEqual(meets(3, 1, 4), 4)  # 1, 4: the second group starts bar two
        self.assertEqual(meets(3, 2, 4), 8)


class FillsTest(unittest.TestCase):
    def test_threes_through_four_bars_of_four_four(self):
        found = list(fills(3, 16, (1, 2, 3)))
        self.assertEqual(found[0], (3, 3, 3, 3, 3, 1))  # five threes and one left over

    def test_in_twos_and_threes(self):
        found = list(fills(3, 16))
        self.assertEqual(found[0], (3, 3, 3, 3, 2, 2))
        self.assertTrue(all(sum(fill) == 16 for fill in found))
        self.assertEqual(len(found), len(set(found)))

    def test_exact_fit_comes_first(self):
        self.assertEqual(next(fills(4, 16)), (4, 4, 4, 4))


class InterlockTest(unittest.TestCase):
    def test_complement_fills_every_gap(self):
        mine = PitchClassSet((0, 3, 6), 8)
        answer = mine.complement()
        self.assertFalse(set(mine) & set(answer))
        self.assertEqual(set(mine) | set(answer), set(range(8)))

    def test_full_set_leaves_silence(self):
        self.assertEqual(PitchClassSet(tuple(range(4)), 4).complement(), PitchClassSet((), 4))

    def test_midpoints_follow_the_halving_rule(self):
        self.assertEqual(midpoints(PitchClassSet((0, 3, 6), 8)), (1, 4, 7))  # 3s as 1+2, 2 as 1+1
        self.assertEqual(midpoints(PitchClassSet((0,), 5)), (2,))  # 5 as 2+3
        self.assertEqual(midpoints(PitchClassSet((0, 1), 2)), ())


class LayerInputTest(unittest.TestCase):
    def test_groups_of_no_pulses_are_rejected(self):
        for call in (lambda: meets(0, 0, 4), lambda: meets(3, 0, 0), lambda: next(fills(0, 4))):
            with self.assertRaises(ValueError):
                call()


if __name__ == "__main__":
    unittest.main()
