"""Music theory as intervals and maths. See docs/theory.md and docs/architecture.md.

The names a newcomer reaches for first are importable from here (`from lazy_theory import
Chord, Fretboard, Taste`); each lives in its domain's package and is loaded only when first
used, so importing the standard-library core never pulls in NumPy. (`pitch` and `suggest`
are not among them: those names are packages.)
"""

from importlib import import_module
from typing import TYPE_CHECKING, Any

_HOMES = {  # name: the module it lives in
    "PitchClassSet": "core.pcset",
    "EqualTemperament": "core.temperament",
    "Scale": "pitch.scale",
    "Chord": "pitch.chord",
    "Key": "pitch.key",
    "load_scales": "pitch.catalog",
    "load_chords": "pitch.catalog",
    "chord_names": "pitch.catalog",
    "pitch_class": "pitch.catalog",
    "chord_symbol": "pitch.names",
    "parse_chord": "pitch.names",
    "note_name": "pitch.names",
    "Meter": "rhythm.meter",
    "Phrase": "rhythm.phrase",
    "Performance": "rhythm.performance",
    "Fretboard": "instruments.fretboard",
    "Taste": "instruments.taste",
    "Trellis": "instruments.trellis",
    "load_tunings": "instruments.catalog",
    "tab": "instruments.names",
    "named": "suggest.neighbours",
    "harmonise": "suggest.harmonise",
}

__all__ = sorted(_HOMES)


def __getattr__(name: str) -> Any:
    if name not in _HOMES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(import_module(f"{__name__}.{_HOMES[name]}"), name)


if TYPE_CHECKING:  # the same names for type checkers and editors (a test keeps them in step)
    from lazy_theory.core.pcset import PitchClassSet as PitchClassSet
    from lazy_theory.core.temperament import EqualTemperament as EqualTemperament
    from lazy_theory.instruments.catalog import load_tunings as load_tunings
    from lazy_theory.instruments.fretboard import Fretboard as Fretboard
    from lazy_theory.instruments.names import tab as tab
    from lazy_theory.instruments.taste import Taste as Taste
    from lazy_theory.instruments.trellis import Trellis as Trellis
    from lazy_theory.pitch.catalog import chord_names as chord_names
    from lazy_theory.pitch.catalog import load_chords as load_chords
    from lazy_theory.pitch.catalog import load_scales as load_scales
    from lazy_theory.pitch.catalog import pitch_class as pitch_class
    from lazy_theory.pitch.chord import Chord as Chord
    from lazy_theory.pitch.key import Key as Key
    from lazy_theory.pitch.names import chord_symbol as chord_symbol
    from lazy_theory.pitch.names import note_name as note_name
    from lazy_theory.pitch.names import parse_chord as parse_chord
    from lazy_theory.pitch.scale import Scale as Scale
    from lazy_theory.rhythm.meter import Meter as Meter
    from lazy_theory.rhythm.performance import Performance as Performance
    from lazy_theory.rhythm.phrase import Phrase as Phrase
    from lazy_theory.suggest.harmonise import harmonise as harmonise
    from lazy_theory.suggest.neighbours import named as named
