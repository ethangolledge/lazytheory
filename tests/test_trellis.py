import unittest
from unittest import mock

import numpy as np
from fixtures import IONIAN, MAJOR, REACH, STANDARD, X, rows

from lazy_theory.instruments.acoustics import roughness
from lazy_theory.instruments.arrays import MUTED
from lazy_theory.instruments.rules import (
    contiguous,
    fingers,
    motion,
    moved,
    strings_changed,
    within,
)
from lazy_theory.instruments.trellis import Trellis
from lazy_theory.pitch.chord import Chord

C, F, G = 0, 5, 7  # pitch classes


def bass(voicings: np.ndarray) -> np.ndarray:
    return np.nanmin(STANDARD.notes(voicings), axis=1)


def bass_motion(previous: np.ndarray, following: np.ndarray) -> np.ndarray:
    return motion(bass(previous), bass(following))


def playable(voicings: np.ndarray, lowest: int, highest: int) -> np.ndarray:
    return voicings[(fingers(voicings) <= 4) & within(voicings, lowest, highest)]


class ShortestTest(unittest.TestCase):
    def test_matches_brute_force(self):
        def transition(previous, following):
            return moved(previous, following) + 5 * strings_changed(previous, following)

        def cost(voicings):
            return 10 * roughness(STANDARD.notes(voicings), STANDARD.hertz, STANDARD.temperament)

        two, five, one = [
            playable(STANDARD.voicings(Chord(IONIAN.chord(degree, 4), C + step), REACH), 5, 9)
            for degree, step in ((1, 2), (4, 7), (0, 0))
        ]
        every_path = (
            cost(two)[:, None, None]
            + transition(two, five)[:, :, None]
            + cost(five)[None, :, None]
            + transition(five, one)[None, :, :]
            + cost(one)[None, None, :]
        )
        trellis = Trellis.build([two, five, one], transition, [cost(two), cost(five), cost(one)])
        path, total, picks, _ = trellis.shortest()
        self.assertAlmostEqual(total, every_path.min())
        np.testing.assert_array_equal(path, [two[picks[0]], five[picks[1]], one[picks[2]]])
        chosen = sum(cost(path[i : i + 1])[0] for i in range(3)) + sum(
            transition(path[i : i + 1], path[i + 1 : i + 2])[0, 0] for i in range(2)
        )
        self.assertAlmostEqual(chosen, every_path.min())

    def test_fixed_starting_voicing(self):
        start = rows([X, X, 10, 10, 10, 10])
        five = STANDARD.voicings(Chord(IONIAN.chord(4, 4), C + 7), REACH)
        path = Trellis.build([start, five], moved).shortest().path
        np.testing.assert_array_equal(path[0], start[0])

    def test_a_mask_pins_a_voicing(self):
        five = STANDARD.voicings(Chord(IONIAN.chord(4, 4), C + 7), REACH)
        one = STANDARD.voicings(Chord(IONIAN.chord(0, 4), C), REACH)
        trellis, pinned = Trellis.build([five, one], moved), np.arange(len(one)) == 3
        route = trellis.shortest([None, pinned])
        self.assertEqual(route.picks[1], 3)
        self.assertAlmostEqual(route.cost, moved(five, one[3:4]).min())
        with self.assertRaises(ValueError):
            trellis.shortest([None, np.zeros(len(one), dtype=bool)])

    def test_many_searches_match_one_at_a_time(self):
        five, one = (
            playable(STANDARD.voicings(Chord(IONIAN.chord(degree, 4), C + step), REACH), 5, 9)
            for degree, step in ((4, 7), (0, 0))
        )
        trellis = Trellis.build([five, one, five], moved)
        picks, totals = trellis.search([None, np.eye(len(one), dtype=bool), None])
        for k in (0, 7, len(one) - 1):
            alone = trellis.shortest([None, np.arange(len(one)) == k, None])
            self.assertAlmostEqual(totals[k], alone.cost)
            self.assertEqual(tuple(picks[k]), alone.picks)

    def test_batches_give_the_same_answer(self):
        five, one = (
            playable(STANDARD.voicings(Chord(IONIAN.chord(degree, 4), C + step), REACH), 5, 9)
            for degree, step in ((4, 7), (0, 0))
        )
        trellis = Trellis.build([five, one, five], moved)
        masks = [None, np.eye(len(one), dtype=bool), np.ones((1, len(five)), dtype=bool)]
        whole = trellis.search(masks)
        with mock.patch("lazy_theory.instruments.trellis._CELLS", 5 * five.shape[0] * len(one)):
            in_batches = trellis.search(masks)  # five searches at a time
        np.testing.assert_array_equal(whole[0], in_batches[0])
        np.testing.assert_array_equal(whole[1], in_batches[1])

    def test_rejects_an_empty_progression(self):
        with self.assertRaises(ValueError):
            Trellis.build([], lambda a, b: np.zeros((len(a), len(b))))

    def test_rejects_a_chord_with_no_voicings(self):
        with self.assertRaises(ValueError):
            Trellis.build([rows([0, 2, 2, 1, 0, 0]), rows()[:0]], moved)


