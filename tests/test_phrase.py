import unittest
from itertools import product

from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.rhythm.meter import compositions
from lazy_theory.rhythm.phrase import NOTE, REST, Phrase

TAKADIMI_TAKITA = Phrase((1,) * 7, (NOTE,) * 7, ((4, 3),))


def phrases(pulses: int) -> list[Phrase]:
    """Every phrase of up to `pulses` pulses with one level of words: every way to cut the
    pulses into tokens, each a note or a rest (no two rests in a word), cut into words."""
    found = []
    for total in range(1, pulses + 1):
        for lengths in compositions(total, range(1, total + 1)):
            for sounds in product((NOTE, REST), repeat=len(lengths)):
                for words in compositions(len(lengths), range(1, len(lengths) + 1)):
                    try:
                        found.append(Phrase(lengths, sounds, (words,)))
                    except ValueError:
                        pass  # two rests inside a word
    return found


class PhraseTest(unittest.TestCase):
    def test_keeps_syllables_and_accents_apart(self):
        self.assertEqual(TAKADIMI_TAKITA.onsets(), PitchClassSet(tuple(range(7)), 7))
        self.assertEqual(TAKADIMI_TAKITA.accents(), PitchClassSet((0, 4), 7))

    def test_a_gap_inside_a_word(self):
        ta_rest_di_mi = Phrase((1, 1, 1, 1), (NOTE, REST, NOTE, NOTE), ((4,),))
        self.assertEqual(ta_rest_di_mi.onsets(), PitchClassSet((0, 2, 3), 4))
        self.assertEqual(ta_rest_di_mi.accents(), PitchClassSet((0,), 4))  # still one word

    def test_a_hold_is_a_longer_length(self):
        held = Phrase((2, 1, 1), (NOTE,) * 3)
        self.assertEqual(held.onsets(), PitchClassSet((0, 2, 3), 4))
        self.assertEqual(held.pulses, 4)

    def test_notes_and_stream_round_trip_onsets(self):
        for size in range(1, 9):
            for steps in compositions(size, range(1, size + 1)):
                for offset in range(steps[-1]):
                    onsets = PitchClassSet.from_steps(steps).transpose(offset)
                    with self.subTest(onsets=onsets):
                        self.assertEqual(Phrase.notes(onsets).onsets(), onsets)
                        self.assertEqual(Phrase.stream(onsets).accents(), onsets)

    def test_beats_share_a_grid(self):
        theka = Phrase.beats([[1], [2, 3], [1, 2, 3, 4]])  # dhin, dha-ge, ti-ra-ki-ta
        self.assertEqual(theka.lengths, (4, 2, 2, 1, 1, 1, 1))
        self.assertEqual(theka.starts(), (0, 4, 8))

    def test_rejects_malformed(self):
        for lengths, sounds, groups in [
            ((), (), ()),
            ((1,), (NOTE, NOTE), ()),
            ((0,), (NOTE,), ()),
            ((1, 1), (REST, REST), ()),  # two rests in one word
            ((1, 1), (NOTE, NOTE), ((3,),)),
        ]:
            with self.assertRaises(ValueError):
                Phrase(lengths, sounds, groups)
        self.assertEqual(Phrase((1, 1), (REST, REST), ((1, 1),)).pulses, 2)  # two rest words


