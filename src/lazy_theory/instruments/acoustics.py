"""What a voicing sounds like: measures computed from its frequencies."""

import numpy as np
from numpy.typing import NDArray

Floats = NDArray[np.float64]


def roughness(frequencies: Floats, harmonics: int = 11) -> Floats:
    """Roughness of each row of frequencies (hertz, NaN for silent strings): Hutchinson &
    Knopoff (1978), with the parameters Harrison & Pearce (2020) use.

    Each note is a harmonic tone with `harmonics` partials at amplitude 1/n. Two partials beat
    when they are less than 1.2 critical bandwidths apart, most at a quarter of one, and the
    critical bandwidth widens with frequency (1.72 * f ** 0.65 Hz), so the same interval is
    rougher lower down. Pairs are weighted by their amplitudes and normalised by total energy.
    """
    number = np.arange(1, harmonics + 1)
    partials = (frequencies[:, :, None] * number).reshape(len(frequencies), -1)
    amplitudes = np.where(np.isnan(partials), 0.0, np.tile(1 / number, frequencies.shape[1]))
    first, second = np.triu_indices(partials.shape[1], k=1)
    low, high = partials[:, first], partials[:, second]
    distance = np.abs(high - low) / (1.72 * ((low + high) / 2) ** 0.65)
    beating = np.where(distance < 1.2, (4 * distance * np.exp(1 - 4 * distance)) ** 2, 0.0)
    pairs = (amplitudes[:, first] * amplitudes[:, second] * beating).sum(axis=1)
    rough: Floats = pairs / (amplitudes**2).sum(axis=1)
    return rough
