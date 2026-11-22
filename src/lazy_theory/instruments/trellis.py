"""A progression as a graph, and every search through it as one shortest-path problem.

Why: choosing how to play a progression is choosing one voicing per chord. Each voicing has a
cost of its own (how it sounds) and each change has a cost (how far the hand and the notes
move), so the best way to play it is the cheapest path through a layered graph: one layer per
chord, one node per voicing. Built once as arrays, the same graph answers every question
asked of it: the best route, the best route with some voicings ruled out, the best route for
each melody the top voice could sing, the best route that plays a repeated chord the same way
each time. They differ only in which nodes are allowed, so there is one search, not one per
feature.

Theory it speaks to: this is the Viterbi algorithm (dynamic programming over a trellis, exact:
every path is considered by keeping only the cheapest way to reach each node). Musically it is
why inversions are chosen, not requested: the smoothest inversion of each chord falls out of
the whole progression, as voice-leading practice teaches but by measurement.

Could grow into: sampling routes in proportion to exp(-cost) (the same pass with a soft
minimum), the k cheapest routes, costs that look two chords back (a wider trellis), and a
melody or bass line given in advance (a mask per chord, already supported).
"""

from collections.abc import Callable, Hashable, Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import NamedTuple

import numpy as np
from numpy.typing import NDArray

from lazy_theory.instruments.arrays import Floats, Grid, Mask

Picks = NDArray[np.intp]  # which voicing of each chord: [search, chord]
_CELLS = 4_000_000  # most search x voicing x voicing cells held at once (32 MB of float64)


class Route(NamedTuple):
    """One way through a progression: a voicing per chord and what it costs in all."""

    path: Grid  # one voicing per chord
    cost: float
    picks: tuple[int, ...]  # the row of each chord's options that was chosen
    labels: tuple[float, ...] = ()  # what `each` grouped by, e.g. the top note of each chord


