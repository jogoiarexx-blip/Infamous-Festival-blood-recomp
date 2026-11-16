"""Testes sintéticos: dispensam arquivos de qualquer jogo."""
import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from inspect_ps3_binary import inspect_binary, inventory_directory, sha256_file  # noqa: E402


def sample_elf64_be() -> bytes:
    ident = b"\x7fELF" + bytes((2, 2, 1, 0)) + bytes(8)
    body = struct.pack(
        ">HHIQQQIHHHHHH",
        2, 21, 1, 0x10000, 0, 0, 0, 64, 0, 0, 0, 0, 0,
    )
    assert len(ident + body) == 64
    return ident + body


class BinaryInspectorTests(unittest.TestCase):
    def test_ppu_elf64_big_endian(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "EBOOT.ELF"
            path.write_bytes(sample_elf64_be())
            info = inspect_binary(path)
            self.assertEqual(info["format"], "ELF")
            self.assertEqual(info["class_bits"], 64)
            self.assertEqual(info["byte_order"], "big")
            self.assertEqual(info["machine"], 21)
            self.assertEqual(info["entry_point"], "0x10000")
            self.assertTrue(info["ppu_candidate"])
            self.assertEqual(info["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_sce_self_not_claimed_as_elf(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "EBOOT.BIN"
            path.write_bytes(b"SCE\x00" + bytes(60))
            info = inspect_binary(path)
            self.assertEqual(info["format"], "SELF/SCE")
            self.assertNotIn("ppu_candidate", info)

    def test_invalid_header_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.elf"
            path.write_bytes(b"\x7fELF\x02\x02")
            with self.assertRaises(ValueError):
                inspect_binary(path)

    def test_inventory_and_hashes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "sub").mkdir()
            (root / "sub" / "test.dat").write_bytes(b"abc")
            output = root / "inventory.json"
            output.write_text("output", encoding="utf-8")
            result = inventory_directory(root, output)
            self.assertEqual(result["file_count"], 1)
            self.assertEqual(result["files"][0]["path"], "sub/test.dat")
            self.assertEqual(result["total_bytes"], 3)
            self.assertEqual(result["files"][0]["sha256"], sha256_file(root / "sub" / "test.dat"))


if __name__ == "__main__":
    unittest.main()
