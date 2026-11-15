import unittest

import numpy as np

from lazy_theory.catalog import load_tunings
from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.core.scale import Scale
from lazy_theory.instruments.acoustics import roughness
from lazy_theory.instruments.fretboard import MUTED, Fretboard
from lazy_theory.instruments.rules import (
    contiguous,
    fingers,
    motion,
    moved,
    open_within,
    placeable,
    ringing,
    smoothest,
    sounding,
    strings_changed,
    within,
)

X = MUTED
STANDARD = Fretboard.from_tuning(load_tunings()["guitar standard"])
REACH = STANDARD.fret_distance[4] - STANDARD.fret_distance[1]
IONIAN = Scale.from_steps((2, 2, 1, 2, 2, 2, 1))
MAJOR = PitchClassSet((0, 4, 7))
C, F, G = 0, 5, 7  # pitch classes


def rows(*voicings: list[int]) -> np.ndarray:
    return np.array(voicings, dtype=np.int16)


def bass(voicings: np.ndarray) -> np.ndarray:
    return np.nanmin(STANDARD.notes(voicings), axis=1)


def bass_motion(previous: np.ndarray, following: np.ndarray) -> np.ndarray:
    return motion(bass(previous), bass(following))


def playable(voicings: np.ndarray, lowest: int, highest: int) -> np.ndarray:
    return voicings[(fingers(voicings) <= 4) & within(voicings, lowest, highest)]


class FingersTest(unittest.TestCase):
    def test_open_shapes(self):
        self.assertEqual(fingers(rows([X, 3, 2, 0, 1, 0], [3, 2, 0, 0, 0, 3])).tolist(), [3, 3])

    def test_one_finger_barres_a_fret(self):
        self.assertEqual(fingers(rows([X, 0, 2, 2, 2, X], [1, 3, 3, 2, 1, 1])).tolist(), [1, 4])

    def test_a_barre_lies_to_the_highest_string(self):
        # The finger lies over every string above the barre's first note: an open string there
        # is damped (A with an open high E needs three fingers), a lower note can't sound
        # (B minor's ring finger can't barre over the 3rd fret), but a muted one is fine.
        voicings = rows(
            [X, 0, 2, 2, 2, 0], [X, 2, 4, 4, 3, 2], [2, 3, 2, 2, 0, 2], [5, 5, 5, X, X, X]
        )
        self.assertEqual(fingers(voicings).tolist(), [3, 4, 5, 1])

    def test_a_string_below_the_barre_fret_breaks_it(self):
        open_, muted, lower = rows([5, 0, 5, 5, X, X], [3, X, 3, 3, X, X], [5, 4, 5, X, X, X])
        self.assertEqual(fingers(np.stack([open_, muted, lower])).tolist(), [2, 2, 3])

    def test_too_many_notes(self):
        self.assertEqual(fingers(rows([1, 2, 3, 4, 5, X])).tolist(), [5])


class PlaceableTest(unittest.TestCase):
    spans = (34.4, 66.8, 97.4)  # one finger per fret at the nut

    def placeable(self, board: Fretboard, *voicings: list[int]) -> list[bool]:
        return placeable(rows(*voicings), board.fret_distance, self.spans).tolist()

    def test_familiar_shapes(self):
        c, g, a = [X, 3, 2, 0, 1, 0], [3, 2, 0, 0, 0, 3], [X, 0, 2, 2, 2, 0]
        f, b_minor = [1, 3, 3, 2, 1, 1], [X, 2, 4, 4, 3, 2]
        self.assertEqual(self.placeable(STANDARD, c, g, a, f, b_minor), [True] * 5)

    def test_stretch_too_far(self):
        self.assertEqual(self.placeable(STANDARD, [1, X, X, X, X, 6]), [False])

    def test_shapes_checked_by_hand(self):
        # Capo 5: three fingers on one fret with the pinky three frets on; a barre sharing its
        # fret with another finger; ring to pinky across two frets.
        capo_5 = STANDARD.capo(5)
        awkward = [2, 5, 2, 0, 0, 2], [2, 0, 2, 4, 3, 2], [2, 2, 0, 3, 5, 0]
        self.assertEqual(self.placeable(capo_5, *awkward), [False, False, False])
        # No capo, D string raised to E: Em, Am and B7 that fit the hand.
        fine = [0, 2, 0, 0, 5, 0], [0, 3, 0, 2, 5, 0], [2, 2, 2, 2, 4, 2]
        self.assertEqual(self.placeable(STANDARD, *fine), [True, True, True])


class ShapeRulesTest(unittest.TestCase):
    def test_contiguous(self):
        self.assertEqual(
            contiguous(rows([X, 3, 2, 0, 1, 0], [3, X, 2, 0, 1, 0])).tolist(), [True, False]
        )

    def test_within_allows_open_strings(self):
        voicings = rows([X, X, 9, 9, 8, 8], [0, X, 9, 9, 8, 8], [X, X, 9, 9, 8, 12])
        self.assertEqual(within(voicings, 7, 11).tolist(), [True, True, False])

    def test_open_strings_only_near_the_hand(self):
        voicings = rows([X, X, X, 12, 0, 12], [X, X, X, 4, 0, 5], [X, X, 9, 9, 8, 7])
        self.assertEqual(open_within(voicings, 5).tolist(), [False, True, True])

    def test_sounding_counts_strings(self):
        self.assertEqual(sounding(rows([X, 3, 2, 0, 1, 0], [X, X, 9, 9, 8, X])).tolist(), [5, 3])

    def test_ringing_counts_open_strings(self):
        self.assertEqual(ringing(rows([X, 3, 2, 0, 1, 0], [X, X, 9, 9, 8, 7])).tolist(), [2, 0])


