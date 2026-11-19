"""Synthetic, no game files: verify read-only SPU overlay diagnostics."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from inspect_spu_overlays import PROLOGUE, map_entries, parse_offsets, scan_spu_candidates


class ScanOverlayTests(unittest.TestCase):
    def test_detects_valid_aligned_prefix(self):
        head = b"".join(n.to_bytes(4, "big") for n in
                        (0x42000001, 0x43000002, 0x42000003, 0x43000004))
        data = bytes(32) + head + PROLOGUE + bytes(64)
        self.assertEqual(scan_spu_candidates(data), [32])

    def test_rejects_invalid_prefix_and_alignment(self):
        valid_head = (0x42000001).to_bytes(4, "big") * 4
        wrong_head = (0x44000001).to_bytes(4, "big") * 4
        self.assertEqual(scan_spu_candidates(wrong_head + PROLOGUE + bytes(12)), [])
        self.assertEqual(scan_spu_candidates(bytes(1) + valid_head + PROLOGUE + bytes(64)), [])

    def test_multiple_candidates(self):
        head = (0x42000001).to_bytes(4, "big") * 4
        block = head + PROLOGUE + bytes(36)  # 64 bytes
        data = block + block
        self.assertEqual(scan_spu_candidates(data), [0, 64])


class MapEntriesTests(unittest.TestCase):
    def test_unique_exact_window_at_shifted_offset(self):
        source = bytes(range(64))
        target = bytes([255] * 32) + source + bytes([254] * 32)
        rows = map_entries(source, target, [0, 16])
        self.assertEqual([r["target_offset"] for r in rows], ["0x20", "0x30"])
        self.assertTrue(all(r["status"] == "unique_exact_window" for r in rows))

    def test_ambiguous_duplicate_pattern_is_not_mapped(self):
        source = bytes(range(32))
        target = source + bytes(8) + source
        row = map_entries(source, target, [0])[0]
        self.assertEqual(row["status"], "ambiguous")
        self.assertIsNone(row["target_offset"])

    def test_missing_pattern_is_not_guessed(self):
        source = bytes(range(32))
        target = bytes([255] * 64)
        row = map_entries(source, target, [0])[0]
        self.assertEqual(row["status"], "not_found")

    def test_rejects_bad_alignment_and_duplicates(self):
        with self.assertRaisesRegex(ValueError, "alinhados"):
            map_entries(b"123", bytes(64), [0])
        with self.assertRaisesRegex(ValueError, "não alinhado"):
            map_entries(bytes(32), bytes(32), [1])
        with self.assertRaisesRegex(ValueError, "repetidos"):
            parse_offsets("0x4,0x4")


if __name__ == "__main__":
    unittest.main()
