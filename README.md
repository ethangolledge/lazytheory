# lazy_theory

Music theory as intervals and maths, not letters.

A minor triad is *root, minor third, fifth*: steps `0 3 7`. That's true in every key, on every
instrument. Letter names are a label added at the end. This repo models music theory that way:
built on the physics of sound, derived with maths, with every cultural convention swappable.

The goal is a web app where pianists, guitarists, bassists and anyone else can explore scales,
chords, melody and rhythm, and learn why they work.

## Principles

- **Physics first.** Pitch is frequency; intervals are ratios; 12-TET is one choice of
  temperament among many, so microtones are supported too.
- **Everything relative.** Work in steps from a root. Keys, tunings and instruments are
  configuration.
- **Conventions are data.** Greek mode names, chord symbols, letter names: kept and supported, but
  replaceable. Add any scale and give it any name.
- **Clean code.** Modular, DRY, one-way dependencies, no circular imports.

## Docs

- [docs/theory.md](docs/theory.md): the music theory being modelled, tagged physics / math /
  convention.
- [docs/architecture.md](docs/architecture.md): how the code is organised and extended.

## Development

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync                                     # create .venv with the package and dev tools
uv run python -m unittest discover tests    # tests
uv run ruff format . && uv run ruff check . # format and lint
uv run mypy                                 # type check (strict, src only)
```

The same checks run on every push (`.github/workflows/checks.yml`).

## Status

Early. Built: temperaments, pitch-class sets, scales and modes, chord stacking and
identification, voice leading, and a NumPy fretboard that maps any scale or chord onto any
tuning and finds every voicing. `base.py` is the original 12-TET guitar prototype, kept for
reference until the export layer replaces its CSV output.

Near-term goals carried over from the prototype:

- Map any scale or mode onto any instrument and string tuning
- Build chords by stacking (triads, sevenths, extensions) and generate inversions/voicings
- Suggest notes and chords from interval relationships
