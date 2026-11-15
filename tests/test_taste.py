import unittest

import numpy as np

from lazy_theory.catalog import load_tunings
from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.instruments.fretboard import Fretboard
from lazy_theory.instruments.rules import contiguous, placeable, ringing, within
from lazy_theory.instruments.taste import Taste

STANDARD = Fretboard.from_tuning(load_tunings()["guitar standard"])
MINOR, MAJOR = PitchClassSet((0, 3, 7)), PitchClassSet((0, 4, 7))
E, A, C, G = 4, 9, 0, 7  # pitch classes


class TasteTest(unittest.TestCase):
    def test_cutting_the_neck_first_loses_nothing(self):
        taste = Taste(contiguous=False, fingers=6)
        every = STANDARD.voicings(MAJOR, C, taste.reach)
        rules = within(every, taste.lowest, taste.highest)
        expected = every[rules & placeable(every, STANDARD.fret_distance, taste.spans)]
        np.testing.assert_array_equal(taste.voicings(STANDARD, MAJOR, C), expected)

    def test_building_contiguous_matches_the_rule(self):
        chords = [(MAJOR, C), (MINOR, E), (PitchClassSet((0, 4, 7, 10)), G)]
        every, which = STANDARD.voicings_of(chords, Taste().reach)
        built, built_which = STANDARD.voicings_of(chords, Taste().reach, contiguous=True)
        keep = contiguous(every)
        np.testing.assert_array_equal(built, every[keep])
        np.testing.assert_array_equal(built_which, which[keep])

    def test_open_strings_only_near_the_hand(self):
        voicings = Taste(highest=12, open_within=5).voicings(STANDARD, MINOR, E)
        has_open = (voicings == 0).any(axis=1)
        self.assertTrue(has_open.any())
        self.assertLessEqual(voicings[has_open].max(), 5)

    def test_path_total_is_its_costs(self):
        taste, board = Taste(), STANDARD
        path, total = taste.path(board, [(MINOR, E), (MINOR, A)])
        expected = taste.standing(board, path).sum() + taste.transition(board, path[:1], path[1:])
        self.assertAlmostEqual(total, float(expected[0, 0]))

    def test_rewarding_ringing_chooses_open_strings(self):
        chords = [(MAJOR, G), (MAJOR, C), (MAJOR, G)]
        plain, _ = Taste().path(STANDARD, chords)
        ringing_path, _ = Taste(ringing=5.0).path(STANDARD, chords)
        self.assertGreater(ringing(ringing_path).sum(), ringing(plain).sum())


if __name__ == "__main__":
    unittest.main()
