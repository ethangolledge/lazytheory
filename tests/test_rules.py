import unittest

import numpy as np
from fixtures import STANDARD, X, rows

from lazy_theory.instruments.fretboard import Fretboard
from lazy_theory.instruments.rules import (
    barres,
    contiguous,
    fingers,
    motion,
    moved,
    open_within,
    placeable,
    ringing,
    sounding,
    strings_changed,
    within,
)

C, F, G = 0, 5, 7  # pitch classes


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

    def test_open_and_muted_strings_are_never_barred(self):
        self.assertFalse(barres(rows([0, 0, 0, 0, 0, 0])).any())
        self.assertFalse(barres(rows([X, X, 0, 0, X, X])).any())
        self.assertTrue(barres(rows([X, X, 3, 3, X, X]))[0, 2, 3])

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

    def test_separate_fingers_where_a_barre_would_crowd(self):
        # D/F#: a barre on fret 2 would block the F#, but index, middle and ring on fret 2 and
        # the pinky on fret 3 (or a thumb on the F#) hold it fine.
        self.assertEqual(self.placeable(STANDARD, [2, 0, 0, 2, 3, 2]), [True])

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
        silent = STANDARD.bass(rows([X] * 6))  # NaN: nothing sounds, so nothing moves
        np.testing.assert_allclose(motion(STANDARD.bass(self.previous), silent), [[0.0]])
        np.testing.assert_allclose(bass_motion(self.previous, self.following), [[1, 5]])


if __name__ == "__main__":
    unittest.main()
