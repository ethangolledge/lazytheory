import unittest

from lazy_theory.instruments.names import tab


class TabTest(unittest.TestCase):
    def test_highest_string_on_top_one_column_per_chord(self):
        text = tab([28, 33, 38, 43, 47, 52], [[-1, 3, 2, 0, 1, 0], [0, 2, 2, 0, 0, 0]], ["C", "Em"])
        self.assertEqual(
            text.splitlines(),
            ["   C  Em", "E |0  0", "B |1  0", "G |0  0", "D |2  2", "A |3  2", "E |x  0"],
        )


class OtherSizeTabTest(unittest.TestCase):
    def test_strings_labelled_in_numbers(self):
        text = tab([0, 6, 11], [[0, 1, 2]], size=19)
        self.assertEqual([line.split()[0] for line in text.splitlines()[1:]], ["11", "6", "0"])


if __name__ == "__main__":
    unittest.main()
