import unittest

import numpy as np

from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.instruments.arrays import MUTED
from lazy_theory.instruments.catalog import load_tunings
from lazy_theory.instruments.fretboard import Fretboard
from lazy_theory.instruments.taste import Taste
from lazy_theory.pitch.catalog import load_scales
from lazy_theory.pitch.chord import Chord
from lazy_theory.pitch.key import Key
from lazy_theory.suggest.harmonise import MelodicTaste, contrary, harmonise, parallels

X = MUTED
STANDARD = Fretboard.from_tuning(load_tunings()["guitar standard"])
MINOR = PitchClassSet((0, 3, 7))
E, F, A = 4, 5, 9  # pitch classes
E_PHRYGIAN = Key(load_scales()["Phrygian"], E).chords()


def rows(*voicings: list[int]) -> np.ndarray:
    return np.array(voicings, dtype=np.int16)


class VoiceMotionTest(unittest.TestCase):
    def test_parallel_fifths_and_octaves(self):
        c5, d5 = rows([X, 3, 5, X, X, X]), rows([X, 5, 7, X, X, X])
        c_octave, d_octave = rows([X, 3, 5, 5, X, X]), rows([X, 5, 7, 7, X, X])
        self.assertEqual(parallels(STANDARD, c5, d5).tolist(), [[1]])
        self.assertEqual(parallels(STANDARD, c_octave, d_octave).tolist(), [[2]])  # 5th + 8ve

    def test_moving_to_another_interval_is_not_parallel(self):
        self.assertEqual(
            parallels(STANDARD, rows([X, 3, 5, X, X, X]), rows([X, 5, 4, X, X, X])).tolist(), [[0]]
        )

    def test_contrary_motion(self):
        c, g, d = rows([X, 3, 2, 0, 1, 0]), rows([3, 2, 0, 0, 0, 3]), rows([X, X, 0, 2, 3, 2])
        self.assertEqual(contrary(STANDARD, c, np.concatenate([g, d])).tolist(), [[1, 0]])


class MelodicTasteTest(unittest.TestCase):
    def test_is_a_taste(self):
        self.assertIsInstance(MelodicTaste(), Taste)

    def test_without_its_weights_it_is_the_plain_taste(self):
        before, after = rows([X, 3, 5, X, X, X]), rows([X, 5, 7, X, X, X], [X, 5, 4, X, X, X])
        plain = Taste().transition(STANDARD, before, after)
        silent = MelodicTaste(parallels=0.0, contrary=0.0).transition(STANDARD, before, after)
        np.testing.assert_array_equal(silent, plain)

    def test_penalises_parallels(self):
        before, after = rows([X, 3, 5, X, X, X]), rows([X, 5, 7, X, X, X])
        plain = Taste().transition(STANDARD, before, after)
        self.assertEqual(MelodicTaste().transition(STANDARD, before, after) - plain, [[5.0]])


class HarmoniseTest(unittest.TestCase):
    def test_melody_on_top_and_fixed_chords_kept(self):
        melody = [E, F, E]  # the Phrygian half step on top
        slots = [[Chord(MINOR, E)], E_PHRYGIAN, [Chord(MINOR, A)]]
        harmony = harmonise(STANDARD, melody, slots, MelodicTaste())
        tops = STANDARD.top(harmony.path) % 12
        self.assertEqual(tops.tolist(), melody)
        self.assertEqual((harmony.chords[0], harmony.chords[-1]), (0, 0))

    def test_a_free_melody_is_the_plain_path(self):
        chords, taste = [Chord(MINOR, E), Chord(MINOR, A)], Taste()
        harmony = harmonise(STANDARD, [None, None], [[chord] for chord in chords], taste)
        path, cost, *_ = taste.path(STANDARD, chords)
        np.testing.assert_array_equal(harmony.path, path)
        self.assertEqual(harmony.cost, cost)

    def test_a_note_outside_every_allowed_chord(self):
        with self.assertRaises(ValueError):
            harmonise(STANDARD, [F], [[Chord(MINOR, E)]], Taste())


if __name__ == "__main__":
    unittest.main()
