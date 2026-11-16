#!/usr/bin/env python3
"""Analise local de ELF64 PowerPC para pesquisa de recompilacao PS3.

Somente metadados. Nao extrai codigo, nao descriptografa SELF e nao modifica o ELF.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct


class ELFAnalysisError(ValueError):
    """Arquivo invalido ou arquitetura nao suportada."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def analyze(path: Path) -> dict:
    data = path.read_bytes()
    if len(data) < 64 or data[:4] != b"\x7fELF":
        raise ELFAnalysisError("Esperado ELF, nao um SELF/SCE.")
    if data[4:7] != b"\x02\x02\x01":
        raise ELFAnalysisError("Esperado ELF64 big-endian versao 1.")
    h = struct.unpack_from(">HHIQQQIHHHHHH", data, 16)
    e_type, machine, ver, entry, phoff, shoff, flags, ehsize, phsize, phnum, shsize, shnum, shstrndx = h
    if machine != 21 or e_type not in (2, 3):
        raise ELFAnalysisError("Esperado executavel ou PRX PowerPC64.")
    if ehsize < 64 or phsize < 56 or phoff + phsize * phnum > len(data):
        raise ELFAnalysisError("Segmentos invalidos.")
    if shnum and (shsize < 64 or shoff + shsize * shnum > len(data)):
        raise ELFAnalysisError("Tabela de secoes invalida.")

    ph = []
    for i in range(phnum):
        kind, pflags, offset, vaddr, paddr, filesz, memsz, align = (
            struct.unpack_from(">IIQQQQQQ", data, phoff + i * phsize)
        )
        if offset + filesz > len(data):
            raise ELFAnalysisError(f"Segmento {i} excede arquivo.")
        if kind == 1 and filesz > memsz:
            raise ELFAnalysisError(f"Segmento LOAD {i} tem filesz > memsz.")
        ph.append((kind, pflags, offset, vaddr, filesz, memsz))

    def read_va(vaddr: int, n: int) -> bytes | None:
        if n < 0:
            return None
        for kind, pflags, offset, va, sz, memsz in ph:
            if kind == 1 and sz and va <= vaddr and vaddr + n <= va + sz:
                pos = offset + vaddr - va
                return data[pos:pos + n]
        return None

    code_ranges = [(va, va + sz) for kind, fl, off, va, sz, ms in ph
                   if kind == 1 and (fl & 1) and sz]

    def is_code(addr: int) -> bool:
        return addr % 4 == 0 and any(a <= addr < z for a, z in code_ranges)

    raw_entry = read_va(entry, 8)
    actual_code, toc = struct.unpack(">II", raw_entry) if raw_entry else (0, 0)
    entry_valid = is_code(actual_code)

    sections = []
    for i in range(shnum):
        s = struct.unpack_from(">IIQQQQIIQQ", data, shoff + shsize * i)
        sections.append((i, s[3], s[5]))
    candidates = [(i, va, sz) for i, va, sz in sections if sz and va <= entry < va + sz]
    opd = min(candidates, key=lambda t: t[2]) if candidates else None
    descriptors = 0
    unique_funcs = set()
    tocs = Counter()
    if opd and opd[2] <= 20_000_000:
        raw_opd = read_va(opd[1], opd[2])
        if raw_opd:
            for i in range(0, len(raw_opd) - 7, 8):
                fn, r2 = struct.unpack_from(">II", raw_opd, i)
                if is_code(fn):
                    descriptors += 1
                    unique_funcs.add(fn)
                    tocs[r2] += 1

    def u32(va: int) -> int | None:
        raw = read_va(va, 4)
        return struct.unpack(">I", raw)[0] if raw else None

    def string_at(va: int) -> str:
        b = bytearray()
        for i in range(96):
            char = read_va(va + i, 1)
            if not char or char == b"\x00":
                break
            if char[0] < 32 or char[0] > 126:
                return "<invalido>"
            b.extend(char)
        return b.decode("ascii") if b else "<sem-nome>"

    libs = []
    for kind, fl, off, va, sz, memsz in ph:
        if kind != 0x60000002:
            continue
        proc = read_va(va, 32)
        if not proc or struct.unpack_from(">I", proc, 4)[0] != 0x1B434CEC:
            continue
        first, end = struct.unpack_from(">II", proc, 24)
        if first > end or end - first > 1000000:
            continue
        addr = first
        while addr < end and len(libs) < 4096:
            lib = read_va(addr, 0x1c)
            if lib is None or lib[0] < 0x1c or addr + lib[0] > end:
                break
            count = struct.unpack_from(">H", lib, 6)[0]
            if count > 4096:
                break
            name_ptr, nids, stubs = struct.unpack_from(">III", lib, 16)
            libs.append({
                "name": string_at(name_ptr), "functions": count,
                "nid_table_present": read_va(nids, count * 4) is not None,
                "stub_table_present": read_va(stubs, count * 4) is not None,
            })
            addr += lib[0]
        break

    return {
        "format": "ELF64-PS3-PPU", "filename": path.name,
        "size_bytes": len(data), "sha256": sha256(path), "machine": machine,
        "entry_opd": hex(entry),
        "entry_function": hex(actual_code) if entry_valid else None,
        "entry_toc": hex(toc) if entry_valid else None,
        "program_segments": phnum,
        "loadable_segments": sum(kind == 1 and sz for kind, fl, off, va, sz, ms in ph),
        "executable_segments": len(code_ranges),
        "section_count": shnum,
        "opd_section_index": opd[0] if opd else None,
        "opd_section_start": hex(opd[1]) if opd else None,
        "opd_section_size_bytes": opd[2] if opd else None,
        "valid_opd_descriptors": descriptors,
        "unique_opd_function_addresses": len(unique_funcs),
        "most_common_toc": hex(tocs.most_common(1)[0][0]) if tocs else None,
        "import_library_count": len(libs),
        "import_function_count": sum(x["functions"] for x in libs),
        "import_libraries": libs,
        "notes": [
            "A lista OPD nao cobre necessariamente funcoes sem descriptor.",
            "Analise de metadados; nenhuma instrucao ou asset de jogo exportado.",
            "Nao e uma recompilacao nem prova de jogabilidade."
        ]
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("elf", type=Path)
    parser.add_argument("--output", "-o", type=Path)
    args = parser.parse_args()
    try:
        if args.output and args.elf.resolve() == args.output.resolve():
            raise ELFAnalysisError("Recusado sobrescrever o ELF.")
        report = analyze(args.elf)
        output = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output, encoding="utf-8")
            print(f"Relatorio gerado: {args.output}")
        else:
            print(output, end="")
    except (OSError, ELFAnalysisError, struct.error) as exc:
        parser.exit(2, f"Erro: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
