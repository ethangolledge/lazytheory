import unittest

from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.rhythm.catalog import load_spoken, load_tals, syllable_id
from lazy_theory.rhythm.layers import dissonance
from lazy_theory.rhythm.meter import Meter, compositions
from lazy_theory.rhythm.names import (
    counted,
    counting,
    dissonance_label,
    jam_name,
    khali,
    parse_meter,
    parse_phrase,
    phrase_text,
    spell,
    tala_marks,
)
from lazy_theory.rhythm.phrase import NOTE, REST, Phrase


def spoken(onsets: PitchClassSet, meter: Meter | None = None) -> str:
    """Konnakol for a rhythm: a word from each onset, a syllable per grid point."""
    points = meter.to_grid(onsets) if meter else onsets
    return phrase_text(spell(Phrase.stream(points), "konnakol"))


def parse_spoken(text: str, meter: Meter | None = None) -> PitchClassSet:
    """`spoken` read back: the onsets are the words that start on a syllable."""
    points = parse_phrase(text).accents()
    return meter.from_grid(points) if meter else points


class SpokenTest(unittest.TestCase):
    def test_seven_eight_clapped_on_one_four_and_six(self):
        meter = parse_meter("7/8")
        self.assertEqual(spoken(PitchClassSet((0, 3, 5), 7), meter), "ta-ki-ta ta-ka ta-ka")

    def test_jati_words_match_the_theory_doc(self):
        # docs/theory.md section 10: khanda, misra, sankeerna
        expected = {
            3: "ta-ki-ta",
            4: "ta-ka-di-mi",
            5: "ta-ka-ta-ki-ta",
            7: "ta-ki-ta-ta-ka-di-mi",
            9: "ta-ka-di-mi-ta-ka-ta-ki-ta",
        }
        for size, word in expected.items():
            self.assertEqual(spoken(PitchClassSet((0,), size)), word, size)

    def test_silence_before_the_first_onset(self):
        self.assertEqual(spoken(PitchClassSet((2, 5), 7)), ",-, ta-ki-ta ta-ka")

    def test_quintuplet_beat_says_five_syllables(self):
        meter = Meter.of((2, 2), (4, 5, 4, 4))
        text = spoken(meter.starts(meter.beat), meter)
        self.assertEqual(text, "ta-ka-di-mi ta-ka-ta-ki-ta ta-ka-di-mi ta-ka-di-mi")
        self.assertEqual(parse_spoken(text, meter), meter.starts(meter.beat))

    def test_round_trip_over_every_rhythm(self):
        for size in range(1, 11):
            for steps in compositions(size, range(1, size + 1)):
                onsets = PitchClassSet.from_steps(steps)
                for offset in range(steps[-1]):
                    moved = PitchClassSet(tuple(p + offset for p in onsets), size)
                    with self.subTest(onsets=moved):
                        self.assertEqual(parse_spoken(spoken(moved)), moved)

    def test_typed_without_hyphens(self):
        self.assertEqual(parse_spoken("takita taka tadiginathom"), PitchClassSet((0, 3, 5), 10))
        self.assertEqual(parse_spoken("Tha-Ka-Dhi-Mi"), PitchClassSet((0,), 4))

    def test_a_word_of_rests_lengthens_the_one_before(self):
        self.assertEqual(parse_spoken("ta-ka ,-, ta"), PitchClassSet((0, 4), 5))

    def test_rejects_unknown_text_and_mismatched_meters(self):
        for text in ["", "takabanana"]:
            with self.assertRaises(ValueError, msg=text):
                parse_spoken(text)
        self.assertEqual(parse_spoken(",-,"), PitchClassSet((), 2))  # silence is a rhythm
        with self.assertRaises(ValueError):
            parse_spoken("ta-ka", parse_meter("3/4"))
        with self.assertRaises(ValueError):
            spoken(PitchClassSet((1,), 80), Meter.of((2, 2), (4, 5, 4, 4)))  # off the grid


