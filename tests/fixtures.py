"""Values the tests share: the bundled catalog, one standard guitar, and two small helpers."""

import numpy as np

from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.instruments.arrays import MUTED
from lazy_theory.instruments.catalog import load_tunings
from lazy_theory.instruments.fretboard import Fretboard
from lazy_theory.pitch.catalog import load_chords, load_scales, pitch_class
from lazy_theory.pitch.key import Key

X = MUTED
TUNINGS = load_tunings()
SCALES = load_scales()
CHORDS = load_chords()
IONIAN = SCALES["Ionian"]
MAJOR = PitchClassSet((0, 4, 7))
MINOR = PitchClassSet((0, 3, 7))
STANDARD = Fretboard.from_tuning(TUNINGS["guitar standard"])
REACH = STANDARD.fret_distance[4] - STANDARD.fret_distance[1]  # one finger per fret, frets 1-4


def rows(*voicings: list[int]) -> np.ndarray:
    """Voicings written as fret lists, as the grid every instrument function takes."""
    return np.array(voicings, dtype=np.int16)


def key(mode: str, tonic: str) -> Key:
    """A key by name: key("Phrygian", "E")."""
    return Key(SCALES[mode], pitch_class(tonic))
