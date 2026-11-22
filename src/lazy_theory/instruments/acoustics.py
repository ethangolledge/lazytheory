"""What a voicing sounds like: measures computed from its frequencies.

Why: "does this voicing sound good" should not be an opinion in the code. The part of it that
is physics can be computed: partials of two notes that fall close together beat, and the ear
hears that as roughness. It is why the same third sounds clear high on the neck and muddy on
the low strings, and why a voicing, not just a chord, has a sound.

Theory it speaks to: sensory dissonance (Helmholtz; Plomp & Levelt 1965) in the form of
Hutchinson & Knopoff (1978), with the parameters of Harrison & Pearce (2020), who found
consonance to be roughness, harmonicity and familiarity together. Only roughness is here.

Could grow into: harmonicity (how well the notes fit one harmonic series), real string
spectra and inharmonicity in place of ideal 1/n partials, and loudness per string.
"""

from functools import lru_cache

import numpy as np
from numpy.typing import NDArray

from lazy_theory.core.temperament import EqualTemperament
from lazy_theory.instruments.arrays import Floats


def roughness(
    steps: Floats, hertz: float, temperament: EqualTemperament, harmonics: int = 11
) -> Floats:
    """Roughness of each row of notes, given as steps of `temperament` above `hertz` (NaN for a
    silent string): Hutchinson & Knopoff (1978), with the parameters Harrison & Pearce (2020)
    use.

    Each note is a harmonic tone with `harmonics` partials at amplitude 1/n. Two partials beat
    when they are less than 1.2 critical bandwidths apart, most at a quarter of one, and the
    critical bandwidth widens with frequency (1.72 * f ** 0.65 Hz), so the same interval is
    rougher lower down. Pairs are weighted by their amplitudes and normalised by total energy.

    A neck has few distinct notes, so the beating between every pair of steps in the octaves
    played is computed once and kept: every neck tuned from the same pitch reuses the table,
    and each voicing only sums its notes' pairs from it.
    """
    steps = np.sort(steps, axis=1)
    sounding = ~np.isnan(steps)
    if not sounding.any():
        return np.zeros(len(steps))
    size = temperament.size
    low = int(np.nanmin(steps)) // size * size
    high = (int(np.nanmax(steps)) // size + 1) * size
    table = _tempered_beating(hertz, temperament, low, high, harmonics)
    return _total(table, np.where(sounding, steps - low, 0).astype(np.intp), sounding, harmonics)


@lru_cache(maxsize=64)
def _tempered_beating(
    hertz: float, temperament: EqualTemperament, low: int, high: int, harmonics: int
) -> Floats:
    table = _beating(hertz * temperament.ratio(np.arange(low, high)), harmonics)
    table.flags.writeable = False
    return table


def _beating(frequencies: Floats, harmonics: int) -> Floats:
    """Amplitude-weighted beating between the partials of every pair of `frequencies`' tones,
    as [frequency, frequency]. Within one tone each pair of partials counts twice."""
    amplitude = _amplitudes(harmonics)
    partials = frequencies[:, None] * np.arange(1, harmonics + 1)  # [frequency, partial]
    low, high = partials[:, :, None, None], partials[None, None, :, :]
    distance = np.abs(high - low) / (1.72 * ((low + high) / 2) ** 0.65)
    beating = np.where(distance < 1.2, (4 * distance * np.exp(1 - 4 * distance)) ** 2, 0.0)
    weighted = beating * amplitude[None, :, None, None] * amplitude[None, None, None, :]
    pair: Floats = weighted.sum(axis=(1, 3))
    return pair


def _total(
    pair: Floats, note: NDArray[np.intp], sounding: NDArray[np.bool_], harmonics: int
) -> Floats:
    """Each voicing's beating, summed over its pairs of notes (indices into `pair`), over the
    energy of its tones."""
    weight = sounding[:, :, None] & sounding[:, None, :]
    pairs = (pair[note[:, :, None], note[:, None, :]] * weight).sum(axis=(1, 2)) / 2
    energy = (_amplitudes(harmonics) ** 2).sum()  # per tone
    rough: Floats = pairs / (np.maximum(sounding.sum(axis=1), 1) * energy)  # silence is smooth
    return rough


def _amplitudes(harmonics: int) -> Floats:
    """Each partial's amplitude in an ideal harmonic tone: 1/n."""
    amplitudes: Floats = 1 / np.arange(1, harmonics + 1)
    return amplitudes
