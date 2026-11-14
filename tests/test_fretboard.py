import unittest

import numpy as np

from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.core.scale import Scale
from lazy_theory.instruments.fretboard import MUTED, Fretboard, by_movement

STANDARD = Fretboard.from_gaps((5, 5, 5, 4, 5))
DROP_D = Fretboard.from_gaps((7, 5, 5, 4, 5))
PHRYGIAN = Scale.from_steps((1, 2, 2, 2, 1, 2, 2))
MAJOR = PitchClassSet((0, 4, 7))
C = 8  # steps above standard tuning's low E
E = 0


def contains_row(grid: np.ndarray, row: list[int]) -> bool:
    return bool((grid == row).all(axis=1).any())


class FretboardTest(unittest.TestCase):
    def test_open_strings_from_gaps(self):
        self.assertEqual(STANDARD.open_strings.tolist(), [0, 5, 10, 15, 19, 24])

    def test_open_strings_are_read_only(self):
        with self.assertRaises(ValueError):
            STANDARD.open_strings[0] = 1

    def test_pitch_grid(self):
        self.assertEqual(STANDARD.pitches.shape, (6, 25))
        self.assertEqual(STANDARD.pitches[0, 5], STANDARD.pitches[1, 0])  # 5th fret = next string
        self.assertEqual(STANDARD.pitches[0, 12], 12)

    def test_intervals_from_any_root(self):
        self.assertEqual(STANDARD.intervals(root=5)[1, 0], 0)
        self.assertEqual(STANDARD.intervals(root=5)[0, 0], 7)

    def test_scale_positions(self):
        positions = STANDARD.positions(PHRYGIAN, E)
        self.assertEqual(positions[0, :4].tolist(), [True, True, False, True])

    def test_retuning_a_string_shifts_only_that_string(self):
        # Drop D measures from D, two steps below E, so the same key's root is 2.
        standard, drop_d = STANDARD.positions(PHRYGIAN, E), DROP_D.positions(PHRYGIAN, 2)
        np.testing.assert_array_equal(drop_d[0, 2:], standard[0, :-2])
        np.testing.assert_array_equal(drop_d[1:], standard[1:])

    def test_re_entrant_tuning(self):
        ukulele = Fretboard.from_gaps((-7, 4, 5), frets=12)
        self.assertEqual(ukulele.open_strings.tolist(), [0, -7, -3, 2])

    def test_other_temperaments(self):
        fretboard_31 = Fretboard.from_gaps((13, 13, 13, 10, 13), size=31)
        self.assertTrue(fretboard_31.positions(PitchClassSet((0, 10, 18), 31), 0)[0, 0])
        with self.assertRaises(ValueError):
            fretboard_31.positions(MAJOR, 0)


class VoicingsTest(unittest.TestCase):
    def test_familiar_shapes_are_found(self):
        self.assertTrue(contains_row(STANDARD.voicings(MAJOR, C), [MUTED, 3, 2, 0, 1, 0]))
        self.assertTrue(contains_row(STANDARD.voicings(MAJOR, E), [0, 2, 2, 1, 0, 0]))

    def test_every_voicing_sounds_every_tone_and_only_chord_tones(self):
        voicings = STANDARD.voicings(MAJOR, C)
        for frets in voicings:
            sounding = frets != MUTED
            tones = set(((STANDARD.open_strings + frets - C) % 12)[sounding].tolist())
            self.assertEqual(tones, set(MAJOR))

    def test_fretted_notes_stay_within_span(self):
        voicings = STANDARD.voicings(MAJOR, C, max_span=3)
        fretted = np.where(voicings > 0, voicings, np.nan)
        spans = np.nanmax(fretted, axis=1) - np.nanmin(fretted, axis=1)
        self.assertLessEqual(np.nanmax(spans), 3)

    def test_no_duplicates(self):
        voicings = STANDARD.voicings(MAJOR, C)
        self.assertEqual(len(np.unique(voicings, axis=0)), len(voicings))

    def test_moving_a_shape_up_one_fret_moves_the_chord_up_one_step(self):
        here, up_one = STANDARD.voicings(MAJOR, C), STANDARD.voicings(MAJOR, C + 1)
        movable = here[(here != 0).all(axis=1) & (here < STANDARD.frets).all(axis=1)]
        shifted = np.where(movable == MUTED, MUTED, movable + 1)
        for frets in shifted:
            self.assertTrue(contains_row(up_one, frets.tolist()))


class ByMovementTest(unittest.TestCase):
    def test_orders_by_strings_changed_then_frets_moved(self):
        current = np.array([0, 2, 2, 1, 0, 0])
        candidates = np.array(
            [
                [MUTED, 2, 2, 1, 0, 0],  # one string stops
                [1, 3, 3, 2, 1, 1],  # every string moves one fret
                [0, 2, 2, 1, 0, 0],  # no change
            ]
        )
        self.assertEqual(by_movement(current, candidates)[:, 0].tolist(), [0, 1, MUTED])

    def test_dominant_resolves_by_single_steps(self):
        g_seventh = np.array([3, 2, 0, 0, 0, 1])
        best = by_movement(g_seventh, STANDARD.voicings(MAJOR, C))[0]
        self.assertEqual((best - g_seventh).tolist(), [0, 1, 2, 0, 1, -1])


if __name__ == "__main__":
    unittest.main()
