import unittest

import numpy as np

from lazy_theory.core.temperament import EqualTemperament
from lazy_theory.instruments import acoustics

TET = EqualTemperament()
C0 = 440 * TET.ratio(-57)
C4 = 48  # steps above C0


def roughness(steps: np.ndarray) -> np.ndarray:
    return acoustics.roughness(steps, C0, TET)


def chord(*steps: int, root: int = C4) -> np.ndarray:
    return np.array([[root + step for step in steps]], dtype=float)


class RoughnessTest(unittest.TestCase):
    def test_simpler_intervals_are_smoother(self):
        # minor 2nd, major 2nd, minor 3rd, major 3rd, 4th, 5th, octave
        values = [roughness(chord(0, step))[0] for step in (1, 2, 3, 4, 5, 7, 12)]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_the_same_interval_is_rougher_lower_down(self):
        self.assertGreater(roughness(chord(0, 4, root=C4 - 24))[0], roughness(chord(0, 4))[0])

    def test_wide_spacing_at_the_bottom_is_smoother(self):
        close, spread = chord(0, 4, 7, root=C4 - 12), chord(0, 7, 16, root=C4 - 12)
        self.assertGreater(roughness(close)[0], roughness(spread)[0])

    def test_silent_strings_add_nothing(self):
        with_silence = np.array([[C4, np.nan, C4 + 4]])
        self.assertAlmostEqual(roughness(with_silence)[0], roughness(chord(0, 4))[0])


class PureToneTest(unittest.TestCase):
    """Two pure tones (one partial each): roughness is Hutchinson & Knopoff's curve,
    (4y e^(1 - 4y))^2 at y critical bandwidths apart, the bandwidth 1.72 f^0.65 Hz at the
    pair's mean frequency, over the two tones' energy."""

    def test_matches_the_published_curve(self):
        for low, high in ((48, 49), (48, 50), (24, 25), (60, 64), (36, 48)):
            f, g = C0 * TET.ratio(low), C0 * TET.ratio(high)
            y = (g - f) / (1.72 * ((f + g) / 2) ** 0.65)
            curve = (4 * y * np.exp(1 - 4 * y)) ** 2 if y < 1.2 else 0.0
            found = acoustics.roughness(chord(0, high - low, root=low), C0, TET, harmonics=1)
            self.assertAlmostEqual(float(found[0]), curve / 2, places=12)

    def test_steps_are_whole(self):
        with self.assertRaises(ValueError):
            roughness(np.array([[48, 52.5]]))


if __name__ == "__main__":
    unittest.main()
