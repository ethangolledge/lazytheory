# lazy_theory

Music theory as intervals and maths, not letters.

A minor triad is *root, minor third, fifth*: steps `0 3 7`. That's true in every key, on every
instrument. The only letter you ever give is the root. This repo models music theory that way:
built on the physics of sound, derived with maths, with every cultural convention swappable.

The goal is a web app where pianists, guitarists, bassists and anyone else can explore scales,
chords, melody and rhythm, and learn why they work.

## Principles

- **Physics first.** Pitch is frequency; intervals are ratios; 12-TET is one choice of
  temperament among many, so microtones are supported too.
- **Everything relative.** Work in steps from a root. Keys, tunings and instruments are
  configuration.
- **Conventions are data.** Mode, chord and tuning names live in TOML files. Add any scale and
  give it any name.
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

## Example

```python
from lazy_theory.catalog import load_chords, load_scales, load_tunings
from lazy_theory.instruments.fretboard import Fretboard

tuning = load_tunings()["guitar open D"]
board = Fretboard.from_gaps(tuning.gaps)
root = tuning.root("A")

board.positions(load_scales()["Phrygian"], root)   # where A Phrygian lives on the neck
board.voicings(load_chords()["minor 7th"], root)   # every playable Am7, one row per voicing
```

## Status

Built: temperament, pitch-class sets, scales and modes, chord stacking and identification,
voice leading, and a NumPy fretboard for any tuning. Next: rhythm, then export for the web app.
