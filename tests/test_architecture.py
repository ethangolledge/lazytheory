"""The dependency rules in docs/architecture.md, checked against the source."""

import ast
import sys
import unittest
from pathlib import Path

PACKAGE = Path(__file__).parents[1] / "src" / "lazy_theory"

# What each package may import from the library. Pitch and rhythm are separate domains that share
# only `core`'s circle maths; instruments play pitch; suggestions search instruments.
ALLOWED = {
    "core": {"core"},
    "pitch": {"core", "data", "pitch"},
    "rhythm": {"core", "data", "rhythm"},
    "instruments": {"core", "data", "pitch", "instruments"},
    "suggest": {"core", "pitch", "instruments", "suggest"},
}
# the modules that hold names; the maths beside them never imports them
WORDS = {"catalog", "names"}
STANDARD_LIBRARY_ONLY = {"core", "pitch", "rhythm"}


def imports(path: Path) -> set[str]:
    modules = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def library(path: Path) -> list[list[str]]:
    """The library modules `path` imports, each as its parts after "lazy_theory"."""
    return [m.split(".")[1:] for m in imports(path) if m.startswith("lazy_theory.")]


class LayerTest(unittest.TestCase):
    def test_every_package_is_listed(self):
        found = {path.name for path in PACKAGE.iterdir() if (path / "__init__.py").exists()}
        self.assertEqual(found, set(ALLOWED))

    def test_packages_import_only_what_they_may(self):
        for package, allowed in ALLOWED.items():
            for path in (PACKAGE / package).glob("*.py"):
                for parts in library(path):
                    with self.subTest(file=f"{package}/{path.name}", imports=".".join(parts)):
                        self.assertIn(parts[0], allowed)

    def test_maths_never_imports_words(self):
        for package in ALLOWED:
            for path in (PACKAGE / package).glob("*.py"):
                if path.stem in WORDS:
                    continue
                for parts in library(path):
                    with self.subTest(file=f"{package}/{path.name}", imports=".".join(parts)):
                        self.assertNotIn(parts[-1], WORDS)  # any package's words

    def test_the_data_reader_imports_nothing_of_the_library(self):
        self.assertEqual(library(PACKAGE / "data.py"), [])

    def test_no_import_cycles(self):
        graph = {
            ".".join(
                ("lazy_theory", *path.relative_to(PACKAGE).with_suffix("").parts)
            ).removesuffix(".__init__"): {
                module for module in imports(path) if module.startswith("lazy_theory.")
            }
            for path in PACKAGE.rglob("*.py")
        }
        done: set[str] = set()

        def visit(module: str, path: tuple[str, ...]) -> None:
            self.assertNotIn(module, path, f"import cycle: {' -> '.join((*path, module))}")
            if module not in done:
                for imported in graph.get(module, ()):
                    visit(imported, (*path, module))
                done.add(module)

        for module in graph:
            visit(module, ())

    def test_top_level_names_are_the_ones_in_their_modules(self):
        import importlib

        import lazy_theory

        for name in lazy_theory.__all__:
            module = importlib.import_module(f"lazy_theory.{lazy_theory._HOMES[name]}")
            self.assertIs(getattr(lazy_theory, name), getattr(module, name), name)

    def test_type_checkers_see_the_same_top_level_names(self):
        tree = ast.parse((PACKAGE / "__init__.py").read_text())
        guarded = next(node for node in tree.body if isinstance(node, ast.If))
        typed = {alias.name for node in guarded.body for alias in node.names}  # type: ignore[attr-defined]
        import lazy_theory

        self.assertEqual(typed, set(lazy_theory.__all__))

    def test_the_core_loads_without_numpy(self):
        import subprocess

        code = (
            "import sys, lazy_theory, lazy_theory.core.pcset, lazy_theory.pitch.names,"
            " lazy_theory.rhythm.phrase; print('numpy' in sys.modules)"
        )
        found = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, check=True
        )
        self.assertEqual(found.stdout.strip(), "False")

    def test_pitch_rhythm_and_core_use_only_the_standard_library(self):
        for package in STANDARD_LIBRARY_ONLY:
            for path in (PACKAGE / package).glob("*.py"):
                for module in imports(path):
                    root = module.split(".")[0]
                    with self.subTest(file=f"{package}/{path.name}", imports=module):
                        self.assertIn(root, sys.stdlib_module_names | {"lazy_theory"})


if __name__ == "__main__":
    unittest.main()
