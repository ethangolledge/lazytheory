import unittest
from fractions import Fraction

from lazy_theory.core.temperament import EqualTemperament, JustIntonation, ratio_to_cents

JUST_MAJOR = JustIntonation(tuple(map(Fraction, ["1", "9/8", "5/4", "4/3", "3/2", "5/3", "15/8"])))


def best_fifth_error(edo: int) -> float:
    """Cents between the pure fifth (3/2) and the closest step of `edo` equal divisions."""
    temperament = EqualTemperament(edo)
    pure = ratio_to_cents(1.5)
    return min(abs(temperament.cents(step) - pure) for step in range(edo + 1))


class RatioToCentsTest(unittest.TestCase):
    def test_harmonic_series_intervals(self):
        for ratio, cents in [(2, 1200), (3 / 2, 701.955), (5 / 4, 386.314), (6 / 5, 315.641)]:
            self.assertAlmostEqual(ratio_to_cents(ratio), cents, places=3)

    def test_commas(self):
        self.assertAlmostEqual(ratio_to_cents(3**12 / 2**19), 23.460, places=3)
        self.assertAlmostEqual(ratio_to_cents(81 / 80), 21.506, places=3)


class EqualTemperamentTest(unittest.TestCase):
    def test_semitones_are_100_cents(self):
        twelve = EqualTemperament()
        for step in range(13):
            self.assertAlmostEqual(twelve.cents(step), step * 100)

    def test_steps_beyond_the_period(self):
        twelve = EqualTemperament()
        self.assertAlmostEqual(twelve.ratio(12), 2)
        self.assertAlmostEqual(twelve.ratio(-12), 0.5)
        self.assertAlmostEqual(twelve.ratio(24), 4)

    def test_tempered_fifth_is_two_cents_flat(self):
        self.assertAlmostEqual(EqualTemperament().cents(7) - ratio_to_cents(1.5), -1.955, places=3)

    def test_non_octave_period(self):
        bohlen_pierce = EqualTemperament(13, Fraction(3))
        self.assertAlmostEqual(bohlen_pierce.ratio(13), 3)

    def test_convergent_edos_beat_every_smaller_edo_at_the_fifth(self):
        for edo in (5, 12, 41, 53):
            smaller = min(best_fifth_error(n) for n in range(1, edo))
            self.assertLess(best_fifth_error(edo), smaller, edo)

    def test_rejects_invalid_systems(self):
        with self.assertRaises(ValueError):
            EqualTemperament(0)
        with self.assertRaises(ValueError):
            EqualTemperament(12, Fraction(1))


class JustIntonationTest(unittest.TestCase):
    def test_size_is_number_of_ratios(self):
        self.assertEqual(JUST_MAJOR.size, 7)

    def test_steps_are_exact_ratios(self):
        self.assertAlmostEqual(JUST_MAJOR.cents(2), 386.314, places=3)
        self.assertAlmostEqual(JUST_MAJOR.ratio(4), 1.5)

    def test_steps_beyond_the_period(self):
        self.assertAlmostEqual(JUST_MAJOR.ratio(7), 2)
        self.assertAlmostEqual(JUST_MAJOR.ratio(9), 2.5)
        self.assertAlmostEqual(JUST_MAJOR.ratio(-1), 15 / 16)

    def test_rejects_invalid_ratios(self):
        for ratios in [(), (Fraction(9, 8),), (1, Fraction(5, 4), Fraction(9, 8)), (1, 2)]:
            with self.assertRaises(ValueError, msg=ratios):
                JustIntonation(tuple(map(Fraction, ratios)))


if __name__ == "__main__":
    unittest.main()
