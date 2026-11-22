"""Rhythm: onsets on a cycle of pulses, and meters as groups nested inside groups.

Why: a rhythm is where notes start in a repeating cycle, so it is a set of points on a circle
of pulses, the same maths as a scale on the circle of twelve steps. It is a `PitchClassSet`
whose `size` is the pulses per cycle, so displacement is `transpose`, its gaps are steps
(`from_steps` and `gaps`) and the Euclidean rhythms are `maximally_even`. Nothing new is
needed to hold one. A meter says which pulses are strong: the cycle splits into groups, each
group splits again, down to the pulse. 7/8 as 3+2+2, Adi tala as 4+2+2, 4/4 in sixteenths and
a beat of quintuplets are all one type, `Meter`. Spoken rhythm (konnakol) reads the same
numbers aloud: a group of n pulses is a word of n syllables.

Theory it speaks to: rhythm as a set on a circle (Toussaint, "The Geometry of Musical Rhythm",
2013), whose Euclidean rhythms are maximal evenness (Clough & Douthett 1991; Demaine et al.
2009); metrical weight and syncopation (Longuet-Higgins & Lee 1984); counting the ways to fill
a span with short and long units (Pingala, Hemachandra: the Fibonacci numbers, before
Fibonacci); and the gestures that keep a tala (claps, waves, finger counts).

Could grow into: a feel (how far each pulse is pushed or pulled in time: a polska, a Mande
groove), searched per beat with the trellis; accents from a melody's contour; a cycle whose
subdivision changes mid-way. Spoken phrases are `rhythm.phrase`; cadences `rhythm.cadence`; the
gestures that keep a tala are `Meter.hands`.
"""

from collections.abc import Callable, Collection, Iterator, Sequence
from dataclasses import dataclass, replace
from functools import cache
from itertools import combinations, pairwise
from math import lcm

from lazy_theory.core.pcset import PitchClassSet, group_starts

Levels = tuple[tuple[int, ...], ...]  # groups inside groups, coarsest first

CLAP, WAVE, UNMARKED = 0, -1, -2  # gestures that keep a cycle; k > 0 is the k-th finger counted


