import polars as pl
from time import perf_counter
import json
import duckdb
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent

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

INTERVAL_CONSONANCE_RATIOS: dict[int, float] = {
    0: 1.0,      # unison
    1: 16/15,    # minor 2nd
    2: 9/8,      # major 2nd
    3: 6/5,      # minor 3rd
    4: 5/4,      # major 3rd
    5: 4/3,      # perfect 4th
    6: 45/32,    # tritone
    7: 3/2,      # perfect 5th
    8: 8/5,      # minor 6th
    9: 5/3,      # major 6th
    10: 9/5,     # minor 7th
    11: 15/8,    # major 7th
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

    def identify_notes(
        self,
        key_relative_intervals: list[int]
    ) -> list[str]:
        """
        Determine the actual note names for the scale intervals,ensuring each note letter appears only once.
        """
        used_letters = set()
        notes_in_scale = []

        key_chromatic = self.key_chromatic
        key_letter = self.key_note[0]

        for interval in key_relative_intervals:
            chrom_value = (key_chromatic + interval - 1) % 12 + 1
            candidate = CHROMATIC_TO_NOTE[chrom_value]

            candidate_letter = candidate[0]
            if candidate_letter in used_letters:
                # pick enharmonic alternative if available
                alternatives = [n for n, v in NOTE_TO_CHROMATIC.items() if v == chrom_value and n[0] not in used_letters]
                if alternatives:
                    candidate = alternatives[0]

            notes_in_scale.append(candidate)
            used_letters.add(candidate[0])

        return notes_in_scale


    def identify_chord(
        self,
        degree_relative_intervals: list[int]
    ) -> str:
        sorted_intervals = tuple(sorted(degree_relative_intervals))
        return CHORD_INTERVALS.get(sorted_intervals, "unknown")

    def label_intervals(
        self,
        intervals: list[int]
    ):
        return [CHROMATIC_INTERVALS[i][0] for i in intervals]

    def compute_chord_intervals(
        self,
        mode_intervals: list[int],
        degree: int, 
        chord_size: int
    ):
        scale_len = len(mode_intervals)
        chord_intervals_key = [
            mode_intervals[(degree + i * 2) % scale_len]
            for i in range(chord_size)
        ]
        root_interval = mode_intervals[degree]
        chord_intervals_degree = [
            (i - root_interval) % 12 for i in chord_intervals_key
        ]
        return chord_intervals_key, chord_intervals_degree, root_interval


    def chords_dict(
        self, 
        mode_intervals: list[int], 
        chord_size: int = 4
    ):
        chord_dict: dict[str, list[dict]] = {}
        scale_len = len(mode_intervals)

        # Get notes for the scale with unique letters
        scale_notes = self.identify_notes(mode_intervals)

        for degree in range(scale_len):
            chord_intervals_key, chord_intervals_degree, root_interval = self.compute_chord_intervals(
                mode_intervals, degree, chord_size
            )

            chord_interval_labels_key = self.label_intervals(chord_intervals_key)
            chord_interval_labels_degree = self.label_intervals(chord_intervals_degree)

            tones = [
                {
                    "tone_index": i,
                    "interval_key_relative": chord_intervals_key[i],
                    "interval_degree_relative": chord_intervals_degree[i],
                    "label_key": chord_interval_labels_key[i],
                    "label_degree": chord_interval_labels_degree[i],
                    "note": scale_notes[(degree + i * 2) % scale_len]  # assign actual note
                }
                for i in range(chord_size)
            ]

            quality = self.identify_chord(chord_intervals_degree)
            root_note = scale_notes[degree]
            chord_display_name = f"{root_note} {quality}"
            chord_name = f"{degree + 1}_chord"

            chord_dict[chord_name] = [
                {
                    "degree": degree + 1,
                    "root_interval": root_interval,
                    "root_note": root_note,
                    "quality": quality,
                    "chord_name": chord_display_name,
                    "chord_size": chord_size,
                    "tones": tones
                }
            ]

        return chord_dict

    @execution_time
    def chord_builder(
        self,
        chord_size: int = 3,
        scale_variant: str = "NATURAL",
        degree: int = 0,
        save_csv: str | Path | None = None
    ) -> pl.DataFrame:
        """
        Build a Polars DataFrame from chords_dict output, using key-relative intervals
        for direct joining with fretboard_builder DF.
        Each row corresponds to a single tone in a chord.
        """
        mode_intervals = self.mode_intervals_from_scale(degree, scale_variant)
        chord_dict = self.chords_dict(mode_intervals, chord_size)
        scale_notes = self.identify_notes(mode_intervals)
        rows = []

        for chord_name, chord_info_list in chord_dict.items():
            chord_info = chord_info_list[0]
            root_interval = chord_info["root_interval"]

            for tone in chord_info["tones"]:
                # Compute key-relative interval for this tone
                interval_key_relative = (root_interval + tone["interval_degree_relative"]) % 12
                interval_label = CHROMATIC_INTERVALS[interval_key_relative][0]
                note = tone["note"]

                rows.append({
                    "chord_name": chord_info["chord_name"],
                    "chord_degree": chord_info["degree"],
                    "chord_quality": chord_info["quality"],
                    "chord_size": chord_info["chord_size"],
                    "tone_index": tone["tone_index"],
                    "tone_note": note,
                    "interval": interval_key_relative,   # key-relative
                    "interval_label": interval_label,    # label for key-relative interval
                    "root_note": chord_info["root_note"],
                    "root_interval": root_interval
                })

        df = pl.DataFrame(rows, schema={
            "chord_name": pl.Utf8,
            "chord_degree": pl.Int8,
            "chord_quality": pl.Utf8,
            "chord_size": pl.Int8,
            "tone_index": pl.Int8,
            "tone_note": pl.Utf8,
            "interval": pl.Int8,
            "interval_label": pl.Utf8,
            "root_note": pl.Utf8,
            "root_interval": pl.Int8
        })

        if save_csv:
            df.write_csv(save_csv)

        duckdb.register("chords_table", df.to_arrow())
        print(df.head(20))
        return df



    def frets_in_mode_for_string(
        self, 
        start_interval: int, 
        mode_intervals: list[int]
    ) -> list[tuple[int, int]]:
        """Return fret numbers and interval values for a string in a mode."""
        return [(fret, (start_interval + fret) % 12)
                for fret in range(self.total_frets + 1)
                if (start_interval + fret) % 12 in mode_intervals]
        
    @execution_time
    def fretboard_builder(
        self,
        scale_variant: str = "NATURAL",
        degree: int = 0,
        save_csv: str | Path | None = None
    ) -> pl.DataFrame:

        mode_intervals = self.mode_intervals_from_scale(degree, scale_variant) # might be worth moving this down the exection

        # Get notes for the scale with unique letters
        scale_notes = self.identify_notes(mode_intervals)

        rows = []

        for string_number, open_string_note in enumerate(self.open_string_notes, 1):
            string_chromatic = NOTE_TO_CHROMATIC[open_string_note]
            start_interval = (string_chromatic - self.key_chromatic) % 12
            frets_and_intervals = self.frets_in_mode_for_string(start_interval, mode_intervals)

            for fret, interval_value in frets_and_intervals:
                # Use scale_notes to ensure proper sharps/flats
                note_index = (interval_value + self.key_chromatic - 1) % len(scale_notes)
                note_at_fret = scale_notes[note_index]
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

        duckdb.register("frets_table", df.to_arrow())


        print(df.head(20))
        return df


if __name__ == "__main__":
    scale_variant = "NATURAL"
    degree = 0
    guitar_theory = LazyTheory(total_frets=12, tuning="EADGBE", key="E")
    guitar_theory.fretboard_builder(scale_variant=scale_variant, degree=degree, save_csv=PROJECT_DIR / "intervals.csv")
    guitar_theory.chord_builder(scale_variant=scale_variant, degree=degree, chord_size=4, save_csv=PROJECT_DIR / "chords.csv")
    
    # Parameters
    MAX_FRET_SPAN = 4  # maximum distance between lowest and highest fret in an inversion

    # SQL: join frets and chords on key-relative interval
    # then compute inversions per chord using the min fret of the chord tones
    query = f"""
    WITH chord_notes AS (
        SELECT
            c.chord_name,
            c.chord_degree,
            c.chord_quality,
            c.chord_size,
            c.tone_index,
            c.tone_note AS chord_tone_note,
            c.interval AS chord_interval,
            c.root_note AS chord_root_note,
            c.root_interval AS chord_root_interval
        FROM chords_table AS c
    ),

    fret_chord_matches AS (
        SELECT 
            f.key,
            f.string,
            f.string_number,
            f.note AS fret_note,
            f.chromatic_note,
            f.interval AS fret_interval,
            f.interval_label AS fret_interval_label,
            f.fret,
            cn.chord_name,
            cn.chord_degree,
            cn.chord_quality,
            cn.chord_size,
            cn.tone_index,
            cn.chord_tone_note,
            cn.chord_interval,
            cn.chord_root_note,
            cn.chord_root_interval
        FROM frets_table AS f
        JOIN chord_notes AS cn
          ON f.interval = cn.chord_interval
    ),

    chord_positions AS (
        SELECT
            chord_name,
            chord_degree,
            chord_quality,
            chord_size,
            chord_root_note,
            chord_root_interval,
            ARRAY_AGG(fret) AS frets,
            ARRAY_AGG(fret_note) AS notes,
            ARRAY_AGG(string_number) AS strings,
            MIN(fret) AS lowest_fret,
            MAX(fret) AS highest_fret
        FROM fret_chord_matches
        GROUP BY chord_name, chord_degree, chord_quality, chord_size, chord_root_note, chord_root_interval
    ),

    valid_inversions AS (
        SELECT
            *,
            highest_fret - lowest_fret AS fret_span,
            ROW_NUMBER() OVER (PARTITION BY chord_name ORDER BY lowest_fret) AS inversion_number
        FROM chord_positions
        WHERE (highest_fret - lowest_fret) <= {MAX_FRET_SPAN}  -- filter after aggregation
    )

    SELECT
        vi.chord_name,
        vi.chord_degree,
        vi.chord_quality,
        vi.chord_size,
        vi.chord_root_note,
        vi.chord_root_interval,
        vi.inversion_number,
        UNNEST(vi.notes) AS note,
        UNNEST(vi.frets) AS fret,
        UNNEST(vi.strings) AS string_number
    FROM valid_inversions AS vi
    ORDER BY chord_name, inversion_number, fret
    """

    # Execute and get Polars DF
    joined_df = duckdb.query(query).pl()

    # Save as CSV
    joined_df.write_csv(PROJECT_DIR / "fretboard_chords_inversions.csv")