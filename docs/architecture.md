# Architecture

How the code turns [theory.md](theory.md) into software. Every module's own docstring says why
it exists, which theory it speaks to and what it could grow into; this page is the map.

## The framework in one page

Music is modelled as five kinds of value, each with one job. A feature is a new function over
them, not a new kind of value.

| Value | What it is | Where |
|---|---|---|
| **Step** | An integer. Pitch is steps above C0; a pitch class is pitch mod the steps per period (C = 0); an interval is a difference of two. There is no `Note` or `Interval` class | everywhere |
| **Set** | `PitchClassSet`: points on the circle of steps. A `Scale` is a set that holds 0 | `core.pcset`, `core.scale` |
| **Set on a root** | `Rooted(pattern, root)`: a pattern placed on a pitch class. `Chord` adds a bass under a slash; `Key` adds the chords on its degrees. Same arithmetic for both | `core.chord`, `core.key` |
| **Grid** | Voicings as an array, one row each, one fret (or MUTED) per string. Every measure of a voicing is a function from a grid to one value per row | `instruments` |
| **Trellis** | A progression as a graph: one layer per chord, one node per voicing, a cost per node and per change. Every "how should I play this" is a shortest path through it, with masks for what is allowed | `instruments.trellis` |

Words (note names, symbols, numerals) appear only in `catalog.names`, built from numbers at the
edge and read back into numbers at the edge.

The flow of almost every feature:

```
names ──parse──▶ Chords ──Fretboard.voicings_of──▶ grids ──Taste.allows──▶ options
                                                                      │ Taste.standing, transition
 words ◀──chord_symbol, tab── Route ◀──shortest / each / tied / search── Trellis
```

## Layers

Each layer imports only from itself and the layers above it in this table.
`tests/test_architecture.py` enforces this; add new layers to its `LAYERS` list.

| Layer | Module | Does | Dependencies |
|---|---|---|---|
| `core` | `temperament` | Steps → frequency ratio (`ratio`, one step or an array of them), ratio → steps, cents. Every frequency and fret distance comes from here | standard library |
| | `pcset` | `PitchClassSet`: sets mod `size`, built from steps or maximal evenness; rotate, transpose, `in`; `shortest`, the signed short way round the circle (voice leading and accidentals both use it) | |
| | `scale` | `Scale(PitchClassSet)`: always contains its root; stacks notes and chords by stride | |
| | `chord` | `Rooted`: a pattern on a root (notes, interval of a pitch, `in`). `Chord(Rooted)` with an optional bass and `with_note`; `identify` reads a set as every chord it could be | |
| | `key` | `Key(Rooted)`: a scale on a root, and the chord on each degree | |
| | `voice_leading` | Smallest total movement between two sets, voice by voice; exact, by dynamic programming | |
| | `attraction` | Lerdahl's melodic attraction: each pitch class's stability in a key, and the pull of one pitch to another | |
| `catalog` | | Names as data: scales, chords and their symbols, tunings as open-string pitches (TOML). `pitch`, `pitch_class`: note names into the integer frame; `major`, `accidentals`, `alteration`: the scale and the sharps and flats every name is written in; `chord_names`: patterns back to names | core |
| | `names` | The only way to and from words: `interval_name` (one rule for degrees, chord tones, extensions and numerals), spelled notes, chord symbols and `parse_chord`, Roman numerals, tab | |
| `instruments` | `arrays` | The shared array types: voicing grids, `MUTED`, masks, counts | NumPy |
| | `fretboard` | Positions, every voicing within a hand's reach (with a written bass lowest), and each voicing read back: pitches, bass, top, chroma, frequencies, stack of intervals, `readings` as chords. A capo returns a new, shorter fretboard | core, catalog, NumPy |
| | `acoustics` | Roughness of each voicing from its frequencies | NumPy |
| | `rules` | Small measures on grids: barres, fingers, whether a shape fits the hand, fret region, strings sounding, steps moved, strings changed | |
| | `trellis` | `Trellis`: the progression as a graph. `shortest` (with masks), `search` (many masked searches at once), `each` (the best route per line), `tied` (a repeated chord keeps its shape) | |
| | `taste` | `Taste`: one player's rules and weights. `allows`, `standing`, `transition` are the three seams; `options`, `trellis`, `path`, `lines` are built from them | |
| `suggest` | `tunings` | Optional: retunings and capos ranked for a progression and key, screened cheaply then searched; names from the catalog | catalog, instruments, NumPy |
| | `melody` | Optional: harmonise a melody, one chord per note with the note on top; `MelodicTaste(Taste)` adds parallel and contrary-motion costs | |
| | `neighbours` | Optional: the chord a shape plays (`named`), chords one finger away, and the shapes passing between two (each voice moved or not yet) | |
| | `drones` | Optional: a note held on one string through several chords, joining the chords it isn't in | |
| | `extensions` | Optional: extended chords derived from the key (core plus any of the 7th, 9th, 11th, 13th) | core |

