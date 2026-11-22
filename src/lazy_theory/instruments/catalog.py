"""Named tunings, loaded from TOML: each a set of open strings on a neck of a given length.

Why: "drop D" is a convention, so it is data. Each tuning is written as its lowest string and
the steps up to each next one, so a re-entrant ukulele is a negative step, and pitches are
read once, in the pitch frame (`pitch.catalog.pitch`), against the file's reference.

Your own files load as `lazy_theory.data` describes.
"""

from collections.abc import Mapping
from fractions import Fraction
from itertools import accumulate
from pathlib import Path

from lazy_theory.core.temperament import EqualTemperament
from lazy_theory.data import add, bundled_once, read
from lazy_theory.instruments.fretboard import Tuning
from lazy_theory.pitch.catalog import TWELVE, pitch


@bundled_once
def load_tunings(path: Path | None = None) -> Mapping[str, Tuning]:
    """Every named tuning, keyed by instrument and name, e.g. "guitar standard". An
    instrument's `steps` per `period` (twelve to the octave, 2, if not given) is its
    temperament; outside twelve to the octave, `first` is steps above C0, since note names are
    for twelve."""
    data = read(__name__, "tunings.toml", path)
    reference = data["reference"]  # a note name, so in twelve steps
    hertz = reference["hertz"] * EqualTemperament(TWELVE).ratio(-pitch(reference["note"]))
    tunings: dict[str, Tuning] = {}
    for instrument, entry in data.items():
        if instrument == "reference":
            continue
        temperament = EqualTemperament(entry.get("steps", TWELVE), Fraction(entry.get("period", 2)))
        for name, tuning in entry["tunings"].items():
            first = tuning["first"]
            if temperament != EqualTemperament(TWELVE) and not isinstance(first, int):
                raise ValueError(f"{instrument} {name}: give `first` in steps above C0")
            start = first if isinstance(first, int) else pitch(first)
            strings = tuple(accumulate(tuning["gaps"], initial=start))
            add(
                tunings,
                f"{instrument} {name}",
                Tuning(strings, entry["scale_length"], hertz, temperament),
            )
    return tunings