class EachTest(unittest.TestCase):
    @staticmethod
    def transition(previous, following):
        return moved(previous, following) + 5 * strings_changed(previous, following)

    def setUp(self):
        self.options = [
            playable(STANDARD.voicings(Chord(IONIAN.chord(degree, 3), C + step), REACH), 0, 4)
            for degree, step in ((0, 0), (5, 9), (3, 5), (4, 7))  # C Am F G
        ]
        self.costs = [
            10 * roughness(STANDARD.notes(v), STANDARD.hertz, STANDARD.temperament)
            for v in self.options
        ]
        self.tops = [STANDARD.top(v) for v in self.options]
        self.trellis = Trellis.build(self.options, self.transition, self.costs)

    def test_matches_brute_force(self):
        routes = self.trellis.each(self.tops, slack=6)
        every = self.costs[0][:, None, None, None] + self.costs[1][None, :, None, None]
        every = every + self.costs[2][None, None, :, None] + self.costs[3][None, None, None, :]
        every = every + self.transition(*self.options[:2])[:, :, None, None]
        every = every + self.transition(*self.options[1:3])[None, :, :, None]
        every = every + self.transition(*self.options[2:])[None, None, :, :]
        best: dict[tuple, float] = {}
        for index in zip(*np.nonzero(every <= every.min() + 6), strict=True):
            line = tuple(float(tops[i]) for tops, i in zip(self.tops, index, strict=True))
            best[line] = min(best.get(line, np.inf), float(every[index]))
        self.assertEqual(
            {r.labels: round(r.cost, 9) for r in routes},
            {line: round(cost, 9) for line, cost in best.items()},
        )
        self.assertGreater(len(routes), 1)

    def test_first_is_shortest_and_each_path_plays_its_line(self):
        routes = self.trellis.each(self.tops, slack=6)
        total = self.trellis.shortest().cost
        self.assertAlmostEqual(routes[0].cost, total)
        self.assertEqual([r.cost for r in routes], sorted(r.cost for r in routes))
        for route in routes:
            self.assertEqual(tuple(STANDARD.top(route.path).tolist()), route.labels)

    def test_no_slack_gives_only_the_best_lines(self):
        routes = self.trellis.each(self.tops, slack=0)
        total = self.trellis.shortest().cost
        self.assertTrue(all(abs(r.cost - total) < 1e-9 for r in routes))

    def test_rejects_masks_for_the_wrong_number_of_chords(self):
        trellis = Trellis.build([rows([0, 2, 2, 1, 0, 0]), rows([0, 2, 2, 0, 0, 0])], moved)
        with self.assertRaises(ValueError):
            trellis.shortest([None])
        with self.assertRaises(ValueError):
            trellis.tied(["C"])


