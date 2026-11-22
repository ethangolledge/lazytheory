import unittest

from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.rhythm.meter import Meter
from lazy_theory.rhythm.performance import Performance

EIGHTHS = Meter.of((2, 2), 2)  # 4/4 in eighths: 8 pulses, a beat every 2


class PerformanceTest(unittest.TestCase):
    def test_keeps_every_onset_as_played(self):
        played = Performance((2.97, 0.03, 1.48), 4)
        self.assertEqual(played.times, (0.03, 1.48, 2.97))  # in the order they sound

    def test_folds_later_laps_into_the_cycle(self):
        self.assertEqual(Performance((4.5, 9.0), 4).times, (0.5, 1.0))

    def test_a_tap_a_rounding_error_before_the_one_is_on_the_one(self):
        played = Performance((-1e-17,), 4)
        self.assertEqual(played.times, (0.0,))
        self.assertEqual(played.placed(Meter.of((4,), 4)).points, (0,))

    def test_silence_is_a_performance(self):
        silence = Performance((), 4)
        self.assertEqual(silence.placed(EIGHTHS).points, ())
        self.assertEqual(silence.placed(EIGHTHS).onsets(8), PitchClassSet((), 8))

    def test_rejects_an_empty_cycle_and_impossible_times(self):
        with self.assertRaises(ValueError):
            Performance((0.0,), 0)
        with self.assertRaises(ValueError):
            Performance((float("nan"),), 4)


class PlacedTest(unittest.TestCase):
    def test_nearest_point_and_how_far_off(self):
        placed = Performance((0.05, 1.45, 3.0), 4).placed(EIGHTHS)
        self.assertEqual(placed.points, (0, 3, 6))
        for offset, expected in zip(placed.offsets, (0.05, -0.05, 0.0), strict=True):
            self.assertAlmostEqual(offset, expected)  # counts: negative is early

    def test_reading_never_changes_the_performance(self):
        played = Performance((0.05, 1.45), 4)
        played.placed(EIGHTHS)
        self.assertEqual(played.times, (0.05, 1.45))

    def test_swing_moves_where_the_offbeat_is_heard(self):
        late = Performance((0.66,), 4)  # a swung "and": two thirds of the beat
        self.assertEqual(late.placed(EIGHTHS).points, (1,))
        self.assertAlmostEqual(late.placed(EIGHTHS).offsets[0], 0.16)  # straight: late
        self.assertAlmostEqual(late.placed(EIGHTHS, swing=2).offsets[0], 0.66 - 2 / 3)

    def test_wraps_round_the_cycle(self):
        placed = Performance((3.98,), 4).placed(EIGHTHS)
        self.assertEqual(placed.points, (0,))  # just before the 1 belongs to the 1
        self.assertAlmostEqual(placed.offsets[0], -0.02)

    def test_two_onsets_on_one_point_show_up(self):
        self.assertEqual(Performance((0.0, 0.1), 4).placed(EIGHTHS).points, (0, 0))

    def test_a_beat_split_differently_is_read_in_its_own_points(self):
        meter = Meter.of((2, 2), (2, 5, 2, 2))  # a quintuplet on beat two
        placed = Performance((1.4,), 4).placed(meter)
        grid = tuple(meter.starts(-1))
        self.assertEqual(
            tuple(meter.to_grid(PitchClassSet(placed.points, meter.pulses))),
            (grid.index(placed.points[0]),),
        )
        self.assertAlmostEqual(placed.offsets[0], 0.0)  # 1.4 is the third quintuplet

    def test_rejects_a_meter_with_another_count(self):
        with self.assertRaises(ValueError):
            Performance((0.0,), 3).placed(EIGHTHS)


if __name__ == "__main__":
    unittest.main()
