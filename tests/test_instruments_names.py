import unittest

from lazy_theory.instruments.names import tab
from lazy_theory.pitch.catalog import load_chords, load_scales, pitch_class
from lazy_theory.pitch.key import Key

SCALES, CHORDS = load_scales(), load_chords()


def key(mode: str, tonic: str) -> Key:
    return Key(SCALES[mode], pitch_class(tonic))


class TabTest(unittest.TestCase):
    def test_highest_string_on_top_one_column_per_chord(self):
        text = tab([28, 33, 38, 43, 47, 52], [[-1, 3, 2, 0, 1, 0], [0, 2, 2, 0, 0, 0]], ["C", "Em"])
        self.assertEqual(
            text.splitlines(),
            ["   C  Em", "E |0  0", "B |1  0", "G |0  0", "D |2  2", "A |3  2", "E |x  0"],
        )


if __name__ == "__main__":
    unittest.main()
