"""Words for instruments: tab, and the name of a set of open strings."""

from collections.abc import Mapping, Sequence

from lazy_theory.instruments.fretboard import Tuning
from lazy_theory.pitch.key import Key
from lazy_theory.pitch.names import note_name


def tab(
    open_strings: Sequence[int],
    voicings: Sequence[Sequence[int]],
    titles: Sequence[str] = (),
    key: Key | None = None,
) -> str:
    """Voicings as guitar tab: one line per string, the highest string on top, labelled with
    its open note; one column per voicing under its title. A negative fret is a muted "x"."""
    columns = [[str(fret) if fret >= 0 else "x" for fret in voicing] for voicing in voicings]
    titles = list(titles) + [""] * (len(columns) - len(titles))
    widths = [
        max(len(title), *map(len, column)) for title, column in zip(titles, columns, strict=True)
    ]
    labels = [note_name(string, key) for string in open_strings]
    pad = max(map(len, labels))
    lines = [" " * (pad + 2) + "  ".join(t.ljust(w) for t, w in zip(titles, widths, strict=True))]
    for string in reversed(range(len(open_strings))):
        cells = "  ".join(
            column[string].ljust(w) for column, w in zip(columns, widths, strict=True)
        )
        lines.append(f"{labels[string].ljust(pad)} |{cells}")
    return "\n".join(line.rstrip() for line in lines)


def tuning_name(open_strings: Sequence[int], tunings: Mapping[str, Tuning]) -> str | None:
    """The name of these open strings among `tunings`, or of a named tuning moved by whole
    steps, e.g. "guitar open D +2"; the smallest move wins. None if no tuning fits."""
    moved = {}
    for name, tuning in tunings.items():
        if len(tuning.open_strings) == len(open_strings):
            shifts = {int(a) - b for a, b in zip(open_strings, tuning.open_strings, strict=True)}
            if len(shifts) == 1:
                moved[name] = shifts.pop()
    if not moved:
        return None
    nearest = min(moved, key=lambda name: abs(moved[name]))
    return nearest if moved[nearest] == 0 else f"{nearest} {moved[nearest]:+d}"
