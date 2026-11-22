import tempfile
import unittest
from pathlib import Path

from fixtures import SCALES

from lazy_theory.pitch.catalog import (
    LETTERS,
    TWELVE,
    accidentals,
    alteration,
    chord_names,
    load_aliases,
    load_chords,
    load_scales,
    load_symbols,
    major,
    pitch,
    pitch_class,
)
from lazy_theory.pitch.chord import identify


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

    def test_the_letters_name_the_bundled_major_scale(self):
        self.assertEqual((major().size, len(major())), (TWELVE, len(LETTERS)))

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

    def test_aliases_name_real_symbols_and_never_shadow_one(self):
        chords = 'size = 12\n[chords]\n"major" = [0, 4, 7]\n[symbols]\n"major" = ""\n'
        self.assertEqual(load_aliases(self.write_toml(chords + '[aliases]\n"M" = ""\n')), {"M": ""})
        for bad in ['"M" = "m"', '"" = ""']:
            with self.subTest(alias=bad), self.assertRaises(ValueError):
                load_aliases(self.write_toml(chords + "[aliases]\n" + bad + "\n"))

    def test_accidentals_read_back(self):
        for shift in range(-3, 4):
            self.assertEqual(alteration(accidentals(shift)), shift)
        self.assertEqual([accidentals(shift) for shift in (-2, 0, 1)], ["bb", "", "#"])


class StrictNoteTest(unittest.TestCase):
    def test_rejects_mixed_accidentals_and_lower_case(self):
        for note in ("C#b", "Cb#", "c", "e2"):
            with self.subTest(note=note), self.assertRaises(ValueError):
                pitch(note) if note[-1].isdigit() else pitch_class(note)


if __name__ == "__main__":
    unittest.main()
