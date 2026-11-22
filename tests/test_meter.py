import unittest
from itertools import combinations

from lazy_theory.core.pcset import PitchClassSet, group_starts
from lazy_theory.rhythm.meter import (
    CLAP,
    WAVE,
    Meter,
    cells,
    compositions,
    count,
    gaps,
    grouping,
    groupings,
    guest,
    metric_grouping,
    nesting,
    syncopation,
    unevenness,
)

FOUR_FOUR_SIXTEENTHS = Meter.of((2, 2), 4)


def rhythm(*steps: int) -> PitchClassSet:
    return PitchClassSet.from_steps(steps)


class GroupingTest(unittest.TestCase):
    def test_splits_in_two_shorter_first(self):
        expected = {4: (2, 2), 5: (2, 3), 6: (3, 3), 7: (3, 4), 8: (4, 4), 9: (4, 5)}
        for total, parts in expected.items():
            self.assertEqual(grouping(total), parts, total)

    def test_three_or_fewer_are_single_pulses(self):
        self.assertEqual(grouping(3), (1, 1, 1))
        self.assertEqual(grouping(1), (1,))

    def test_nesting_keeps_twos_and_threes_as_a_level(self):
        self.assertEqual(nesting((7,)), ((7,), (3, 4), (3, 2, 2), (1,) * 7))
        self.assertEqual(nesting((12,)), ((12,), (6, 6), (3, 3, 3, 3), (1,) * 12))  # 12/8

    def test_rejects_an_empty_group(self):
        with self.assertRaises(ValueError):
            grouping(0)

    def test_meters_in_multiples_of_three_are_compound(self):
        expected = {6: (3, 3), 9: (3, 3, 3), 12: (6, 6), 15: (6, 9), 18: (9, 9), 7: (3, 4)}
        for total, parts in expected.items():
            self.assertEqual(metric_grouping(total), parts, total)
        self.assertEqual(nesting((15,))[-2], (3,) * 5)  # 15/8: five dotted quarters
        self.assertEqual(nesting((21,))[-2], (3,) * 7)

    def test_spoken_nine_stays_four_and_five(self):
        self.assertEqual(
            nesting((9,), grouping)[1], (4, 5)
        )  # sankeerna: ta-ka-di-mi ta-ka-ta-ki-ta
        self.assertEqual(Meter.of((9,)).levels[1], (3, 3, 3))  # 9/8


class MeterTest(unittest.TestCase):
    def test_longuet_higgins_and_lee_weights_for_four_four(self):
        # LHL's 4/4 in sixteenths: 0 -4 -3 -4 -2 -4 -3 -4 -1 ..., the same up to a constant
        lhl = (0, -4, -3, -4, -2, -4, -3, -4, -1, -4, -3, -4, -2, -4, -3, -4)
        self.assertEqual(FOUR_FOUR_SIXTEENTHS.weights(), tuple(w + 5 for w in lhl))

    def test_beats(self):
        self.assertEqual(
            tuple(FOUR_FOUR_SIXTEENTHS.starts(FOUR_FOUR_SIXTEENTHS.beat)), (0, 4, 8, 12)
        )

    def test_mixed_divisions_share_a_grid_of_their_lcm(self):
        meter = Meter.of((2, 2), (4, 5, 4, 4))  # a quintuplet on beat two
        self.assertEqual(meter.pulses, 80)
        grid = tuple(meter.starts(-1))
        self.assertEqual(grid[4:9], (20, 24, 28, 32, 36))
        self.assertEqual(len(grid), 17)
        self.assertEqual(meter.weights()[1], 0)  # between grid points

    def test_additive_meter_strength(self):
        self.assertEqual(Meter.of((7,)).weights(), (4, 1, 1, 3, 1, 2, 1))  # 3+4, then 3+2+2
        self.assertEqual(Meter.of((3, 2, 2)).weights(), (3, 1, 1, 2, 1, 2, 1))  # the 2s are equal

    def test_rejects_levels_that_do_not_nest(self):
        with self.assertRaises(ValueError):
            Meter(((4,), (2, 2), (1, 3)), 1)
        with self.assertRaises(ValueError):
            Meter(((4,), (3,)), 0)
        with self.assertRaises(ValueError):
            Meter.of((2, 2), (4, 4))  # one division per beat

    def test_one_gesture_per_beat(self):
        with self.assertRaises(ValueError):
            Meter.of((3,)).with_hands((CLAP, WAVE))
        self.assertEqual(Meter.of((3,)).with_hands((CLAP, 1, 2)).hands, (CLAP, 1, 2))


class BarsTest(unittest.TestCase):
    def test_bars_are_a_level_above_the_groups(self):
        meter = Meter.of((3, 2, 2), bars=2)
        self.assertEqual(meter.levels[:2], ((14,), (7, 7)))
        self.assertEqual(meter.levels[2], (3, 2, 2, 3, 2, 2))
        self.assertGreater(meter.weights()[7], meter.weights()[3])  # bar two beats a group

    def test_rejects_no_bars(self):
        with self.assertRaises(ValueError):
            Meter.of((4,), bars=0)


