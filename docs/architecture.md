# Architecture

How the code will turn [theory.md](theory.md) into software. **Status: proposal.** The current
code is in `base.py`, a 12-TET guitar prototype that will be replaced module by module.

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
  core      │ temperament → interval → pcset  │   pure maths, standard library only
            │                 ↓               │
            │           scale, chord          │
            │                                 │
            │ rhythm   (stands alone)         │
            └─────────────────────────────────┘
```

| Module | Responsibility | Depends on |
|---|---|---|
| `temperament` | Steps ↔ ratio/cents/frequency. `Temperament` base; `EqualTemperament(n, period)`, `JustIntonation(ratios)` | — |
| `interval` | `Interval` as a step count within a temperament; ratio and cents via the temperament | temperament |
| `pcset` | `PitchClassSet`: immutable set mod N with transpose, rotate, invert, complement, step pattern | temperament |
| `scale` | `Scale(PitchClassSet)`: modes, generated scales, degrees | pcset |
| `chord` | `Chord(PitchClassSet)`: building by stride from a scale, inversions, voicings, matching against patterns | pcset, scale |
| `rhythm` | `Cycle`, groupings, subdivisions, polyrhythm alignment | — |
| `catalog` | Named scales, chord patterns, string tunings, talas, stored as data files and loaded into core objects | core |
| `naming` | Letter names, interval labels, Greek names, reference pitch: core values → strings | core |
| `instruments` | `Instrument` base; `Keyboard`, `FrettedInstrument(string tuning, frets)`: position ↔ pitch | core |
| `export` | DataFrames, CSV, database tables, query helpers | everything below |

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
│   ├── core/
│   │   ├── temperament.py
│   │   ├── interval.py
│   │   ├── pcset.py
│   │   ├── scale.py
│   │   └── chord.py
│   ├── rhythm/
│   ├── catalog/          # loaders + data files (scales, chords, tunings, talas)
│   ├── naming/
│   ├── instruments/
│   └── export/
└── tests/
```

## Open decisions

- Data file format for `catalog` (TOML is in the standard library and readable).
- Compute live vs. store results in a database: decided when the web app's needs are known.
- Web stack: later.
- Automatically enforcing the layer rules (e.g. with `import-linter`): optional, needs a
  dependency.
