import unittest

from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.rhythm.meter import Meter
from lazy_theory.rhythm.stroke import BOTH, HIGH, LIGHT, SILENCE, voicing


class VoicingTest(unittest.TestCase):
    def test_only_notes_sound(self):
        meter = Meter.of((7,))  # 3+4, then 3+2+2
        strokes = voicing(PitchClassSet((0, 3, 5), 7), meter)
        self.assertEqual(strokes, (BOTH, SILENCE, SILENCE, BOTH, SILENCE, BOTH, SILENCE))

    def test_plain_counts_get_the_high_head(self):
        meter = Meter.of((2, 2), 2)  # 4/4 in eighths: bass on 1 and 3
        strokes = voicing(meter.starts(meter.beat), meter)
        self.assertEqual(strokes, (BOTH, SILENCE, HIGH, SILENCE, BOTH, SILENCE, HIGH, SILENCE))

    def test_sixteenths_are_lighter_than_eighths(self):
        meter = Meter.of((2, 2), 4)
        strokes = voicing(meter.starts(-1), meter)
        self.assertEqual(strokes[4:8], (HIGH, LIGHT, HIGH, LIGHT))

    def test_a_five_felt_two_plus_three_lifts_its_three(self):
        meter = Meter.of((2, 2), (4, 5, 4, 4))
        strokes = voicing(meter.starts(-1), meter)
        self.assertEqual(strokes[4:9], (HIGH, LIGHT, HIGH, LIGHT, LIGHT))  # the five: 2+3

    def test_one_stroke_per_grid_point_on_a_shared_grid(self):
        meter = Meter.of((2, 2), (4, 5, 4, 4))
        self.assertEqual(len(voicing(meter.starts(meter.beat), meter)), 17)
        with self.assertRaises(ValueError):
            voicing(PitchClassSet((1,), 80), meter)  # off the grid

    def test_your_accents_get_the_bass_and_the_rest_is_lighter(self):
        meter = Meter.of((2, 2), 4)
        strokes = voicing(PitchClassSet((0, 3, 6, 12), 16), meter, PitchClassSet((0, 12), 16))
        self.assertEqual(
            (strokes[0], strokes[3], strokes[6], strokes[12]), (BOTH, HIGH, HIGH, BOTH)
        )
        self.assertEqual(strokes[4], SILENCE)


if __name__ == "__main__":
    unittest.main()
