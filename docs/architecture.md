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
| `instruments` | `fretboard` | Positions, every voicing within a hand's reach, and each voicing's pitches, frequencies, stack of intervals and hand position. A capo returns a new, shorter fretboard | core, catalog, NumPy |
| | `acoustics` | Roughness of each voicing from its frequencies | NumPy |
| | `rules` | Swappable rules over voicing arrays; the cheapest path through a progression | |
| | `taste` | `Taste`: one player's rules and weights; voicings, costs and the cheapest path on any neck | |
| `suggest` | `tunings` | Optional: retunings and capos ranked for a progression and key, screened cheaply then searched; names from the catalog | catalog, instruments, NumPy |
| | `melody` | Optional: harmonise a melody, one chord per note with the note on top; `MelodicTaste(Taste)` adds parallel and contrary-motion costs | |
| | `extensions` | Optional: extended chords derived from the key (core plus any of the 7th, 9th, 11th, 13th), spelled by stack number | catalog, core |

Planned: `rhythm` (cycles, groupings, subdivisions) in core; `export` (tables for the web app)
on top.

## Decisions

- **Intervals in one frame.** Everything is steps from a root, and every pitch is measured from
  one origin: steps above C0 (E2 is 28), so a root is a pitch class with C = 0 on every
  instrument and any two things compare by subtraction. The origin and the note letters are
  catalog conventions (`pitch`, `pitch_class`); core only sees integers. The letters are not a
  table: they are the Ionian scale on C.
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
  nothing is missed. Rules then remove what a hand can't play and costs rank the rest. The grid
  grows one string at a time over each chord's playable frets, and a row is dropped as soon as
  its fretted notes span more than `reach` mm (or, if asked, a muted string splits the sounding
  ones), so impossible stretches are never built. `voicings_of` builds a whole progression in
  that one pass, with a column saying which chord each row plays.
- **Physical measures in physical units.** Reach and hand movement are millimetres, from the fret
  positions the temperament and scale length give; roughness is computed from frequencies in
  hertz. So the same rules hold on a bass, a ukulele or a 31-EDO guitar.
- **Playability is a set of small rules, not a list of shapes.** Each rule takes the voicing
  array and returns one value per row: the fewest fingers needed (a barre lies to the highest string),
  whether those fingers fit the hand in fret order,
  contiguous strings, inside a fret region, open strings only near the hand. Combine them with `&`; replace any rule without
  touching the others. Limits are parameters.
- **Inversions are chosen, not requested.** `smoothest` takes a cost per voicing (e.g.
  roughness) and a cost per change (e.g. hand movement, steps moved on each string, bass
  motion) and picks one voicing per chord with the least total over the whole progression,
  checking every path by keeping only the cheapest way to reach each voicing. The inversions
  fall out; `stack` reports them. The weights are arguments, because they are not yet measured
  for guitar.
- **One taste, many searches.** Rules and weights live in one frozen `Taste`, so every search
  scores voicings the same way and a preference changes in one place. Reach is millimetres, so a
  capo doesn't shrink the hand. The neck is cut at the highest allowed fret before voicings are
  built, not filtered after. A neck's chords are built, filtered and scored together, and
  roughness reads a table of note pairs computed once per reference pitch.
- **Suggestions are opt-in.** `suggest` sits on top and nothing imports it: standard tuning stays
  the default. Candidate tunings are generated, not looked up: every string moved within safe
  tension (4 steps down, 2 up), then named afterwards by matching the catalog, shifts included
  ("open D +2"). A screen scores every retuning at every capo at once by how many open strings
  are chord tones: each string's count depends only on its own step and the capo, so six small
  [step, capo] tables are broadcast into the full array, and a partition picks the shortlist
  without sorting it. Only the shortlist gets the full path search. Retuning
  costs per step, so the base tuning wins unless another clearly sounds better, and the key's
  other chords can be weighed in so a neck isn't chosen for three easy shapes alone.
- **Features extend, not edit.** Optional features subclass what exists: `MelodicTaste` is a
  `Taste` whose `transition` adds voice-motion costs to `super()`'s, so every search that takes a
  Taste takes it too, and the foundations don't change.
- **Inheritance only for shared behaviour; configuration otherwise.** `Scale` is a
  `PitchClassSet`. A guitar is a `Fretboard` with gaps `5 5 5 4 5`, not a `Guitar` class.
- **Immutable values, no I/O in core.** Frozen dataclasses; functions return values.
- **Tests come from the facts.** Each [math] claim in `theory.md` becomes a test.
