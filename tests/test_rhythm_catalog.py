import unittest

from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.rhythm.catalog import load_talas, load_timelines
from lazy_theory.rhythm.meter import (
    CLAP,
    WAVE,
    Meter,
    gaps,
    unevenness,
)

FOUR_FOUR_SIXTEENTHS = Meter.of((2, 2), 4)


class TalaTest(unittest.TestCase):
    def test_suladi_talas(self):
        talas = load_talas()
        self.assertEqual(len(talas), 35)  # 7 families x 5 jatis
        lengths = {name: meter.pulses for name, meter in talas.items()}
        self.assertEqual(lengths["chatusra triputa"], 8)  # Adi tala
        self.assertEqual(talas["chatusra triputa"].levels[1], (4, 2, 2))
        self.assertEqual(lengths["chatusra dhruva"], 14)
        self.assertEqual(lengths["khanda ata"], 14)
        self.assertEqual(lengths["misra jhampa"], 10)
        self.assertEqual((min(lengths.values()), max(lengths.values())), (3, 29))

    def test_suladi_gestures_and_no_accents_inside_a_laghu(self):
        adi = load_talas()["chatusra triputa"]
        self.assertEqual(adi.hands, (CLAP, 1, 2, 3, CLAP, WAVE, CLAP, WAVE))
        self.assertEqual(adi.weights(), (3, 1, 1, 1, 2, 1, 2, 1))
        misra = load_talas()["misra triputa"]  # a laghu of 7: no 3+2+2 inside it
        self.assertEqual(misra.weights()[:7], (3, 1, 1, 1, 1, 1, 1))


class TimelineTest(unittest.TestCase):
    """Toussaint, "A Mathematical Analysis of African, Brazilian, and Cuban Clave Rhythms"
    (Bridges 2002), with the bembe bell from Toussaint (2005)."""

    def setUp(self):
        self.timelines = load_timelines()

    def test_metric_complexity_matches_the_published_table(self):
        # 17 minus the sum of Lerdahl & Jackendoff's 16-pulse weights, which are this meter's
        weight = FOUR_FOUR_SIXTEENTHS.weights()
        published = {"shiko": 2, "son": 4, "soukous": 6, "rumba": 5, "bossa-nova": 6, "gahu": 5}
        for name, complexity in published.items():
            onsets = self.timelines[name]
            self.assertEqual(17 - sum(weight[p] for p in onsets), complexity, name)

    def test_symmetries(self):
        def mirrored(onsets: PitchClassSet, axis: int) -> PitchClassSet:
            return PitchClassSet(tuple(2 * axis - p for p in onsets), onsets.size)

        for name in ("shiko", "bossa-nova"):  # palindromes about 0
            self.assertEqual(mirrored(self.timelines[name], 0), self.timelines[name], name)
        son = self.timelines["son"]
        self.assertNotEqual(mirrored(son, 0), son)
        self.assertEqual(mirrored(son, 3), son)  # a weak palindrome, about 3
        self.assertEqual(unevenness(self.timelines["bossa-nova"]), 0)  # maximally even

    def test_bembe_is_the_major_scale(self):
        self.assertEqual(gaps(self.timelines["bembe"]), (2, 2, 1, 2, 2, 2, 1))


if __name__ == "__main__":
    unittest.main()
