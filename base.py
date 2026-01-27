import polars as pl

class LazyTheory:
    def __init__(
        self
    ):
        self.TOTAL_FRETS: int = 12 # number of available frets on my acoustic
        
        self.IONIAN_ST: list[int] = [0, 2, 4, 5, 7, 9, 11]
        self.MODES_ST: dict[str, tuple[str, ...]] = {
            'IONIAN':     ('1', '2', '3', '4', '5', '6', '7'),
            'DORIAN':     ('1', '2', 'b3', '4', '5', '6', 'b7'),
            'PHRYGIAN':   ('1', 'b2', 'b3', '4', '5', 'b6', 'b7'),
            'LYDIAN':     ('1', '2', '3', '#4', '5', '6', '7'),
            'MIXOLYDIAN': ('1', '2', '3', '4', '5', '6', 'b7'),
            'AEOLIAN':    ('1', '2', 'b3', '4', '5', 'b6', 'b7'),
            'LOCRIAN':    ('1', 'b2', 'b3', '4', 'b5', 'b6', 'b7')
        }

        self.MODE_ST_DEGREES: dict[str, int] = {
            'IONIAN': 0,
            'DORIAN': 1,
            'PHRYGIAN': 2,
            'LYDIAN': 3,
            'MIXOLYDIAN': 4,
            'AEOLIAN': 5,
            'LOCRIAN': 6,
        }

        self.CHROMATIC_INTERVALS: dict[int, tuple[str, ...]] = {
            0:  ('1',),
            1:  ('b2',),
            2:  ('2',),
            3:  ('b3',),
            4:  ('3',),
            5:  ('4',),
            6:  ('b5', '#4'), # this is dependant on the context
            7:  ('5',),
            8:  ('b6',),
            9:  ('6',),
            10: ('b7',),
            11: ('7',),
        }
       
        self.STANDARD_TUNING: tuple[str, ...] = 

    def mode_from_major(
        self, 
        degree: int
    ) -> list[int]:
        """
        Derive any standard mode using the ionian scale by specifying a degree
            args: 2: i.e 1st degree is Dorian
        """
        rotated = self.IONIAN_ST[degree:] + self.IONIAN_ST[:degree]
        return [(x - rotated[0]) % 12 for x in rotated]

    def mode_from_chromatic(
        self,
        chromatic: list[int]
    ) -> tuple[str, ...]:
        """
        Convert a list of chromatic semitone offsets to interval labels.
        """
        return tuple(
            self.CHROMATIC_INTERVALS[x % 12][0]
            for x in chromatic
        )

if __name__ == "__main__":
    theory = LazyTheory()
    dorian_chromatic = theory.mode_from_major(1)
    print(f"DORIAN chromatic semitone offsets:: \n{dorian_chromatic}")
    dorian_intervals = theory.mode_from_chromatic(dorian_chromatic)
    print(f"DORIAN intervals: \n{dorian_intervals}")
