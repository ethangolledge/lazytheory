import unittest
from dataclasses import replace

import numpy as np

from lazy_theory.catalog import load_tunings
from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.core.scale import Scale
from lazy_theory.instruments.fretboard import Fretboard
from lazy_theory.instruments.taste import Taste
from lazy_theory.suggest.tunings import key, name, retunings, screen, suggest

TUNINGS = load_tunings()
STANDARD = Fretboard.from_tuning(TUNINGS["guitar standard"])
OPEN_D = (-2, 0, 0, -1, -2, -2)  # D A D F# A D from E A D G B E
MAJOR = PitchClassSet((0, 4, 7))
D, G, A = 10, 3, 5  # steps above standard tuning's low E


class ScreenTest(unittest.TestCase):
    def test_every_retuning_once(self):
        moves = retunings(2, range(-2, 3))
        self.assertEqual(moves.shape, (25, 2))
        self.assertEqual(len(np.unique(moves, axis=0)), 25)

    def test_share_of_open_strings_in_the_chords(self):
        tunings = STANDARD.open_strings + np.array([(0,) * 6, OPEN_D], dtype=np.int16)
        np.testing.assert_allclose(screen(tunings, [(MAJOR, D)], 12), [2 / 6, 1.0])

    def test_a_capo_moves_the_open_strings(self):
        # No open string of standard tuning is in F# major; capo 2 rings F#, C# and F#.
        capo = np.array([[0], [2]], dtype=np.int16)
        share = screen(STANDARD.open_strings + capo, [(MAJOR, 2)], 12)
        np.testing.assert_allclose(share, [0.0, 0.5])


class KeyAndNameTest(unittest.TestCase):
    def test_key_chords(self):
        major = Scale.from_steps((2, 2, 1, 2, 2, 2, 1))
        chords = key(major, root=8)  # C, in steps above low E
        roots = [root % 12 for _, root in chords]
        self.assertEqual(roots, [8, 10, 0, 1, 3, 5, 7])  # C D E F G A B
        self.assertEqual([chord.pitch_classes for chord, _ in chords][:2], [(0, 4, 7), (0, 3, 7)])

    def test_names_from_the_catalog(self):
        open_e = STANDARD.open_strings + np.array([0, 2, 2, 1, 0, 0])
        self.assertEqual(name(STANDARD.open_strings, STANDARD, TUNINGS), "guitar standard")
        self.assertEqual(name(STANDARD.open_strings + OPEN_D, STANDARD, TUNINGS), "guitar open D")
        self.assertEqual(name(open_e, STANDARD, TUNINGS), "guitar open D +2")
        self.assertIsNone(name(STANDARD.open_strings + [0, 0, 0, 0, 0, 1], STANDARD, TUNINGS))


class SuggestTest(unittest.TestCase):
    def test_no_retuning_is_the_plain_path(self):
        chords, taste = [(MAJOR, G), (MAJOR, D)], Taste()
        (only,) = suggest(STANDARD, chords, taste, steps=(0,), capos=(0,))
        path, cost = taste.path(STANDARD, chords)
        self.assertEqual((only.retuning, only.capo, only.cost), ((0,) * 6, 0, cost))
        np.testing.assert_array_equal(only.path, path)

    def test_never_worse_than_the_base_tuning(self):
        chords, taste = [(MAJOR, D), (MAJOR, G), (MAJOR, A)], Taste(sounding=1.0, ringing=1.0)
        best = suggest(STANDARD, chords, taste)[0]
        _, cost = taste.path(STANDARD, chords)
        self.assertLessEqual(best.cost, cost)

    def test_costly_retuning_keeps_the_base_tuning(self):
        chords = [(MAJOR, D), (MAJOR, G), (MAJOR, A)]
        best = suggest(STANDARD, chords, Taste(sounding=1.0, ringing=1.0), retune=100.0)[0]
        self.assertEqual(best.retuning, (0,) * 6)

    def test_context_chords_add_their_cheapest_voicing(self):
        chords, taste = [(MAJOR, G), (MAJOR, D)], Taste()
        context = [(MAJOR, A)]
        only = {"steps": (0,), "capos": (0,)}
        (plain,) = suggest(STANDARD, chords, taste, **only)
        (keyed,) = suggest(STANDARD, chords, taste, context=context, context_weight=0.5, **only)
        cheapest = taste.standing(STANDARD, taste.voicings(STANDARD, MAJOR, A)).min()
        self.assertAlmostEqual(keyed.cost - plain.cost, 0.5 * cheapest)

    def test_each_suggestion_sounds_different(self):
        found = suggest(STANDARD, [(MAJOR, D), (MAJOR, A)], Taste(sounding=1.0), top=10)
        sounds = {
            replace(STANDARD, open_strings=STANDARD.open_strings + one.retuning)
            .capo(one.capo)
            .notes(one.path)
            .tobytes()
            for one in found
        }
        self.assertEqual(len(sounds), len(found))

    def test_sorted_by_cost(self):
        found = suggest(STANDARD, [(MAJOR, D), (MAJOR, A)], Taste(ringing=1.0), top=10)
        costs = [suggestion.cost for suggestion in found]
        self.assertEqual(costs, sorted(costs))


if __name__ == "__main__":
    unittest.main()
