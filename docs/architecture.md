# Architecture

How the code turns [theory.md](theory.md) into software.

## Layers

Each layer imports only from itself and the layers above it in this table.
`tests/test_architecture.py` enforces this; add new layers to its `LAYERS` list.

| Layer | Module | Does | Dependencies |
|---|---|---|---|
| `core` | `temperament` | Steps → frequency ratio and cents | standard library |
| | `pcset` | `PitchClassSet`: sets mod `size`, built from steps or maximal evenness; rotate, transpose | |
| | `scale` | `Scale(PitchClassSet)`: always contains its root; stacks chords by stride | |
| | `chord` | `identify`: names a set against patterns passed in, trying every root | |
| | `voice_leading` | Smallest total movement between two sets, voice by voice | |
| `catalog` | | Names as data: scales, chords, tunings with scale length and frequency (TOML). Note names | core |
| `instruments` | `fretboard` | Positions, every voicing within a hand's reach, and each voicing's pitches, frequencies, stack of intervals and hand position | core, catalog, NumPy |
| | `acoustics` | Roughness of each voicing from its frequencies | NumPy |
| | `rules` | Swappable rules over voicing arrays; the cheapest path through a progression | |

Planned: `rhythm` (cycles, groupings, subdivisions) in core; `export` (tables for the web app)
on top.

## Decisions

- **Relative everywhere; one name.** Everything is steps from a root. The only note name is the
  root, given against a tuning's first string (`tuning.root("A")`). The letters are not a table:
  they are the Ionian scale on C.
- **Conventions are data.** Mode, chord and tuning names live in `catalog`. Core never imports
  it; `identify` takes its patterns as an argument.
- **Derived, not listed.** Chords come from stacking a scale; modes from rotation; symmetric
  sets from maximal evenness; secondary dominants, tritone substitutes and borrowed chords from
  `chord`, `rotate`, `transpose` and `voice_leading` (see `tests/test_harmony.py`). No chord
  shapes, scale boxes or function tables are stored.
- **Ints until there is behaviour.** No `Interval` class (a step count) and no `Chord` class (a
  `PitchClassSet`) until something needs more.
- **NumPy at the instrument, tuples in core.** Core sets hold 3 to 8 numbers and must be
  hashable, where tuples are faster. The fretboard works on whole grids and every combination of
  strings, where vectors pay off.
- **Map every voicing, then work backwards.** `voicings` builds every voicing within reach, so
  nothing is missed. Rules then remove what a hand can't play and costs rank the rest. Each
  window starts at a voicing's lowest fretted note and ends `reach` mm up the neck, so each
  voicing is built once and impossible stretches are never built.
- **Physical measures in physical units.** Reach and hand movement are millimetres, from the fret
  positions the temperament and scale length give; roughness is computed from frequencies in
  hertz. So the same rules hold on a bass, a ukulele or a 31-EDO guitar.
- **Playability is a set of small rules, not a list of shapes.** Each rule takes the voicing
  array and returns one value per row: the fewest fingers needed (a finger can barre any fret),
  contiguous strings, inside a fret region. Combine them with `&`; replace any rule without
  touching the others. Limits are parameters.
- **Inversions are chosen, not requested.** `smoothest` takes a cost per voicing (e.g.
  roughness) and a cost per change (e.g. hand movement, steps moved on each string, bass
  motion) and picks one voicing per chord with the least total over the whole progression,
  checking every path by keeping only the cheapest way to reach each voicing. The inversions
  fall out; `stack` reports them. The weights are arguments, because they are not yet measured
  for guitar.
- **Inheritance only for shared behaviour; configuration otherwise.** `Scale` is a
  `PitchClassSet`. A guitar is a `Fretboard` with gaps `5 5 5 4 5`, not a `Guitar` class.
- **Immutable values, no I/O in core.** Frozen dataclasses; functions return values.
- **Tests come from the facts.** Each [math] claim in `theory.md` becomes a test.
