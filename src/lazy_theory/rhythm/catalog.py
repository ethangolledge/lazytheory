"""Spoken rhythm, talas, tals and timelines, loaded from TOML.

Why: konnakol words, Takadimi syllables, tabla bols and the gestures that keep a tala are
conventions of particular traditions, so they are data, checked against each other on
loading (every syllable a word uses is listed; every word has as many syllables as pulses).

Theory it speaks to: the 35 suladi talas built from their angas (a laghu is a clap then
fingers counted), Hindustani tals as sections with marks and thekas, and the bell and clave
timelines of West African and Afro-Cuban music.

Pass a path to load your own file instead of the bundled one.
"""

from collections.abc import Mapping
from functools import cache
from pathlib import Path
from typing import NamedTuple

from lazy_theory.core.pcset import PitchClassSet, group_starts
from lazy_theory.data import add, read
from lazy_theory.rhythm.meter import CLAP, NONE, WAVE, Meter
from lazy_theory.rhythm.phrase import Phrase
from lazy_theory.rhythm.stroke import Stroke

_PACKAGE = __name__.rpartition(".")[0]  # where the bundled data files sit


class Spoken(NamedTuple):
    """Everything spoken rhythm needs from the catalog, checked against itself on loading."""

    words: Mapping[int, tuple[str, ...]]  # the syllables of a group of n pulses, for short n
    syllables: frozenset[str]  # every syllable typed text may use
    rest: str  # a silent pulse
    counting: Mapping[int, tuple[str, ...]]  # words after the count's number, per split
    subdivisions: Mapping[int, str]  # "16ths" for 4 per count
    names: tuple[str, ...]  # every syllable in order: a phrase's sound id n is names[n - 1]
    hold: str  # holds the syllable before it one more pulse
    takadimi: Mapping[int, tuple[str, ...]]  # the syllables of a beat split n ways
    strokes: Mapping[str, Stroke]  # each tabla bol the sources class, as its stroke
    khali: Mapping[str, str]  # each bol without its bass


@cache
def load_spoken(path: Path | None = None) -> Spoken:
    """The words and syllables of spoken rhythm: konnakol words, Takadimi positions, tabla bols
    with their strokes."""
    data = read(_PACKAGE, "rhythm.toml", path)
    names = tuple(data["syllables"]["spoken"])
    syllables = frozenset(names)
    if len(syllables) != len(names):
        raise ValueError("a syllable is listed twice")
    words = {int(size): tuple(word.split()) for size, word in data["words"].items()}
    takadimi = {int(split): tuple(said.split()) for split, said in data["takadimi"].items()}
    for size, word in (*words.items(), *takadimi.items()):
        if len(word) != size:
            raise ValueError(f"the word for {size} pulses has {len(word)} syllables")
    strokes = {bol: Stroke(*stroke) for bol, stroke in data["strokes"].items()}
    khali = dict(data["khali"])
    used = {s for word in (*words.values(), *takadimi.values()) for s in word}
    unknown = (used | set(strokes) | set(khali) | set(khali.values())) - syllables
    if unknown:
        raise ValueError(f"syllables not listed: {sorted(unknown)}")
    counting = {int(split): tuple(said.split()) for split, said in data["counting"].items()}
    for split, said in counting.items():
        if len(said) != split - 1:
            raise ValueError(f"counting a split of {split} needs {split - 1} words")
    subdivisions = {int(split): name for split, name in data["subdivisions"].items()}
    return Spoken(
        words,
        syllables,
        data["rest"],
        counting,
        subdivisions,
        names,
        data["hold"],
        takadimi,
        strokes,
        khali,
    )


def syllable_id(name: str) -> int:
    """The sound id a phrase stores for the syllable `name` (rhythm.phrase: ids start at 1)."""
    names = load_spoken().names
    if name not in names:
        raise ValueError(f"unknown syllable {name!r}")
    return names.index(name) + 1


_GESTURES = {"clap": CLAP, "wave": WAVE}


@cache
def load_talas(path: Path | None = None) -> Mapping[str, Meter]:
    """The 35 suladi talas, keyed "<jati> <family>" ("chatusra triputa" is Adi tala), each a
    meter of one beat per pulse in three levels: the cycle, its angas, its beats. A laghu
    ("I") is jati beats, a clap then a finger counted on each beat after it; the other angas'
    beats and gestures are data. Nothing is grouped inside an anga, so no beat of a laghu is
    heavier than another."""
    talas = read(_PACKAGE, "rhythm.toml", path)["talas"]
    gestures = {anga: [_GESTURES[g] for g in hands] for anga, hands in talas["gestures"].items()}
    meters: dict[str, Meter] = {}
    for jati, beats in talas["jatis"].items():
        for family, angas in talas["families"].items():
            parts = [beats if anga == "I" else talas["angas"][anga] for anga in angas]
            hands = [
                hand
                for anga in angas
                for hand in ([CLAP, *range(1, beats)] if anga == "I" else gestures[anga])
            ]
            meters[f"{jati} {family}"] = _cycle(parts, hands)
    return meters


class Tal(NamedTuple):
    """A Hindustani tal or Carnatic chapu: how its cycle is kept, and the bols that mark it."""

    meter: Meter  # one beat per pulse: the cycle, its sections, its beats; a gesture per beat
    theka: Phrase | None  # the bols that mark it, one word per beat, if the file gives them


@cache
def load_tals(path: Path | None = None) -> Mapping[str, Tal]:
    """Every named Hindustani tal and Carnatic chapu, keyed by name. Section marks become
    gestures on each section's first beat (X or a number a clap, 0 a wave); a chapu lists the
    beats it claps on."""
    tals: dict[str, Tal] = {}
    for name, entry in read(_PACKAGE, "rhythm.toml", path)["tals"].items():
        sections = entry["sections"]
        beats = sum(sections)
        hands = [NONE] * beats
        if "marks" in entry:
            if len(entry["marks"]) != len(sections):
                raise ValueError(f"{name}: one mark per section")
            for start, mark in zip(group_starts(sections), entry["marks"], strict=True):
                hands[start] = WAVE if mark == "0" else CLAP
        for beat in entry.get("claps", ()):
            hands[beat - 1] = CLAP
        theka = None
        if "theka" in entry:
            if len(entry["theka"]) != beats:
                raise ValueError(f"{name}: the theka needs one entry per beat ({beats})")
            theka = Phrase.beats(
                [[syllable_id(b) for b in beat.split()] for beat in entry["theka"]]
            )
        tals[name] = Tal(_cycle(sections, hands), theka)
    return tals


def _cycle(sections: list[int], hands: list[int]) -> Meter:
    """A cycle of one beat per pulse: the whole, its `sections`, its beats, kept by `hands`."""
    beats = sum(sections)
    levels = tuple(dict.fromkeys([(beats,), tuple(sections), (1,) * beats]))
    return Meter(levels, len(levels) - 1, tuple(hands))


@cache
def load_timelines(path: Path | None = None) -> Mapping[str, PitchClassSet]:
    """Every named timeline (bell or clave pattern), keyed by name, as onsets on its cycle."""
    timelines: dict[str, PitchClassSet] = {}
    for name, steps in read(_PACKAGE, "rhythm.toml", path)["timelines"].items():
        add(timelines, name, PitchClassSet.from_steps(steps))
    return timelines
