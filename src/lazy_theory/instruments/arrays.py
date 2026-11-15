"""The array types every instrument module shares.

A voicing grid has one row per voicing and one fret (or MUTED) per string. Rule results are one
value per voicing, or one per pair of voicings for a change between chords.
"""

import numpy as np
from numpy.typing import NDArray

MUTED = -1  # a string that isn't played
Grid = NDArray[np.int16]  # frets or pitches
Floats = NDArray[np.float64]  # hertz, mm or costs; NaN where a string is silent
Mask = NDArray[np.bool_]
Counts = NDArray[np.int64]
