#!/usr/bin/env python3
"""Inspeciona cabeçalhos PS3 ELF/SELF e inventaria arquivos locais.

Não descriptografa, modifica, distribui ou reconstitui conteúdo do jogo.
Usa apenas a biblioteca padrão do Python (3.10+).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_binary(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError("O caminho indicado não é um arquivo regular.")
    size = path.stat().st_size
    with path.open("rb") as stream:
        header = stream.read(64)

    report: dict[str, Any] = {
        "filename": path.name,
        "size_bytes": size,
        "sha256": sha256_file(path),
    }
    if header.startswith(b"SCE\x00"):
        report.update({
            "format": "SELF/SCE",
            "status": "contêiner SCE detectado (não é um ELF pronto para análise PPU)",
            "note": "Esta ferramenta não descriptografa nem extrai o contêiner.",
        })
        return report

    if not header.startswith(b"\x7fELF"):
        report.update({
            "format": "unknown",
            "status": "Não possui assinatura ELF nem SCE/SELF reconhecida.",
        })
        return report

    if len(header) < 16:
        raise ValueError("Identificação ELF truncada.")
    elf_class = header[4]
    elf_data = header[5]
    if elf_class not in (1, 2):
        raise ValueError(f"Classe ELF desconhecida: {elf_class}")
    if elf_data not in (1, 2):
        raise ValueError(f"Codificação de bytes ELF desconhecida: {elf_data}")

    bits = 32 if elf_class == 1 else 64
    byte_order = "little" if elf_data == 1 else "big"
    endian = "<" if elf_data == 1 else ">"
    fmt = "HHIIIIIHHHHHH" if bits == 32 else "HHIQQQIHHHHHH"
    required = 16 + struct.calcsize(endian + fmt)
    if len(header) < required:
        raise ValueError("Cabeçalho ELF incompleto.")

    values = struct.unpack_from(endian + fmt, header, 16)
    (
        file_type, machine, version, entry, phoff, shoff, flags,
        ehsize, phentsize, phnum, shentsize, shnum, shstrndx,
    ) = values
    if ehsize < required or ehsize > size:
        raise ValueError("Tamanho de cabeçalho ELF inválido.")
    if phnum and (phoff == 0 or phoff + phentsize * phnum > size):
        raise ValueError("Tabela de segmentos ELF está fora do arquivo.")
    if shnum and (shoff == 0 or shoff + shentsize * shnum > size):
        raise ValueError("Tabela de seções ELF está fora do arquivo.")

    candidate_ppu = bits == 64 and byte_order == "big" and machine == 21
    report.update({
        "format": "ELF",
        "class_bits": bits,
        "byte_order": byte_order,
        "machine": machine,
        "machine_name": "PowerPC64" if machine == 21 else "other",
        "elf_type": file_type,
        "elf_version": version,
        "entry_point": f"0x{entry:x}",
        "program_header_count": phnum,
        "section_header_count": shnum,
        "section_name_index": shstrndx,
        "flags": f"0x{flags:x}",
        "ppu_candidate": candidate_ppu,
        "status": (
            "Candidato ELF PowerPC64 big-endian; identidade do jogo ainda NÃO verificada."
            if candidate_ppu else
            "ELF reconhecido, mas não tem o perfil básico esperado de PPU PowerPC64."
        ),
    })
    return report


def inventory_directory(root: Path, exclude: Path | None = None) -> dict[str, Any]:
    if not root.is_dir():
        raise ValueError("O caminho do inventário deve ser uma pasta.")
    root = root.resolve()
    excluded = exclude.resolve() if exclude else None
    entries: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        if excluded and path.resolve() == excluded:
            continue
        entries.append({
            "path": path.relative_to(root).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    return {
        "format_version": 1,
        "file_count": len(entries),
        "total_bytes": sum(item["size_bytes"] for item in entries),
        "files": entries,
        "note": "Inventário local; não inclui o conteúdo dos arquivos.",
    }


def write_json(data: dict[str, Any], dest: Path | None) -> None:
    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if dest is None:
        print(payload, end="")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(payload, encoding="utf-8")
    print(f"Relatório salvo em: {dest}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("inspect", "Inspecionar um arquivo ELF ou SELF local"),
        ("inventory", "Gerar lista de nomes, tamanhos e hashes de uma pasta"),
    ):
        p = subs.add_parser(name, help=help_text)
        p.add_argument("path", type=Path)
        p.add_argument("--output", "-o", type=Path, help="Salvar JSON local")
    args = parser.parse_args()
    try:
        if args.command == "inspect":
            if args.output and args.path.resolve() == args.output.resolve():
                raise ValueError("O relatório não pode substituir o arquivo de entrada.")
            result = inspect_binary(args.path)
        else:
            result = inventory_directory(args.path, args.output)
        write_json(result, args.output)
    except (OSError, ValueError, struct.error) as exc:
        parser.exit(2, f"Erro: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
