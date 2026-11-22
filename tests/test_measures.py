import unittest

from lazy_theory.rhythm.catalog import load_talas
from lazy_theory.rhythm.measures import RATE_LIMIT, even_beats, npvi, tactus, too_fast
from lazy_theory.rhythm.meter import Meter
from lazy_theory.rhythm.names import parse_meter


class NpviTest(unittest.TestCase):
    def test_even_and_alternating(self):
        self.assertEqual(npvi([2, 2, 2, 2]), 0)
        self.assertAlmostEqual(npvi([2, 1, 2, 1]), 200 / 3)  # |2 - 1| / 1.5 each pair

    def test_rejects_fewer_than_two(self):
        with self.assertRaises(ValueError):
            npvi([3])


class RateLimitTest(unittest.TestCase):
    def test_sixteenths_too_fast_at_a_quick_tempo(self):
        meter = Meter.of((2, 2), 4)  # 4/4 in sixteenths
        self.assertEqual(too_fast(meter, 0.125), [])  # 120 bpm: 16ths 125 ms apart
        self.assertEqual(too_fast(meter, 0.08), [len(meter.levels) - 1])  # 188 bpm
        self.assertEqual(RATE_LIMIT, 0.1)


class EvenBeatsTest(unittest.TestCase):
    def test_londons_uneven_beats(self):
        self.assertTrue(even_beats(Meter.of((3, 2, 2)), 1))
        self.assertTrue(even_beats(Meter.of((3, 3, 2)), 1))
        self.assertFalse(even_beats(Meter.of((4, 1, 2)), 1))

    def test_a_talas_sections_are_not_beats(self):
        self.assertFalse(even_beats(load_talas()["chatusra triputa"], 1))  # Adi: 4+2+2


class TactusTest(unittest.TestCase):
    def test_six_eight_is_tapped_in_two(self):
        meter = parse_meter("6/8")
        self.assertEqual(meter.levels[tactus(meter, 0.25, 0.6)], (3, 3))

    def test_slow_eighths_are_tapped_as_they_are(self):
        meter = parse_meter("6/8")
        self.assertEqual(tactus(meter, 0.6, 0.6), len(meter.levels) - 1)


if __name__ == "__main__":
    unittest.main()
