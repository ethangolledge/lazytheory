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

IONIAN_SCALE_INTERVALS: list[int] = [0, 2, 4, 5, 7, 9, 11]


def execution_time(
    func
):
    def wrapper(*args, **kwargs):
        start_time: float = perf_counter()
        result = func(*args, **kwargs)
        end_time: float = perf_counter()
        print(f"Execution time: {end_time - start_time:.4f} seconds")
        return result
    return wrapper


class LazyTheory:
    total_frets: int

    def __init__(
        self, 
        total_frets: int
    ) -> None:
        self.total_frets = total_frets

    def mode_intervals_from_major_scale(
        self, 
        major_scale_degree: int
    ) -> set[int]:
        """Return a set of intervals for the mode derived from the major (Ionian) scale."""
        rotated_scale: list[int] = IONIAN_SCALE_INTERVALS[major_scale_degree:] + IONIAN_SCALE_INTERVALS[:major_scale_degree]
        return {(interval - rotated_scale[0]) % 12 for interval in rotated_scale}

    def frets_in_mode_for_string(
        self, 
        start_interval: int, 
        mode_intervals: list[int]
    ) -> list[tuple[int, int]]:
        """Return all fret numbers and their intervals on a string in a given mode."""
        frets_with_intervals: list[tuple[int, int]] = []
        for fret_number in range(self.total_frets + 1):
            interval_at_fret: int = (start_interval + fret_number) % 12
            if interval_at_fret in mode_intervals:
                frets_with_intervals.append((fret_number, interval_at_fret))
        return frets_with_intervals

    @execution_time
    def parse_tuning(
        self, 
        tuning: str, 
        key: str, 
        mode: str
    ) -> pl.DataFrame:
        string_notes: list[str] = [note.strip().upper() for note in tuning]
        if not all(note in NOTE_TO_CHROMATIC for note in string_notes):
            raise ValueError("Invalid note in tuning")

        key_note: str = key.upper().strip()
        key_chromatic_value: int = NOTE_TO_CHROMATIC[key_note]

        mode_name: str = mode.upper().strip()
        mode_interval_set: set[int] = self.mode_intervals_from_major_scale(MODE_ST_DEGREES[mode_name])

        rows: list[dict[str, int | str]] = []

        for string_note in string_notes:
            string_root_chromatic: int = NOTE_TO_CHROMATIC[string_note]
            starting_interval: int = (string_root_chromatic - key_chromatic_value) % 12
            frets_and_intervals: list[tuple[int, int]] = self.frets_in_mode_for_string(starting_interval, list(mode_interval_set))

            for fret_number, interval_value in frets_and_intervals:
                note_at_fret: str = CHROMATIC_TO_NOTE[(string_root_chromatic + fret_number - 1) % 12 + 1]
                chromatic_value_at_fret: int = NOTE_TO_CHROMATIC[note_at_fret]
                interval_label: str = CHROMATIC_INTERVALS[interval_value][0]

                rows.append({
                    "key": key_note,
                    "string": string_note,
                    "note": note_at_fret,
                    "chromatic_note": chromatic_value_at_fret,
                    "interval": interval_value,
                    "interval_label": interval_label,
                    "fret": fret_number,
                })

        df: pl.DataFrame = pl.DataFrame(rows, schema={
            "key": pl.Utf8,
            "string": pl.Utf8,
            "note": pl.Utf8,
            "chromatic_note": pl.Int8,
            "interval": pl.Int8,
            "interval_label": pl.Utf8,
            "fret": pl.Int8,
        })

        df.write_csv("/home/ethan/code/venv/lazy_theory/intervals.csv")
        print(df)
        return df


if __name__ == "__main__":
    guitar_theory: LazyTheory = LazyTheory(total_frets=12)
    guitar_theory.parse_tuning("EADGBE", "E", "DORIAN")
