"""The dependency rules in docs/architecture.md, checked against the source."""

import ast
import sys
import unittest
from pathlib import Path

PACKAGE = Path(__file__).parents[1] / "src" / "lazy_theory"
LAYERS = ["core", "catalog", "instruments", "suggest"]  # lowest first; import only itself and below


def imports(path: Path) -> set[str]:
    modules = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


class LayerTest(unittest.TestCase):
    def test_every_layer_is_listed(self):
        found = {path.name for path in PACKAGE.iterdir() if (path / "__init__.py").exists()}
        self.assertEqual(found, set(LAYERS))

    def test_layers_only_import_downwards(self):
        for layer in LAYERS:
            allowed = LAYERS[: LAYERS.index(layer) + 1]
            for path in (PACKAGE / layer).glob("*.py"):
                for module in imports(path):
                    if module.startswith("lazy_theory."):
                        with self.subTest(file=path.name, imports=module):
                            self.assertIn(module.split(".")[1], allowed)

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

    def test_core_uses_only_the_standard_library(self):
        for path in (PACKAGE / "core").glob("*.py"):
            for module in imports(path):
                root = module.split(".")[0]
                with self.subTest(file=path.name, imports=module):
                    self.assertIn(root, sys.stdlib_module_names | {"lazy_theory"})


if __name__ == "__main__":
    unittest.main()
