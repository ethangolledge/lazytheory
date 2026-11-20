import unittest

import numpy as np

from lazy_theory.catalog import load_tunings
from lazy_theory.core.chord import Chord
from lazy_theory.core.key import Key
from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.core.scale import Scale
from lazy_theory.core.temperament import EqualTemperament
from lazy_theory.instruments.arrays import MUTED
from lazy_theory.instruments.fretboard import Fretboard

X = MUTED
TUNINGS = load_tunings()
STANDARD = Fretboard.from_tuning(TUNINGS["guitar standard"])
DROP_D = Fretboard.from_tuning(TUNINGS["guitar drop D"])
UKULELE = Fretboard.from_tuning(TUNINGS["ukulele standard"], frets=12)
REACH = STANDARD.fret_distance[4] - STANDARD.fret_distance[1]  # one finger per fret, frets 1-4
PHRYGIAN = Scale.from_steps((1, 2, 2, 2, 1, 2, 2))
MAJOR = PitchClassSet((0, 4, 7))
C, E = 0, 4  # pitch classes


def rows(*voicings: list[int]) -> np.ndarray:
    return np.array(voicings, dtype=np.int16)


def contains_row(grid: np.ndarray, row: list[int]) -> bool:
    return bool((grid == row).all(axis=1).any())


class FretboardTest(unittest.TestCase):
    def test_open_strings_from_gaps(self):
        self.assertEqual(
            STANDARD.open_strings.tolist(), [28, 33, 38, 43, 47, 52]
        )  # E2 A2 D3 G3 B3 E4

    def test_open_strings_are_read_only(self):
        with self.assertRaises(ValueError):
            STANDARD.open_strings[0] = 1

    def test_pitch_grid(self):
        self.assertEqual(STANDARD.pitches.shape, (6, 25))
        self.assertEqual(STANDARD.pitches[0, 5], STANDARD.pitches[1, 0])  # 5th fret = next string
        self.assertEqual(STANDARD.pitches[0, 12], 40)  # E3

    def test_intervals_from_any_root(self):
        self.assertEqual(STANDARD.intervals(root=9)[1, 0], 0)  # A is the root
        self.assertEqual(STANDARD.intervals(root=9)[0, 0], 7)  # E is its fifth

    def test_scale_positions(self):
        positions = STANDARD.positions(Key(PHRYGIAN, E))
        self.assertEqual(positions[0, :4].tolist(), [True, True, False, True])

    def test_retuning_a_string_shifts_only_that_string(self):
        # The same key has the same root on any neck; only the dropped string's frets move.
        standard, drop_d = (
            STANDARD.positions(Key(PHRYGIAN, E)),
            DROP_D.positions(Key(PHRYGIAN, E)),
        )
        np.testing.assert_array_equal(drop_d[0, 2:], standard[0, :-2])
        np.testing.assert_array_equal(drop_d[1:], standard[1:])

    def test_re_entrant_tuning(self):
        self.assertEqual(UKULELE.open_strings.tolist(), [55, 48, 52, 57])  # G4 C4 E4 A4

    def test_other_temperaments(self):
        tet31 = Fretboard((0, 13, 26, 39, 49, 62), 648.0, 82.41, temperament=EqualTemperament(31))
        self.assertTrue(tet31.positions(Chord(PitchClassSet((0, 10, 18), 31), 0))[0, 0])
        with self.assertRaises(ValueError):
            tet31.positions(Chord(MAJOR, 0))


class ChromaTest(unittest.TestCase):
    def test_pitch_classes_each_voicing_sounds(self):
        chroma = STANDARD.chroma(rows([X, 3, 2, 0, 1, 0], [X, X, X, X, X, X]))
        self.assertEqual(np.flatnonzero(chroma[0]).tolist(), [0, 4, 7])  # C E G
        self.assertFalse(chroma[1].any())


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

    def test_familiar_shapes_are_found(self):
        self.assertTrue(contains_row(STANDARD.voicings(Chord(MAJOR, C), REACH), [X, 3, 2, 0, 1, 0]))
        self.assertTrue(contains_row(STANDARD.voicings(Chord(MAJOR, E), REACH), [0, 2, 2, 1, 0, 0]))

    def test_every_voicing_sounds_every_tone_and_only_chord_tones(self):
        voicings = STANDARD.voicings(Chord(MAJOR, C), REACH)
        for frets in voicings:
            sounding = frets != MUTED
            tones = set(((STANDARD.open_strings + frets - C) % 12)[sounding].tolist())
            self.assertEqual(tones, set(MAJOR))

    def test_fretted_notes_stay_within_reach(self):
        voicings = STANDARD.voicings(Chord(MAJOR, C), REACH)
        fretted = np.where(voicings > 0, STANDARD.fret_distance[voicings], np.nan)
        spans = np.nanmax(fretted, axis=1) - np.nanmin(fretted, axis=1)
        self.assertLessEqual(np.nanmax(spans), REACH)

    def test_the_same_reach_spans_more_frets_up_the_neck(self):
        voicings = STANDARD.voicings(Chord(MAJOR, C), REACH)
        fretted = np.where(voicings > 0, voicings, np.nan)
        lowest = np.nanmin(fretted, axis=1)
        spans = np.nanmax(fretted, axis=1) - lowest
        self.assertLessEqual(np.nanmax(spans[lowest <= 3]), 3)
        self.assertGreater(np.nanmax(spans[lowest >= 12]), 4)

    def test_no_duplicates(self):
        voicings = STANDARD.voicings(Chord(MAJOR, C), REACH)
        self.assertEqual(len(np.unique(voicings, axis=0)), len(voicings))

    def test_every_inversion_on_every_set_of_adjacent_strings(self):
        # Triads on 3 strings, seventh chords on 4: every chord tone in the bass on every set.
        for chord in (MAJOR, PitchClassSet((0, 4, 7, 11))):
            voicings = STANDARD.voicings(Chord(chord, C), REACH)
            notes = len(chord)
            for first in range(7 - notes):
                strings = (np.arange(6) >= first) & (np.arange(6) < first + notes)
                on_set = voicings[((voicings != MUTED) == strings).all(axis=1)]
                inversions = set(STANDARD.stack(on_set, C)[:, 0].tolist())
                self.assertEqual(inversions, set(chord), (chord, first))


