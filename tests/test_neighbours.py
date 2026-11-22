import unittest

import numpy as np
from fixtures import CHORDS, STANDARD, X

from lazy_theory.instruments.taste import Taste
from lazy_theory.pitch.catalog import chord_names, load_scales
from lazy_theory.pitch.chord import Chord
from lazy_theory.pitch.key import Key
from lazy_theory.pitch.scale import Scale
from lazy_theory.suggest.drones import drones
from lazy_theory.suggest.neighbours import named, one_finger, passing

OPEN = Taste(highest=4, sounding=1.0)
C, A, F, G = 0, 9, 5, 7


def row(*frets: int) -> np.ndarray:
    return np.array(frets, dtype=np.int16)


class NamedTest(unittest.TestCase):
    def test_reads_the_chord_on_its_bass(self):
        # C E G A is C6 or Am7: the A in the bass makes it Am7; C/E is C with its bass written
        shapes = np.stack([row(X, 3, 2, 0, 1, 0), row(X, 0, 2, 0, 1, 0), row(0, 3, 2, 0, 1, 0)])
        c, a_minor_7, c_over_e = named(STANDARD, shapes, chord_names())
        self.assertEqual(c, Chord(CHORDS["major"], C))
        self.assertEqual(a_minor_7, Chord(CHORDS["minor 7th"], A))
        self.assertEqual(c_over_e, Chord(CHORDS["major"], C, bass=4))

    def test_without_a_reading_on_the_bass_the_key_decides(self):
        # F A B D over F: Bm7b5 or Dm6, neither on F; in D Dorian, D is the steadier root
        d_dorian = Key(load_scales()["Dorian"], 2)
        (chord,) = named(STANDARD, row(1, 2, 0, 2, 3, X)[None], chord_names(), d_dorian)
        self.assertEqual(chord, Chord(CHORDS["minor 6th"], 2, bass=F))

    def test_none_without_a_pattern(self):
        shapes = np.stack([row(X, X, X, X, 1, 0), row(*[X] * 6)])  # a bare third; silence
        self.assertEqual(named(STANDARD, shapes, chord_names()), [None, None])


class OneFingerTest(unittest.TestCase):
    def test_from_open_c(self):
        found = one_finger(STANDARD, OPEN, row(X, 3, 2, 0, 1, 0), chord_names())
        shapes = [one.frets.tolist() for one in found]
        self.assertIn([X, 3, 2, 0, 0, 0], shapes)  # Cmaj7: the B string lifts
        self.assertIn([X, 0, 2, 0, 1, 0], shapes)  # Am7: the bass moves to the open A
        for one in found:  # one string differs, it still sounds, and the chord is new
            changed = one.frets != row(X, 3, 2, 0, 1, 0)
            self.assertEqual(changed.sum(), 1)
            self.assertNotEqual(one.frets[changed][0], X)
            new = (one.chord.pitch_classes, STANDARD.bass(one.frets[None])[0] % 12)
            self.assertNotEqual(new, (Chord(CHORDS["major"], C).pitch_classes, C))
        self.assertEqual([one.steps for one in found], sorted(one.steps for one in found))

    def test_line_cliche_from_a_minor(self):
        shapes = [
            one.frets.tolist()
            for one in one_finger(STANDARD, OPEN, row(X, 0, 2, 2, 1, 0), chord_names())
        ]
        self.assertIn([X, 0, 2, 1, 1, 0], shapes)  # Am(maj7): the A falls a semitone


class PassingTest(unittest.TestCase):
    def test_c_to_a_minor(self):
        found = passing(STANDARD, OPEN, row(X, 3, 2, 0, 1, 0), row(X, 0, 2, 2, 1, 0), chord_names())
        shapes = [one.frets.tolist() for one in found]
        self.assertIn([X, 0, 2, 0, 1, 0], shapes)  # bass moves first: Am7
        self.assertIn([X, 3, 2, 2, 1, 0], shapes)  # G moves first: Am/C
        for one in found:  # every string is where it was or where it goes
            self.assertTrue(
                ((one.frets == row(X, 3, 2, 0, 1, 0)) | (one.frets == row(X, 0, 2, 2, 1, 0))).all()
            )

    def test_nothing_between_neighbours(self):
        self.assertEqual(
            passing(STANDARD, OPEN, row(X, 3, 2, 0, 1, 0), row(X, 3, 2, 0, 0, 0), chord_names()), []
        )


class DronesTest(unittest.TestCase):
    def test_each_drone_holds_its_note_through_its_chords(self):
        chords = [Chord(CHORDS["major"], G), Chord(CHORDS["major"], C), Chord(CHORDS["major"], 2)]
        found = drones(STANDARD, OPEN, chords, notes=range(12))
        self.assertTrue(found)
        for drone in found:
            for string, fret in zip(drone.strings, drone.frets, strict=True):
                held = drone.path[drone.first : drone.last + 1, string]
                self.assertTrue((held == fret).all(), drone)
            self.assertGreaterEqual(drone.last - drone.first, 1)
            self.assertLessEqual(drone.extra, OPEN.strings_changed + 1e-9)
            self.assertGreaterEqual(drone.extra, -1e-9)  # holding never makes a route cheaper
        lengths = [d.last - d.first for d in found]
        self.assertEqual(lengths, sorted(lengths, reverse=True))

    def test_a_held_note_joins_the_chords_it_is_not_in(self):
        chords = [Chord(CHORDS["major"], G), Chord(CHORDS["major"], C), Chord(CHORDS["major"], 2)]
        for drone in drones(STANDARD, OPEN, chords, notes=range(12)):
            for string, fret in zip(drone.strings, drone.frets, strict=True):
                pitch_class = (int(STANDARD.open_strings[string]) + fret) % 12
                for chord in drone.chords[drone.first : drone.last + 1]:
                    self.assertIn(pitch_class, chord)

    def test_one_entry_per_route(self):
        chords = [Chord(CHORDS["major"], G), Chord(CHORDS["major"], C), Chord(CHORDS["major"], 2)]
        found = drones(STANDARD, OPEN, chords, notes=range(12))
        routes = [(d.path.tobytes(), d.first, d.last) for d in found]
        self.assertEqual(len(routes), len(set(routes)))


class KeySizeTest(unittest.TestCase):
    def test_a_key_of_another_size_is_refused(self):
        nineteen = Key(Scale.from_steps((3, 3, 2, 3, 3, 3, 2)), 0)
        with self.assertRaises(ValueError):
            named(STANDARD, row(X, 3, 2, 0, 1, 0)[None], chord_names(), nineteen)


if __name__ == "__main__":
    unittest.main()
