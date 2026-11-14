import unittest

import numpy as np

from lazy_theory.core.temperament import EqualTemperament
from lazy_theory.instruments.acoustics import roughness

TET = EqualTemperament()
C4 = 440 * TET.ratio(-9)


def chord(*steps: int, root: float = C4) -> np.ndarray:
    return np.array([[root * TET.ratio(step) for step in steps]])


class RoughnessTest(unittest.TestCase):
    def test_simpler_intervals_are_smoother(self):
        # minor 2nd, major 2nd, minor 3rd, major 3rd, 4th, 5th, octave
        values = [roughness(chord(0, step))[0] for step in (1, 2, 3, 4, 5, 7, 12)]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_the_same_interval_is_rougher_lower_down(self):
        self.assertGreater(roughness(chord(0, 4, root=C4 / 4))[0], roughness(chord(0, 4))[0])

    def test_wide_spacing_at_the_bottom_is_smoother(self):
        close, spread = chord(0, 4, 7, root=C4 / 2), chord(0, 7, 16, root=C4 / 2)
        self.assertGreater(roughness(close)[0], roughness(spread)[0])

    def test_silent_strings_add_nothing(self):
        with_silence = np.array([[C4, np.nan, C4 * TET.ratio(4)]])
        self.assertAlmostEqual(roughness(with_silence)[0], roughness(chord(0, 4))[0])


if __name__ == "__main__":
    unittest.main()
