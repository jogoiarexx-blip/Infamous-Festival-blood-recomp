"""CLI regressions: report generation must preserve all binary inputs."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1] / "tools"


class ReportOutputTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.left, self.right = self.root / "left", self.root / "right"
        self.left.mkdir()
        self.right.mkdir()
        self.source = self.left / "source.bin"
        self.target = self.right / "target.bin"
        self.data = bytes(range(64))
        self.source.write_bytes(self.data)
        self.target.write_bytes(self.data)

    def invoke(self, script, args, destination):
        return subprocess.run(
            [sys.executable, str(TOOLS / script), *map(str, args),
             "--json", str(destination)],
            capture_output=True, text=True, timeout=10)

    def compare(self, destination):
        return self.invoke("compare_spu_modules.py",
                           ["--left", self.left, "--right", self.right], destination)

    def inspect(self, command, destination):
        args = [command, self.source]
        if command == "entries":
            args += [self.target, "--offsets", "0"]
        return self.invoke("inspect_spu_overlays.py", args, destination)

    def assert_preserved_rejection(self, result):
        self.assertEqual(self.source.read_bytes(), self.data)
        self.assertEqual(self.target.read_bytes(), self.data)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("entrada", result.stderr)

    def test_compare_rejects_source_as_report(self):
        self.assert_preserved_rejection(self.compare(self.source))

    def test_compare_rejects_target_as_report(self):
        self.assert_preserved_rejection(self.compare(self.target))

    def test_inspect_rejects_inputs_in_all_modes(self):
        for mode in ("scan", "data", "entries"):
            with self.subTest(mode=mode):
                self.source.write_bytes(self.data)
                self.assert_preserved_rejection(self.inspect(mode, self.source))

    def test_entries_rejects_target_as_report(self):
        self.assert_preserved_rejection(self.inspect("entries", self.target))

    def test_compare_rejects_hard_link_alias(self):
        alias = self.root / "alias.json"
        try:
            os.link(self.source, alias)
        except OSError as exc:
            self.skipTest(str(exc))
        self.assert_preserved_rejection(self.compare(alias))

    def test_inspect_rejects_symbolic_link_alias(self):
        alias = self.root / "alias.json"
        try:
            alias.symlink_to(self.source)
        except OSError as exc:
            self.skipTest(str(exc))
        self.assert_preserved_rejection(self.inspect("scan", alias))

    def test_compare_writes_separate_report(self):
        output = self.root / "report.json"
        result = self.compare(output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(output.read_text())["results"])
        self.assertEqual(self.source.read_bytes(), self.data)
        self.assertEqual(self.target.read_bytes(), self.data)

    def test_inspect_writes_separate_report(self):
        output = self.root / "report.json"
        result = self.inspect("entries", output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(output.read_text())["entries"][0]["status"],
                         "unique_exact_window")
        self.assertEqual(self.source.read_bytes(), self.data)
        self.assertEqual(self.target.read_bytes(), self.data)


if __name__ == "__main__":
    unittest.main()
