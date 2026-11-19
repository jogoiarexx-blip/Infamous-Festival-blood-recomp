"""Synthetic-only tests; no copyrighted game data needed."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from compare_spu_modules import compare, read_modules, similarity  # noqa: E402


def save_words(path, words):
    path.write_bytes(b"".join(int(w).to_bytes(4, "big") for w in words))


class CompareSpuModulesTests(unittest.TestCase):
    def test_exact_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b = root / "a", root / "b"
            a.mkdir(); b.mkdir()
            save_words(a / "job_a.bin", [0x11, 0x22, 0x33, 0x44])
            save_words(b / "job_b.bin", [0x11, 0x22, 0x33, 0x44])
            result = compare(read_modules(a), read_modules(b))
            self.assertTrue(result[0]["candidates"][0]["exact_bytes"])
            self.assertEqual(result[0]["candidates"][0]["score"], 1.0)

    def test_modified_instruction_is_not_exact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b = root / "a", root / "b"
            a.mkdir(); b.mkdir()
            save_words(a / "job_a.bin", list(range(24)))
            save_words(b / "job_b.bin", [*range(10), 0xDEADBEEF, *range(11, 24)])
            result = compare(read_modules(a), read_modules(b))
            candidate = result[0]["candidates"][0]
            self.assertFalse(candidate["exact_bytes"])
            self.assertGreater(candidate["score"], 0.9)
            self.assertLess(candidate["score"], 1.0)

    def test_shifted_words_generate_only_a_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b = root / "a", root / "b"
            a.mkdir(); b.mkdir()
            save_words(a / "a.bin", list(range(20)))
            save_words(b / "b.bin", [99, 98, *range(20)])
            candidate = compare(read_modules(a), read_modules(b))[0]["candidates"][0]
            self.assertFalse(candidate["exact_bytes"])
            self.assertGreater(candidate["score"], 0.9)

    def test_invalid_module_alignment_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / "bad.bin").write_bytes(b"abc")
            with self.assertRaisesRegex(ValueError, "alinhado"):
                read_modules(path)

    def test_no_matches_and_size_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b = root / "a", root / "b"
            a.mkdir(); b.mkdir()
            save_words(a / "a.bin", list(range(30)))
            save_words(b / "b.bin", [900, 901])
            self.assertEqual(similarity(read_modules(a)[0], read_modules(b)[0]), 0.0)
            self.assertEqual(compare(read_modules(a), read_modules(b))[0]["candidates"], [])


if __name__ == "__main__":
    unittest.main()
