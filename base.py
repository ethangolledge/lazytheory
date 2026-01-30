import polars as pl

NOTE_TO_CHROMATIC = {
    "C": 1,
    "C#": 2, "Db": 2,
    "D": 3,
    "D#": 4, "Eb": 4,
    "E": 5,
    "F": 6,
    "F#": 7, "Gb": 7,
    "G": 8,
    "G#": 9, "Ab": 9,
    "A": 10,
    "A#": 11, "Bb": 11,
    "B": 12,
}

MODE_ST_DEGREES: dict[str, int] = {
    'IONIAN': 0,
    'DORIAN': 1,
    'PHRYGIAN': 2,
    'LYDIAN': 3,
    'MIXOLYDIAN': 4,
    'AEOLIAN': 5,
    'LOCRIAN': 6,
}

CHROMATIC_INTERVALS: dict[int, tuple[str, ...]] = {
    0:  ('1',),
    1:  ('b2',),
    2:  ('2',),
    3:  ('b3',),
    4:  ('3',),
    5:  ('4',),
    6:  ('b5', '#4'),
    7:  ('5',),
    8:  ('b6',),
    9:  ('6',),
    10: ('b7',),
    11: ('7',),
}

IONIAN_ST: list[int] = [0, 2, 4, 5, 7, 9, 11]


class LazyTheory:
    def __init__(self, total_frets: int):
        self.total_frets = total_frets

    def mode_from_major(self, degree: int) -> list[int]:
        rotated = IONIAN_ST[degree:] + IONIAN_ST[:degree]
        return [(x - rotated[0]) % 12 for x in rotated]

    def mode_from_chromatic(self, chromatic: list[int]) -> tuple[str, ...]:
        return tuple(
            CHROMATIC_INTERVALS[x % 12][0]
            for x in chromatic
        )

    def parse_tuning(
        self,
        tuning: str,
        key: str,
        mode: str
    ):
        g_strings = [g.strip().upper() for g in tuning]
        if not all(g in NOTE_TO_CHROMATIC for g in g_strings):
            raise ValueError("Invalid note in tuning")

        key = key.upper().strip()
        print(f"key: {key}")
        chromatic_key = NOTE_TO_CHROMATIC[key]
        print(f"chromatic key: {chromatic_key}")

        mode = mode.upper().strip()
        print(f"mode: {mode}")
        mode_degree = MODE_ST_DEGREES[mode]
        print(f"mode degree: {mode_degree}")

        mode_intervals = self.mode_from_major(mode_degree)
        print(f"mode intervals: {mode_intervals}")

        g_df = pl.DataFrame(
            schema={
                "key": pl.Utf8,
                "note": pl.Utf8,
                "chromatic_note": pl.Int8,
                "interval": pl.Int8,          # semitone offset
                "interval_label": pl.Utf8,    # theory label
                "fret": pl.Int8,
            }
        )

        for note in g_strings:
            fret = 0
            chromatic_note = NOTE_TO_CHROMATIC[note]
            print(f"\nnote: {note}")
            print(f"chromatic note: {chromatic_note}")

            interval = (chromatic_note - chromatic_key) % 12
            print(f"raw interval: {interval}")

            if interval not in mode_intervals:
                print("interval not in mode, skipping")
                continue

            interval_label = CHROMATIC_INTERVALS[interval][0]
            print(f"interval label: {interval_label}")

            g_df = g_df.vstack(
                pl.DataFrame({
                    "key": [key],
                    "note": [note],
                    "chromatic_note": pl.Series([chromatic_note], dtype=pl.Int8),
                    "interval": pl.Series([interval], dtype=pl.Int8),
                    "interval_label": [interval_label],
                    "fret": pl.Series([fret], dtype=pl.Int8),
                })
            )

        print(g_df)
        return g_df


if __name__ == "__main__":
    theory = LazyTheory(total_frets=12)
    theory.parse_tuning("EADGBE", "E", "IONIAN")
