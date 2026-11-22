"""Rhythms one move away: what to try next while jamming on a rhythm.

Why: a rhythm you clap is rarely the one you keep; the one you keep is usually a small move
from it. Each move here is one simple operation on the onsets, counted in grid points (what a
player counts), so every suggestion is a rhythm a player could have stumbled on, and it says
which move made it. Nothing is ranked or weighted: the caller shows each move's results with
the measures from `rhythm.meter` and the player's ear chooses.

Theory it speaks to: the moves are the ones traditions vary rhythms by. Moving one note by one
grid point is the smallest change between two rhythms (Toussaint's swap distance), the
rhythmic twin of one finger moving on a chord. Splitting a gap adds a note where the halving
rule of every meter here divides it, so a rhythm gets busier along the meter's own grain;
merging is the reverse. Shifting the whole pattern is displacement (Krebs' D); shifted far
enough, a 3-2 clave becomes a 2-3. The even version is the Euclidean rhythm with as many notes
(Toussaint 2005).

`jam` is the jam's ideas: the gaps between your accents filled with groups (3s in 16ths, 2s in
triplets), each gap landing on the next accent, the way a drummer fills towards a hit. They
are new parts to play with yours, never a change to yours.

To weigh a move, measure its result with `rhythm.meter.syncopation` and `unevenness`: groove
peaks at medium syncopation (Witek et al. 2014), so neither more nor less is better and nothing
here is ranked.

Could grow into: the shortest chain of moves between two rhythms (a breadth-first search over
these), moves that keep the necklace (only rotations), and a search that suggests the move
that lands a phrase on one.
"""

from collections.abc import Callable, Iterable
from fractions import Fraction

from lazy_theory.core.pcset import PitchClassSet, group_starts
from lazy_theory.rhythm.layers import fills, midpoints
from lazy_theory.rhythm.meter import Meter, gaps

RhythmMove = Callable[[PitchClassSet], list[PitchClassSet]]


def nudged(points: PitchClassSet) -> list[PitchClassSet]:
    """Each note moved one grid point earlier or later, where that point is free."""
    found = []
    for point in points:
        for step in (-1, 1):
            target = (point + step) % points.size
            if target not in points:
                found.append(_with(points, point, target))
    return _unique(points, found)


def split(points: PitchClassSet) -> list[PitchClassSet]:
    """A note added inside one gap of two or more, where `grouping` splits it: 4 into 2+2,
    5 into 2+3, 3 into 1+2 (`rhythm.layers.midpoints`)."""
    found = [PitchClassSet((*points, note), points.size) for note in midpoints(points)]
    return _unique(points, found)


def merged(points: PitchClassSet) -> list[PitchClassSet]:
    """Each note but the first taken out, joining the gaps either side of it."""
    found = [_with(points, point, None) for point in points.pitch_classes[1:]]
    return _unique(points, found)


def shifted(points: PitchClassSet) -> list[PitchClassSet]:
    """The whole rhythm one grid point earlier and one later."""
    return _unique(points, [points.transpose(-1), points.transpose(1)])


def even(points: PitchClassSet) -> list[PitchClassSet]:
    """The maximally even rhythm with as many notes closest to this one: started on its first
    note, in whichever rotation keeps the most of its notes. Nothing if it is already even
    (silence included)."""
    if not points.pitch_classes:
        return []
    spread = PitchClassSet.maximally_even(len(points), points.size)
    first = points.pitch_classes[0]
    placed = [spread.rotate(degree).transpose(first) for degree in range(len(spread))]
    return _unique(points, [max(placed, key=lambda rhythm: len(set(rhythm) & set(points)))])


def filled(spine: PitchClassSet, per_count: int, group: int) -> PitchClassSet | None:
    """A new part over `spine` (accents, in counts): each gap to the next accent filled with
    groups of `group` points on a grid of `per_count` points a count, finished in 2s and 3s so
    the last group ends exactly on the next accent (`rhythm.layers.fills`). In 16ths, 3s across a
    three-count gap are 3+3+3+3 and across a two-count gap 3+3+2, so one idea varies across the
    bar. Every accent of `spine` sounds in it; `spine` itself is untouched. None if a `group`
    fits in no gap, since then it isn't in `group`s at all."""
    notes: list[int] = []
    fitted = False
    for accent, gap in zip(spine, gaps(spine), strict=True):
        groups = next(fills(group, gap * per_count), (gap * per_count,))  # one point: the accent
        fitted |= group in groups
        notes += [accent * per_count + start for start in group_starts(groups)]
    return PitchClassSet(tuple(notes), spine.size * per_count) if fitted else None


def jam(
    spine: PitchClassSet, splits: Iterable[int] = range(2, 6), groups: Iterable[int] = range(2, 6)
) -> list[tuple[int, int, PitchClassSet]]:
    """Every `filled` version of `spine`: (per count, group, notes) for each subdivision and
    group size,
    leaving out a group as long as a count (that is just the counts), a group that fits in no
    gap, and any idea that sounds the same as one already found. Fewest notes first: a count,
    not a taste."""
    found: dict[frozenset[Fraction], tuple[int, int, PitchClassSet]] = {}
    for per_count in splits:
        for group in groups:
            notes = filled(spine, per_count, group) if group != per_count else None
            if notes is not None:
                heard = frozenset(Fraction(point, per_count) for point in notes)
                found.setdefault(heard, (per_count, group, notes))
    return sorted(found.values(), key=lambda idea: (len(idea[2]), idea[0], idea[1]))


MOVES: dict[str, RhythmMove] = {
    "nudge": nudged,
    "split": split,
    "merge": merged,
    "shift": shifted,
    "even": even,
}


def moves(onsets: PitchClassSet, meter: Meter) -> dict[str, list[PitchClassSet]]:
    """Every rhythm one move from `onsets`, by move, each in pulses on `meter`. A rhythm two
    moves reach is listed under the first, so each appears once."""
    points = meter.to_grid(onsets)
    seen = {points}
    found: dict[str, list[PitchClassSet]] = {}
    for name, move in MOVES.items():
        fresh = [result for result in move(points) if result not in seen]
        seen.update(fresh)
        found[name] = [meter.from_grid(result) for result in fresh]
    return found


def _with(points: PitchClassSet, old: int, new: int | None) -> PitchClassSet:
    kept = [point for point in points if point != old]
    return PitchClassSet((*kept, *([] if new is None else [new])), points.size)


def _unique(original: PitchClassSet, found: list[PitchClassSet]) -> list[PitchClassSet]:
    return [
        rhythm for i, rhythm in enumerate(found) if rhythm != original and rhythm not in found[:i]
    ]
