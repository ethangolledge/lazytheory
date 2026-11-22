# lazy_theory

Music theory as intervals and maths, not letters.

A minor triad is *root, minor third, fifth*: steps `0 3 7`. That's true in every key, on every
instrument. The only letter you ever give is the root. This repo models music theory that way:
built on the physics of sound, derived with maths, with every cultural convention swappable.

The goal is a web app where pianists, guitarists, bassists and anyone else can explore scales,
chords, melody and rhythm, and learn why they work. Today the instruments modelled are fretted
(guitar, bass, ukulele); keyboards are not modelled yet.

## Principles

- **Physics first.** Pitch is frequency; intervals are ratios; 12-TET is one choice of
  temperament among many, so microtones are supported too.
- **Everything relative.** Work in steps from a root. Keys, tunings and instruments are
  configuration.
- **Conventions are data.** Mode, chord, tuning and syllable names live in TOML files. Add a
  line to add a scale, a chord or a tuning, with any name.
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

## Front end

There isn't one yet: it is being redesigned. What it should look and feel like is in
[docs/design.md](docs/design.md).

## Example

The examples import each name from its home module, so you can see where it lives. The
common ones also import from the top: `from lazy_theory import Chord, Fretboard, Taste`
(the list is `lazy_theory.__all__`).

```python
from lazy_theory.instruments.catalog import load_tunings
from lazy_theory.pitch.catalog import load_chords, load_scales, pitch_class
from lazy_theory.pitch.chord import Chord
from lazy_theory.pitch.key import Key
from lazy_theory.instruments.fretboard import Fretboard

board = Fretboard.from_tuning(load_tunings()["guitar open D"])
root = pitch_class("A")  # 9: roots are pitch classes, C = 0, on every instrument
reach = board.fret_distance[4] - board.fret_distance[1]  # a hand spanning frets 1-4, in mm

a_minor_7 = Chord(load_chords()["minor 7th"], root)
board.positions(Key(load_scales()["Phrygian"], root))  # where A Phrygian lives on the neck
board.voicings(a_minor_7, reach)  # every Am7 in reach, one row each
board.capo(5).voicings(a_minor_7, reach)  # with a capo at 5
board.voicings(Chord(a_minor_7.pattern, root, bass=pitch_class("C")), reach)  # Am7/C only
```

Choosing inversions for a progression: a `Taste` holds the rules and weights, one place to
change them.

```python
from lazy_theory.instruments.taste import Taste

chords = [Chord(load_chords()["minor"], pitch_class(note)) for note in "EA"]
taste = Taste(highest=9, roughness=10.0)
route = taste.path(board, chords)  # route.path: one voicing per chord; route.cost
[board.stack(v[None], chord.root)[0, 0] for v, chord in zip(route.path, chords)]  # each inversion
taste.lines(board, chords)  # the best route for each top line about as easy as the best
```

Back to words, only at the edge:

```python
from lazy_theory.instruments.names import tab
from lazy_theory.pitch.catalog import chord_names
from lazy_theory.pitch.names import chord_symbol, parse_chord
from lazy_theory.suggest.neighbours import named

titles = [
    chord_symbol(chord) for chord in named(board, route.path, chord_names())
]  # each shape, read back
print(tab(board.open_strings, route.path, titles))  # one column per chord, high string on top
parse_chord("Em7(b9)/G")  # and words back into numbers: a Chord with its bass
```

Optionally, suggest a tuning and capo for a progression. Standard tuning stays the default; this
is a separate layer you opt into:

```python
from lazy_theory.instruments.names import tuning_name
from lazy_theory.suggest.tunings import suggest

tunings = load_tunings()
standard = Fretboard.from_tuning(tunings["guitar standard"])
e = pitch_class("E")
chords = [Chord(load_chords()["minor"], e), Chord(load_chords()["minor"], e + 5)]  # Em, Am
rich = Taste(sounding=1.0, ringing=1.0, open_within=5)  # reward full chords and open strings
e_minor = Key(load_scales()["Aeolian"], e).chords()  # the key's other chords count a little
best = suggest(standard, chords, rich, context=e_minor)  # retunings and capos, cheapest first
tuning_name(standard.open_strings + best[0].retuning, tunings)  # e.g. "guitar open G"
```

Optionally, harmonise a melody: one note per chord, the note on top, chords chosen from those
allowed in each slot:

```python
from lazy_theory.suggest.harmonise import MelodicTaste, harmonise

phrygian = Key(load_scales()["Phrygian"], e).chords()  # E Phrygian's chords
em, am = phrygian[0], phrygian[3]
melody = [e, e + 1, e, e]  # E F E E
harmony = harmonise(standard, melody, [[em], phrygian, phrygian, [am]], MelodicTaste())
harmony.chords, harmony.path  # which chord in each slot (F, the flat II, then Am), and the voicings
```

## Status

Built: temperament, pitch-class sets, scales and modes, chords and keys as patterns on a root,
chord identification, exact voice leading, melodic attraction, and a NumPy fretboard for any
tuning that maps every voicing of a chord, reads any shape back as chords, measures roughness
and answers every question about a progression as one shortest-path search: the smoothest
inversions, the best route for each top or bass line, a repeated chord kept on one shape.
Optionally: tunings and capos, harmonised melodies, chords one finger away, passing chords,
held notes, and extensions derived from the key. Rhythm: meters as groups inside groups (any
time signature, talas and tals), swing, syncopation and other measures with sources, spoken
phrases (konnakol, Takadimi, counting, bols) with the moves traditions vary them by, cadences
(tihai, chakradar, yati) solved exactly, rhythms one move away, and performances kept exactly as
played, read onto a grid only when asked. Next: the front end
([docs/design.md](docs/design.md)).
