"""Dependency-free guard for the API's unavailable live-data route."""
import ast
from pathlib import Path
import unittest


class LiveApiDisabledContractTests(unittest.TestCase):
    def test_premove_route_fails_closed_without_provider_calls(self):
        source = Path(__file__).resolve().parents[1] / "api" / "main.py"
        tree = ast.parse(source.read_text(encoding="utf-8-sig"))
        route = next(node for node in tree.body
                     if isinstance(node, ast.FunctionDef) and node.name == "premove_scan")
        calls = [node.func.id if isinstance(node.func, ast.Name)
                 else node.func.attr if isinstance(node.func, ast.Attribute) else ""
                 for node in ast.walk(route) if isinstance(node, ast.Call)]
        literals = {node.value for node in ast.walk(route)
                    if isinstance(node, ast.Constant) and isinstance(node.value, str)}
        self.assertNotIn("build_live_premove_snapshot", calls)
        self.assertNotIn("urlopen", calls)
        self.assertIn("DATA_UNAVAILABLE", literals)
        self.assertIn("NO_TRADE", literals)


if __name__ == "__main__":
    unittest.main()
