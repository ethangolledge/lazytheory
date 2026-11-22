import unittest
from dataclasses import replace
from itertools import combinations

from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.pitch.catalog import load_chords, load_scales, pitch, pitch_class
from lazy_theory.pitch.chord import Chord
from lazy_theory.pitch.key import Key
from lazy_theory.pitch.names import (
    chord_symbol,
    chord_tone_names,
    degree_names,
    note_name,
    note_names,
    numeral,
    parse_chord,
    pitch_name,
    quality,
    step_names,
)

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


class DegreeNameTest(unittest.TestCase):
    def test_modes_against_the_major_scale(self):
        self.assertEqual(" ".join(degree_names(key("Phrygian", "E"))), "1 b2 b3 4 5 b6 b7")
        self.assertEqual(" ".join(degree_names(key("Lydian", "F"))), "1 2 3 #4 5 6 7")
        self.assertEqual(" ".join(degree_names(key("Locrian", "B"))), "1 b2 b3 4 b5 b6 b7")

    def test_other_sizes_take_the_nearest_degree(self):
        self.assertEqual(" ".join(degree_names(key("Minor Pentatonic", "A"))), "1 b3 4 5 b7")
        self.assertEqual(" ".join(degree_names(key("Whole Tone", "C"))), "1 2 3 b5 b6 b7")


class QualityTest(unittest.TestCase):
    def test_modes_by_the_chord_on_their_first_note(self):
        expected = {
            "Ionian": "major",
            "Dorian": "minor",
            "Locrian": "diminished",
            "Harmonic Minor": "minor",
            "Phrygian Dominant": "major",
            "Lydian Augmented": "augmented",
            "Major Pentatonic": "major",
            "Minor Pentatonic": "minor",
        }
        for name, sound in expected.items():
            self.assertEqual(quality(SCALES[name]), sound, name)

    def test_every_mode_gets_an_answer_or_none(self):
        for name, scale in SCALES.items():
            self.assertIn(quality(scale), ("major", "minor", "diminished", "augmented", None), name)


