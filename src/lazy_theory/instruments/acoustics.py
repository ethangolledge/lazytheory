"""What a voicing sounds like: measures computed from its frequencies."""

from functools import lru_cache

import numpy as np
from numpy.typing import NDArray

from lazy_theory.core.temperament import EqualTemperament
from lazy_theory.instruments.arrays import Floats


def roughness(frequencies: Floats, harmonics: int = 11) -> Floats:
    """Roughness of each row of frequencies (hertz, NaN for silent strings): Hutchinson &
    Knopoff (1978), with the parameters Harrison & Pearce (2020) use.

    Each note is a harmonic tone with `harmonics` partials at amplitude 1/n. Two partials beat
    when they are less than 1.2 critical bandwidths apart, most at a quarter of one, and the
    critical bandwidth widens with frequency (1.72 * f ** 0.65 Hz), so the same interval is
    rougher lower down. Pairs are weighted by their amplitudes and normalised by total energy.

    A fretboard has few distinct frequencies, so the beating between each pair of them is
    computed once, and each voicing sums its notes' pairs from that table.
    """
    frequencies = np.sort(frequencies, axis=1)  # the same notes on other strings score the same
    sounding = ~np.isnan(frequencies)
    unique, note = np.unique(np.where(sounding, frequencies, 1.0), return_inverse=True)
    return _total(_beating(unique, harmonics), note.reshape(frequencies.shape), sounding, harmonics)


def tempered_roughness(
    steps: Floats, hertz: float, temperament: EqualTemperament, harmonics: int = 11
) -> Floats:
    """`roughness` of notes given as steps of `temperament` above `hertz` (NaN for silent).

    The same values, but the table of pairs covers whole octaves of steps and is kept, so
    every neck tuned from the same pitch reuses it.
    """
    if steps.size == 0:
        return np.zeros(len(steps))
    steps = np.sort(steps, axis=1)
    sounding = ~np.isnan(steps)
    size = temperament.size
    low = int(np.nanmin(steps)) // size * size
    high = (int(np.nanmax(steps)) // size + 1) * size
    table = _tempered_beating(hertz, temperament, low, high, harmonics)
    return _total(table, np.where(sounding, steps - low, 0).astype(np.intp), sounding, harmonics)


@lru_cache(maxsize=64)
def _tempered_beating(
    hertz: float, temperament: EqualTemperament, low: int, high: int, harmonics: int
) -> Floats:
    period = float(temperament.period)
    table = _beating(hertz * period ** (np.arange(low, high) / temperament.size), harmonics)
    table.flags.writeable = False
    return table


def _beating(frequencies: Floats, harmonics: int) -> Floats:
    """Amplitude-weighted beating between the partials of every pair of `frequencies`' tones,
    as [frequency, frequency]. Within one tone each pair of partials counts twice."""
    amplitude = 1 / np.arange(1, harmonics + 1)
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
    energy = ((1 / np.arange(1, harmonics + 1)) ** 2).sum()  # per tone, partials at 1/n
    rough: Floats = pairs / (sounding.sum(axis=1) * energy)
    return rough
