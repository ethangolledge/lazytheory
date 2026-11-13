# Architecture

How the code will turn [theory.md](theory.md) into software. **Status:** `core` and `catalog` are
built and tested. The rest is proposal. `base.py` is the original 12-TET guitar prototype, kept
for reference until `instruments` and `export` replace it.

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
| `rhythm` | `Cycle`, groupings, subdivisions, polyrhythm alignment | — |
| `catalog` | Named scales and chord patterns in TOML, loaded into core objects (later: string tunings, talas) | core |
| `naming` | Letter names, interval labels, Greek names, reference pitch: core values → strings | core |
| `instruments` | `Instrument` base; `Keyboard`, `FrettedInstrument(string tuning, frets)`: position ↔ pitch | core |
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
- **Scales are step patterns; chords are members.** Each is written the way it's usually thought
  about. A scale's steps also fix its `size`, so a 31-step scale needs no extra setting.

## Design rules

- **Immutable values.** Core objects are frozen dataclasses. Operations return new objects.
- **Inheritance for real "is-a" relationships with shared behaviour.** `Scale` and `Chord` are
  both `PitchClassSet`s; `EqualTemperament` and `JustIntonation` are both `Temperament`s. Keep
  hierarchies shallow, one or two levels.
- **Configuration, not subclasses.** A guitar is a `FrettedInstrument` with six strings and gaps
  `5 5 5 4 5`, not a `Guitar` class. Dorian is a rotation of a set, not a `Dorian` class.
- **Extend by adding data.** A new scale, chord pattern, string tuning or tala is one entry in a
  `catalog` file, with no code changes. Its name can be anything.
- **One source of truth.** Every fact is defined once (e.g. the step pattern of the diatonic
  scale); everything else is derived from it, not duplicated.
- **Core has no third-party dependencies.** Polars and DuckDB belong in `export` only.
- **No hidden I/O or printing in core.** Functions return values; callers decide what to show
  or save.
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
│   │   └── chord.py
│   ├── catalog/          # built: loader + scales.toml, chords.toml
│   ├── rhythm/           # proposed
│   ├── naming/           # proposed
│   ├── instruments/      # proposed
│   └── export/           # proposed
└── tests/
```

## Open decisions

- Compute live vs. store results in a database: decided when the web app's needs are known.
- Web stack: later.
- Automatically enforcing the layer rules (e.g. with `import-linter`): optional, needs a
  dependency.
