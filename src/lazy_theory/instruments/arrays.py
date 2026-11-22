"""The array types every instrument module shares.

Why: thousands of voicings are judged at once, so they live in arrays, not objects. A voicing
grid has one row per voicing and one fret (or MUTED) per string; a rule returns one value per
row, or one per pair of rows for a change between chords. Naming those few shapes once keeps
every signature readable.

Theory it speaks to: none of its own; it is the shape the rules (`rules`), the costs
(`acoustics`, `taste`) and the search (`trellis`) agree on.

Could grow into: a typed shape checker, if NumPy's typing comes to carry array shapes.
"""

import numpy as np
from numpy.typing import NDArray

MUTED = -1  # a string that isn't played
Grid = NDArray[np.int16]  # frets or pitches
Floats = NDArray[np.float64]  # hertz, mm or costs; NaN where a string is silent
Mask = NDArray[np.bool_]
Counts = NDArray[np.int64]