class ChordNameTest(unittest.TestCase):
    def test_symbols_and_slash_bass(self):
        e_minor_7 = Chord(CHORDS["minor 7th"], pitch_class("E"))
        self.assertEqual(chord_symbol(e_minor_7), "Em7")
        self.assertEqual(chord_symbol(replace(e_minor_7, bass=pitch_class("G"))), "Em7/G")
        self.assertEqual(chord_symbol(replace(e_minor_7, bass=pitch_class("E"))), "Em7")

    def test_extended_chords_are_a_named_core_plus_extensions(self):
        e = pitch_class("E")
        self.assertEqual(chord_symbol(Chord(PitchClassSet((0, 1, 3, 7)), e)), "Em(b9)")
        self.assertEqual(chord_symbol(Chord(PitchClassSet((0, 1, 3, 7, 10)), e)), "Em7(b9)")
        self.assertEqual(chord_symbol(Chord(PitchClassSet((0, 2, 4, 7, 9)), 0)), "C6/9")
        self.assertEqual(chord_symbol(Chord(PitchClassSet((0, 4, 6, 7, 9)), 0)), "C6(#11)")
        self.assertEqual(chord_symbol(Chord(PitchClassSet((0, 2, 3, 7, 11)), 9)), "Am(maj7)(9)")
        self.assertEqual(chord_symbol(Chord(PitchClassSet((0, 3, 5, 7, 10)), e, 7)), "Em7(11)/G")

    def test_every_step_has_a_name_in_the_key(self):
        d_dorian = Key(load_scales()["Dorian"], pitch_class("D"))
        self.assertEqual(
            step_names(d_dorian), ("1", "b2", "2", "b3", "3", "4", "b5", "5", "b6", "6", "b7", "7")
        )
        lydian = Key(load_scales()["Lydian"], 0)
        self.assertEqual(step_names(lydian)[6], "#4")  # the key's own spelling wins

    def test_notes_outside_the_key_are_spelled_by_their_interval(self):
        d_dorian = Key(load_scales()["Dorian"], pitch_class("D"))
        self.assertEqual(note_name(pitch_class("A#"), d_dorian), "Bb")  # b6
        self.assertEqual(note_name(pitch_class("F#"), d_dorian), "F#")  # 3
        self.assertEqual(note_name(pitch_class("G#"), d_dorian), "Ab")  # b5

    def test_a_sixth_without_a_seventh_is_a_6_chord(self):
        # the symbol and the chord's own interval names agree: 6, not 13
        f = pitch_class("F")
        for pattern, symbol in (((0, 4, 7, 9), "F6"), ((0, 3, 7, 9), "Fm6")):
            chord = Chord(PitchClassSet(pattern), f)
            self.assertEqual(chord_symbol(chord), symbol)
            self.assertIn("6", chord_tone_names(chord.pattern))
            self.assertEqual(parse_chord(symbol), chord)

    def test_any_leftover_note_has_a_name(self):
        # the largest named core here is a minor triad; the major 7th is left over
        self.assertEqual(chord_symbol(Chord(PitchClassSet((0, 3, 7, 11, 2)), 9)), "Am(maj7)(9)")
        for steps in range(1, 12):
            chord_symbol(Chord(PitchClassSet((0, 4, 7, steps)), 0))  # never raises

    def test_pattern_with_no_named_core_lists_every_note(self):
        cluster = Chord(PitchClassSet((0, 1, 2)), 4)
        self.assertEqual(chord_symbol(cluster), "E(1,b9,2)")
        self.assertEqual(parse_chord("E(1,b9,2)"), cluster)

    def test_a_symbol_and_its_note_names_agree(self):
        # what the symbol calls a note is what the note is labelled, for every possible chord
        for size in range(1, 12):  # all 2,047 patterns on a root
            for rest in combinations(range(1, 12), size):
                chord = Chord(PitchClassSet((0, *rest)), 0)
                symbol, tones = chord_symbol(chord), chord_tone_names(chord.pattern)
                self.assertEqual(parse_chord(symbol), chord, symbol)
                if "(" in symbol and not symbol.endswith("(maj7)"):
                    written = symbol[symbol.rindex("(") + 1 : -1].replace("maj7", "7").split(",")
                    notes = {label for label in written if not label.startswith("no")}
                    self.assertLessEqual(notes, set(tones), symbol)

    def test_reading_forgives_spaces_but_not_a_missing_bass(self):
        self.assertEqual(parse_chord(" Em7(b9, 11) "), parse_chord("Em7(b9,11)"))
        with self.assertRaises(ValueError):
            parse_chord("Em7/")

    def test_power_chords(self):
        self.assertEqual(chord_symbol(Chord(PitchClassSet((0, 7)), 9)), "A5")
        self.assertEqual(chord_tone_names(PitchClassSet((0, 7))), ("1", "5"))

    def test_note_names_follow_the_chord_like_its_symbol(self):
        for name, expected in (
            ("sus2", ("1", "2", "5")),
            ("sus4", ("1", "4", "5")),
            ("augmented 7th", ("1", "3", "#5", "b7")),
            ("diminished 7th", ("1", "b3", "b5", "bb7")),
            ("half-diminished 7th", ("1", "b3", "b5", "b7")),
        ):
            self.assertEqual(chord_tone_names(CHORDS[name]), expected, name)

    def test_roman_numerals_from_the_triads(self):
        self.assertEqual(
            [numeral(key("Ionian", "C"), d) for d in range(7)],
            ["I", "ii", "iii", "IV", "V", "vi", "vii°"],
        )
        self.assertEqual(numeral(key("Phrygian", "E"), 1), "bII")
        self.assertEqual(numeral(key("Harmonic Minor", "A"), 2), "bIII+")


