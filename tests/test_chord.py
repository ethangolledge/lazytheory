import unittest

from lazy_theory.core.chord import ChordMatch, identify
from lazy_theory.core.pcset import PitchClassSet

PATTERNS = {
    "major": PitchClassSet((0, 4, 7)),
    "augmented": PitchClassSet((0, 4, 8)),
    "sus2": PitchClassSet((0, 2, 7)),
    "sus4": PitchClassSet((0, 5, 7)),
}


class IdentifyTest(unittest.TestCase):
    def test_root_position(self):
        self.assertEqual(identify(PitchClassSet((0, 4, 7)), PATTERNS), [ChordMatch("major", 0)])

    def test_inversion_finds_the_root(self):
        first_inversion = PitchClassSet((0, 3, 8))
        self.assertEqual(identify(first_inversion, PATTERNS), [ChordMatch("major", 8)])

    def test_ambiguous_set_returns_every_reading(self):
        self.assertEqual(
            identify(PitchClassSet((0, 2, 7)), PATTERNS),
            [ChordMatch("sus2", 0), ChordMatch("sus4", 7)],
        )

    def test_symmetric_chord_matches_on_every_member(self):
        matches = identify(PitchClassSet((0, 4, 8)), PATTERNS)
        self.assertEqual([match.root for match in matches], [0, 4, 8])

    def test_unknown_set(self):
        self.assertEqual(identify(PitchClassSet((0, 1, 2)), PATTERNS), [])

    def test_different_temperament_does_not_match(self):
        self.assertEqual(identify(PitchClassSet((0, 4, 7), 31), PATTERNS), [])


if __name__ == "__main__":
    unittest.main()