class MoveTest(unittest.TestCase):
    every = phrases(5)

    def test_joining_is_associative_and_adds_lengths(self):
        a, b, c = TAKADIMI_TAKITA, TAKADIMI_TAKITA.grouped(), Phrase((2,), (NOTE,))
        self.assertEqual((a + b) + c, a + (b + c))
        self.assertEqual((a + c).pulses, a.pulses + c.pulses)

    def test_reversal_and_speed_invert(self):
        for phrase in self.every:
            with self.subTest(phrase=phrase):
                self.assertEqual(phrase.reversed().reversed(), phrase)
                self.assertEqual(phrase.scaled(3).faster(3), phrase)

    def test_rotation_round_the_top_groups(self):
        for phrase in self.every:
            count = len(phrase.groups[0])
            for k in range(count):
                with self.subTest(phrase=phrase, k=k):
                    turned = phrase.rotated(k)
                    self.assertEqual(turned.rotated(count - k), phrase)
                    if NOTE in phrase.sounds:  # displacement: the onsets, moved
                        moved = phrase.onsets().transpose(-phrase.starts(0)[k])
                        self.assertEqual(turned.onsets(), moved)

    def test_faster_needs_whole_lengths(self):
        with self.assertRaises(ValueError):
            Phrase((3, 2), (NOTE, NOTE)).faster(2)

    def test_a_tihai_needs_at_least_one_statement(self):
        for times in (0, -5):
            with self.subTest(times=times), self.assertRaises(ValueError):
                Phrase((1,), (NOTE,)).tihai(1, times=times)

    def test_tihai_is_three_statements_and_two_gaps(self):
        for phrase in self.every:
            for gap in range(3):
                for hold in (False, True):
                    tihai = phrase.tihai(gap, hold=hold)
                    with self.subTest(phrase=phrase, gap=gap, hold=hold):
                        self.assertEqual(tihai.pulses, 3 * phrase.pulses + 2 * gap)
                        self.assertEqual(len(tihai.groups[0]), 3)
                        statement = len(phrase) + (gap > 0 and not hold)
                        self.assertEqual(tihai.starts(0)[1], phrase.pulses + gap)
                        self.assertEqual(tihai.groups[0][0], statement)

    def test_regroup_keeps_the_stream(self):
        fours = Phrase((1,) * 12, (NOTE,) * 12, ((4, 4, 4),))
        threes = fours.regrouped((3, 3, 3, 3))
        self.assertEqual(threes.onsets(), fours.onsets())
        self.assertEqual(threes.accents(), PitchClassSet((0, 3, 6, 9), 12))  # gati bhedam

    def test_substitute_and_permute(self):
        dha, ta = 1, 2
        bols = Phrase((1, 1, 1), (dha, dha, ta), ((1, 2),))
        self.assertEqual(bols.substituted({dha: ta}).sounds, (ta, ta, ta))
        swapped = bols.permuted((1, 0))
        self.assertEqual(swapped.sounds, (dha, ta, dha))
        self.assertEqual(swapped.groups, ((2, 1),))
        self.assertEqual(swapped.permuted((1, 0)), bols)
        with self.assertRaises(ValueError):
            bols.permuted((0, 0))

    def test_yati_cuts_statements_from_the_end(self):
        takita = Phrase((1, 1, 1), (1, 2, 3), ((3,),))  # ta ki ta, as ids
        grow = takita.yati((1, 2, 3))  # srotovaha: ta / ki-ta / ta-ki-ta
        self.assertEqual(grow.sounds, (3, 2, 3, 1, 2, 3))
        self.assertEqual(grow.groups[0], (1, 2, 3))
        self.assertEqual(takita.yati((3, 2, 1), from_start=True).sounds, (1, 2, 3, 1, 2, 1))
        with self.assertRaises(ValueError):
            takita.yati((4,))


class CycleTest(unittest.TestCase):
    def test_a_cycle_of_no_pulses_is_refused(self):
        phrase = Phrase.notes(PitchClassSet((0, 2), 4))
        with self.assertRaises(ValueError):
            phrase.onsets(size=0)
        self.assertEqual(phrase.onsets(size=8), PitchClassSet((0, 2), 8))


class AccentLevelTest(unittest.TestCase):
    def test_a_level_the_phrase_has(self):
        with self.assertRaises(ValueError):
            Phrase.notes(PitchClassSet((0, 2), 4)).accents(level=5)


if __name__ == "__main__":
    unittest.main()
