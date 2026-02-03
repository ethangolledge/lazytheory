import polars as pl
from time import perf_counter
import json

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

CHROMATIC_INTERVALS: dict[int, tuple[str, ...]] = {
    0: ('1',), 1: ('b2',), 2: ('2',), 3: ('b3',), 4: ('3',),
    5: ('4',), 6: ('b5', '#4'), 7: ('5',), 8: ('b6',), 9: ('6',),
    10: ('b7',), 11: ('7',),
}

MODE_DEGREES: dict[str, dict[int, str]] = {
    'IONIAN_ST_SCALE_INTERVALS': {
        0: 'Ionian', 1: 'Dorian', 2: 'Phrygian', 3: 'Lydian',
        4: 'Mixolydian', 5: 'Aeolian', 6: 'Locrian'
    },
    'AEOLIAN_HM_SCALE_INTERVALS': {
        0: 'Harmonic Minor', 1: 'Locrian ♯6', 2: 'Ionian ♯5',
        3: 'Dorian ♯4', 4: 'Phrygian Dominant', 5: 'Lydian ♯2', 6: 'Super Locrian'
    },
    'AEOLIAN_MD_SCALE_INTERVALS': {
        0: 'Melodic Minor', 1: 'Dorian ♭2', 2: 'Lydian Augmented',
        3: 'Lydian Dominant', 4: 'Mixolydian ♭6', 5: 'Locrian ♮2', 6: 'Altered'
    },
    'WHOLE_TONE_SCALE': {0: 'Whole Tone'},
    'DIMINISHED_SCALE': {0: 'Diminished'},
    'PENTATONIC_MAJOR': {0: 'Major Pentatonic'},
    'PENTATONIC_MINOR': {0: 'Minor Pentatonic'}
}

CHORD_INTERVALS = {
    (0, 3, 7): "minor",
    (0, 4, 7): "major",
    (0, 3, 6): "diminished",
    (0, 4, 8): "augmented",
    (0, 4, 7, 10): "dominant 7th",
    (0, 4, 7, 11): "major 7th",
    (0, 3, 7, 10): "minor 7th",
    (0, 3, 6, 10): "half-diminished 7th",
    (0, 3, 6, 9): "diminished 7th",
    (0, 4, 8, 10): "augmented 7th",
}


IONIAN_ST_SCALE_INTERVALS = [0, 2, 4, 5, 7, 9, 11]
AEOLIAN_HM_SCALE_INTERVALS = [0, 2, 3, 5, 7, 8, 11]  # raised 7th
AEOLIAN_MD_SCALE_INTERVALS = [0, 2, 3, 5, 7, 9, 11]  # raised 6th & 7th

WHOLE_TONE_SCALE = [0, 2, 4, 6, 8, 10]
DIMINISHED_SCALE = [0, 2, 3, 5, 6, 8, 9, 11]
PENTATONIC_MAJOR = [0, 2, 4, 7, 9]
PENTATONIC_MINOR = [0, 3, 5, 7, 10]


def execution_time(func):
    def wrapper(*args, **kwargs):
        start_time = perf_counter()
        result = func(*args, **kwargs)
        end_time = perf_counter()
        print(f"Execution time: {end_time - start_time:.4f} seconds")
        return result
    return wrapper


