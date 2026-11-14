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
board = Fretboard.from_tuning(tuning)
root = tuning.root("A")
reach = board.fret_distance[4] - board.fret_distance[1]  # a hand spanning frets 1-4, in mm

board.positions(load_scales()["Phrygian"], root)  # where A Phrygian lives on the neck
board.voicings(load_chords()["minor 7th"], root, reach)  # every Am7 in reach, one row each
```

Choosing inversions for a progression with `lazy_theory.instruments.rules`, weighting each
measure as you like:

```python
def lowest(v):
    return np.nanmin(board.notes(v), axis=1)


def change(a, b):  # cost of moving from each voicing in a to each in b
    return moved(a, b) + 5 * strings_changed(a, b) + motion(lowest(a), lowest(b))


chords = [board.voicings(chord, root, reach) for chord, root in zip(chords, roots)]
playable = [v[(fingers(v) <= 4) & contiguous(v) & within(v, 5, 9)] for v in chords]
path = smoothest(playable, change, lambda v: 10 * roughness(board.frequencies(v)))
[board.stack(v[None], root)[0, 0] for v, root in zip(path, roots)]  # each bass: the inversion
```

## Status

Built: temperament, pitch-class sets, scales and modes, chord stacking and identification,
voice leading, and a NumPy fretboard for any tuning that maps every voicing of a chord,
measures its roughness and picks playable inversions for a progression. Next: rhythm, then
export for the web app.
