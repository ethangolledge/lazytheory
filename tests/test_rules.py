import unittest

import numpy as np

from lazy_theory.core.scale import Scale
from lazy_theory.instruments.fretboard import MUTED, Fretboard
from lazy_theory.instruments.rules import (
    contiguous,
    fingers,
    smoothest,
    transition_cost,
    within,
)

X = MUTED
STANDARD = Fretboard.from_gaps((5, 5, 5, 4, 5))
IONIAN = Scale.from_steps((2, 2, 1, 2, 2, 2, 1))
C = 8  # steps above standard tuning's low E


def rows(*voicings: list[int]) -> np.ndarray:
    return np.array(voicings, dtype=np.int16)


class FingersTest(unittest.TestCase):
    def test_open_shapes(self):
        self.assertEqual(fingers(rows([0, 2, 2, 1, 0, 0], [X, 3, 2, 0, 1, 0])).tolist(), [3, 3])

    def test_barre_counts_as_one_finger(self):
        self.assertEqual(fingers(rows([1, 3, 3, 2, 1, 1])).tolist(), [4])

    def test_open_string_under_the_barre_breaks_it(self):
        self.assertEqual(fingers(rows([5, 0, 5, 5, X, X])).tolist(), [3])

    def test_too_many_notes(self):
        self.assertEqual(fingers(rows([1, 2, 3, 4, 5, X])).tolist(), [5])


class ShapeRulesTest(unittest.TestCase):
    def test_contiguous(self):
        self.assertEqual(
            contiguous(rows([X, 3, 2, 0, 1, 0], [3, X, 2, 0, 1, 0])).tolist(), [True, False]
        )

    def test_within_allows_open_strings(self):
        voicings = rows([X, X, 9, 9, 8, 8], [0, X, 9, 9, 8, 8], [X, X, 9, 9, 8, 12])
        self.assertEqual(within(voicings, 7, 11).tolist(), [True, True, False])


class BassTest(unittest.TestCase):
    def test_bass_interval_names_the_inversion(self):
        voicings = rows([X, 3, 2, 0, 1, 0], [0, 3, 2, 0, 1, 0], [3, 3, 2, 0, 1, 0])
        self.assertEqual(STANDARD.bass(voicings, C).tolist(), [0, 4, 7])

    def test_bass_is_lowest_pitch_not_first_string(self):
        ukulele = Fretboard.from_gaps((-7, 4, 5), frets=12)
        self.assertEqual(ukulele.bass(rows([0, 0, 0, 3]), root=-7).tolist(), [0])


class TransitionTest(unittest.TestCase):
    def test_cost_is_frets_moved_plus_strings_changed(self):
        previous = rows([X, X, 10, 10, 10, 10])
        following = rows([X, X, 9, 10, 8, 10], [X, 10, 9, 10, 8, X])
        costs = transition_cost(previous, following, string_change=5)
        self.assertEqual(costs.tolist(), [[3, 13]])

    def test_smoothest_matches_brute_force(self):
        options = [
            STANDARD.voicings(IONIAN.chord(degree, 4), C + IONIAN.pitch_classes[degree])
            for degree in (1, 4, 0)
        ]
        two, five, one = [v[(fingers(v) <= 4) & contiguous(v) & within(v, 5, 9)] for v in options]
        every_path = (
            transition_cost(two, five, 5)[:, :, None] + transition_cost(five, one, 5)[None, :, :]
        )
        chosen = smoothest([two, five, one], 5)
        chosen_cost = sum(
            int(transition_cost(a[None], b[None], 5)[0, 0])
            for a, b in zip(chosen, chosen[1:], strict=False)
        )
        self.assertEqual(chosen_cost, every_path.min())

    def test_fixed_starting_voicing(self):
        start = rows([X, X, 10, 10, 10, 10])
        five = STANDARD.voicings(IONIAN.chord(4, 4), C + 7)
        path = smoothest([start, five], string_change=5)
        np.testing.assert_array_equal(path[0], start[0])

    def test_rejects_a_chord_with_no_voicings(self):
        with self.assertRaises(ValueError):
            smoothest([rows([0, 2, 2, 1, 0, 0]), rows()[:0]], 5)


class TwoFiveOneTest(unittest.TestCase):
    """ii-V-I in C, one hand position: the path keeps its strings and picks its inversions."""

    def test_stays_on_the_same_strings(self):
        roots = [C + IONIAN.pitch_classes[degree] for degree in (1, 4, 0)]
        options = []
        for degree, root in zip((1, 4, 0), roots, strict=True):
            voicings = STANDARD.voicings(IONIAN.chord(degree, 4), root)
            keep = (fingers(voicings) <= 4) & contiguous(voicings) & within(voicings, 7, 11)
            options.append(voicings[keep & (voicings != 0).all(axis=1)])
        path = smoothest(options, string_change=5)
        sounding = path != MUTED
        self.assertTrue((sounding == sounding[0]).all())
        self.assertEqual(path.tolist()[-1], [X, X, 9, 9, 8, 8])


if __name__ == "__main__":
    unittest.main()