class GridTest(unittest.TestCase):
    def test_round_trip_on_a_shared_grid(self):
        meter = Meter.of((2, 2), (4, 5, 4, 4))
        beats = meter.starts(meter.beat)
        self.assertEqual(meter.to_grid(beats), PitchClassSet((0, 4, 9, 13), 17))
        self.assertEqual(meter.from_grid(meter.to_grid(beats)), beats)

    def test_rejects_off_grid_onsets(self):
        meter = Meter.of((2, 2), (4, 5, 4, 4))
        with self.assertRaises(ValueError):
            meter.to_grid(PitchClassSet((1,), 80))


class FeelTest(unittest.TestCase):
    def test_straight_is_the_grid(self):
        meter = Meter.of((2, 2), 2)
        self.assertEqual(meter.timing(), tuple(float(p) for p in range(8)))

    def test_triplet_swing_puts_the_off_beat_two_thirds_through(self):
        times = Meter.of((2, 2), 2).timing(2)
        self.assertAlmostEqual(times[1], 4 / 3)
        self.assertEqual(times[2], 2.0)  # beats don't move

    def test_threes_do_not_swing(self):
        times = Meter.of((3, 2, 2)).timing(2)
        self.assertEqual(times[:4], (0.0, 1.0, 2.0, 3.0))
        self.assertAlmostEqual(times[4], 3 + 4 / 3)

    def test_triplet_division_does_not_swing(self):
        meter = Meter.of((2, 2), 3)
        self.assertEqual(meter.timing(3), meter.timing())

    def test_every_pair_of_grid_points_swings_on_a_mixed_grid(self):
        meter = Meter.of((4,), (4, 5, 3, 2))  # 16ths, a five, a triplet, 8ths: 60 per beat
        times = meter.timing(2)
        self.assertEqual(times[15], 20.0)  # the second 16th of beat one, swung
        self.assertEqual(times[210], 220.0)  # the second 8th of beat four swings too
        self.assertEqual(times[140], 140.0)  # the triplet doesn't

    def test_swing_a_chosen_level(self):
        times = FOUR_FOUR_SIXTEENTHS.timing(2, level=FOUR_FOUR_SIXTEENTHS.beat)  # 8th swing
        self.assertAlmostEqual(times[2], 8 / 3)  # the off-beat 8th
        self.assertAlmostEqual(times[1], 4 / 3)  # the 16ths inside stretch with it
        self.assertAlmostEqual(times[3], 10 / 3)
        with self.assertRaises(ValueError):
            FOUR_FOUR_SIXTEENTHS.timing(2, level=-1)  # nothing below the grid

    def test_rejects_non_positive_swing(self):
        with self.assertRaises(ValueError):
            Meter.of((2, 2), 2).timing(0)


class CellsTest(unittest.TestCase):
    def test_every_way_to_fill_a_small_count(self):
        self.assertEqual([len(cells(split)) for split in (1, 2, 3, 4)], [1, 3, 7, 15])
        self.assertEqual(cells(2), [(0,), (1,), (0, 1)])

    def test_binary_and_ternary_groupings_from_five(self):
        self.assertEqual(cells(5), [(0,), (0, 2), (0, 3), (0, 1, 2, 3, 4)])  # 2+3 and 3+2
        self.assertIn((0, 3), cells(6))  # 3+3
        self.assertIn((0, 2, 4), cells(6))  # 2+2+2
        self.assertEqual(cells(7)[1:4], [(0, 2, 4), (0, 2, 5), (0, 3, 5)])

    def test_rejects_an_empty_count(self):
        with self.assertRaises(ValueError):
            cells(0)


class CompositionTest(unittest.TestCase):
    def test_fibonacci_from_short_and_long(self):
        # Hemachandra: the metres of n beats made of 1s and 2s
        self.assertEqual([count(n, (1, 2)) for n in range(1, 9)], [1, 2, 3, 5, 8, 13, 21, 34])

    def test_padovan_from_twos_and_threes(self):
        self.assertEqual(
            [count(n, (2, 3)) for n in range(2, 13)], [1, 1, 1, 2, 2, 3, 4, 5, 7, 9, 12]
        )

    def test_seven_has_three_groupings_into_twos_and_threes(self):
        self.assertEqual(list(compositions(7, (2, 3))), [(2, 2, 3), (2, 3, 2), (3, 2, 2)])

    def test_count_agrees_with_listing(self):
        for parts in [(1, 2), (2, 3), (2, 3, 4, 5), (3, 5)]:
            for total in range(16):
                with self.subTest(parts=parts, total=total):
                    self.assertEqual(count(total, parts), len(list(compositions(total, parts))))

    def test_claps_choose_the_grouping(self):
        self.assertEqual(groupings(PitchClassSet((0, 3, 5), 7)), [(3, 2, 2)])
        self.assertEqual(groupings(PitchClassSet((0,), 7)), [(2, 2, 3), (2, 3, 2), (3, 2, 2)])
        self.assertEqual(groupings(PitchClassSet((1,), 7)), [])