@dataclass(frozen=True, eq=False)
class Trellis:
    """`options[i]` are chord i's voicings, `costs[i]` the cost of each, and `steps[i][a, b]`
    the cost of changing from voicing a of chord i to voicing b of chord i + 1."""

    options: Sequence[Grid]
    costs: Sequence[Floats]
    steps: Sequence[Floats]

    @classmethod
    def build(
        cls,
        options: Sequence[Grid],
        transition: Callable[[Grid, Grid], NDArray[np.floating] | NDArray[np.integer]],
        costs: Sequence[NDArray[np.floating] | NDArray[np.integer]] | None = None,
    ) -> Trellis:
        """The graph of `options`, with `transition` measured once between each pair of
        neighbouring chords. Without `costs` a voicing costs nothing in itself."""
        if not options:
            raise ValueError("a progression needs at least one chord")
        for index, voicings in enumerate(options):
            if len(voicings) == 0:
                raise ValueError(f"no voicing of chord {index} satisfies the rules")
        standing = costs if costs is not None else [np.zeros(len(voicings)) for voicings in options]
        return cls(
            list(options),
            [np.asarray(cost, dtype=np.float64) for cost in standing],
            [np.asarray(transition(a, b), dtype=np.float64) for a, b in pairwise(options)],
        )

    def shortest(self, allowed: Sequence[Mask | None] | None = None) -> Route:
        """The cheapest route: one voicing per chord with the least total cost. `allowed`
        holds, per chord, a mask of the voicings the route may use (None: any), which is how a
        voicing is pinned, a bass or top note required, or a string held."""
        masks = [None if mask is None else mask[None, :] for mask in allowed or ()]
        picks, totals = self.search(masks or [None] * len(self.options))
        if not np.isfinite(totals[0]):
            raise ValueError("no route satisfies the constraints")
        return self.route(picks[0], float(totals[0]))

    def search(self, allowed: Sequence[Mask | None]) -> tuple[Picks, Floats]:
        """`shortest` for many sets of constraints at once: each chord's mask is None or
        [search, voicing], or [1, voicing] to share one mask between all of them. The picks of
        every search and its total, infinite where nothing is allowed. Searches run together
        as one array, in batches that bound memory."""
        if len(allowed) != len(self.options):
            raise ValueError(f"one mask per chord ({len(self.options)}), got {len(allowed)}")
        searches = max((len(mask) for mask in allowed if mask is not None), default=1)
        batch = max(1, _CELLS // max((step.size for step in self.steps), default=1))
        found = [
            self._search([_rows(mask, start, start + batch) for mask in allowed])
            for start in range(0, searches, batch)
        ]
        return np.concatenate([p for p, _ in found]), np.concatenate([t for _, t in found])

    def each(self, labels: Sequence[Floats], slack: float) -> list[Route]:
        """The cheapest route for each sequence of labels (`labels[i]` holds one per voicing of
        chord i), for every sequence whose route costs at most `slack` more than the cheapest
        of all. Cheapest first, so the first is `shortest`.

        Labelled by top note, each route is the best way to play one top line; by bass, one
        bass line. A line is dropped as soon as even its cheapest finish costs too much (a
        backward pass gives that for every voicing), so only lines that can finish within
        `slack` are followed.
        """
        finish = [np.zeros(len(self.options[-1]))]  # cheapest way on from each voicing
        for step, cost in zip(reversed(self.steps), reversed(self.costs[1:]), strict=True):
            finish.insert(0, (step + cost + finish[0]).min(axis=1))
        budget = float((self.costs[0] + finish[0]).min()) + slack + 1e-9
        kinds = [np.unique(chord_labels) for chord_labels in labels]
        routes: list[Route] = []

        def follow(chord: int, arrive: Floats, back: list[Picks], line: tuple[float, ...]) -> None:
            for label in kinds[chord]:
                total = np.where(labels[chord] == label, arrive, np.inf)
                if (total + finish[chord]).min() > budget:
                    continue
                named = (*line, label.item())
                if chord == len(self.steps):
                    picks = _trace(back, total.argmin(axis=1))[0]
                    routes.append(self.route(picks, float(total.min()), named))
                else:
                    onward, pointers = _advance(total, self.steps[chord], self.costs[chord + 1])
                    follow(chord + 1, onward, [*back, pointers], named)

        follow(0, self.costs[0][None, :], [], ())
        return sorted(routes, key=lambda route: route.cost)

    def tied(self, groups: Sequence[Hashable]) -> Route:
        """`shortest`, with every chord of a group on the same voicing: a song keeps one shape
        for a chord it plays again. `groups` holds one id per chord; chords sharing an id must
        have the same options.

        Each repeated group in turn tries every voicing at all its places at once while the
        other groups stay where they are, until no group can lower the total. With one
        repeated chord that is the cheapest tied route; with several it is the cheapest any
        one group can reach alone (coordinate descent), which may miss a route that needs two
        groups to change together.
        """
        if len(groups) != len(self.options):
            raise ValueError(f"one group per chord ({len(self.options)}), got {len(groups)}")
        places: dict[Hashable, list[int]] = {}
        for index, group in enumerate(groups):
            places.setdefault(group, []).append(index)
        repeated = [where for where in places.values() if len(where) > 1]
        for where in repeated:
            if any(not np.array_equal(self.options[where[0]], self.options[i]) for i in where):
                raise ValueError("chords in a group must have the same options")
        every = [i for where in repeated for i in where]
        picks = np.array(self.shortest().picks)
        for where in repeated:  # start tied, each group on its shape where it first plays
            picks[where] = picks[where[0]]

        def held(chords: Sequence[int]) -> list[Mask | None]:
            masks: list[Mask | None] = [None] * len(self.options)
            for i in chords:
                masks[i] = np.arange(len(self.options[i]))[None, :] == picks[i]
            return masks

        found, totals = self.search(held(every))
        picks, best = found[0], float(totals[0])
        improved = True
        while improved:
            improved = False
            for where in repeated:
                masks = held([i for i in every if i not in where])
                for i in where:
                    masks[i] = np.eye(len(self.options[i]), dtype=bool)  # search k: shape k
                found, totals = self.search(masks)
                k = int(totals.argmin())
                if totals[k] < best - 1e-9:
                    picks, best, improved = found[k], float(totals[k]), True
        return self.route(picks, best)

    def route(
        self, picks: Sequence[int] | Picks, cost: float, labels: tuple[float, ...] = ()
    ) -> Route:
        """The Route that takes voicing `picks[i]` of each chord."""
        chosen = tuple(int(pick) for pick in picks)
        path: Grid = np.stack([o[pick] for o, pick in zip(self.options, chosen, strict=True)])
        return Route(path, cost, chosen, labels)

    def _search(self, allowed: Sequence[Mask | None]) -> tuple[Picks, Floats]:
        def only(chord: int, total: Floats) -> Floats:
            mask = allowed[chord]
            return total if mask is None else np.where(mask, total, np.inf)

        total, back = only(0, self.costs[0][None, :]), []
        for chord, step in enumerate(self.steps):
            total, pointers = _advance(total, step, self.costs[chord + 1])
            total = only(chord + 1, total)
            back.append(pointers)
        return _trace(back, total.argmin(axis=1)), total.min(axis=1)


def _rows(mask: Mask | None, start: int, stop: int) -> Mask | None:
    """A batch of a mask's searches; a mask shared by all of them stays whole."""
    return mask if mask is None or len(mask) == 1 else mask[start:stop]


def _advance(total: Floats, step: Floats, cost: Floats) -> tuple[Floats, Picks]:
    """One chord on, for every search at once: from the cheapest total at each voicing
    ([search, voicing]), the cheapest total at each voicing of the next chord, and which
    voicing each was reached from."""
    reach = total[:, :, None] + step
    came = reach.argmin(axis=1)
    return np.take_along_axis(reach, came[:, None, :], axis=1)[:, 0] + cost, came


def _trace(back: Sequence[Picks], last: Picks) -> Picks:
    """Each search's route, read backwards from its last voicing through `back`."""
    picks = np.empty((len(last), len(back) + 1), dtype=np.intp)
    picks[:, -1] = last
    search = np.arange(len(last))
    for chord in range(len(back) - 1, -1, -1):
        shared = len(back[chord]) == 1  # searches not yet told apart share one row of pointers
        picks[:, chord] = back[chord][0 if shared else search, picks[:, chord + 1]]
    return picks
