"""The README's examples run as written, so they can't drift from the code."""

import re
import unittest
from pathlib import Path

README = Path(__file__).resolve().parents[1] / "README.md"


class ReadmeTest(unittest.TestCase):
    def test_the_examples_run(self):
        blocks = re.findall(r"```python\n(.*?)```", README.read_text(), re.S)
        self.assertTrue(blocks)
        exec(compile("\n".join(blocks), str(README), "exec"), {"print": lambda *_: None})


if __name__ == "__main__":
    unittest.main()
