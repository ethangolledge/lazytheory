import polars as pl
from time import perf_counter

NOTE_TO_CHROMATIC: dict[str, int] = {
    "C": 1, "C#": 2, "DB": 2, "D": 3,
    "D#": 4, "EB": 4, "E": 5, "F": 6,
    "F#": 7, "GB": 7, "G": 8, "G#": 9,
    "AB": 9, "A": 10, "A#": 11, "BB": 11, "B": 12,
}

CHROMATIC_TO_NOTE: dict[int, str] = {
    1: 'C', 2: 'C#', 3: 'D', 4: 'D#', 5: 'E', 6: 'F',
    7: 'F#', 8: 'G', 9: 'G#', 10: 'A', 11: 'A#', 12: 'B'
}

MODE_ST_DEGREES: dict[str, int] = {
    'IONIAN': 0, 'DORIAN': 1, 'PHRYGIAN': 2, 'LYDIAN': 3,
    'MIXOLYDIAN': 4, 'AEOLIAN': 5, 'LOCRIAN': 6,
}

CHROMATIC_INTERVALS: dict[int, tuple[str, ...]] = {
    0: ('1',), 1: ('b2',), 2: ('2',), 3: ('b3',), 4: ('3',),
    5: ('4',), 6: ('b5', '#4'), 7: ('5',), 8: ('b6',), 9: ('6',),
    10: ('b7',), 11: ('7',),
}

IONIAN_ST: list[int] = [0, 2, 4, 5, 7, 9, 11]

def execution_time(func):
    def wrapper(*args, **kwargs):
        start = perf_counter()
        result = func(*args, **kwargs)
        end = perf_counter()
        print(f"Execution time: {end - start:.4f} seconds")
        return result
    return wrapper


class LazyTheory:
    def __init__(self, total_frets: int):
        self.total_frets = total_frets

    def mode_from_major(self, degree: int) -> list[int]:
        """Return a list of the intervals in the mode using the Major scale. Literally the only time this is useful."""
        rotated = IONIAN_ST[degree:] + IONIAN_ST[:degree]
        return set([(x - rotated[0]) % 12 for x in rotated])

    def mode_notes_up_string(self, start_interval: int, mode_intervals: list[int]) -> list[tuple[int, int]]:
        """Return all frets and their intervals on this string in the mode."""
        notes = []
        for fret in range(self.total_frets + 1):
            interval = (start_interval + fret) % 12
            if interval in mode_intervals:
                notes.append((fret, interval))
        return notes

    @execution_time
    def parse_tuning(self, tuning: str, key: str, mode: str):
        strings = [s.strip().upper() for s in tuning]
        if not all(s in NOTE_TO_CHROMATIC for s in strings):
            raise ValueError("Invalid note in tuning")

        key = key.upper().strip()
        chromatic_key = NOTE_TO_CHROMATIC[key]

        mode = mode.upper().strip()
        mode_intervals = self.mode_from_major(MODE_ST_DEGREES[mode])

        df = pl.DataFrame(
            schema={
                "key": pl.Utf8,
                "string": pl.Utf8,
                "note": pl.Utf8,
                "chromatic_note": pl.Int8,
                "interval": pl.Int8,
                "interval_label": pl.Utf8,
                "fret": pl.Int8,
            }
        )

        for string_note in strings:
            chromatic_note = NOTE_TO_CHROMATIC[string_note]
            start_interval = (chromatic_note - chromatic_key) % 12

            notes_up = self.mode_notes_up_string(start_interval, mode_intervals)

            for fret, interval in notes_up:
                note = CHROMATIC_TO_NOTE[(chromatic_note + fret - 1) % 12 + 1]
                chromatic_note = NOTE_TO_CHROMATIC[note]
                interval_label = CHROMATIC_INTERVALS[interval][0]


                df = df.vstack(
                    pl.DataFrame({
                        "key": [key],
                        "string": [string_note],
                        "note": [note],
                        "chromatic_note": pl.Series([chromatic_note], dtype=pl.Int8),
                        "interval": pl.Series([interval], dtype=pl.Int8),
                        "interval_label": [interval_label],
                        "fret": pl.Series([fret], dtype=pl.Int8),
                    })
                )

        print(df)
        df.write_csv("/home/ethan/code/venv/lazy_theory/intervals.csv")
        return df


if __name__ == "__main__":
    theory = LazyTheory(total_frets=12)
    theory.parse_tuning("EADGBE", "E", "DORIAN")
