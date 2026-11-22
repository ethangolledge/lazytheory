"""Cadences: making a phrase land, as small linear equations in whole numbers.

Why: the hardest thing to work out by hand in rhythm is the ending, a figure played three times
that finishes exactly on beat one of some later cycle. Every such ending is a template of
unknown lengths that has to fill a known span: three phrases and two gaps fill 3p + 2g pulses,
a tihai of tihais 9p + 6g + 2G, a phrase that grows by d each time k·a + d·k(k−1)/2. So one
solver lists every set of numbers that lands, and the player chooses; nothing is searched by
trial and error, and no answer is missed.

Theory it speaks to: the tihai and mora (Hindustani and Carnatic cadences), the chakradar (a
tihai of tihais: 65 = 64 + 1 in Teentaal), yati shapes (arithmetic progressions of statement
lengths) and the kōrvai (Krishnaswamy & Wells 2023, who prove that a trio of equal or
evenly-growing parts always spans a multiple of 3, so it cannot land on an eduppu e ≢ 0 mod 3
in a cycle divisible by 3). Traditions disagree on where a cadence lands: on its last note
(Jhaptaal: 21 = 2 × 10 + 1) or just after it (16 over 16), so `span` asks which.

Could grow into: kōrvais with a middle part, cumulative designs (each statement adding a
phrase), and cadences over a cycle whose subdivision changes on the way.
"""

from collections.abc import Sequence

from lazy_theory.core.pcset import PitchClassSet
from lazy_theory.rhythm.phrase import Phrase


def solve(
    coefficients: Sequence[int], total: int, lower: int | Sequence[int] = 1
) -> list[tuple[int, ...]]:
    """Every way to choose whole numbers x, each at least its `lower` bound, with
    sum(c * x) == `total`: (3, 2) and 16 give (2, 5) and (4, 2), the tihais of Teentaal. In order
    of the first number, then the next. Coefficients must be positive."""
    count = len(coefficients)
    lows = (lower,) * count if isinstance(lower, int) else tuple(lower)
    if not count or any(c < 1 for c in coefficients) or len(lows) != count:
        raise ValueError(f"need positive coefficients, one bound each, got {coefficients}")
    if any(low < 0 for low in lows):
        raise ValueError(f"bounds must not be negative, got {lows}")
    floors = [
        sum(c * low for c, low in zip(coefficients[i:], lows[i:], strict=True))
        for i in range(count)
    ]
    floors.append(0)
    found: list[tuple[int, ...]] = []

    def fill(i: int, left: int, chosen: tuple[int, ...]) -> None:
        if i == count:
            if left == 0:
                found.append(chosen)
            return
        for x in range(lows[i], (left - floors[i + 1]) // coefficients[i] + 1):
            fill(i + 1, left - coefficients[i] * x, (*chosen, x))

    fill(0, total, ())
    return found


def span(cycle: int, start: int, target: int = 0, laps: int = 0, on_target: bool = True) -> int:
    """Pulses a cadence fills, from its first note on pulse `start` of a `cycle` to landing on
    `target`, going round `laps` more times on the way. `on_target` counts the landing pulse
    itself, the last note sounding on it (Jhaptaal: span(10, 0, laps=2) is 21); otherwise
    the cadence ends just before it (span(16, 0, laps=1, on_target=False) is 16)."""
    if cycle < 1 or laps < 0:
        raise ValueError(f"need a positive cycle and no negative laps, got {cycle}, {laps}")
    total = (target - start) % cycle + laps * cycle + on_target
    if total < 1:
        raise ValueError("a cadence can't land where it starts without going round")
    return total


def landing(start: int, span: int, cycle: int, on_target: bool = True) -> int:
    """The pulse of a `cycle` where a phrase of `span` pulses from `start` lands, `span`'s
    inverse. `on_target` means the phrase's last note is the landing (21 pulses over a 10-beat
    cycle land on its first beat); otherwise the landing is the pulse after it (16 over 16)."""
    if cycle < 1:
        raise ValueError(f"a cycle has at least one pulse, got {cycle}")
    return (start + span - on_target) % cycle


def tihais(total: int, gap_min: int = 0) -> list[tuple[int, int]]:
    """Every (phrase, gap) with 3 phrases and 2 gaps of at least `gap_min` filling `total`
    pulses, longest phrase first. 16 gives (4, 2) and (2, 5)."""
    return sorted(((p, g) for p, g in solve((3, 2), total, (1, gap_min))), reverse=True)


def chakradars(total: int) -> list[tuple[int, int, int]]:
    """Every tihai of tihais filling `total`: (phrase, gap, outer gap), each tihai 3p + 2g,
    played three times with two outer gaps, 9p + 6g + 2G in all, longest phrase first. 65
    includes (7, 0, 1): a phrase of 7 nine times, one pulse between the tihais."""
    return sorted(
        ((p, g, outer) for p, g, outer in solve((9, 6, 2), total, (1, 0, 0))), reverse=True
    )


def yatis(total: int, parts: int) -> list[tuple[int, ...]]:
    """Every run of `parts` statement lengths, each at least 1 and each `d` longer than the one
    before (d may be negative or 0), filling `total`: k·a + d·k(k−1)/2. A growing run is
    srotovaha, a shrinking one gopuccha, an equal one sama. In order of d."""
    if parts < 1:
        raise ValueError(f"need at least one part, got {parts}")
    steps = parts * (parts - 1) // 2
    found = []
    for d in range(-total, total + 1) if steps else (0,):
        first, left = divmod(total - d * steps, parts)
        lengths = tuple(first + d * i for i in range(parts))
        if not left and min(lengths) >= 1:
            found.append(lengths)
    return found


def cadences(
    points: PitchClassSet, start: int = 0, on_target: bool = False
) -> list[tuple[int, int, PitchClassSet]]:
    """Tihais made from the rhythm itself, longest phrase first: the rhythm's first `phrase`
    pulses, played three times by `Phrase.tihai` with `gap` pulses after each but the last,
    from pulse `start` so that the next cycle's first pulse is the landing (`span`'s two
    conventions; with `on_target` the phrase must end on a note, which then sounds on 1).
    Empty if the rhythm's first pulse is silent, since a phrase starts on a note."""
    if 0 not in points:
        return []
    total = span(points.size, start, laps=0 if start % points.size else 1, on_target=on_target)
    found = []
    for phrase, gap in tihais(total):
        if on_target and phrase - 1 not in points:
            continue
        opening = Phrase.notes(PitchClassSet(tuple(n for n in points if n < phrase), phrase))
        found.append((phrase, gap, opening.tihai(gap).onsets(start, points.size)))
    return found
