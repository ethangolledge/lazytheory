import unittest

from lazy_theory.catalog import load_chords, load_scales, pitch, pitch_class
from lazy_theory.catalog.names import chord_symbol, note_name, note_names, numeral, pitch_name, tab
from lazy_theory.core.chord import Chord
from lazy_theory.core.key import Key
from lazy_theory.core.pcset import PitchClassSet

SCALES, CHORDS = load_scales(), load_chords()


def key(mode: str, tonic: str) -> Key:
    return Key(SCALES[mode], pitch_class(tonic))


class SpellingTest(unittest.TestCase):
    def test_each_letter_once_with_fewest_accidentals(self):
        self.assertEqual(" ".join(note_names(key("Ionian", "F"))), "F G A Bb C D E")
        self.assertEqual(" ".join(note_names(key("Aeolian", "C"))), "C D Eb F G Ab Bb")
        self.assertEqual(" ".join(note_names(key("Harmonic Minor", "A"))), "A B C D E F G#")
        self.assertEqual(note_names(key("Ionian", "Bb"))[0], "Bb")  # not A#

    def test_every_key_spells_back_to_its_notes(self):
        for name, scale in SCALES.items():
            for tonic in range(12):
                k = Key(scale, tonic)
                with self.subTest(scale=name, tonic=tonic):
                    spelled = {pitch_class(note) % 12 for note in note_names(k)}
                    self.assertEqual(spelled, set(k.pitch_classes))

    def test_notes_outside_a_key_follow_its_accidentals(self):
        self.assertEqual(note_name(1), "C#")
        self.assertEqual(note_name(1, key("Ionian", "F")), "Db")

    def test_pitches_round_trip(self):
        for note in ("E2", "A4", "C#3"):
            self.assertEqual(pitch_name(pitch(note)), note)
        self.assertEqual(pitch_name(pitch("Bb1"), key("Ionian", "F")), "Bb1")
        self.assertEqual(
            pitch_name(48, key("Harmonic Minor", "C#")), "B#3"
        )  # C4 as the leading note


class ChordNameTest(unittest.TestCase):
    def test_symbols_and_slash_bass(self):
        e_minor_7 = Chord(CHORDS["minor 7th"], pitch_class("E"))
        self.assertEqual(chord_symbol(e_minor_7), "Em7")
        self.assertEqual(chord_symbol(e_minor_7, bass=pitch_class("G")), "Em7/G")
        self.assertEqual(chord_symbol(e_minor_7, bass=pitch_class("E")), "Em7")

    def test_unnamed_pattern_shows_its_intervals(self):
        self.assertEqual(chord_symbol(Chord(PitchClassSet((0, 1, 3, 7)), 4)), "E(0 1 3 7)")

    def test_roman_numerals_from_the_triads(self):
        self.assertEqual(
            [numeral(key("Ionian", "C"), d) for d in range(7)],
            ["I", "ii", "iii", "IV", "V", "vi", "vii°"],
        )
        self.assertEqual(numeral(key("Phrygian", "E"), 1), "bII")
        self.assertEqual(numeral(key("Harmonic Minor", "A"), 2), "bIII+")


class TabTest(unittest.TestCase):
    def test_highest_string_on_top_one_column_per_chord(self):
        text = tab([28, 33, 38, 43, 47, 52], [[-1, 3, 2, 0, 1, 0], [0, 2, 2, 0, 0, 0]], ["C", "Em"])
        self.assertEqual(
            text.splitlines(),
            ["   C  Em", "E |0  0", "B |1  0", "G |0  0", "D |2  2", "A |3  2", "E |x  0"],
        )


if __name__ == "__main__":
    unittest.main()
