import tempfile
import unittest
from pathlib import Path

from lazy_theory.data import add, read
from lazy_theory.pitch.catalog import load_scales


class ReadTest(unittest.TestCase):
    def test_the_shared_data_cannot_be_changed(self):
        data = read("lazy_theory.pitch.catalog", "chords.toml")
        with self.assertRaises(TypeError):
            data["chords"]["major"] = [0]  # type: ignore[index]
        self.assertIsInstance(data["chords"]["major"], tuple)
        self.assertIs(read("lazy_theory.pitch.catalog", "chords.toml"), data)  # parsed once

    def test_your_own_file_is_read_again_after_an_edit(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "scales.toml"
        path.write_text('[a]\nsteps = [6, 6]\nmodes = ["Tritone"]\n')
        self.assertEqual(list(load_scales(path)), ["Tritone"])
        path.write_text('[a]\nsteps = [4, 4, 4]\nmodes = ["Augmented"]\n')
        self.assertEqual(list(load_scales(path)), ["Augmented"])
        self.assertIs(load_scales(), load_scales())  # the bundled file, loaded once


class AddTest(unittest.TestCase):
    def test_rejects_a_repeated_name_or_value(self):
        named = {"one": 1}
        add(named, "two", 2)
        for name, value in (("one", 3), ("uno", 1)):
            with self.subTest(name=name), self.assertRaises(ValueError):
                add(named, name, value)
        self.assertEqual(named, {"one": 1, "two": 2})


if __name__ == "__main__":
    unittest.main()
