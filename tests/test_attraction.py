import unittest

from lazy_theory.catalog import load_scales, pitch
from lazy_theory.core.attraction import anchoring, attraction
from lazy_theory.core.key import Key

C_MAJOR = Key(load_scales()["Ionian"], 0)


class AttractionTest(unittest.TestCase):
    def test_lerdahl_and_krumhansls_worked_examples(self):
        # "Modeling Tonal Tension" (2007), figure 13c, in C major
        pairs = [("B3", "C4", 2.0), ("D4", "C4", 0.5), ("F4", "E4", 1.5), ("E4", "F4", 2 / 3)]
        for source, target, expected in pairs:
            with self.subTest(source=source, target=target):
                self.assertAlmostEqual(attraction(C_MAJOR, pitch(source), pitch(target)), expected)

    def test_anchoring_by_level(self):
        levels = [anchoring(C_MAJOR)[pc] for pc in (0, 4, 7, 2, 11, 1, 6)]
        self.assertEqual(levels, [4, 3, 3, 2, 2, 1, 1])

    def test_the_same_pitch_has_no_pull(self):
        self.assertEqual(attraction(C_MAJOR, pitch("C4"), pitch("C4")), 0.0)

    def test_a_ninth_away_counts_its_steps(self):
        self.assertAlmostEqual(attraction(C_MAJOR, pitch("B3"), pitch("C5")), 2 / 13**2)

    def test_follows_the_key(self):
        a_minor = Key(load_scales()["Aeolian"], 9)
        self.assertEqual(anchoring(a_minor)[9], 4)
        self.assertEqual(anchoring(a_minor)[0], 3)  # C is the minor third of A minor


if __name__ == "__main__":
    unittest.main()
