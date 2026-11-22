"""Named tunings, loaded from TOML: each a set of open strings on a neck of a given length.

Why: "drop D" is a convention, so it is data. Each tuning is written as its lowest string and
the steps up to each next one, so a re-entrant ukulele is a negative step, and pitches are
read once, in the pitch frame (`pitch.catalog.pitch`), against the file's reference.

Pass a path to load your own file instead of the bundled one.
"""

from collections.abc import Mapping
from functools import cache
from itertools import accumulate
from pathlib import Path

from lazy_theory.core.temperament import EqualTemperament
from lazy_theory.data import add, read
from lazy_theory.instruments.fretboard import Tuning
from lazy_theory.pitch.catalog import major, pitch

_PACKAGE = __name__.rpartition(".")[0]  # where the bundled data files sit


@cache
def load_tunings(path: Path | None = None) -> Mapping[str, Tuning]:
    """Every named tuning, keyed by instrument and name, e.g. "guitar standard"."""
    data = read(_PACKAGE, "tunings.toml", path)
    reference = data["reference"]
    temperament = EqualTemperament(major().size)
    hertz = reference["hertz"] * temperament.ratio(-pitch(reference["note"]))
    tunings: dict[str, Tuning] = {}
    for instrument, entry in data.items():
        if instrument == "reference":
            continue
        for name, tuning in entry["tunings"].items():
            strings = accumulate(tuning["gaps"], initial=pitch(tuning["first"]))
            add(
                tunings,
                f"{instrument} {name}",
                Tuning(tuple(strings), entry["scale_length"], hertz),
            )
    return tunings