class CountingTest(unittest.TestCase):
    def test_how_a_guitarist_counts(self):
        meter = Meter.of((2, 2), (2, 3, 4, 1))
        self.assertEqual(" ".join(counting(meter, 4)), "1 & 2 trip let 3 e & a 4")

    def test_fives_are_said_in_konnakol(self):
        self.assertEqual(counting(Meter.of((1,), 5), 1), ("1", "ka", "ta", "ki", "ta"))

    def test_counts_restart_each_bar(self):
        self.assertEqual(counting(parse_meter("3/4", 1, 2), 3), ("1", "2", "3", "1", "2", "3"))


class JamNameTest(unittest.TestCase):
    def test_subdivision_and_group(self):
        self.assertEqual(jam_name(4, 3), "16ths in 3s")
        self.assertEqual(jam_name(3, 2), "triplets in 2s")


class MeterNameTest(unittest.TestCase):
    def test_numerator_groups_by_halving(self):
        self.assertEqual(parse_meter("7/8").levels[1:3], ((3, 4), (3, 2, 2)))
        self.assertEqual(parse_meter("12/8").levels[1:3], ((6, 6), (3, 3, 3, 3)))
        self.assertEqual(parse_meter("4/4").levels, ((4,), (2, 2), (1, 1, 1, 1)))

    def test_written_grouping(self):
        self.assertEqual(parse_meter("2+2+3/8"), Meter.of((2, 2, 3)))
        self.assertEqual(parse_meter(" 3 + 2 + 2 / 8 "), Meter.of((3, 2, 2)))

    def test_division(self):
        self.assertEqual(parse_meter("4/4", 4).pulses, 16)

    def test_rejects_malformed(self):
        for text in ["7", "7/", "/8", "a/4", "3+/4", "0/4", "4/0"]:
            with self.assertRaises(ValueError, msg=text):
                parse_meter(text)


class DissonanceLabelTest(unittest.TestCase):
    def test_krebs_labels(self):
        self.assertEqual(dissonance_label(dissonance(3, 0, 4)), "G3/4")
        self.assertEqual(dissonance_label(dissonance(3, 1, 3)), "D3+1")
        self.assertEqual(dissonance_label(dissonance(3, 2, 3)), "D3-1")
        self.assertEqual(dissonance_label(dissonance(2, 0, 4)), "aligned")


class PhraseTextTest(unittest.TestCase):
    def test_round_trip_over_every_spelled_phrase(self):
        names = load_spoken().names
        for total in range(1, 7):
            for lengths in compositions(total, range(1, total + 1)):
                n = len(lengths)
                for rests in range(1 << n):
                    sounds = tuple(
                        REST if rests >> t & 1 else 1 + (t * 7 + total) % len(names)
                        for t in range(n)
                    )
                    for words in compositions(n, range(1, n + 1)):
                        try:
                            phrase = Phrase(lengths, sounds, (words,))
                        except ValueError:
                            continue  # two rests inside a word
                        for shaped in (phrase, phrase.tihai(1), phrase.grouped() + phrase):
                            with self.subTest(phrase=shaped):
                                self.assertEqual(parse_phrase(phrase_text(shaped)), shaped)

    def test_a_gap_inside_a_word_survives(self):
        for text in ["ta , di mi", "ta-,-di-mi", "ta-_-ki-ta ,-, ta"]:
            self.assertEqual(phrase_text(parse_phrase(text)), text)

    def test_brackets_and_repeats_make_a_tihai(self):
        tihai = parse_phrase("[takadimi ta ,]x2 [takadimi ta]")
        self.assertEqual(tihai.pulses, 3 * 5 + 2 * 1)
        self.assertEqual(tihai.groups[0], (6, 6, 5))  # each statement a group: 5 syllables, a rest
        self.assertEqual(tihai, parse_phrase("ta-ka-di-mi ta").tihai(1))

    def test_rejects_malformed(self):
        for text in ["", "[", "ta]", "[]", "_ta", ",-_", "takabanana", "[ta]x0"]:
            with self.assertRaises(ValueError, msg=text):
                parse_phrase(text)

    def test_writing_needs_syllables(self):
        with self.assertRaises(ValueError):
            phrase_text(Phrase((1,), (NOTE,)))


