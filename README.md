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
board.capo(5).voicings(load_chords()["minor 7th"], root, reach)  # with a capo at 5
```

Choosing inversions for a progression: a `Taste` holds the rules and weights, one place to
change them.

```python
from lazy_theory.instruments.taste import Taste

chords = [(load_chords()["minor"], tuning.root(note)) for note in "EA"]
path, cost = Taste(highest=9, roughness=10.0).path(board, chords)
[board.stack(v[None], root)[0, 0] for v, (_, root) in zip(path, chords)]  # each bass: the inversion
```

Optionally, suggest a tuning and capo for a progression. Standard tuning stays the default; this
is a separate layer you opt into:

```python
from lazy_theory.suggest.tunings import key, name, suggest

tunings = load_tunings()
standard = Fretboard.from_tuning(tunings["guitar standard"])
e = tunings["guitar standard"].root("E")
chords = [(load_chords()["minor"], e), (load_chords()["minor"], e + 5)]  # Em, Am
rich = Taste(sounding=1.0, ringing=1.0, open_within=5)  # reward full chords and open strings
e_minor = key(load_scales()["Aeolian"], e)  # the key's other chords count a little
best = suggest(standard, chords, rich, context=e_minor)  # retunings and capos, cheapest first
name(standard.open_strings + best[0].retuning, standard, tunings)  # e.g. "guitar open G"
```

Optionally, harmonise a melody: one note per chord, the note on top, chords chosen from those
allowed in each slot:

```python
from lazy_theory.suggest.melody import MelodicTaste, harmonise

phrygian = key(load_scales()["Phrygian"], e)  # E Phrygian's chords
em, am = phrygian[0], phrygian[3]
melody = [e, e + 1, e, e]  # E F E E
harmony = harmonise(standard, melody, [[em], phrygian, phrygian, [am]], MelodicTaste())
harmony.chords, harmony.path  # which chord in each slot (F, the flat II, then Am), and the voicings
```

## Status

Built: temperament, pitch-class sets, scales and modes, chord stacking and identification,
voice leading, and a NumPy fretboard for any tuning that maps every voicing of a chord,
measures its roughness and picks playable inversions for a progression, with or without a
capo; optionally, suggests tunings and capos, harmonises melodies and walks between chords
through extensions derived from the key. Next: rhythm, then
export for the web app.
