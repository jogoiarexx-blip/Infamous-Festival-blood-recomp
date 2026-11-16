"""Testes com ELF sintetico: nunca usar assets de jogos em CI."""
import sys
from pathlib import Path
import struct
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from analyze_ppu import analyze, ELFAnalysisError  # noqa: E402


def elf_fixture():
    b = bytearray(0x1400)
    b[:16] = b"\x7fELF" + bytes((2, 2, 1, 0x66)) + bytes(8)
    struct.pack_into(">HHIQQQIHHHHHH", b, 16, 2, 21, 1, 0x20100, 64, 0x1200, 0, 64, 56, 3, 64, 2, 0)
    struct.pack_into(">IIQQQQQQ", b, 64, 1, 5, 0x100, 0x10000, 0x10000, 0x500, 0x500, 0x100)
    struct.pack_into(">IIQQQQQQ", b, 120, 1, 6, 0x800, 0x20000, 0x20000, 0x600, 0x700, 0x100)
    struct.pack_into(">IIQQQQQQ", b, 176, 0x60000002, 0, 0xA00, 0x20200, 0x20200, 0x40, 0x40, 4)
    struct.pack_into(">IIQQQQIIQQ", b, 0x1240, 0, 1, 3, 0x20100, 0x900, 24, 0, 0, 8, 0)
    struct.pack_into(">IIIIII", b, 0x900, 0x10020, 0x20400, 0x10020, 0x20400, 0, 0)
    struct.pack_into(">I", b, 0xA04, 0x1B434CEC)
    struct.pack_into(">II", b, 0xA18, 0x20280, 0x202AC)
    struct.pack_into(">B", b, 0xA80, 0x2C)
    struct.pack_into(">H", b, 0xA86, 2)
    struct.pack_into(">III", b, 0xA90, 0x20300, 0x20340, 0x20360)
    b[0xB00:0xB09] = b"sys_test\0"
    return bytes(b)


class ELFScanTests(unittest.TestCase):
    def test_synthetic_entry_imports(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "example.elf"
            p.write_bytes(elf_fixture())
            r = analyze(p)
            self.assertEqual(r["entry_function"], "0x10020")
            self.assertEqual(r["entry_toc"], "0x20400")
            self.assertEqual(r["valid_opd_descriptors"], 2)
            self.assertEqual(r["unique_opd_function_addresses"], 1)
            self.assertEqual(r["import_function_count"], 2)
            self.assertEqual(r["import_libraries"][0]["name"], "sys_test")

    def test_reject_self(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "EBOOT.BIN"
            p.write_bytes(b"SCE\x00" + bytes(100))
            with self.assertRaises(ELFAnalysisError):
                analyze(p)

    def test_reject_truncated(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "truncated.elf"
            p.write_bytes(elf_fixture()[:150])
            with self.assertRaises(ELFAnalysisError):
                analyze(p)

    def test_reject_other_cpu(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "other.elf"
            b = bytearray(elf_fixture())
            struct.pack_into(">H", b, 18, 62)
            p.write_bytes(b)
            with self.assertRaises(ELFAnalysisError):
                analyze(p)


if __name__ == "__main__":
    unittest.main()