class CapoTest(unittest.TestCase):
    CAPO_2 = STANDARD.capo(2)

    def test_open_strings_sound_higher(self):
        self.assertEqual(self.CAPO_2.open_strings.tolist(), [30, 35, 40, 45, 49, 54])  # F#2 .. F#4
        self.assertEqual(self.CAPO_2.frets, 22)

    def test_capo_is_a_movable_nut(self):
        # Fret k above the capo sits where fret 2 + k was, measured from the capo.
        np.testing.assert_allclose(
            self.CAPO_2.fret_distance, STANDARD.fret_distance[2:] - STANDARD.fret_distance[2]
        )
        np.testing.assert_allclose(
            self.CAPO_2.frequencies(rows([0, 0, 0, 0, 0, 0], [3, X, X, X, X, 1])),
            STANDARD.frequencies(rows([2, 2, 2, 2, 2, 2], [5, X, X, X, X, 3])),
        )

    def test_open_shapes_move_with_the_capo(self):
        # The open E shape with a capo at 2 is F# major.
        self.assertTrue(
            contains_row(self.CAPO_2.voicings(Chord(MAJOR, E + 2), REACH), [0, 2, 2, 1, 0, 0])
        )

    def test_capo_must_be_on_the_neck(self):
        for fret in (-1, 24):
            with self.assertRaises(ValueError):
                STANDARD.capo(fret)


class ReadingsTest(unittest.TestCase):
    PATTERNS = {MAJOR, PitchClassSet((0, 3, 7, 10)), PitchClassSet((0, 4, 7, 9))}

    def test_every_reading_with_the_bass_written(self):
        # C E G A over A: A minor 7th on its root, or C major 6th over A
        (found,) = STANDARD.readings(rows([X, 0, 2, 0, 1, 0]), self.PATTERNS)
        a, c = 9, 0
        self.assertEqual(
            found,
            [Chord(PitchClassSet((0, 4, 7, 9)), c, bass=a), Chord(PitchClassSet((0, 3, 7, 10)), a)],
        )

    def test_reads_back_what_voicings_builds(self):
        shapes = STANDARD.voicings(Chord(MAJOR, C, bass=E), REACH)[:50]
        for found in STANDARD.readings(shapes, self.PATTERNS):
            self.assertIn(Chord(MAJOR, C, bass=E), found)

    def test_nothing_to_read(self):
        silent_and_unknown = rows([X] * 6, [X, X, X, X, 1, 0])
        self.assertEqual(STANDARD.readings(silent_and_unknown, self.PATTERNS), [[], []])


class StackTest(unittest.TestCase):
    def test_bass_names_the_inversion(self):
        voicings = rows([X, 3, 2, 0, 1, 0], [0, 3, 2, 0, 1, 0], [3, 3, 2, 0, 1, 0])
        self.assertEqual(STANDARD.stack(voicings, C)[:, 0].tolist(), [0, 4, 7])

    def test_top_is_the_highest_pitch(self):
        # C major: E4 (52 steps above C0) on top; nothing sounds in the second.
        np.testing.assert_array_equal(STANDARD.top(rows([X, 3, 2, 0, 1, 0], [X] * 6)), [52, np.nan])

    def test_lowest_pitch_first_then_muted(self):
        stack = STANDARD.stack(rows([X, 3, 2, 0, 1, 0]), C)
        self.assertEqual(stack[0].tolist(), [0, 4, 7, 0, 4, X])

    def test_sorted_by_pitch_not_string(self):
        c_major = rows([0, 0, 0, 3])  # G4 C4 E4 C5 on a re-entrant ukulele
        self.assertEqual(UKULELE.stack(c_major, root=C)[0].tolist(), [0, 4, 7, 0])


if __name__ == "__main__":
    unittest.main()
