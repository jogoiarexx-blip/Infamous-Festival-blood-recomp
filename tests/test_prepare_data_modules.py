import hashlib
from pathlib import Path
import struct
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from prepare_data_modules import ModuleSpec, mapped_address, validate_module


class DataModuleValidationTests(unittest.TestCase):
    def make_image(self):
        elf = bytearray(0x200)
        elf[:6] = b"\x7fELF\x02\x02"
        struct.pack_into(">Q", elf, 32, 64)
        struct.pack_into(">HH", elf, 54, 56, 1)
        struct.pack_into(">IIQQQQQQ", elf, 64, 1, 5, 0, 0x10000, 0, len(elf), len(elf), 16)
        struct.pack_into(">4I", elf, 0x100, *([0x42000000] * 4))
        struct.pack_into(">III", elf, 0x110, 0xDA7ABA5E, 0x30, 0x100)
        struct.pack_into(">I", elf, 0x120, 0x80)
        return elf

    def spec(self, elf, **changes):
        values = dict(offset=0x100, size=0x100,
                      sha256=hashlib.sha256(elf[0x100:0x200]).hexdigest(),
                      ea=0x10100, image=300)
        values.update(changes)
        return ModuleSpec(**values)

    def test_maps_file_offset_through_load_segment(self):
        elf = self.make_image()
        self.assertEqual(mapped_address(elf, 0x100, 0x100), 0x10100)

    def test_accepts_exact_module(self):
        elf = self.make_image()
        result = validate_module(elf, self.spec(elf))
        self.assertEqual(result.get("entry"), 0x30)
        self.assertEqual(result.get("code_end"), 0x80)
        self.assertEqual(result.get("raw"), bytes(elf[0x100:]))

    def test_rejects_changed_fingerprint(self):
        elf = self.make_image()
        with self.assertRaises(ValueError):
            validate_module(elf, self.spec(elf, sha256="0" * 64))

    def test_rejects_truncated_file(self):
        elf = self.make_image()
        with self.assertRaises(ValueError):
            validate_module(elf[:-1], self.spec(elf))

    def test_rejects_wrong_guest_address(self):
        elf = self.make_image()
        with self.assertRaises(ValueError):
            validate_module(elf, self.spec(elf, ea=0x10200))

    def test_rejects_bss_only_extent(self):
        elf = self.make_image()
        struct.pack_into(">Q", elf, 64 + 32, 0x180)
        with self.assertRaises(ValueError):
            mapped_address(elf, 0x100, 0x100)

    def test_rejects_invalid_header_even_with_matching_hash(self):
        for field, value in [(0x110, 0), (0x114, 0x20), (0x118, 0x104),
                             (0x120, 0x20), (0x120, 0x101)]:
            with self.subTest(field=field, value=value):
                elf = self.make_image()
                struct.pack_into(">I", elf, field, value)
                with self.assertRaises(ValueError):
                    validate_module(elf, self.spec(elf))

    def test_rejects_malformed_elf_and_segment_table(self):
        for offset, data in [(0, b"NOPE"), (4, b"\x01"), (5, b"\x01"),
                             (32, struct.pack(">Q", 0x1000))]:
            with self.subTest(offset=offset):
                elf = self.make_image()
                elf[offset:offset + len(data)] = data
                with self.assertRaises(ValueError):
                    mapped_address(elf, 0x100, 0x100)

    def test_rejects_segment_larger_than_memory(self):
        elf = self.make_image()
        struct.pack_into(">Q", elf, 64 + 40, 0x100)
        with self.assertRaises(ValueError):
            mapped_address(elf, 0x100, 0x100)

    def test_replay_binary_output_stays_private(self):
        from test_data_module_replay import private_output_dir
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(private_output_dir(root / "out/replay-test"),
                         (root / "out/replay-test").resolve())
        with self.assertRaises(ValueError):
            private_output_dir(root / "public-replay-test")