Planned: `rhythm` (cycles, groupings, subdivisions) in core.

## Extending

Most features are one of five moves. Each has a worked example in the code.

| To add | Do this | Example |
|---|---|---|
| A scale, chord, tuning or name | Add a line to a TOML file. No code | `catalog/chords.toml`: `"fifth" = [0, 7]` made power chords nameable, parseable and readable from shapes |
| A property of a voicing or of a change | Write a function from grids to one value per row (or per pair of rows) | `rules.strings_changed`, `melody.parallels` |
| A preference or a hard rule | Subclass `Taste` and extend `allows` (a rule), `standing` (a cost per voicing) or `transition` (a cost per change) with `super()`. Every search then obeys it | `melody.MelodicTaste` |
| A constraint on one chord of a progression | Pass a mask to `Trellis.shortest`, or many to `Trellis.search` | a pinned voicing; `melody.harmonise` (top note given); `drones` (a string held) |
| A new question about a progression | Build `taste.trellis(board, options)` once and ask it | `Taste.lines` (the best route per top or bass line) |

Three rules keep it clean:

- **Never restate.** If two things differ only in a number (stride 2 or 3, top or bass, which
  strings), it is one function with that number as an argument. If two things share behaviour,
  the behaviour lives in a base class (`Rooted`, `Taste`, `PitchClassSet`) and the differences
  in subclasses.
- **Numbers in, numbers out.** A function in `core` or `instruments` never takes or returns a
  name. Names are made once, at the edge, by `catalog.names`.
- **Callers get data, not policy.** The library returns every reading, every route within a
  slack, every option. Choosing how many to show, and how, belongs to the caller.

## Decisions

- **Intervals in one frame.** Everything is steps from a root, and every pitch is measured from
  one origin: steps above C0 (E2 is 28), so a root is a pitch class with C = 0 on every
  instrument and any two things compare by subtraction. The origin and the note letters are
  catalog conventions (`pitch`, `pitch_class`); core only sees integers. The letters are not a
  table: they are the Ionian scale on C.
- **Conventions are data.** Mode, chord and tuning names live in `catalog`. Core never imports
  it; `identify` takes its patterns as an argument and returns `Chord`s, so core never sees a
  name at all.
- **Derived, not listed.** Chords come from stacking a scale; modes from rotation; symmetric
  sets from maximal evenness; secondary dominants, tritone substitutes and borrowed chords from
  `chord`, `rotate`, `transpose` and `voice_leading` (see `tests/test_harmony.py`). No chord
  shapes, scale boxes or function tables are stored.
- **Ints until there is behaviour.** No `Interval` class: an interval is a step count. A chord
  and a key share real behaviour (their notes, the interval a pitch makes with the root,
  membership), so that lives once in `Rooted` and `Chord` and `Key` inherit it. They are frozen
  dataclasses: equal when their fields are, never equal to each other.