class LazyTheory:
    def __init__(
        self, 
        total_frets: int,
        tuning: str,
        key: str
    ):
        self.total_frets = total_frets
        self.key_note = key.upper()
        self.key_chromatic = NOTE_TO_CHROMATIC[self.key_note]
        self.tuning = tuning

        self.open_string_notes = [n.strip().upper() for n in tuning]
        if not all(n in NOTE_TO_CHROMATIC for n in self.open_string_notes):
            raise ValueError("Invalid note in tuning")

    def mode_intervals_from_scale(
        self, 
        degree: int = 0, 
        scale_variant: str = "NATURAL"
    ) -> list[int]:
        """Return the mode intervals for a given scale and degree."""
        scale_variant = scale_variant.upper().replace(" ", "")

        scale_map = {
            "NATURAL": (IONIAN_ST_SCALE_INTERVALS, 'IONIAN_ST_SCALE_INTERVALS'),
            "HARMONIC": (AEOLIAN_HM_SCALE_INTERVALS, 'AEOLIAN_HM_SCALE_INTERVALS'),
            "MELODIC": (AEOLIAN_MD_SCALE_INTERVALS, 'AEOLIAN_MD_SCALE_INTERVALS'),
            "WHOLETONE": (WHOLE_TONE_SCALE, 'WHOLE_TONE_SCALE'),
            "DIMINISHED": (DIMINISHED_SCALE, 'DIMINISHED_SCALE'),
            "PENTATONICMAJOR": (PENTATONIC_MAJOR, 'PENTATONIC_MAJOR'),
            "PENTATONICMINOR": (PENTATONIC_MINOR, 'PENTATONIC_MINOR')
        }

        if scale_variant not in scale_map:
            raise ValueError("Invalid scale variant")

        scale_intervals, variant_key = scale_map[scale_variant]

        # Rotate scale if multiple modes exist
        if variant_key in ("IONIAN_ST_SCALE_INTERVALS", "AEOLIAN_HM_SCALE_INTERVALS", "AEOLIAN_MD_SCALE_INTERVALS"):
            degree %= len(scale_intervals)
            rotated = scale_intervals[degree:] + scale_intervals[:degree]
            mode_name = MODE_DEGREES[variant_key][degree]
            print(f"Mode: {mode_name}")
        else:
            rotated = scale_intervals
            mode_name = MODE_DEGREES[variant_key][0]
            print(f"Scale: {mode_name}")

        base = rotated[0]
        return [(i - base) % 12 for i in rotated]

    def frets_in_mode_for_string(
        self, 
        start_interval: int, 
        mode_intervals: list[int]
    ) -> list[tuple[int, int]]:
        """Return fret numbers and interval values for a string in a mode."""
        return [(fret, (start_interval + fret) % 12)
                for fret in range(self.total_frets + 1)
                if (start_interval + fret) % 12 in mode_intervals]
        
    def identify_chord(
        self,
        degree_relative_intervals: list[int]
    ) -> str:
        sorted_intervals = tuple(sorted(degree_relative_intervals))
        return CHORD_INTERVALS.get(sorted_intervals, "unknown")

    def build_chords_rework(
        self,
        mode_intervals: list[int],
        chord_size: int = 4
    ):
        chord_dict: dict[str, list[dict]] = {}
        scale_len = len(mode_intervals)

        for degree in range(scale_len):
            root_interval = mode_intervals[degree]

            # Key-relative intervals
            chord_intervals_key = [
                mode_intervals[(degree + i * 2) % scale_len]
                for i in range(chord_size)
            ]

            # Degree-relative intervals (distance from chord root)
            chord_intervals_degree = [
                (i - root_interval) % 12
                for i in chord_intervals_key
            ]

            # Labels
            chord_interval_labels_key = [
                CHROMATIC_INTERVALS[i][0]
                for i in chord_intervals_key
            ]

            chord_interval_labels_degree = [
                CHROMATIC_INTERVALS[i][0]
                for i in chord_intervals_degree
            ]

            chord_name = f"{degree + 1}_chord"

            quality = self.identify_chord(chord_intervals_degree)
            root_note = CHROMATIC_TO_NOTE[root_interval + 1]
            chord_display_name = f"{root_note} {quality}"

            chord_name = f"{degree + 1}_chord"

            chord_dict[chord_name] = [
                {
                    "degree": degree + 1,
                    "root_interval": root_interval,
                    "root_note": root_note,

                    "intervals_key": chord_intervals_key,
                    "intervals_degree": chord_intervals_degree,

                    "labels_key": chord_interval_labels_key,
                    "labels_degree": chord_interval_labels_degree,

                    "quality": quality,
                    "chord_name": chord_display_name,

                    "chord_size": chord_size
                }
            ]

        return chord_dict

    @execution_time
    def fretboard_builder(
        self,
        scale_variant: str = "NATURAL",
        degree: int = 0,
        save_csv: str | None = None
    ) -> pl.DataFrame:

        mode_intervals = self.mode_intervals_from_scale(degree, scale_variant)
        print(mode_intervals)
        rows = []
        chord_dict = self.build_chords_rework(mode_intervals)
        print(chord_dict)
        print(json.dumps(chord_dict, indent=2))

        for string_number, open_string_note in enumerate(self.open_string_notes, 1):
            string_chromatic = NOTE_TO_CHROMATIC[open_string_note]
            start_interval = (string_chromatic - self.key_chromatic) % 12
            frets_and_intervals = self.frets_in_mode_for_string(start_interval, mode_intervals)

            for fret, interval_value in frets_and_intervals:
                # Calculate note at fret and convert to 1–12 to pull the chromatic note
                note_at_fret = CHROMATIC_TO_NOTE[((string_chromatic + fret - 1) % 12) + 1]
                chromatic_value_at_fret = NOTE_TO_CHROMATIC[note_at_fret]
                interval_label = CHROMATIC_INTERVALS[interval_value][0]

                rows.append({
                    "key": self.key_note,
                    "string": open_string_note,
                    "string_number": string_number,
                    "note": note_at_fret,
                    "chromatic_note": chromatic_value_at_fret,
                    "interval": interval_value,
                    "interval_label": interval_label,
                    "fret": fret,
                })

        df = pl.DataFrame(rows, schema={
            "key": pl.Utf8,
            "string": pl.Utf8,
            "string_number": pl.Int8,
            "note": pl.Utf8,
            "chromatic_note": pl.Int8,
            "interval": pl.Int8,
            "interval_label": pl.Utf8,
            "fret": pl.Int8,
        })

        if save_csv:
            df.write_csv(save_csv)

        print(df.head(20))
        return df


if __name__ == "__main__":
    guitar_theory = LazyTheory(total_frets=12, tuning="EADGBE", key="E")
    guitar_theory.fretboard_builder(scale_variant="NATURAL", degree=0, save_csv="/home/ethan/code/venv/lazy_theory/intervals.csv")