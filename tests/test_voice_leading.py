import random
import unittest
from itertools import product

from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.pitch.voice_leading import Move, voice_leading

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


class ExactTest(unittest.TestCase):
    def test_matches_trying_every_pairing(self):
        rng = random.Random(4)
        for _ in range(300):
            a, b = (PitchClassSet(tuple(rng.sample(range(12), rng.randint(1, 5)))) for _ in "ab")
            larger, smaller = (a, b) if len(a) >= len(b) else (b, a)
            every = (
                sum(min((t - s) % 12, (s - t) % 12) for s, t in zip(larger, choice, strict=True))
                for choice in product(smaller, repeat=len(larger))
                if set(choice) == set(smaller)
            )
            self.assertEqual(voice_leading(a, b).distance, min(every), (a, b))

    def test_whole_scales_are_quick(self):
        ionian = PitchClassSet((0, 2, 4, 5, 7, 9, 11))
        self.assertEqual(voice_leading(ionian, ionian.transpose(7)).distance, 1)  # F to F#
        chromatic = PitchClassSet(tuple(range(12)))
        self.assertEqual(voice_leading(chromatic, ionian).distance, 5)  # each black key, a step


class NeoRiemannianTest(unittest.TestCase):
    """Cohn (1997): P, L and R each hold two notes of a triad and move the third, by a semitone
    (P: C to Cm; L: C to Em) or a whole tone (R: C to Am)."""

    def test_parallel_leading_tone_and_relative(self):
        c_major = PitchClassSet((0, 4, 7))
        for target, distance in [((0, 3, 7), 1), ((4, 7, 11), 1), ((9, 0, 4), 2)]:
            moved = voice_leading(c_major, PitchClassSet(target))
            self.assertEqual(moved.distance, distance, target)
            self.assertEqual(sum(move.steps != 0 for move in moved.moves), 1, target)


if __name__ == "__main__":
    unittest.main()
