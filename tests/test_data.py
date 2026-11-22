import unittest

from lazy_theory.data import read


class ReadTest(unittest.TestCase):
    def test_the_shared_data_cannot_be_changed(self):
        data = read("lazy_theory.pitch.catalog", "chords.toml")
        with self.assertRaises(TypeError):
            data["chords"]["major"] = [0]  # type: ignore[index]
        self.assertIsInstance(data["chords"]["major"], tuple)
        self.assertIs(read("lazy_theory.pitch.catalog", "chords.toml"), data)  # parsed once


if __name__ == "__main__":
    unittest.main()
