import unittest

from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.core.voice_leading import Move, voice_leading

C_MAJOR = PitchClassSet((0, 4, 7))
G_SEVENTH = PitchClassSet((7, 11, 2, 5))


class VoiceLeadingTest(unittest.TestCase):
    def test_same_set_does_not_move(self):
        self.assertEqual(voice_leading(C_MAJOR, C_MAJOR).distance, 0)

    def test_dominant_seventh_to_tonic(self):
        moves = voice_leading(G_SEVENTH, C_MAJOR).moves
        self.assertEqual(moves, (Move(2, 0, -2), Move(5, 4, -1), Move(7, 7, 0), Move(11, 0, 1)))

    def test_smaller_set_splits_to_reach_a_larger_one(self):
        moves = voice_leading(C_MAJOR, G_SEVENTH).moves
        self.assertEqual(moves, (Move(0, 2, 2), Move(0, 11, -1), Move(4, 5, 1), Move(7, 7, 0)))

    def test_distance_is_symmetric(self):
        self.assertEqual(
            voice_leading(G_SEVENTH, C_MAJOR).distance, voice_leading(C_MAJOR, G_SEVENTH).distance
        )

    def test_moves_take_the_shorter_way_round(self):
        self.assertEqual(voice_leading(PitchClassSet((11,)), PitchClassSet((1,))).moves[0].steps, 2)

    def test_tritone_counts_as_upwards(self):
        self.assertEqual(voice_leading(PitchClassSet((0,)), PitchClassSet((6,))).moves[0].steps, 6)

    def test_rejects_different_temperaments(self):
        with self.assertRaises(ValueError):
            voice_leading(C_MAJOR, PitchClassSet((0, 10, 18), 31))


if __name__ == "__main__":
    unittest.main()