class TiedTest(unittest.TestCase):
    transition = staticmethod(EachTest.transition)

    def setUp(self):
        c, am, g = (
            playable(STANDARD.voicings(Chord(IONIAN.chord(degree, 3), C + step), REACH), 0, 4)
            for degree, step in ((0, 0), (5, 9), (4, 7))
        )
        self.options = [c, am, c, g]  # C Am C G: C comes back
        self.costs = [
            10 * roughness(STANDARD.notes(v), STANDARD.hertz, STANDARD.temperament)
            for v in self.options
        ]
        self.trellis = Trellis.build(self.options, self.transition, self.costs)

    def test_matches_brute_force_with_one_repeated_chord(self):
        path, total, *_ = self.trellis.tied([0, 1, 0, 2])
        o, k = self.options, self.costs
        every = (
            k[0][:, None, None] + k[1][None, :, None] + k[2][:, None, None] + k[3][None, None, :]
        )
        every = every + self.transition(o[0], o[1])[:, :, None]  # C (first) to Am
        every = every + self.transition(o[1], o[2]).T[:, :, None]  # Am to C, the same C
        every = every + self.transition(o[2], o[3])[:, None, :]  # C to G
        self.assertAlmostEqual(total, every.min())
        np.testing.assert_array_equal(path[0], path[2])

    def test_without_repeats_it_is_shortest(self):
        tied, free = self.trellis.tied([0, 1, 2, 3]).cost, self.trellis.shortest().cost
        self.assertAlmostEqual(tied, free)

    def test_a_tie_never_beats_the_free_route(self):
        tied, free = self.trellis.tied([0, 1, 0, 2]).cost, self.trellis.shortest().cost
        self.assertGreaterEqual(tied, free - 1e-9)

    def test_a_group_needs_the_same_options(self):
        with self.assertRaises(ValueError):
            self.trellis.tied([0, 0, 1, 2])


class InversionsFromTheBassTest(unittest.TestCase):
    """The common-practice uses of inversions follow from one rule: move the bass as little as
    possible (docs/theory.md section 7)."""

    tonic = rows([X, 3, 2, 0, 1, 0])  # C, bass C3

    def inversion(self, chords: list[np.ndarray], middle: int) -> int:
        path = Trellis.build(chords, bass_motion).shortest().path
        return int(STANDARD.stack(path[1:2], middle)[0, 0])

    def test_pedal_six_four(self):
        # I - IV - I over a held bass: IV takes its fifth in the bass.
        subdominant = playable(STANDARD.voicings(Chord(MAJOR, F), REACH), 0, 4)
        self.assertEqual(self.inversion([self.tonic, subdominant, self.tonic], F), 7)

    def test_passing_six_four(self):
        # I - V - I6, bass C3 to E3: V takes its fifth, D3, to pass by step.
        dominant = playable(STANDARD.voicings(Chord(MAJOR, G), REACH), 0, 4)
        tonic_six = rows([X, X, 2, 0, 1, 0])
        self.assertEqual(self.inversion([self.tonic, dominant, tonic_six], G), 7)

    def test_four_two_resolves_to_six(self):
        # V4/2, seventh F2 in the bass, falls a step to I6 with E2 in the bass.
        dominant_seventh = rows([1, X, 0, 0, 0, 1])
        tonic = playable(STANDARD.voicings(Chord(MAJOR, C), REACH), 0, 4)
        path = Trellis.build([dominant_seventh, tonic], bass_motion).shortest().path
        self.assertEqual(STANDARD.stack(path[1:], C)[0, 0], 4)


class TwoFiveOneTest(unittest.TestCase):
    """ii-V-I in C in one hand position keeps its strings and picks its inversions."""

    def test_stays_on_the_same_strings(self):
        options = [
            playable(STANDARD.voicings(Chord(IONIAN.chord(degree, 4), C + step), REACH), 7, 11)
            for degree, step in ((1, 2), (4, 7), (0, 0))
        ]
        options = [voicings[contiguous(voicings)] for voicings in options]
        graph = Trellis.build(options, lambda a, b: moved(a, b) + 5 * strings_changed(a, b))
        path = graph.shortest().path
        sounding = path != MUTED
        self.assertTrue((sounding == sounding[0]).all())
        self.assertEqual(path.tolist()[-1], [X, X, 9, 9, 8, 8])


class CostArrayTest(unittest.TestCase):
    def test_costs_may_be_one_array(self):
        options = [rows([0, 2, 2, 1, 0, 0], [0, 2, 2, 0, 0, 0])] * 2
        trellis = Trellis.build(options, moved, np.array([[0.0, 5.0], [5.0, 0.0]]))
        self.assertEqual(trellis.shortest().picks, (0, 1))


class MaskShapeTest(unittest.TestCase):
    def test_a_mask_must_cover_every_voicing(self):
        two = rows([0, 2, 2, 1, 0, 0], [0, 2, 2, 0, 0, 0])
        trellis = Trellis.build([two, two], moved)
        for bad in (np.array([True]), np.ones((2, 2, 2), dtype=bool)):
            with self.subTest(shape=bad.shape), self.assertRaises(ValueError):
                trellis.shortest([bad, None])


if __name__ == "__main__":
    unittest.main()
