#!/usr/bin/env python3
"""Read-only diagnostics for locally owned SPU binary overlays.

scan: identify candidates for position-independent SPU job blobs in a decrypted
EBOOT.elf. Follows the documented inFAMOUS 2 four-word prefix + prologue
signature; these are only candidates and MUST be verified for NPUA80657.

entries: locate unique byte-exact code windows from an SPU job module in
another local module. Returns offsets, not translated function addresses.

No EBOOT data, instruction bytes, or SPU job bodies are written to reports.
"""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

# Observed in inFAMOUS 2's position-independent SPU module scanner.
PROLOGUE = bytes.fromhex("440128503200008044012850")
ENTRY_WINDOW_BYTES = (32, 24, 16)


def scan_spu_candidates(data: bytes) -> list[int]:
    """Report only plausible aligned starts; pattern does not prove a module."""
    out = []
    for prologue_off in range(16, len(data) - len(PROLOGUE) + 1, 16):
        if data[prologue_off:prologue_off + len(PROLOGUE)] != PROLOGUE:
            continue
        start = prologue_off - 16
        prefix_words = struct.unpack_from(">4I", data, start)
        if all((word >> 24) in (0x42, 0x43) for word in prefix_words):
            out.append(start)
    return out


def map_entries(source: bytes, target: bytes, offsets: list[int],
                window_bytes: tuple[int, ...] = ENTRY_WINDOW_BYTES) -> list[dict]:
    """Require one aligned target match; never derive an offset from similarity."""
    if not source or not target or len(source) % 4 or len(target) % 4:
        raise ValueError("Ambos os módulos devem ser não vazios e alinhados a 4 bytes")
    result = []
    for offset in offsets:
        if offset % 4 or offset < 0 or offset >= len(source):
            raise ValueError(f"Offset inválido ou não alinhado: 0x{offset:X}")
        entry = {"source_offset": f"0x{offset:X}", "status": "not_found",
                 "target_offset": None, "window_bytes": None}
        ambiguous = False
        for span in window_bytes:
            if span < 4 or span % 4 or offset + span > len(source):
                continue
            pattern = source[offset:offset + span]
            hits = [
                p for p in range(0, len(target) - span + 1, 4)
                if target[p:p + span] == pattern
            ]
            if len(hits) == 1:
                entry.update(status="unique_exact_window",
                             target_offset=f"0x{hits[0]:X}", window_bytes=span)
                break
            if len(hits) > 1:
                ambiguous = True
        if entry["status"] != "unique_exact_window" and ambiguous:
            entry["status"] = "ambiguous"
        result.append(entry)
    return result


def parse_offsets(spec: str) -> list[int]:
    items = [x.strip() for x in spec.split(",")]
    if not items or any(not x for x in items):
        raise ValueError("Informe pelo menos um offset, separado por vírgulas")
    offsets = [int(item, 0) for item in items]
    if len(offsets) != len(set(offsets)):
        raise ValueError("Offsets repetidos")
    return offsets


def cli() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan", help="Buscar candidatos a overlays SPU em EBOOT.elf local")
    scan.add_argument("eboot", type=Path, help="Arquivo ELF descriptografado local (não enviar)")
    scan.add_argument("--va-offset", type=lambda s: int(s, 0),
                      help="Deslocamento VA manual, derivado de PT_LOAD; não assumir 0x10000")
    scan.add_argument("--json", type=Path, help="Salvar somente offsets em JSON (usar out/)")
    entries = sub.add_parser("entries", help="Mapear entrypoints por janelas exatas")
    entries.add_argument("source", type=Path, help="Módulo SPU binário local")
    entries.add_argument("target", type=Path, help="Outro módulo SPU binário local")
    entries.add_argument("--offsets", required=True, help="Offsets de BYTE relativos ao arquivo, ex. 0x30,0x15280")
    entries.add_argument("--json", type=Path, help="Salvar somente offsets em JSON (usar out/)")
    args = ap.parse_args()
    try:
        if args.command == "scan":
            offsets = scan_spu_candidates(args.eboot.read_bytes())
            rows = [{"file_offset": f"0x{x:X}"} for x in offsets]
            if args.va_offset is not None:
                for row, x in zip(rows, offsets):
                    row["guest_ea_assuming_va_offset"] = f"0x{x + args.va_offset:X}"
            for row in rows:
                print("candidate", row)
            print(f"{len(rows)} candidatos; verifique módulos, limites e offsets de load")
            result = {"mode": "scan", "source": str(args.eboot),
                      "warning": "Assinatura heurística; NÃO comprova módulo SPU nem compatibilidade",
                      "candidates": rows}
        else:
            rows = map_entries(args.source.read_bytes(), args.target.read_bytes(),
                               parse_offsets(args.offsets))
            for row in rows:
                print(row)
            result = {"mode": "entries",
                      "source": str(args.source), "target": str(args.target),
                      "warning": "Só janelas exatas únicas; verificar controle de fluxo, base LS e relocations",
                      "entries": rows}
    except (OSError, ValueError) as exc:
        ap.error(str(exc))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                             encoding="utf-8")
        print(f"Relatório salvo em: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