class SpellTest(unittest.TestCase):
    meter = Meter.of((2, 2), 4)  # 4/4 in sixteenths
    threes = Phrase.stream(PitchClassSet((0, 3, 6, 9, 12, 15), 16))  # 16ths in 3s

    def test_one_phrase_four_ways(self):
        said = {
            "konnakol": "ta-ki-ta ta-ki-ta ta-ki-ta ta-ki-ta ta-ki-ta ta",
            "takadimi": "ta-ka-di mi-ta-ka di-mi-ta ka-di-mi ta-ka-di mi",
            "bols": "dha-na-na dha-na-na dha-na-na dha-na-na dha-na-na dha",
        }
        for system, text in said.items():
            spelled = spell(self.threes, system, self.meter)
            self.assertEqual(phrase_text(spelled), text, system)
            self.assertEqual(parse_phrase(text), spelled, system)
        self.assertEqual(counted(self.threes, self.meter, 4), "1-e-& a-2-e &-a-3 e-&-a 4-e-& a")

    def test_takadimi_names_the_place_in_the_beat(self):
        compound = Meter.of((2,), 3)  # two beats of triplets
        notes = Phrase.notes(PitchClassSet((0, 2, 3, 5), 6))
        self.assertEqual(phrase_text(spell(notes, "takadimi", compound)), "ta-_-da-ta-_-da")

    def test_chosen_sounds_are_kept(self):
        dhin = syllable_id("dhin")
        phrase = Phrase((1, 1, 1), (dhin, NOTE, NOTE), ((3,),))
        self.assertEqual(phrase_text(spell(phrase, "konnakol")), "dhin-ki-ta")

    def test_needs_a_matching_meter(self):
        for system in ("takadimi", "bols"):
            with self.assertRaises(ValueError):
                spell(self.threes, system)
        with self.assertRaises(ValueError):
            spell(self.threes, "morse")


class TalTest(unittest.TestCase):
    def test_marks_come_from_the_gestures(self):
        tals = load_tals()
        firsts = {name: [m for m in tala_marks(tal.meter) if m] for name, tal in tals.items()}
        self.assertEqual(firsts["teentaal"], ["X", "2", "0", "3"])
        self.assertEqual(firsts["ektaal"], ["X", "0", "2", "0", "3", "4"])
        self.assertEqual(firsts["rupak"], ["0", "1", "2"])  # sam on khali
        self.assertEqual(firsts["misra chapu"], ["X", "2", "3", "4"])

    def test_khali_is_the_bass_taken_out(self):
        theka = load_tals()["teentaal"].theka
        assert theka is not None
        text = phrase_text(theka).split()
        self.assertNotIn("dhin", text[8:12])  # the khali section, marked 0
        self.assertEqual(phrase_text(khali(theka)).split()[1:3], text[9:11])  # dhin -> tin

    def test_ektaal_beats_of_several_bols(self):
        theka = load_tals()["ektaal"].theka
        assert theka is not None
        self.assertEqual(theka.starts(), tuple(range(0, 48, 4)))  # twelve beats of 4 pulses
        self.assertEqual(theka.pulses, 48)


class CountingInputTest(unittest.TestCase):
    def test_a_bar_of_no_counts_is_rejected(self):
        with self.assertRaises(ValueError):
            counting(Meter.of((4,)), 0)


class TextInputTest(unittest.TestCase):
    def test_bad_text_says_what_is_wrong(self):
        with self.assertRaises(ValueError):
            phrase_text(Phrase((1,), (999,), ((1,),)))
        with self.assertRaisesRegex(ValueError, "repeat"):
            parse_phrase("[ta]x")
        with self.assertRaises(ValueError):
            parse_meter("³/8")


if __name__ == "__main__":
    unittest.main()
