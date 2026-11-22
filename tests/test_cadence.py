import unittest
from itertools import pairwise

from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.rhythm.cadence import (
    cadences,
    chakradars,
    landing,
    solve,
    span,
    tihais,
    yatis,
)


class SolveTest(unittest.TestCase):
    def test_every_solution_and_only_solutions(self):
        for total in range(0, 30):
            found = solve((3, 2, 5), total, (1, 0, 0))
            brute = [
                (a, b, c)
                for a in range(1, 11)
                for b in range(16)
                for c in range(7)
                if 3 * a + 2 * b + 5 * c == total
            ]
            self.assertEqual(found, brute, total)

    def test_rejects_bad_coefficients(self):
        for coefficients in [(), (0, 1), (-1, 2)]:
            with self.assertRaises(ValueError):
                solve(coefficients, 5)


class TihaiTest(unittest.TestCase):
    def test_teentaal_sixteen(self):
        self.assertEqual(tihais(16), [(4, 2), (2, 5)])  # 4 2 4 2 4 and 2 5 2 5 2

    def test_mukherjee_sixty_five(self):
        self.assertIn((21, 1), tihais(65))  # 3 x 21 + 2 = 65 = 64 + 1

    def test_gap_minimum(self):
        self.assertEqual(tihais(15, gap_min=1), [(3, 3), (1, 6)])  # no gapless 5 5 5

    def test_chakradar_of_sixty_five(self):
        # Wikipedia's layout: a phrase of 7 nine times, one pulse between the tihais
        self.assertIn((7, 0, 1), chakradars(65))
        for phrase, gap, outer in chakradars(65):
            self.assertEqual(9 * phrase + 6 * gap + 2 * outer, 65)


class SpanTest(unittest.TestCase):
    def test_both_landing_conventions(self):
        self.assertEqual(span(10, 0, laps=2), 21)  # Jhaptaal: last stroke on sam
        self.assertEqual(span(16, 0, laps=1, on_target=False), 16)  # resolves into sam
        self.assertEqual(span(16, 9, on_target=False), 7)  # from beat 10 to the next sam

    def test_landing_undoes_span(self):
        for cycle in range(1, 13):
            for start in range(cycle):
                for target in range(cycle):
                    for on_target in (True, False):
                        laps = 1 if start == target and not on_target else 0
                        total = span(cycle, start, target, laps, on_target)
                        self.assertEqual(landing(start, total, cycle, on_target), target)

    def test_rejects_landing_where_it_starts(self):
        with self.assertRaises(ValueError):
            span(8, 3, 3, on_target=False)


class YatiTest(unittest.TestCase):
    def test_runs_fill_the_total_evenly_growing(self):
        for total in range(1, 40):
            for parts in range(1, 6):
                for run in yatis(total, parts):
                    self.assertEqual(sum(run), total)
                    self.assertEqual(len({b - a for a, b in pairwise(run)}), min(1, parts - 1))

    def test_shapes(self):
        self.assertIn((3, 4, 5), yatis(12, 3))  # srotovaha
        self.assertIn((5, 4, 3), yatis(12, 3))  # gopuccha
        self.assertIn((4, 4, 4), yatis(12, 3))  # sama

    def test_krishnaswamy_wells_trios_cannot_reach_an_eduppu_off_three(self):
        # a trio of equal or evenly growing parts spans a multiple of 3, so in a cycle of 12
        # it can't start on sama and land on an eduppu of 1 or 2
        for laps in range(1, 5):
            for eduppu in (1, 2):
                self.assertEqual(yatis(12 * laps + eduppu, 3), [])
        self.assertIn((7, 5), solve((3, 3), 36))  # their 36-pulse korvai: 3 x 7 + 3 x 5


class CadenceTest(unittest.TestCase):
    def test_from_sam_as_before(self):
        found = cadences(PitchClassSet((0, 3, 6), 16))
        self.assertEqual([(p, g) for p, g, _ in found], [(4, 2), (2, 5)])
        self.assertEqual(found[0][2], PitchClassSet((0, 3, 6, 9, 12, 15), 16))

    def test_from_a_later_start(self):
        found = cadences(PitchClassSet((0, 2), 16), start=8)  # 8 pulses to go: 3p + 2g = 8
        self.assertEqual([(p, g) for p, g, _ in found], [(2, 1)])
        self.assertEqual(found[0][2], PitchClassSet((8, 11, 14), 16))

    def test_last_note_on_sam(self):
        found = cadences(PitchClassSet((0, 1, 4), 16), start=0, on_target=True)
        for phrase, gap, notes in found:
            self.assertEqual(3 * phrase + 2 * gap, 17)
            self.assertIn(0, notes)  # the last note sounds on the next 1

    def test_silent_first_pulse(self):
        self.assertEqual(cadences(PitchClassSet((2, 5), 8)), [])

    def test_every_pulse_of_sixteen(self):
        found = cadences(PitchClassSet(tuple(range(16)), 16))
        self.assertEqual([(p, g) for p, g, _ in found], [(4, 2), (2, 5)])
        self.assertEqual(found[0][2].pitch_classes, (0, 1, 2, 3, 6, 7, 8, 9, 12, 13, 14, 15))
        self.assertEqual(found[1][2].pitch_classes, (0, 1, 7, 8, 14, 15))

    def test_each_lands_on_the_next_cycle(self):
        for size in range(3, 25):
            for phrase, gap, _ in cadences(PitchClassSet((0,), size)):
                self.assertEqual(landing(0, 3 * phrase + 2 * gap, size, on_target=False), 0)


if __name__ == "__main__":
    unittest.main()