class RhythmAsSetTest(unittest.TestCase):
    def test_gaps_invert_from_steps(self):
        for steps in [(3, 3, 2), (2, 2, 1, 2, 2, 2, 1), (5,), (1, 4, 2)]:
            self.assertEqual(gaps(rhythm(*steps)), steps)

    def test_gaps_start_at_the_first_onset(self):
        self.assertEqual(gaps(PitchClassSet((2, 5), 8)), (3, 5))

    def test_toussaint_euclidean_rhythms(self):
        # Toussaint (2005): E(3,8) is the tresillo, E(5,8) the cinquillo, E(7,12) the bembe
        # bell, whose steps are the major scale's
        self.assertEqual(PitchClassSet.maximally_even(3, 8).necklace(), rhythm(3, 3, 2).necklace())
        self.assertEqual(
            PitchClassSet.maximally_even(5, 8).necklace(), rhythm(2, 1, 2, 1, 2).necklace()
        )
        self.assertEqual(
            PitchClassSet.maximally_even(7, 12).necklace(),
            rhythm(2, 2, 1, 2, 2, 2, 1).necklace(),
        )

    def test_unevenness_is_zero_exactly_for_maximally_even_sets(self):
        for size in range(2, 13):
            for notes in range(1, size + 1):
                even = PitchClassSet.maximally_even(notes, size).necklace()
                for members in combinations(range(size), notes):
                    onsets = PitchClassSet(members, size)
                    with self.subTest(onsets=onsets):
                        self.assertEqual(unevenness(onsets) == 0, onsets.necklace() == even)

    def test_son_clave_is_not_maximally_even(self):
        self.assertGreater(unevenness(rhythm(3, 3, 4, 2, 4)), 0)

    def test_guest_repeats_and_cuts(self):
        self.assertEqual(tuple(guest((3,), 16)), (0, 3, 6, 9, 12, 15))
        self.assertEqual(tuple(guest((3,), 16, 1)), (1, 4, 7, 10, 13))
        self.assertEqual(tuple(guest((3,), 16, 2)), (2, 5, 8, 11, 14))
        self.assertEqual(guest((3, 3, 2), 8), rhythm(3, 3, 2))
        self.assertEqual(tuple(guest((2, 1), 6, 4)), (0, 1, 3, 4))


class SyncopationTest(unittest.TestCase):
    def test_rhythms_on_the_meter_are_not_syncopated(self):
        meter = FOUR_FOUR_SIXTEENTHS
        for level in range(len(meter.levels)):
            self.assertEqual(syncopation(meter.starts(level), meter), 0, level)

    def test_tresillo(self):
        # the note on the 'and' of 2 (weight 1) leaves beat 3 (weight 3) silent
        self.assertEqual(syncopation(rhythm(3, 3, 2), Meter.of((2, 2), 2)), 2)

    def test_a_silence_stronger_than_the_note_before_it(self):
        meter = FOUR_FOUR_SIXTEENTHS
        self.assertEqual(syncopation(PitchClassSet((0, 7), 16), meter), 4 - 1)  # silent half bar
        self.assertEqual(syncopation(PitchClassSet((0, 15), 16), meter), 0)  # the next note is 1

    def test_rejects_a_mismatched_meter(self):
        with self.assertRaises(ValueError):
            syncopation(PitchClassSet((0,), 8), FOUR_FOUR_SIXTEENTHS)


class CountEdgesTest(unittest.TestCase):
    def test_count_agrees_with_compositions_for_every_total(self):
        for parts in ((1, 2), (2, 3), (3,)):
            for total in range(-4, 12):
                with self.subTest(parts=parts, total=total):
                    self.assertEqual(count(total, parts), len(list(compositions(total, parts))))

    def test_a_bar_needs_groups(self):
        for groups in ((), (3, 0)):
            with self.subTest(groups=groups), self.assertRaises(ValueError):
                Meter.of(groups)


class LevelTest(unittest.TestCase):
    def test_a_level_the_meter_has(self):
        meter = Meter.of((2, 2))
        self.assertEqual(meter.starts(-1), meter.starts(len(meter.levels) - 1))
        with self.assertRaises(ValueError):
            meter.starts(len(meter.levels))


class LongCycleTest(unittest.TestCase):
    def test_groupings_grow_with_the_answers_not_the_cycle(self):
        every_other = PitchClassSet(tuple(range(0, 64, 2)), 64)
        self.assertEqual(groupings(every_other), [(2,) * 32])  # one answer, at once

    def test_groupings_match_filtering_every_composition(self):
        for size in range(1, 13):
            for onsets in combinations(range(size), 2):
                cycle = PitchClassSet(onsets, size)
                every = [
                    option
                    for option in compositions(size, (2, 3))
                    if set(cycle) <= set(group_starts(option))
                ]
                self.assertEqual(groupings(cycle), every)

    def test_compositions_of_any_total(self):
        self.assertEqual(sum(1 for _ in compositions(1200, (1200, 1))), 2)


if __name__ == "__main__":
    unittest.main()