def grouping(total: int) -> tuple[int, ...]:
    """How a group of `total` pulses splits one level down: in two, the shorter half first,
    and 3 or fewer into single pulses. So 4 is 2+2, 5 is 2+3, 6 is 3+3, 7 is 3+4 (and 4 is
    2+2: 7/8 as 3+2+2), 9 is 4+5. One rule gives binary meters, compound meters (12/8 is
    3+3+3+3) and the Carnatic spoken groups of 5, 7 and 9."""
    if total < 1:
        raise ValueError(f"a group needs at least one pulse, got {total}")
    if total <= 3:
        return (1,) * total
    return (total // 2, total - total // 2)


def metric_grouping(total: int) -> tuple[int, ...]:
    """How a bar or beat of `total` pulses splits one level down when it is heard as a meter:
    a multiple of 3 above 3 is compound, beats of 3 grouped as `grouping` groups their count,
    so 9/8 is 3+3+3, 12/8 is 6+6 then 3s, 15/8 is 6+9 then five 3s. Anything else splits as
    `grouping` does (7/8 is 3+4, then 3+2+2). Spoken groups keep `grouping`, where a nine is
    4+5 (ta-ka-di-mi ta-ka-ta-ki-ta), not 3+3+3: the two traditions hear nine differently."""
    if total > 3 and total % 3 == 0:
        return tuple(3 * part for part in grouping(total // 3))
    return grouping(total)


def nesting(
    parts: Sequence[int], split: Callable[[int], tuple[int, ...]] = metric_grouping
) -> Levels:
    """`parts`, then each part longer than 3 split by `split`, level by level, until every
    group is a 2 or a 3; then single pulses. So 7 is 3+4, then 3+2+2, then pulses: the 2s and
    3s are a level of their own, as in any additive meter."""
    levels = [tuple(parts)]
    while any(part > 3 for part in levels[-1]):
        levels.append(
            tuple(q for part in levels[-1] for q in (split(part) if part > 3 else (part,)))
        )
    if any(part > 1 for part in levels[-1]):
        levels.append((1,) * sum(parts))
    return tuple(levels)


@dataclass(frozen=True)
class Meter:
    """A cycle of pulses as nested groups. `levels` runs from the whole cycle to the finest
    grid; each is a composition of the cycle in pulses, and every group start of a level is a
    group start of the next. `beat` is the index of the level the time signature counts in
    (the eighths of 7/8, the quarters of 4/4). `hands` is the gesture a player makes on each
    beat, if the cycle is kept by hand (a tala): CLAP, WAVE, UNMARKED, or k > 0 for the k-th finger
    counted. Strength (`weights`) counts levels; a gesture is a label, which is why it is kept
    apart: a khali section starts a group, yet it is the "empty" one, marked by a wave."""

    levels: Levels
    beat: int
    hands: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        check_nesting(self.levels)
        if not 0 <= self.beat < len(self.levels):
            raise ValueError(f"no level {self.beat}")
        if self.hands and len(self.hands) != len(self.levels[self.beat]):
            raise ValueError(
                f"one gesture per beat ({len(self.levels[self.beat])}), got {self.hands}"
            )
        if any(hand < UNMARKED for hand in self.hands):
            raise ValueError(
                f"a gesture is CLAP, WAVE, UNMARKED or a finger count, got {self.hands}"
            )

    def with_hands(self, hands: Sequence[int]) -> Meter:
        """The same meter kept by these gestures, one per beat."""
        return replace(self, hands=tuple(hands))

    @classmethod
    def of(cls, groups: Sequence[int], division: int | Sequence[int] = 1, bars: int = 1) -> Meter:
        """A bar of `groups` beats (7/8 as (3, 2, 2), Adi tala as (4, 2, 2)), repeated `bars`
        times, each beat split into `division` pulses, or per beat of the whole cycle:
        (4, 5, 4, 4) puts a quintuplet on beat two. Groups and beats nest by `grouping`. Beats
        split differently share a grid of their least common multiple (20 pulses per beat
        above), so every position stays a whole number."""
        if bars < 1:
            raise ValueError(f"a cycle needs at least one bar, got {bars}")
        if not groups or any(group < 1 for group in groups):
            raise ValueError(f"a bar needs one or more groups of at least one beat, got {groups}")
        beats = sum(groups) * bars
        divisions = (division,) * beats if isinstance(division, int) else tuple(division)
        if len(divisions) != beats or any(split < 1 for split in divisions):
            raise ValueError(f"give one positive division per beat ({beats}), got {division}")
        pulse = lcm(*divisions)
        levels: list[tuple[int, ...]] = [(beats * pulse,), (beats // bars * pulse,) * bars]
        levels += [tuple(part * pulse for part in level) * bars for level in nesting(groups)]
        inner = [nesting((split,))[1:] or ((split,),) for split in divisions]
        for depth in range(max(map(len, inner))):
            levels.append(
                tuple(
                    part * (pulse // split)
                    for split, beat in zip(divisions, inner, strict=True)
                    for part in beat[min(depth, len(beat) - 1)]
                )
            )
        unique = tuple(dict.fromkeys(levels))  # a level equal to the one above adds nothing
        return cls(unique, unique.index((pulse,) * beats))

    @property
    def pulses(self) -> int:
        """How many pulses the cycle lasts."""
        return sum(self.levels[0])

    def starts(self, level: int) -> PitchClassSet:
        """Where the groups of `level` start: -1 is the finest grid, `self.beat` the beats."""
        return PitchClassSet(group_starts(self.levels[level]), self.pulses)

    def weights(self) -> tuple[int, ...]:
        """How strong each pulse is: the number of levels with a group starting on it. The
        first pulse is strongest; a pulse between grid points (on a shared grid) is 0. Up to a
        constant these are Longuet-Higgins & Lee's metrical weights."""
        return _weights(self.levels)

    def to_grid(self, onsets: PitchClassSet) -> PitchClassSet:
        """`onsets` counted in grid points instead of pulses: on a shared grid (a quintuplet
        among sixteenths) the grid is what a player counts and speaks."""
        grid = tuple(self.starts(-1))
        if onsets.size != self.pulses or not set(onsets) <= set(grid):
            raise ValueError("every onset must be on the meter's grid")
        return PitchClassSet(tuple(map(grid.index, onsets)), len(grid))

    def from_grid(self, points: PitchClassSet) -> PitchClassSet:
        """`to_grid` undone: grid points back to pulses."""
        grid = tuple(self.starts(-1))
        if points.size != len(grid):
            raise ValueError(f"{points.size} grid points for a meter of {len(grid)}")
        return PitchClassSet(tuple(grid[point] for point in points), self.pulses)

    def timing(self, swing: float = 1.0, level: int | None = None) -> tuple[float, ...]:
        """When each pulse sounds, in pulses: `swing` is how much longer the first of a pair
        is than the second. 1 is straight, 2 a triplet feel, about 3 a hard shuffle. Measured
        swing runs from about 1 when fast to 3.5 when slow (Friberg & Sundström 2002), so it
        is a number, not a style.

        Which pairs: by default every group, at any level, holding exactly two grid points,
        so the finest pairs swing wherever they are (a beat of 8ths beside a beat of 16ths
        swings both) and groups of three don't (7/8 as 3+2+2 swings only its 2s). With
        `level`, the groups of that level that split into exactly two at the next level, and
        the points inside them stretch with the pair: 8th swing over a grid of 16ths."""
        if swing <= 0:
            raise ValueError(f"swing must be positive, got {swing}")
        if level is None:
            swung, inner = self.levels, self.levels[-1]
        else:
            index = level % len(self.levels)
            if index + 1 >= len(self.levels):
                raise ValueError(f"level {level} has no level below it to swing")
            swung, inner = (self.levels[index],), self.levels[index + 1]
        points = set(group_starts(inner))
        pairs = {
            (start, size, inside[1])
            for groups in swung
            for start, size in zip(group_starts(groups), groups, strict=True)
            if len(inside := [p for p in range(start, start + size) if p in points]) == 2
        }
        times = [float(pulse) for pulse in range(self.pulses)]
        for start, size, middle in pairs:
            moved, end = start + size * swing / (1 + swing), start + size
            for pulse in range(start, end):
                times[pulse] = (
                    start + (pulse - start) * (moved - start) / (middle - start)
                    if pulse < middle
                    else moved + (pulse - middle) * (end - moved) / (end - middle)
                )
        return tuple(times)


def cells(split: int) -> list[tuple[int, ...]]:
    """The ways to fill one count of `split` grid points, as the points that sound. Up to 4,
    every one (15 for sixteenths); from 5, the downbeat alone, the binary and ternary groupings
    (each group of a composition into 2s and 3s starts with a note: 2+3 and 3+2 for a five),
    and every point, since all 2**split are too many to choose from by ear."""
    if split < 1:
        raise ValueError(f"a count needs at least one point, got {split}")
    if split <= 4:
        return [
            chosen for size in range(1, split + 1) for chosen in combinations(range(split), size)
        ]
    found = [(0,), *map(group_starts, compositions(split, (2, 3))), tuple(range(split))]
    return list(dict.fromkeys(found))


def compositions(total: int, parts: Collection[int]) -> Iterator[tuple[int, ...]]:
    """Every ordered way to fill `total` pulses with groups whose sizes are in `parts`: the
    prastara of Indian prosody. (2, 3) gives the binary and ternary groupings of a meter."""
    if total == 0:
        yield ()
        return
    for part in sorted(set(parts)):
        if 0 < part <= total:
            for rest in compositions(total - part, parts):
                yield (part, *rest)


def count(total: int, parts: Collection[int]) -> int:
    """How many `compositions` there are, without listing them. With parts (1, 2) these are
    the Fibonacci numbers (Hemachandra's count of metres); with (2, 3), the Padovan numbers."""
    if total < 0:
        return 0
    ways = [1] + [0] * total
    for filled in range(1, total + 1):
        ways[filled] = sum(ways[filled - part] for part in set(parts) if 0 < part <= filled)
    return ways[total]


def gaps(onsets: PitchClassSet) -> tuple[int, ...]:
    """Pulses from each onset to the next, from the first onset round to it again: the
    inverse of `PitchClassSet.from_steps`."""
    points = tuple(onsets)
    if not points:
        return ()
    return tuple(b - a for a, b in pairwise((*points, points[0] + onsets.size)))


def groupings(onsets: PitchClassSet, parts: Collection[int] = (2, 3)) -> list[tuple[int, ...]]:
    """Each way to group the cycle into `parts` with every onset starting a group: clap 1, 4
    and 6 of 7/8 and only 3+2+2 fits. Empty if an onset can't start a group, e.g. the cycle's
    first pulse isn't one."""
    return [
        option
        for option in compositions(onsets.size, parts)
        if set(onsets) <= set(group_starts(option))
    ]


def guest(pattern: Sequence[int], length: int, offset: int = 0) -> PitchClassSet:
    """`pattern` (gaps in pulses) repeated through `length` pulses, its first onset on pulse
    `offset`, cut where the host cycle ends: a pattern laid over a meter. A 3 over 16 is 0, 3,
    6, 9, 12, 15; displacing it is `offset`."""
    if not pattern or any(gap < 1 for gap in pattern):
        raise ValueError(f"gaps must be positive, got {pattern}")
    period = sum(pattern)
    first = -(offset // period) - 1
    return PitchClassSet(
        tuple(
            onset
            for lap in range(first, first + length // period + 3)
            for step in group_starts(pattern)
            if 0 <= (onset := offset + lap * period + step) < length
        ),
        length,
    )


def syncopation(onsets: PitchClassSet, meter: Meter) -> int:
    """Longuet-Higgins & Lee's syncopation: each note followed by a silence stronger than
    itself before the next note adds the difference in weight. 0 when every silence is weaker
    than the note before it, so any rhythm on the beats."""
    if onsets.size != meter.pulses:
        raise ValueError(f"onsets are on {onsets.size} pulses, the meter has {meter.pulses}")
    weight = meter.weights()
    total = 0
    for onset, gap in zip(onsets, gaps(onsets), strict=True):
        silent = [weight[(onset + step) % onsets.size] for step in range(1, gap)]
        total += max(0, max(silent, default=0) - weight[onset])
    return total


def unevenness(onsets: PitchClassSet) -> int:
    """How far from maximally even: for each number of onsets spanned, how much further apart
    its largest and smallest spans are than 1. 0 exactly for the maximally even (Euclidean)
    rhythms (Clough & Douthett: every span comes in one size or two consecutive sizes)."""
    points, size = tuple(onsets), onsets.size
    total = 0
    for spanned in range(1, len(points)):
        spans = [
            (points[(i + spanned) % len(points)] - point) % size for i, point in enumerate(points)
        ]
        total += max(0, max(spans) - min(spans) - 1)
    return total


def check_nesting(levels: Sequence[Sequence[int]]) -> None:
    """Raise ValueError unless `levels` are groups inside groups: at least one level, every
    group positive, every level the same total, and every group start of a level a group start
    of the next. A meter's levels (in pulses) and a phrase's groups (in syllables) both are."""
    if not levels:
        raise ValueError("needs at least one level of groups")
    if any(part < 1 for level in levels for part in level):
        raise ValueError(f"groups must be positive, got {levels}")
    if len({sum(level) for level in levels}) != 1:
        raise ValueError(f"every level must span the same total, got {levels}")
    for coarse, fine in pairwise(levels):
        if not set(group_starts(coarse)) <= set(group_starts(fine)):
            raise ValueError(f"{fine} does not subdivide {coarse}")


@cache
def _weights(levels: Levels) -> tuple[int, ...]:
    weight = [0] * sum(levels[0])
    for level in levels:
        for start in group_starts(level):
            weight[start] += 1
    return tuple(weight)
