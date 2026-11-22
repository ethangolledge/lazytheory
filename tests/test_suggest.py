import unittest
from dataclasses import replace

import numpy as np
from fixtures import MAJOR, STANDARD, TUNINGS

from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.instruments.names import tuning_name
from lazy_theory.instruments.taste import Taste
from lazy_theory.pitch.chord import Chord
from lazy_theory.suggest.tunings import _best, _by_string, screen, suggest

OPEN_D = (-2, 0, 0, -1, -2, -2)  # D A D F# A D from E A D G B E
D, G, A = 2, 7, 9  # pitch classes


class ScreenTest(unittest.TestCase):
    def test_every_retuning_at_every_capo(self):
        counts = screen(STANDARD.open_strings, range(-2, 3), range(4), [Chord(MAJOR, D)], 12)
        self.assertEqual(counts.shape, (5,) * 6 + (4,))

    def test_open_strings_in_the_chords(self):
        counts = screen(STANDARD.open_strings, range(-2, 1), (0,), [Chord(MAJOR, D)], 12)
        unchanged, open_d = (2,) * 6, tuple(np.add(OPEN_D, 2))
        self.assertEqual((counts[(*unchanged, 0)], counts[(*open_d, 0)]), (2, 6))

    def test_matches_counting_each_tuning(self):
        steps, capos, chords = (-1, 0, 2), (0, 3), [Chord(MAJOR, D), Chord(MAJOR, G)]
        counts = screen(STANDARD.open_strings, steps, capos, chords, 12)
        for index in np.ndindex(counts.shape):
            *choice, capo = index
            strings = (STANDARD.open_strings + np.take(steps, choice) + capos[capo]) % 12
            ringing = sum(int(string) in chord for chord in chords for string in strings)
            self.assertEqual(counts[index], ringing)

    def test_a_capo_moves_the_open_strings(self):
        # No open string of standard tuning is in F# major; capo 2 rings F#, C# and F#.
        counts = screen(STANDARD.open_strings, (0,), (0, 2), [Chord(MAJOR, 6)], 12)
        self.assertEqual(counts[(0,) * 6].tolist(), [0, 3])


class TuningNameTest(unittest.TestCase):
    def test_names_from_the_catalog(self):
        open_e = STANDARD.open_strings + np.array([0, 2, 2, 1, 0, 0])
        self.assertEqual(tuning_name(STANDARD.open_strings, TUNINGS), "guitar standard")
        self.assertEqual(tuning_name(STANDARD.open_strings + OPEN_D, TUNINGS), "guitar open D")
        self.assertEqual(tuning_name(open_e, TUNINGS), "guitar open D +2")
        self.assertIsNone(tuning_name(STANDARD.open_strings + [0, 0, 0, 0, 0, 1], TUNINGS))


class SuggestTest(unittest.TestCase):
    def test_no_retuning_is_the_plain_path(self):
        chords, taste = [Chord(MAJOR, G), Chord(MAJOR, D)], Taste()
        (only,) = suggest(STANDARD, chords, taste, steps=(0,), capos=(0,))
        path, cost, *_ = taste.path(STANDARD, chords)
        self.assertEqual((only.retuning, only.capo, only.cost), ((0,) * 6, 0, cost))
        np.testing.assert_array_equal(only.path, path)

    def test_never_worse_than_the_base_tuning(self):
        chords, taste = (
            [Chord(MAJOR, D), Chord(MAJOR, G), Chord(MAJOR, A)],
            Taste(sounding=1.0, ringing=1.0),
        )
        best = suggest(STANDARD, chords, taste)[0]
        cost = taste.path(STANDARD, chords).cost
        self.assertLessEqual(best.cost, cost)

    def test_costly_retuning_keeps_the_base_tuning(self):
        chords = [Chord(MAJOR, D), Chord(MAJOR, G), Chord(MAJOR, A)]
        best = suggest(STANDARD, chords, Taste(sounding=1.0, ringing=1.0), retune=100.0)[0]
        self.assertEqual(best.retuning, (0,) * 6)

    def test_context_chords_add_their_cheapest_voicing(self):
        chords, taste = [Chord(MAJOR, G), Chord(MAJOR, D)], Taste()
        context = [Chord(MAJOR, A)]
        only = {"steps": (0,), "capos": (0,)}
        (plain,) = suggest(STANDARD, chords, taste, **only)
        (keyed,) = suggest(STANDARD, chords, taste, context=context, context_weight=0.5, **only)
        cheapest = taste.standing(STANDARD, taste.voicings(STANDARD, Chord(MAJOR, A))).min()
        self.assertAlmostEqual(keyed.cost - plain.cost, 0.5 * cheapest)

    def test_an_unplayable_context_chord_is_counted_not_fatal(self):
        chords, taste = [Chord(MAJOR, G), Chord(MAJOR, D)], Taste()
        impossible = Chord(PitchClassSet(tuple(range(7))), 0)  # seven adjacent semitones
        plain = suggest(STANDARD, chords, taste)
        keyed = suggest(STANDARD, chords, taste, context=[impossible, Chord(MAJOR, A)])
        self.assertEqual(len(keyed), len(plain))
        self.assertEqual(keyed[0].unplayable, 1)  # the impossible chord, never the A major
        missed = [one.unplayable for one in keyed]
        self.assertEqual(missed, sorted(missed))  # necks that play more of the key come first

    def test_only_capos_and_steps_asked_for(self):
        chords, taste = [Chord(MAJOR, G), Chord(MAJOR, D)], Taste()
        capoed = suggest(STANDARD, chords, taste, capos=(2, 3), shortlist=3)
        self.assertTrue(capoed and all(one.capo in (2, 3) for one in capoed))
        moved = suggest(STANDARD, chords, taste, steps=(-2, -1), capos=(0,), shortlist=3)
        self.assertTrue(moved and all(set(one.retuning) <= {-2, -1} for one in moved))

    def test_each_suggestion_sounds_different(self):
        found = suggest(STANDARD, [Chord(MAJOR, D), Chord(MAJOR, A)], Taste(sounding=1.0), top=10)
        sounds = {
            replace(STANDARD, open_strings=STANDARD.open_strings + one.retuning)
            .capo(one.capo)
            .notes(one.path)
            .tobytes()
            for one in found
        }
        self.assertEqual(len(sounds), len(found))

    def test_sorted_by_cost(self):
        found = suggest(STANDARD, [Chord(MAJOR, D), Chord(MAJOR, A)], Taste(ringing=1.0), top=10)
        costs = [suggestion.cost for suggestion in found]
        self.assertEqual(costs, sorted(costs))


class ShortlistTest(unittest.TestCase):
    def test_matches_ranking_the_whole_table(self):
        rng = np.random.default_rng(1)
        for _ in range(200):
            strings, steps, capos = rng.integers(1, 6), rng.integers(1, 5), rng.integers(1, 4)
            costs = rng.integers(-3, 4, (strings, steps, capos))
            count = int(rng.integers(1, 12))
            shape = (steps,) * strings + (capos,)
            order = np.argsort(_by_string(costs).ravel(), kind="stable")[:count]
            whole = [np.unravel_index(index, shape) for index in order]
            expected = [(tuple(map(int, at[:-1])), int(at[-1])) for at in whole]
            self.assertEqual(_best(costs, count), expected)


if __name__ == "__main__":
    unittest.main()