- **A slash chord is data.** `Chord.bass` is the note written under the slash. Left as None,
  the inversion is chosen by whoever voices the chord (below); set, every voicing has that
  note lowest, in every search, because `Fretboard.voicings_of` builds only those.
- **One rule for every interval name.** `interval_name(step, number)` writes a step as the
  Nth note of the major scale, flat or sharp to fit. Scale degrees, chord tones, extensions in
  a symbol and the accidental on a Roman numeral are all that one call; only the choice of N
  depends on context (`chord_tone_names`). A symbol is built from the same names its notes are
  labelled with, and `parse_chord` reads every symbol `chord_symbol` can write: tested over all
  2,047 chord patterns.
- **Three forms of the same data, one job each.** Pitches are integers (steps above C0) for
  arithmetic; sets are `PitchClassSet`s in core (hashable, exact) and chroma rows,
  `bool[voicing, pitch class]`, on the instrument, where thousands compare at once; positions
  are fret grids. Words appear only in `catalog.names`, at the edge.
- **NumPy at the instrument, tuples in core.** Core sets hold 3 to 8 numbers and must be
  hashable, where tuples are faster. The fretboard works on whole grids and every combination of
  strings, where vectors pay off.
- **Map every voicing, then work backwards.** `voicings` builds every voicing within reach, so
  nothing is missed. Rules then remove what a hand can't play and costs rank the rest. The grid
  grows one string at a time over each chord's playable frets, and a row is dropped as soon as
  its fretted notes span more than `reach` mm (or, if asked, a muted string splits the sounding
  ones), so impossible stretches are never built. `voicings_of` builds a whole progression in
  that one pass, with a column saying which chord each row plays.
- **Voicing has an inverse.** `Fretboard.readings` reads any shape back as every chord it could
  be, bass included. Which reading to show is the caller's choice (`suggest.neighbours.named`
  prefers the one rooted on the bass, then the root steadiest in the key).
- **Physical measures in physical units.** Reach and hand movement are millimetres, from the fret
  positions the temperament and scale length give; roughness is computed from frequencies in
  hertz. So the same rules hold on a bass, a ukulele or a 31-EDO guitar.
- **Playability is a set of small rules, not a list of shapes.** Each rule takes the voicing
  array and returns one value per row: the fewest fingers needed (a barre lies to the highest
  string), whether those fingers fit the hand in fret order, contiguous strings, inside a fret
  region, open strings only near the hand. Combine them with `&`; replace any rule without
  touching the others. Limits are parameters.
- **One search.** A progression is a `Trellis`: voicings as nodes, costs on nodes and changes.
  The cheapest route (the Viterbi algorithm, exact) is the default answer, and inversions fall
  out of it: they are chosen, not requested; `stack` reports them. Every other question is the
  same search with masks saying which voicings are allowed: a pinned shape, a melody on top, a
  string held, a repeated chord tied to one shape (`tied`: exact with one repeated chord,
  coordinate descent with several). Many masked searches run as one array (`search`), in
  batches that bound memory. The weights are arguments, because they are not yet measured for
  guitar.
- **Variety without dice.** One best route hides near-equal ones, but routes chosen at random
  are only worse by the cost. `Trellis.each` instead returns the best route for every line a
  voice could take (the top note or the bass of each chord) within a slack of the best, so each
  option is the best of its kind and named by what the ear follows. `attraction` (Lerdahl 2001)
  describes a line, e.g. E→F resolving; it is not a hidden weight.
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
  `PitchClassSet`; `Chord` and `Key` are `Rooted`. A guitar is a `Fretboard` with gaps
  `5 5 5 4 5`, not a `Guitar` class.
- **Exact before fast, then fast.** Each search is exact (dynamic programming, not sampling
  or greedy choice), and tested against brute force on small cases. Speed comes from doing the
  work once: one pass builds every chord's voicings, one table holds every pair's roughness,
  one trellis answers every question about a progression.
- **Immutable values, no I/O in core.** Frozen dataclasses; functions return values.
- **Tests come from the facts.** Each [math] claim in `theory.md` becomes a test.
