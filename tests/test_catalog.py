import tempfile
import unittest
from pathlib import Path

from lazy_theory.catalog import load_chords, load_scales, load_tunings
from lazy_theory.core.chord import identify

SCALES = load_scales()
CHORDS = load_chords()


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
                        matches = identify(scale.chord(degree, notes), CHORDS)
                        self.assertIn(0, [match.root for match in matches])

    def test_every_pentatonic_triad_is_named_from_some_root(self):
        scale = SCALES["Major Pentatonic"]
        for degree in range(len(scale)):
            self.assertTrue(identify(scale.chord(degree), CHORDS), degree)

    def test_tunings_are_gaps_between_strings(self):
        tunings = load_tunings()
        self.assertEqual(tunings["guitar standard"], (5, 5, 5, 4, 5))
        self.assertEqual(sum(tunings["guitar standard"]), 24)  # two octaves, low E to high E


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


if __name__ == "__main__":
    unittest.main()
