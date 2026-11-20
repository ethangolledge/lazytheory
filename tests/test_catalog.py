import tempfile
import unittest
from pathlib import Path

from lazy_theory.catalog import (
    accidentals,
    alteration,
    chord_names,
    load_chords,
    load_scales,
    load_symbols,
    load_tunings,
    pitch,
    pitch_class,
)
from lazy_theory.core.chord import identify
from lazy_theory.core.temperament import EqualTemperament

SCALES = load_scales()
CHORDS = load_chords()
TUNINGS = load_tunings()


class BundledCatalogTest(unittest.TestCase):
    def test_diatonic_modes_in_order_of_brightness(self):
        # docs/theory.md section 5: each mode lowers one note of the one before.
        expected = {
            "Lydian": (0, 2, 4, 6, 7, 9, 11),
            "Ionian": (0, 2, 4, 5, 7, 9, 11),
            "Mixolydian": (0, 2, 4, 5, 7, 9, 10),
            "Dorian": (0, 2, 3, 5, 7, 9, 10),
            "Aeolian": (0, 2, 3, 5, 7, 8, 10),
            "Phrygian": (0, 1, 3, 5, 7, 8, 10),
            "Locrian": (0, 1, 3, 5, 6, 8, 10),
        }
        for name, pitch_classes in expected.items():
            self.assertEqual(SCALES[name].pitch_classes, pitch_classes, name)

    def test_minor_pentatonic_is_a_mode_of_major_pentatonic(self):
        self.assertEqual(SCALES["Major Pentatonic"].rotate(4), SCALES["Minor Pentatonic"])

    def test_every_tertian_chord_of_every_seven_note_mode_is_named_from_its_root(self):
        for scale_name, scale in SCALES.items():
            if len(scale) != 7:
                continue
            for degree in range(7):
                for notes in (3, 4):
                    with self.subTest(scale=scale_name, degree=degree, notes=notes):
                        readings = identify(scale.chord(degree, notes), chord_names())
                        self.assertIn(0, [chord.root for chord in readings])

    def test_every_pentatonic_triad_is_named_from_some_root(self):
        scale = SCALES["Major Pentatonic"]
        for degree in range(len(scale)):
            self.assertTrue(identify(scale.chord(degree), chord_names()), degree)

    def test_tunings_are_open_string_pitches(self):
        self.assertEqual(TUNINGS["guitar standard"].open_strings, (28, 33, 38, 43, 47, 52))
        self.assertEqual(TUNINGS["guitar drop D"].open_strings[0], pitch("D2"))
        self.assertEqual(TUNINGS["ukulele standard"].open_strings, (55, 48, 52, 57))  # re-entrant

    def test_tunings_know_their_frequency_and_length(self):
        guitar, bass = TUNINGS["guitar standard"], TUNINGS["bass standard"]
        e2 = guitar.hertz * EqualTemperament().ratio(guitar.open_strings[0])
        self.assertAlmostEqual(e2, 82.407, places=3)  # from A4 = 440 Hz
        self.assertEqual(bass.open_strings[0], guitar.open_strings[0] - 12)  # E1
        self.assertEqual((guitar.scale_length, bass.scale_length), (648.0, 864.0))


class NoteTest(unittest.TestCase):
    def test_pitch_classes_count_up_from_c(self):
        self.assertEqual([pitch_class(note) for note in "CDEFGAB"], [0, 2, 4, 5, 7, 9, 11])

    def test_pitches_count_up_from_c0(self):
        self.assertEqual((pitch("C0"), pitch("E2"), pitch("A4")), (0, 28, 57))

    def test_accidentals(self):
        self.assertEqual(pitch_class("F#"), pitch_class("Gb"))
        self.assertEqual(pitch_class("Bb"), 10)
        self.assertEqual(pitch_class("Fb"), pitch_class("E"))
        self.assertEqual(pitch_class("B##"), pitch_class("C#") + 12)  # an octave up; mod as needed

    def test_rejects_non_notes(self):
        for note in ("", "H", "C+", "do"):
            with self.assertRaises(ValueError, msg=note):
                pitch_class(note)


class CustomCatalogTest(unittest.TestCase):
    def write_toml(self, text: str) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "catalog.toml"
        path.write_text(text)
        return path

    def test_any_scale_with_any_name(self):
        path = self.write_toml(
            '[mine]\nsteps = [1, 3, 1, 2, 1, 3, 1]\nmodes = ["Double Harmonic"]\n'
        )
        self.assertEqual(load_scales(path)["Double Harmonic"].pitch_classes, (0, 1, 4, 5, 7, 8, 11))

    def test_microtonal_scale(self):
        path = self.write_toml('[tet31]\nsteps = [5, 5, 3, 5, 5, 5, 3]\nmodes = ["31 Major"]\n')
        self.assertEqual(load_scales(path)["31 Major"].size, 31)

    def test_rejects_duplicate_scale(self):
        path = self.write_toml(
            '[a]\nsteps = [2, 2, 1, 2, 2, 2, 1]\nmodes = ["Ionian"]\n'
            '[b]\nsteps = [2, 2, 1, 2, 2, 2, 1]\nmodes = ["Major"]\n'
        )
        with self.assertRaises(ValueError):
            load_scales(path)

    def test_rejects_more_mode_names_than_notes(self):
        path = self.write_toml('[a]\nsteps = [6, 6]\nmodes = ["A", "B", "C"]\n')
        with self.assertRaises(ValueError):
            load_scales(path)

    def test_tuning_needs_an_octave(self):
        path = self.write_toml(
            'reference = { note = "A4", hertz = 440.0 }\n'
            '[lute]\nscale_length = 600.0\ntunings.old = { first = "G", gaps = [5] }\n'
        )
        with self.assertRaises(ValueError):
            load_tunings(path)

    def test_rejects_duplicate_chord(self):
        path = self.write_toml('size = 12\n[chords]\n"major" = [0, 4, 7]\n"big" = [0, 7, 4]\n')
        with self.assertRaises(ValueError):
            load_chords(path)

    def test_every_chord_needs_a_symbol(self):
        path = self.write_toml(
            'size = 12\n[chords]\n"major" = [0, 4, 7]\n"minor" = [0, 3, 7]\n'
            '[symbols]\n"major" = ""\n'
        )
        with self.assertRaises(ValueError):
            load_symbols(path)

    def test_accidentals_read_back(self):
        for shift in range(-3, 4):
            self.assertEqual(alteration(accidentals(shift)), shift)
        self.assertEqual([accidentals(shift) for shift in (-2, 0, 1)], ["bb", "", "#"])


if __name__ == "__main__":
    unittest.main()