class TransitionTest(unittest.TestCase):
    previous = rows([X, X, 10, 10, 10, 10])
    following = rows([X, X, 9, 10, 8, 10], [X, 10, 9, 10, 8, X])

    def test_steps_moved_on_shared_strings(self):
        self.assertEqual(moved(self.previous, self.following).tolist(), [[3, 3]])

    def test_strings_started_or_stopped(self):
        self.assertEqual(strings_changed(self.previous, self.following).tolist(), [[0, 2]])

    def test_motion_of_any_value(self):
        hands = STANDARD.hand(self.previous), STANDARD.hand(rows([0, 0, 0, 0, 0, 0]))
        np.testing.assert_allclose(motion(*hands), [[0.0]])
        np.testing.assert_allclose(bass_motion(self.previous, self.following), [[1, 5]])


class SmoothestTest(unittest.TestCase):
    def test_matches_brute_force(self):
        def transition(previous, following):
            return moved(previous, following) + 5 * strings_changed(previous, following)

        def cost(voicings):
            return 10 * roughness(STANDARD.frequencies(voicings))

        two, five, one = [
            playable(STANDARD.voicings(IONIAN.chord(degree, 4), C + step, REACH), 5, 9)
            for degree, step in ((1, 2), (4, 7), (0, 0))
        ]
        every_path = (
            cost(two)[:, None, None]
            + transition(two, five)[:, :, None]
            + cost(five)[None, :, None]
            + transition(five, one)[None, :, :]
            + cost(one)[None, None, :]
        )
        path, total = smoothest([two, five, one], transition, [cost(two), cost(five), cost(one)])
        self.assertAlmostEqual(total, every_path.min())
        chosen = sum(cost(path[i : i + 1])[0] for i in range(3)) + sum(
            transition(path[i : i + 1], path[i + 1 : i + 2])[0, 0] for i in range(2)
        )
        self.assertAlmostEqual(chosen, every_path.min())

    def test_fixed_starting_voicing(self):
        start = rows([X, X, 10, 10, 10, 10])
        five = STANDARD.voicings(IONIAN.chord(4, 4), C + 7, REACH)
        path, _ = smoothest([start, five], moved)
        np.testing.assert_array_equal(path[0], start[0])

    def test_rejects_a_chord_with_no_voicings(self):
        with self.assertRaises(ValueError):
            smoothest([rows([0, 2, 2, 1, 0, 0]), rows()[:0]], moved)


class InversionsFromTheBassTest(unittest.TestCase):
    """The common-practice uses of inversions follow from one rule: move the bass as little as
    possible (docs/theory.md section 7)."""

    tonic = rows([X, 3, 2, 0, 1, 0])  # C, bass C3

    def inversion(self, chords: list[np.ndarray], middle: int) -> int:
        path, _ = smoothest(chords, bass_motion)
        return int(STANDARD.stack(path[1:2], middle)[0, 0])

    def test_pedal_six_four(self):
        # I - IV - I over a held bass: IV takes its fifth in the bass.
        subdominant = playable(STANDARD.voicings(MAJOR, F, REACH), 0, 4)
        self.assertEqual(self.inversion([self.tonic, subdominant, self.tonic], F), 7)

    def test_passing_six_four(self):
        # I - V - I6, bass C3 to E3: V takes its fifth, D3, to pass by step.
        dominant = playable(STANDARD.voicings(MAJOR, G, REACH), 0, 4)
        tonic_six = rows([X, X, 2, 0, 1, 0])
        self.assertEqual(self.inversion([self.tonic, dominant, tonic_six], G), 7)

    def test_four_two_resolves_to_six(self):
        # V4/2, seventh F2 in the bass, falls a step to I6 with E2 in the bass.
        dominant_seventh = rows([1, X, 0, 0, 0, 1])
        tonic = playable(STANDARD.voicings(MAJOR, C, REACH), 0, 4)
        path, _ = smoothest([dominant_seventh, tonic], bass_motion)
        self.assertEqual(STANDARD.stack(path[1:], C)[0, 0], 4)


class TwoFiveOneTest(unittest.TestCase):
    """ii-V-I in C in one hand position keeps its strings and picks its inversions."""

    def test_stays_on_the_same_strings(self):
        options = [
            playable(STANDARD.voicings(IONIAN.chord(degree, 4), C + step, REACH), 7, 11)
            for degree, step in ((1, 2), (4, 7), (0, 0))
        ]
        options = [voicings[contiguous(voicings)] for voicings in options]
        path, _ = smoothest(options, lambda a, b: moved(a, b) + 5 * strings_changed(a, b))
        sounding = path != MUTED
        self.assertTrue((sounding == sounding[0]).all())
        self.assertEqual(path.tolist()[-1], [X, X, 9, 9, 8, 8])


if __name__ == "__main__":
    unittest.main()
