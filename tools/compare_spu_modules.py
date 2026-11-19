#!/usr/bin/env python3
"""Compare locally extracted raw SPU job modules without distributing game data.

Compares *.bin files containing raw, four-byte-aligned SPU instruction words.
Exact SHA-256 matches establish byte identity; sequence similarity is only a
heuristic, never proof that two jobs are interchangeable.

Example:
  py tools/compare_spu_modules.py --left out/if2-jobmods --right out/fob-jobmods --json out/spu-cross-title-report.json
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Module:
    name: str
    size: int
    sha256: str
    words: tuple[int, ...]


def read_modules(folder: Path, max_words: int = 12000) -> list[Module]:
    if not folder.is_dir():
        raise ValueError(f"Pasta não encontrada: {folder}")
    modules = []
    for path in sorted(folder.glob("*.bin")):
        data = path.read_bytes()
        if not data or len(data) % 4:
            raise ValueError(f"Módulo vazio ou não alinhado a 4 bytes: {path.name}")
        if len(data) // 4 > max_words:
            raise ValueError(f"Módulo excede {max_words} palavras (limite de análise): {path.name}")
        words = tuple(value[0] for value in struct.iter_unpack(">I", data))
        modules.append(Module(path.name, len(data), hashlib.sha256(data).hexdigest(), words))
    if not modules:
        raise ValueError(f"Nenhum módulo *.bin encontrado: {folder}")
    return modules


def similarity(a: Module, b: Module) -> float:
    if a.sha256 == b.sha256 and a.size == b.size:
        return 1.0
    upper_bound = 2.0 * min(len(a.words), len(b.words)) / (len(a.words) + len(b.words))
    if upper_bound < 0.5:
        return 0.0
    return difflib.SequenceMatcher(None, a.words, b.words, autojunk=True).ratio()


def compare(left: list[Module], right: list[Module], top: int = 3,
            min_score: float = 0.5) -> list[dict]:
    report = []
    for a in left:
        candidates = []
        for b in right:
            score = similarity(a, b)
            if score < min_score:
                continue
            candidates.append({
                "module": b.name,
                "size_bytes": b.size,
                "sha256": b.sha256,
                "score": round(score, 5),
                "exact_bytes": a.size == b.size and a.sha256 == b.sha256,
            })
        candidates.sort(key=lambda c: (-c["score"], not c["exact_bytes"], c["module"]))
        report.append({
            "left": {"module": a.name, "size_bytes": a.size, "sha256": a.sha256},
            "candidates": candidates[:top],
        })
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--left", required=True, type=Path, help="Pasta com módulos SPU raw *.bin da primeira edição")
    parser.add_argument("--right", required=True, type=Path, help="Pasta com módulos SPU raw *.bin da segunda edição")
    parser.add_argument("--json", type=Path, help="Saída JSON opcional (recomenda-se a pasta ignorada out/)")
    parser.add_argument("--top", type=int, default=3, help="Máximo de candidatos por módulo (padrão: 3)")
    parser.add_argument("--min-score", type=float, default=0.5,
                        help="Pontuação mínima heurística entre 0 e 1 (padrão: 0.5)")
    parser.add_argument("--max-words", type=int, default=12000,
                        help="Limite de palavras por módulo para evitar análise custosa")
    args = parser.parse_args()
    if args.top < 1 or args.max_words < 1 or not 0 <= args.min_score <= 1:
        parser.error("--top, --max-words devem ser positivos; --min-score deve estar entre 0 e 1")
    try:
        left = read_modules(args.left, args.max_words)
        right = read_modules(args.right, args.max_words)
    except ValueError as exc:
        parser.error(str(exc))
    results = compare(left, right, args.top, args.min_score)
    for entry in results:
        print(f"{entry['left']['module']} ({entry['left']['size_bytes']} bytes)")
        if not entry["candidates"]:
            print("  sem correspondência acima do limiar")
        for match in entry["candidates"]:
            kind = "EXATO" if match["exact_bytes"] else "CANDIDATO (não validado)"
            print(f"  {match['module']}  score={match['score']:.5f}  {kind}")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps({
            "method": "byte SHA-256 exactness; heuristic four-byte-word SequenceMatcher with autojunk",
            "warning": "Similarity does not prove functional equivalence; validate control flow, relocations and runtime behavior.",
            "left": str(args.left), "right": str(args.right), "results": results,
        }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Relatório salvo em: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
