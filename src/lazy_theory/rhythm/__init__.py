"""Rhythm: onsets on a cycle, meters, spoken phrases, cadences, and the words for them.
Independent of pitch: it shares only the circle maths in `core`.

A rhythm has three forms, each for one job:
- a `Performance` is what was played, every onset at its exact time, never changed;
- a `Phrase` is what is written or spoken: syllables, rests and holds, grouped into words;
- an onset set (`PitchClassSet` of pulses) is what every measure reads, projected from either.
"""
