"""Synthetic, no game files: verify read-only SPU overlay diagnostics."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from inspect_spu_overlays import (PROLOGUE, DATA_MAGIC, map_entries, parse_offsets,
                                  scan_spu_candidates, scan_spu_data_modules)


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



class DataModuleTests(unittest.TestCase):
    @staticmethod
    def make_data_module(code_off=0x30, image_size=0x80, code_end=0x70):
        header = b"".join(v.to_bytes(4, "big") for v in
                          (0x42000001, 0x43000002, 0x42000003, 0x43000004))
        tail = DATA_MAGIC + code_off.to_bytes(4, "big")
        tail += image_size.to_bytes(4, "big") + bytes(4)
        tail += code_end.to_bytes(4, "big")
        return header + tail + bytes(max(0, image_size - len(header) - len(tail)))

    def test_finds_plausible_second_format(self):
        data = bytes(64) + self.make_data_module() + bytes(16)
        rows = scan_spu_data_modules(data)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["file_offset"], "0x40")
        self.assertEqual(rows[0]["entry_offset"], "0x30")
        self.assertFalse(rows[0]["truncated_file_image"])

    def test_rejects_invalid_declared_layout(self):
        for code_off, size, end in ((0x30, 0x80, 0x20),
                                    (0x30, 0x80, 0x90),
                                    (0x33, 0x80, 0x70),
                                    (0x30, 0x50000, 0x70)):
            with self.subTest(code_off=code_off, size=size, end=end):
                self.assertEqual(scan_spu_data_modules(
                    self.make_data_module(code_off, size, end)), [])

    def test_reports_bss_tail_without_extracting_bytes(self):
        raw = self.make_data_module()[:0x70]
        rows = scan_spu_data_modules(raw)
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["truncated_file_image"])
        self.assertEqual(rows[0]["file_bytes_available"], 0x70)

    def test_rejects_header_not_spu_ila_words(self):
        raw = bytearray(self.make_data_module())
        raw[0] = 0x50
        self.assertEqual(scan_spu_data_modules(bytes(raw)), [])


if __name__ == "__main__":
    unittest.main()
