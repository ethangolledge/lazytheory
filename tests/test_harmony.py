"""The tension and resolution claims of docs/theory.md section 9, built from core pieces only."""

import unittest

from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.pitch.catalog import chord_names, load_chords, load_scales
from lazy_theory.pitch.chord import Chord, identify
from lazy_theory.pitch.key import Key
from lazy_theory.pitch.scale import Scale
from lazy_theory.pitch.voice_leading import voice_leading

SCALES = load_scales()
CHORDS = load_chords()
IONIAN = SCALES["Ionian"]
DOMINANT = 4  # 0-based degree of the fifth scale note
TONIC = IONIAN.chord(0)


def chord_in_key(scale, degree: int, notes: int = 3) -> PitchClassSet:
    """A stacked chord placed at its position in the key rather than measured from its own root."""
    return Key(scale, 0).chord(degree, notes).pitch_classes


def name(notes: PitchClassSet) -> str:
    """The catalog's name for the first reading of `notes`."""
    return chord_names()[identify(notes, chord_names())[0].pattern]


def secondary_dominant(target_root: int) -> PitchClassSet:
    """The dominant seventh of the major scale built on `target_root`."""
    return chord_in_key(IONIAN, DOMINANT, notes=4).transpose(target_root)


class ResolutionTest(unittest.TestCase):
    def test_small_motion_alone_is_not_resolution(self):
        submediant_seventh = chord_in_key(IONIAN, 5, notes=4)
        dominant_seventh = chord_in_key(IONIAN, DOMINANT, notes=4)
        self.assertLess(
            voice_leading(submediant_seventh, TONIC).distance,
            voice_leading(dominant_seventh, TONIC).distance,
        )

    def test_dominant_tritone_resolves_by_contrary_semitones(self):
        moves = {
            move.source: move.steps for move in voice_leading(secondary_dominant(0), TONIC).moves
        }
        self.assertEqual((moves[11], moves[5]), (1, -1))

    def test_secondary_dominant_adds_one_leading_tone(self):
        supertonic = IONIAN.pitch_classes[1]
        five_of_two = secondary_dominant(supertonic)
        self.assertEqual(five_of_two.pitch_classes, (1, 4, 7, 9))
        self.assertEqual(name(five_of_two), "dominant 7th")
        self.assertEqual(set(five_of_two) - set(IONIAN), {supertonic - 1})

    def test_tritone_substitute_keeps_the_tritone(self):
        dominant = secondary_dominant(0)
        substitute = dominant.transpose(6)
        self.assertEqual(name(substitute), "dominant 7th")
        self.assertEqual(set(dominant) & set(substitute), {5, 11})

    def test_borrowed_chord_comes_from_a_rotation_on_the_same_root(self):
        borrowed_four = chord_in_key(SCALES["Aeolian"], 3)
        self.assertEqual(borrowed_four.pitch_classes, (0, 5, 8))
        self.assertEqual(identify(borrowed_four, chord_names()), [Chord(CHORDS["minor"], 5)])

    def test_neo_riemannian_moves_are_the_smallest_triad_changes(self):
        parallel, leading_tone, relative = (
            PitchClassSet((0, 3, 7)),
            PitchClassSet((4, 7, 11)),
            PitchClassSet((9, 0, 4)),
        )
        distances = [
            voice_leading(TONIC, chord).distance for chord in (parallel, leading_tone, relative)
        ]
        self.assertEqual(distances, [1, 1, 2])


class CatalogAgreesWithMaximalEvennessTest(unittest.TestCase):
    def test_symmetric_structures(self):
        self.assertEqual(SCALES["Whole Tone"], Scale.maximally_even(6))
        self.assertEqual(CHORDS["diminished 7th"], PitchClassSet.maximally_even(4))
        self.assertEqual(CHORDS["augmented"], PitchClassSet.maximally_even(3))


if __name__ == "__main__":
    unittest.main()
