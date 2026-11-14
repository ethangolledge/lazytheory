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
| `catalog` | | Names as data: scales, chords, tunings (TOML). Root note names | core |
| `instruments` | `fretboard` | Positions, intervals, every voicing and its bass on any tuning | core, NumPy |
| | `rules` | Swappable rules over voicing arrays; the smoothest path through a progression | |

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
- **Voicings are found window by window.** Each window starts at a voicing's lowest fretted note
  and is `max_span` frets wide, so each voicing is built once and impossible stretches are never
  built. Muted strings are allowed anywhere.
- **Playability is a set of small rules, not a list of shapes.** Each rule takes the voicing
  array and returns one value per row: fingers needed (a barre on the lowest fret counts once),
  contiguous strings, inside a fret region. Combine them with `&`; replace any rule without
  touching the others. Limits are parameters.
- **Inversions are chosen, not requested.** `smoothest` picks one voicing per chord with the
  least total movement over the whole progression (frets moved, plus a cost for each string
  that starts or stops), checking every path by keeping only the cheapest way to reach each
  voicing. The inversion falls out; `bass` reports it.
- **Inheritance only for shared behaviour; configuration otherwise.** `Scale` is a
  `PitchClassSet`. A guitar is a `Fretboard` with gaps `5 5 5 4 5`, not a `Guitar` class.
- **Immutable values, no I/O in core.** Frozen dataclasses; functions return values.
- **Tests come from the facts.** Each [math] claim in `theory.md` becomes a test.