class ParseChordTest(unittest.TestCase):
    def test_every_symbol_reads_back(self):
        for pattern in CHORDS.values():
            for root in range(12):
                for bass in (None, *Chord(pattern, root).pitch_classes):
                    chord = Chord(pattern, root, bass)
                    with self.subTest(written=chord_symbol(chord)):
                        read = parse_chord(chord_symbol(chord))  # a bass on the root isn't written
                        self.assertEqual(read, Chord(pattern, root, None if bass == root else bass))

    def test_extensions_and_flats(self):
        parsed = parse_chord("Bbm7(b9)/Db")
        self.assertEqual(parsed, Chord(PitchClassSet((0, 1, 3, 7, 10)), 10, bass=1))

    def test_without_a_key_a_chord_is_spelled_in_its_own(self):
        self.assertEqual(chord_symbol(parse_chord("A#m7b5")), "Bbm7b5")  # Bb minor: 5 flats
        self.assertEqual(chord_symbol(parse_chord("G#maj7(#5)/C")), "Abmaj7#5/C")
        self.assertEqual(chord_symbol(parse_chord("Dbm")), "C#m")  # C# minor: 4 sharps, not 8 flats

    def test_the_common_spellings_read(self):
        same = {
            "CM7": "Cmaj7",
            "CΔ7": "Cmaj7",
            "C-7": "Cm7",
            "Cmin7": "Cm7",
            "Cø7": "Cm7b5",
            "C°7": "Cdim7",
            "Co7": "Cdim7",
            "C+": "Caug",
            "Csus": "Csus4",
            "C69": "C6/9",
            "C-": "Cm",
            "CmM7": "Cm(maj7)",
            "Cadd2": "Cadd9",
        }
        for written, symbol in same.items():
            with self.subTest(written=written):
                self.assertEqual(chord_symbol(parse_chord(written)), symbol)

    def test_extended_chords_by_name(self):
        for symbol in ["C9", "Cmaj9", "Cm9", "C11", "Cm11", "C13", "Cmaj13", "Cm13", "C7sus4"]:
            with self.subTest(symbol=symbol):
                self.assertEqual(chord_symbol(parse_chord(symbol)), symbol)
        self.assertEqual(parse_chord("C13").pattern, PitchClassSet((0, 2, 4, 7, 9, 10)))

    def test_a_seventh_chord_can_leave_out_its_third_or_fifth(self):
        self.assertEqual(chord_symbol(Chord(PitchClassSet((0, 4, 10)), 0)), "C7(no5)")
        self.assertEqual(chord_symbol(Chord(PitchClassSet((0, 7, 10)), 0)), "C7(no3)")
        self.assertEqual(parse_chord("Dm7(no5)").pattern, PitchClassSet((0, 3, 10)))
        self.assertEqual(chord_symbol(Chord(PitchClassSet((0, 2, 7)), 0)), "Csus2")  # no seventh
        self.assertEqual(chord_symbol(Chord(PitchClassSet((0, 3, 9)), 2)), "D(1,b3,6)")  # not dim7

    def test_alterations_written_straight_after_the_type(self):
        self.assertEqual(parse_chord("C7#9"), parse_chord("C7(#9)"))
        self.assertEqual(parse_chord("Cmaj7#11"), parse_chord("Cmaj7(#11)"))
        self.assertEqual(parse_chord("C7b9b13"), parse_chord("C7(b9,b13)"))

    def test_six_nine_is_a_type_and_a_bass_still_reads(self):
        self.assertEqual(parse_chord("C6/9").bass, None)
        self.assertEqual(parse_chord("C6/9/E").bass, pitch_class("E"))

    def test_a_bracketed_chord_tone_alters_it(self):
        self.assertEqual(parse_chord("Bbm7(b5)"), parse_chord("Bbm7b5"))
        self.assertEqual(parse_chord("C7(#5)").pattern, PitchClassSet((0, 4, 8, 10)))
        self.assertEqual(parse_chord("C7(b9)").pattern, PitchClassSet((0, 1, 4, 7, 10)))  # added

    def test_numerals_in_a_key(self):
        e_phrygian = key("Phrygian", "E")
        self.assertEqual(parse_chord("bII", e_phrygian).root, pitch_class("F"))
        self.assertEqual(parse_chord("iv", e_phrygian), e_phrygian.chord(3))

    def test_rejects_what_it_cannot_read(self):
        for text in ("", "Hm7", "Em/F#", "Eblah", "Em(b10)"):
            with self.assertRaises(ValueError, msg=text):
                parse_chord(text)


class ChordToneTest(unittest.TestCase):
    def test_labels_follow_the_chord(self):
        self.assertEqual(chord_tone_names(CHORDS["minor 7th"]), ("1", "b3", "5", "b7"))
        self.assertEqual(
            chord_tone_names(PitchClassSet((0, 3, 4, 7, 10))), ("1", "#9", "3", "5", "b7")
        )
        self.assertEqual(chord_tone_names(PitchClassSet((0, 4, 7, 9))), ("1", "3", "5", "6"))
        self.assertEqual(
            chord_tone_names(PitchClassSet((0, 4, 7, 9, 10))), ("1", "3", "5", "13", "b7")
        )


if __name__ == "__main__":
    unittest.main()
