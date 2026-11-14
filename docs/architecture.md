# Architecture

How the code will turn [theory.md](theory.md) into software. **Status:** `core`, `catalog` and
`instruments` (fretboard) are built and tested. The rest is proposal. `base.py` is the original
12-TET guitar prototype, kept for reference until `export` replaces its CSV output.

## Goals

1. **Physics and math in the core; conventions as data.** Anything tagged **[convention]** in
   `theory.md` (names, reference pitch, chord symbols, Greek modes) lives in swappable data, never
   in core logic.
2. **Everything relative.** The core works in integer steps from a root. Absolute pitch, letter
   names and frequencies are added only at the edges.
3. **Any temperament.** Nothing assumes N = 12. 12-TET is just the default.
4. **Any instrument.** Guitar, bass and piano are configurations of a few general instrument
   types.
5. **Web-ready.** The core is plain Python with no I/O, so it can sit behind an API or run in the
   browser later. Whether results are computed live or stored in a database is a decision for
   the outer layers; the core doesn't care.

## Layers

Dependencies point **downwards only**. No module imports from a layer above it, and modules in the
same layer don't import each other unless shown here.

```
            ┌──────────────┐   ┌──────────────┐
  outer     │   export     │   │   (web app)  │   polars / duckdb / API live here only
            └──────┬───────┘   └──────┬───────┘
                   │                  │
            ┌──────┴──────────────────┴───────┐
  edge      │ catalog │ naming │ instruments  │   named data, labels, physical mappings
            └──────────────┬──────────────────┘
                           │
            ┌──────────────┴──────────────────┐
  core      │ temperament     pcset           │   pure maths, standard library only
            │                 ↓               │
            │           scale, chord          │
            │                                 │
            │ rhythm   (stands alone)         │
            └─────────────────────────────────┘
```

| Module | Responsibility | Depends on |
|---|---|---|
| `temperament` | Steps → ratio and cents. `Temperament` base; `EqualTemperament(size, period)`, `JustIntonation(ratios)` | — |
| `pcset` | `PitchClassSet`: immutable set mod `size`, step patterns, rotation | — |
| `scale` | `Scale(PitchClassSet)`: always contains its root; stacks chords by stride | pcset |
| `chord` | `identify`: names a set against patterns passed in by the caller, trying every root | pcset |
| `voice_leading` | Smallest total movement from one set to another, with each voice's move | pcset |
| `rhythm` | `Cycle`, groupings, subdivisions, polyrhythm alignment | — |
| `catalog` | Named scales, chord patterns and string tunings in TOML, loaded into core objects (later: talas) | core |
| `naming` | Letter names, interval labels, Greek names, reference pitch: core values → strings | core |
| `instruments` | `Fretboard`: pitch, interval and playable-position grids for any tuning; every voicing of a chord; ordering voicings by movement. NumPy arrays | core |
| `export` | DataFrames, CSV, database tables, query helpers | everything below |

## Decisions so far

- **No `Interval` class.** An interval is a step count; `Temperament.ratio(steps)` and
  `.cents(steps)` cover the physics. Add a class only when something needs more than an int.
- **`pcset` doesn't depend on `temperament`.** Set maths only needs the number of steps
  (`size`), so a set doesn't carry a temperament around. Join them when a pitch needs a ratio.
- **No `Chord` class yet.** A chord is a `PitchClassSet`. A class arrives with behaviour of its
  own: voicings and inversions need pitch height, which comes with `instruments`.
- **Identification lives in core but holds no names.** `identify` takes the patterns as an
  argument, so core never imports the catalog.
- **Harmony is composed, not listed.** Secondary dominants, tritone substitutes and borrowed
  chords come from `chord`, `rotate`, `transpose` and `voice_leading`
  (see `tests/test_harmony.py`). There is no function table and no single "tension" score.
- **NumPy at the instrument layer, tuples in core.** Core sets hold 3 to 8 numbers and must be
  hashable for naming, where tuples are faster than arrays. The fretboard works on whole grids
  and every combination of strings, where vector operations pay off. Sets become arrays at
  that boundary.
- **Computed, not looked up.** No chord shapes or scale boxes are stored. A tuning is gaps
  between strings, a key root is steps above the first string, and every position, interval and
  voicing is computed from those. Moving a shape up one fret moves the chord up one step.
- **Voicings are found window by window.** Each window starts at a voicing's lowest fretted note
  and is `max_span` frets wide, so each voicing is built once and invalid spans are never made.
  Every chord tone must sound; muted strings are allowed anywhere.
- **Scales are step patterns; chords are members.** Each is written the way it's usually thought
  about. A scale's steps also fix its `size`, so a 31-step scale needs no extra setting.

## Design rules

- **Immutable values.** Core objects are frozen dataclasses. Operations return new objects.
- **Inheritance for real "is-a" relationships with shared behaviour.** `Scale` and `Chord` are
  both `PitchClassSet`s; `EqualTemperament` and `JustIntonation` are both `Temperament`s. Keep
  hierarchies shallow, one or two levels.
- **Configuration, not subclasses.** A guitar is a `Fretboard` with gaps `5 5 5 4 5`, a bass
  one with `5 5 5`, not `Guitar` and `Bass` classes. Dorian is a rotation of a set, not a `Dorian` class.
- **Extend by adding data.** A new scale, chord pattern, string tuning or tala is one entry in a
  `catalog` file, with no code changes. Its name can be anything.
- **One source of truth.** Every fact is defined once (e.g. the step pattern of the diatonic
  scale); everything else is derived from it, not duplicated.
- **Core has no third-party dependencies.** NumPy is used from `instruments` up; Polars and
  DuckDB will belong in `export` only.
- **No hidden I/O or printing in core.** Functions return values; callers decide what to show
  or save.
- **Layer rules are tested.** `tests/test_architecture.py` fails if a layer imports upwards or
  core imports anything outside the standard library. Add each new layer to its `LAYERS` list.
- **Tests come from the facts.** Every [math] claim in `theory.md` should become a test (e.g.
  rotating Ionian 5 degrees gives Aeolian; stacking 7 fifths gives Lydian).

## Proposed layout

```
lazy_theory/
├── README.md
├── docs/
│   ├── theory.md
│   └── architecture.md
├── src/lazy_theory/
│   ├── core/             # built
│   │   ├── temperament.py
│   │   ├── pcset.py
│   │   ├── scale.py
│   │   ├── chord.py
│   │   └── voice_leading.py
│   ├── catalog/          # built: loader + scales.toml, chords.toml
│   ├── rhythm/           # proposed
│   ├── naming/           # proposed
│   ├── instruments/      # built: fretboard.py
│   └── export/           # proposed
└── tests/
```

## Open decisions

- Compute live vs. store results in a database: decided when the web app's needs are known.
- Web stack: later.
