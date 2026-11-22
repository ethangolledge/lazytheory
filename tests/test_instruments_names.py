import unittest

import numpy as np

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
        self.assertEqual([line.split()[0] for line in text.splitlines()], ["11", "6", "0"])


class TabInputTest(unittest.TestCase):
    def test_arrays_as_a_board_and_route_give_them(self):
        strings, path = np.array([28, 33, 38]), np.array([[0, 2, 2], [3, 2, 0]])
        self.assertEqual(tab(strings, path), tab(strings.tolist(), path.tolist()))

    def test_a_fret_for_every_string(self):
        for strings, voicings in (([28, 33], [[0]]), ([], [])):
            with self.subTest(strings=strings), self.assertRaises(ValueError):
                tab(strings, voicings)


class TitleCountTest(unittest.TestCase):
    def test_a_title_needs_a_voicing(self):
        with self.assertRaises(ValueError):
            tab([28, 33], [[0, 2]], ["C", "Em"])


class NoTitleTest(unittest.TestCase):
    def test_no_titles_no_title_line(self):
        self.assertEqual(tab([28, 33], []), "A |\nE |")


if __name__ == "__main__":
    unittest.main()
