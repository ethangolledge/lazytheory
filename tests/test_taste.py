import unittest

import numpy as np

from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.instruments.catalog import load_tunings
from lazy_theory.instruments.fretboard import Fretboard
from lazy_theory.instruments.rules import contiguous, fingers, placeable, ringing, within
from lazy_theory.instruments.taste import Taste
from lazy_theory.pitch.chord import Chord

STANDARD = Fretboard.from_tuning(load_tunings()["guitar standard"])
MINOR, MAJOR = PitchClassSet((0, 3, 7)), PitchClassSet((0, 4, 7))
E, A, C, G = 4, 9, 0, 7  # pitch classes


class TasteTest(unittest.TestCase):
    def test_cutting_the_neck_first_loses_nothing(self):
        taste = Taste(contiguous=False)
        every = STANDARD.voicings(Chord(MAJOR, C), taste.reach)
        rules = within(every, taste.lowest, taste.highest)
        expected = every[rules & placeable(every, STANDARD.fret_distance, taste.spans)]
        np.testing.assert_array_equal(taste.voicings(STANDARD, Chord(MAJOR, C)), expected)

    def test_building_contiguous_matches_the_rule(self):
        chords = [Chord(MAJOR, C), Chord(MINOR, E), Chord(PitchClassSet((0, 4, 7, 10)), G)]
        every, which = STANDARD.voicings_of(chords, Taste().reach)
        built, built_which = STANDARD.voicings_of(chords, Taste().reach, contiguous=True)
        keep = contiguous(every)
        np.testing.assert_array_equal(built, every[keep])
        np.testing.assert_array_equal(built_which, which[keep])

    def test_open_strings_only_near_the_hand(self):
        voicings = Taste(highest=12, open_within=5).voicings(STANDARD, Chord(MINOR, E))
        has_open = (voicings == 0).any(axis=1)
        self.assertTrue(has_open.any())
        self.assertLessEqual(voicings[has_open].max(), 5)

    def test_top_lines_start_with_the_path_and_differ_on_top(self):
        chords = [Chord(MAJOR, C), Chord(MINOR, A), Chord(MAJOR, 5), Chord(MAJOR, G)]
        taste = Taste(highest=4, sounding=1.0)
        lines = taste.lines(STANDARD, chords)
        path, total, *_ = taste.path(STANDARD, chords)
        self.assertAlmostEqual(lines[0].cost, total)
        self.assertEqual(len({line.labels for line in lines}), len(lines))
        self.assertTrue(all(line.cost <= total + taste.strings_changed + 1e-9 for line in lines))
        basses = taste.lines(STANDARD, chords, Fretboard.bass)
        self.assertEqual(basses[0].labels, tuple(STANDARD.bass(path).tolist()))

    def test_allows_matches_what_options_builds(self):
        taste = Taste(highest=5)
        every = STANDARD.voicings(Chord(MAJOR, C), taste.reach)
        built = taste.voicings(STANDARD, Chord(MAJOR, C))
        np.testing.assert_array_equal(every[taste.allows(STANDARD, every)], built)

    def test_silence_costs_nothing_to_hear(self):
        silent_and_c = np.array([[-1] * 6, [-1, 3, 2, 0, 1, 0]], dtype=np.int16)
        silent, c = Taste().standing(STANDARD, silent_and_c)
        self.assertEqual(silent, 0.0)
        self.assertGreater(c, 0.0)

    def test_a_written_bass_is_lowest_in_every_option(self):
        c_over_e, c = Taste(highest=5).options(STANDARD, [Chord(MAJOR, C, bass=E), Chord(MAJOR, C)])
        self.assertTrue(len(c_over_e) and (STANDARD.bass(c_over_e) % 12 == E).all())
        np.testing.assert_array_equal(c_over_e, c[STANDARD.bass(c) % 12 == E])

    def test_a_subclass_adds_a_rule_to_every_search(self):
        class NoOpenStrings(Taste):
            def allows(self, board, voicings):
                return super().allows(board, voicings) & (voicings != 0).all(axis=1)

        chords, loves_open = [Chord(MAJOR, C), Chord(MINOR, A)], {"highest": 5, "ringing": 5.0}
        self.assertTrue((Taste(**loves_open).path(STANDARD, chords).path == 0).any())
        self.assertFalse((NoOpenStrings(**loves_open).path(STANDARD, chords).path == 0).any())

    def test_path_total_is_its_costs(self):
        taste, board = Taste(), STANDARD
        path, total, *_ = taste.path(board, [Chord(MINOR, E), Chord(MINOR, A)])
        expected = taste.standing(board, path).sum() + taste.transition(board, path[:1], path[1:])
        self.assertAlmostEqual(total, float(expected[0, 0]))

    def test_rewarding_ringing_chooses_open_strings(self):
        chords = [Chord(MAJOR, G), Chord(MAJOR, C), Chord(MAJOR, G)]
        plain = Taste().path(STANDARD, chords).path
        ringing_path = Taste(ringing=5.0).path(STANDARD, chords).path
        self.assertGreater(ringing(ringing_path).sum(), ringing(plain).sum())

    def test_a_chord_that_comes_round_again_is_built_once(self):
        em, c = Chord(MINOR, E), Chord(MAJOR, C)
        first, other, again = Taste().options(STANDARD, [em, c, Chord(MINOR, E)])
        self.assertIs(first, again)
        np.testing.assert_array_equal(first, Taste().voicings(STANDARD, em))
        np.testing.assert_array_equal(other, Taste().voicings(STANDARD, c))
        self.assertEqual(Taste().options(STANDARD, []), [])
        with self.assertRaisesRegex(ValueError, "at least one chord"):
            Taste().path(STANDARD, [])

    def test_a_hand_with_fewer_fingers_plays_fewer_shapes(self):
        four = Taste().voicings(STANDARD, Chord(MAJOR, C))
        three = Taste(spans=Taste().spans[:2]).voicings(STANDARD, Chord(MAJOR, C))
        self.assertLess(len(three), len(four))
        self.assertLessEqual(
            {tuple(row) for row in three.tolist()}, {tuple(row) for row in four.tolist()}
        )
        self.assertLessEqual(int(fingers(three).max()), 3)


if __name__ == "__main__":
    unittest.main()
