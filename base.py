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
MODE_DEGREES: dict[str, dict[int, str]] = {
    'IONIAN_ST_SCALE_INTERVALS': {
        0: 'Ionian',
        1: 'Dorian',
        2: 'Phrygian',
        3: 'Lydian',
        4: 'Mixolydian',
        5: 'Aeolian',
        6: 'Locrian'
    },
    'AEOLIAN_HM_SCALE_INTERVALS': {
        0: 'Harmonic Minor',
        1: 'Locrian ♯6',
        2: 'Ionian ♯5',
        3: 'Dorian ♯4',
        4: 'Phrygian Dominant',
        5: 'Lydian ♯2',
        6: 'Super Locrian'
    },
    'AEOLIAN_MD_SCALE_INTERVALS': {
        0: 'Melodic Minor',
        1: 'Dorian ♭2',
        2: 'Lydian Augmented',
        3: 'Lydian Dominant',
        4: 'Mixolydian ♭6',
        5: 'Locrian ♮2',
        6: 'Altered'
    }
}


CHROMATIC_INTERVALS: dict[int, tuple[str, ...]] = {
    0: ('1',), 1: ('b2',), 2: ('2',), 3: ('b3',), 4: ('3',),
    5: ('4',), 6: ('b5', '#4'), 7: ('5',), 8: ('b6',), 9: ('6',),
    10: ('b7',), 11: ('7',),
}

IONIAN_ST_SCALE_INTERVALS: list[int] = [0, 2, 4, 5, 7, 9, 11]
AEOLIAN_HM_SCALE_INTERVALS: list[int] = [0, 2, 3, 5, 7, 8, 11] # raised 7th
AEOLIAN_MD_SCALE_INTERVALS: list[int] = [0, 2, 3, 5, 7, 9, 11] # raised 6th and 7th


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

    def mode_intervals_from_scale(
        self,
        degree: int,
        scale_variant: str = "NATURAL"
    ) -> set[int]:
        scale_variant = scale_variant.upper().strip()
        if scale_variant not in ("NATURAL", "HARMONIC", "MELODIC"):
            raise ValueError("Invalid scale variant")

        if scale_variant == "NATURAL":
            scale_intervals = IONIAN_ST_SCALE_INTERVALS
            variant_key = 'IONIAN_ST_SCALE_INTERVALS'
        elif scale_variant == "HARMONIC":
            scale_intervals = AEOLIAN_HM_SCALE_INTERVALS
            variant_key = 'AEOLIAN_HM_SCALE_INTERVALS'
        elif scale_variant == "MELODIC":
            scale_intervals = AEOLIAN_MD_SCALE_INTERVALS
            variant_key = 'AEOLIAN_MD_SCALE_INTERVALS'

        rotated_scale = scale_intervals[degree:] + scale_intervals[:degree]

        mode_name = MODE_DEGREES[variant_key][degree]

        print(f"Mode: {mode_name}")

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
        scale_variant: str,
        degree: str
    ) -> pl.DataFrame:
        string_notes: list[str] = [note.strip().upper() for note in tuning]
        if not all(note in NOTE_TO_CHROMATIC for note in string_notes):
            raise ValueError("Invalid note in tuning")

        key_note: str = key.upper().strip()
        key_chromatic_value: int = NOTE_TO_CHROMATIC[key_note]

        mode_intervals: set[int] = self.mode_intervals_from_scale(degree, scale_variant)

        rows: list[dict[str, int | str]] = []

        for string_note in string_notes:
            string_root_chromatic: int = NOTE_TO_CHROMATIC[string_note]
            starting_interval: int = (string_root_chromatic - key_chromatic_value) % 12
            frets_and_intervals: list[tuple[int, int]] = self.frets_in_mode_for_string(starting_interval, list(mode_intervals))

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
    guitar_theory.parse_tuning("EADGBE", "E", "MELODIC", 5)