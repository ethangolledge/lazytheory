import unittest

import numpy as np

from lazy_theory.catalog import load_tunings
from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.core.scale import Scale
from lazy_theory.core.temperament import EqualTemperament
from lazy_theory.instruments.fretboard import MUTED, Fretboard

X = MUTED
TUNINGS = load_tunings()
STANDARD = Fretboard.from_tuning(TUNINGS["guitar standard"])
DROP_D = Fretboard.from_tuning(TUNINGS["guitar drop D"])
UKULELE = Fretboard.from_tuning(TUNINGS["ukulele standard"], frets=12)
REACH = STANDARD.fret_distance[4] - STANDARD.fret_distance[1]  # one finger per fret, frets 1-4
PHRYGIAN = Scale.from_steps((1, 2, 2, 2, 1, 2, 2))
MAJOR = PitchClassSet((0, 4, 7))
C = 8  # steps above standard tuning's low E
E = 0


def rows(*voicings: list[int]) -> np.ndarray:
    return np.array(voicings, dtype=np.int16)


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
        self.assertEqual(UKULELE.open_strings.tolist(), [0, -7, -3, 2])

    def test_other_temperaments(self):
        tet31 = Fretboard((0, 13, 26, 39, 49, 62), 648.0, 82.41, temperament=EqualTemperament(31))
        self.assertTrue(tet31.positions(PitchClassSet((0, 10, 18), 31), 0)[0, 0])
        with self.assertRaises(ValueError):
            tet31.positions(MAJOR, 0)


class PhysicsTest(unittest.TestCase):
    def test_octave_fret_halves_the_string(self):
        self.assertAlmostEqual(STANDARD.fret_distance[12], 648.0 / 2)
        tet31 = Fretboard((0,), 648.0, 82.41, frets=31, temperament=EqualTemperament(31))
        self.assertAlmostEqual(tet31.fret_distance[31], 648.0 / 2)

    def test_frets_get_closer_up_the_neck(self):
        self.assertTrue((np.diff(STANDARD.fret_distance, n=2) < 0).all())

    def test_frequencies(self):
        open_strings = STANDARD.frequencies(rows([0, 0, 0, 0, 0, 0]))[0]
        self.assertAlmostEqual(open_strings[0], 82.41, places=2)  # E2
        self.assertAlmostEqual(open_strings[1], 110.0)  # A2
        self.assertTrue(np.isnan(STANDARD.frequencies(rows([X, 0, 0, 0, 0, 0]))[0, 0]))

    def test_hand_sits_at_the_lowest_fretted_note(self):
        hand = STANDARD.hand(rows([X, 3, 2, 0, 1, 0], [0, 0, 0, 0, 0, 0]))
        self.assertAlmostEqual(hand[0], STANDARD.fret_distance[1])
        self.assertTrue(np.isnan(hand[1]))


class VoicingsTest(unittest.TestCase):
    def test_familiar_shapes_are_found(self):
        self.assertTrue(contains_row(STANDARD.voicings(MAJOR, C, REACH), [X, 3, 2, 0, 1, 0]))
        self.assertTrue(contains_row(STANDARD.voicings(MAJOR, E, REACH), [0, 2, 2, 1, 0, 0]))

    def test_every_voicing_sounds_every_tone_and_only_chord_tones(self):
        voicings = STANDARD.voicings(MAJOR, C, REACH)
        for frets in voicings:
            sounding = frets != MUTED
            tones = set(((STANDARD.open_strings + frets - C) % 12)[sounding].tolist())
            self.assertEqual(tones, set(MAJOR))

    def test_fretted_notes_stay_within_reach(self):
        voicings = STANDARD.voicings(MAJOR, C, REACH)
        fretted = np.where(voicings > 0, STANDARD.fret_distance[voicings], np.nan)
        spans = np.nanmax(fretted, axis=1) - np.nanmin(fretted, axis=1)
        self.assertLessEqual(np.nanmax(spans), REACH)

    def test_the_same_reach_spans_more_frets_up_the_neck(self):
        voicings = STANDARD.voicings(MAJOR, C, REACH)
        fretted = np.where(voicings > 0, voicings, np.nan)
        lowest = np.nanmin(fretted, axis=1)
        spans = np.nanmax(fretted, axis=1) - lowest
        self.assertLessEqual(np.nanmax(spans[lowest <= 3]), 3)
        self.assertGreater(np.nanmax(spans[lowest >= 12]), 4)

    def test_no_duplicates(self):
        voicings = STANDARD.voicings(MAJOR, C, REACH)
        self.assertEqual(len(np.unique(voicings, axis=0)), len(voicings))

    def test_every_inversion_on_every_set_of_adjacent_strings(self):
        # Triads on 3 strings, seventh chords on 4: every chord tone in the bass on every set.
        for chord in (MAJOR, PitchClassSet((0, 4, 7, 11))):
            voicings = STANDARD.voicings(chord, C, REACH)
            notes = len(chord)
            for first in range(7 - notes):
                strings = (np.arange(6) >= first) & (np.arange(6) < first + notes)
                on_set = voicings[((voicings != MUTED) == strings).all(axis=1)]
                inversions = set(STANDARD.stack(on_set, C)[:, 0].tolist())
                self.assertEqual(inversions, set(chord), (chord, first))


class StackTest(unittest.TestCase):
    def test_bass_names_the_inversion(self):
        voicings = rows([X, 3, 2, 0, 1, 0], [0, 3, 2, 0, 1, 0], [3, 3, 2, 0, 1, 0])
        self.assertEqual(STANDARD.stack(voicings, C)[:, 0].tolist(), [0, 4, 7])

    def test_lowest_pitch_first_then_muted(self):
        stack = STANDARD.stack(rows([X, 3, 2, 0, 1, 0]), C)
        self.assertEqual(stack[0].tolist(), [0, 4, 7, 0, 4, X])

    def test_sorted_by_pitch_not_string(self):
        c_major = rows([0, 0, 0, 3])  # G4 C4 E4 C5 on a re-entrant ukulele
        self.assertEqual(UKULELE.stack(c_major, root=-7)[0].tolist(), [0, 4, 7, 0])


if __name__ == "__main__":
    unittest.main()
