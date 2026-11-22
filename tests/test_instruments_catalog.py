import tempfile
import unittest
from pathlib import Path

from fixtures import TUNINGS

from lazy_theory.core.temperament import EqualTemperament
from lazy_theory.instruments.catalog import load_tunings
from lazy_theory.instruments.fretboard import Fretboard
from lazy_theory.pitch.catalog import (
    pitch,
)


class TuningCatalogTest(unittest.TestCase):
    def write_toml(self, text: str) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "catalog.toml"
        path.write_text(text)
        return path

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

    def test_tuning_needs_an_octave(self):
        path = self.write_toml(
            'reference = { note = "A4", hertz = 440.0 }\n'
            '[lute]\nscale_length = 600.0\ntunings.old = { first = "G", gaps = [5] }\n'
        )
        with self.assertRaises(ValueError):
            load_tunings(path)

    def test_another_temperament_from_data(self):
        reference = 'reference = { note = "A4", hertz = 440.0 }\n'
        path = self.write_toml(
            reference + "[guitar19]\nscale_length = 648.0\nsteps = 19\n"
            "tunings.fourths = { first = 44, gaps = [8, 8] }\n"
        )
        tuning = load_tunings(path)["guitar19 fourths"]
        self.assertEqual(
            (tuning.open_strings, tuning.temperament), ((44, 52, 60), EqualTemperament(19))
        )
        self.assertEqual(Fretboard.from_tuning(tuning).size, 19)
        self.assertEqual(TUNINGS["guitar standard"].hertz, tuning.hertz)  # C0 is C0 in any
        named = self.write_toml(
            reference + "[guitar19]\nscale_length = 648.0\nsteps = 19\n"
            'tunings.fourths = { first = "E2", gaps = [8, 8] }\n'
        )
        with self.assertRaises(ValueError):  # note names are for twelve steps
            load_tunings(named)


if __name__ == "__main__":
    unittest.main()
