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

    def test_self_with_realistic_embedded_ppu_header(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "EBOOT.BIN"
            payload = bytearray(512)
            struct.pack_into(">4sIHHIQQ", payload, 0, b"SCE\x00", 2, 1, 1, 0x80, 512, 10927304)
            struct.pack_into(
                ">10Q", payload, 32,
                3, 0x70, 0x90, 0xd0, 0, 0x200, 0x250, 0x300, 0, 0,
            )
            struct.pack_into(">I", payload, 0x70 + 12, 8)
            payload[0x90:0xD0] = sample_elf64_be()
            content_id = b"UP9000-NPUA80657_00-BLOODSHP10041043"
            payload[0x190:0x190 + len(content_id)] = content_id
            path.write_bytes(payload)
            info = inspect_binary(path)
            self.assertEqual(info["format"], "SELF/SCE")
            self.assertEqual(info["title_id"], "NPUA80657")
            self.assertEqual(info["content_id"], content_id.decode("ascii"))
            self.assertTrue(info["is_npdrm"])
            self.assertEqual(info["self_header_size"], 512)
            self.assertEqual(info["elf_size_declared"], 10927304)
            self.assertTrue(info["embedded_elf"]["ppu_candidate"])
            self.assertEqual(info["embedded_elf"]["entry_point"], "0x10000")
            self.assertTrue(info["embedded_elf"]["header_only"])

    def test_sce_header_does_not_claim_decrypted_executable(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "EBOOT.BIN"
            path.write_bytes(b"SCE\x00" + bytes(60))
            info = inspect_binary(path)
            self.assertEqual(info["format"], "SELF/SCE")
            self.assertNotIn("embedded_elf", info)

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
