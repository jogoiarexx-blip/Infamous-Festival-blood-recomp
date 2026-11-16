#!/usr/bin/env python3
"""Prepare the verified NPUA80657 SPU ELF for the ps3recomp template.

Run from the project root with:
    py tools/prepare_spu_elf.py

Only reads locally generated, ignored files. Generated code and the game's
SPU ELF stay under out/ (never committed to the public repository).
This prepares a bounded SPU lift; it does not prove game functionality.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

EXPECTED_SHA256 = "d08b1ad818d026818f1c7cbb2bef448d242a9ae51aab4c7bce69f2ad14308355"
EXPECTED_FINGERPRINT = "00E729804474449A"
EXPECTED_ENTRY = 0x3050
CODE_END = 0xB290
IMAGE_NAME = "fob_spu"


def die(message: str) -> None:
    raise SystemExit("ERRO: " + message)


def run(args: list[str]) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run(args, check=True)


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    sdk = root.parent / "ps3recomp"
    inventory_path = root / "out/build/generated_spu/inventory.json"
    lifter = sdk / "tools/spu_lifter.py"
    registry_builder = sdk / "tools/build_spu_workloads.py"
    port = root / "out/port"
    destination = port / "spu"
    backup = port / "spu.previous"
    if not inventory_path.is_file():
        die("faltou out/build/generated_spu/inventory.json; execute o diagnóstico anterior.")
    if not (lifter.is_file() and registry_builder.is_file()):
        die("ferramentas ps3recomp não encontradas na pasta irmã ../ps3recomp.")
    if not (port / "CMakeLists.txt").is_file():
        die("template out/port ainda não foi preparado.")
    inv = json.loads(inventory_path.read_text(encoding="utf-8"))
    candidates = inv.get("programs", [])
    matching = [p for p in candidates if p.get("sha256", "").lower() == EXPECTED_SHA256]
    if len(matching) != 1:
        die("o inventário não contém exatamente o SPU ELF esperado para NPUA80657.")
    program = matching[0]
    if (str(program.get("fingerprint", "")).upper() != EXPECTED_FINGERPRINT
            or program.get("entry") != EXPECTED_ENTRY):
        die("fingerprint ou ponto de entrada não coincide com a captura validada.")
    source = inventory_path.parent / program["name"]
    image_file = source / "image.elf"
    code_file = source / "code.bin"
    functions_file = source / "functions.json"
    for item in (image_file, code_file, functions_file):
        if not item.is_file():
            die("falta arquivo local: " + str(item))
    image = image_file.read_bytes()
    if hashlib.sha256(image).hexdigest() != EXPECTED_SHA256:
        die("o hash SHA-256 do ELF local não corresponde ao inventário.")
    bounds = json.loads(functions_file.read_text(encoding="utf-8"))
    if not any(int(f["start"]) <= EXPECTED_ENTRY < int(f["end"]) for f in bounds):
        die("a função de entrada não está presente no mapeamento do lifter.")
    executable_ranges = program.get("executable_ranges", [])
    if not any(a <= EXPECTED_ENTRY < CODE_END <= b for a, b in executable_ranges):
        die("limite SPU fora da região executável identificada.")
    if backup.exists():
        die("há um backup anterior em out/port/spu.previous; não sobrescrever.")
    if destination.exists() and not (destination / ".fob-spu-managed").is_file():
        die("out/port/spu contém arquivos não gerenciados; preservados.")

    port.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="fob-spu-stage-", dir=port) as td:
        stage = Path(td)
        lifted = stage / IMAGE_NAME
        lifted.mkdir()
        images = stage / "images"
        images.mkdir()
        shutil.copyfile(image_file, images / (IMAGE_NAME + ".elf"))
        report = lifted / "lift.json"

        run([sys.executable, str(lifter), str(code_file),
             "--base", str(executable_ranges[0][0]),
             "--functions", str(functions_file),
             "--code-end", hex(CODE_END),
             "--symbol-prefix", IMAGE_NAME + "_",
             "--output", str(lifted), "--report", str(report)])

        diag = json.loads(report.read_text(encoding="utf-8"))
        functions = diag.get("functions", [])
        starts = {s for s, _ in functions}
        missing = (set(diag.get("call_targets", []))
                   | set(diag.get("branch_targets", []))) - starts
        if diag.get("unsupported") or missing or EXPECTED_ENTRY not in starts:
            die("SPU incompleto: unsupported="
                + repr(diag.get("unsupported"))
                + ", missing=" + repr([hex(x) for x in sorted(missing)]))
        if not functions or any(not (s < e <= CODE_END) for s, e in functions):
            die("limites de funções inválidos após o corte SPU.")
        generated_c = (lifted / "spu_recomp.c").read_text(encoding="utf-8")
        if "TODO spu:" in generated_c:
            die("o lifter deixou instruções ou saltos TODO no código C.")

        run([sys.executable, str(registry_builder),
             "--images", str(images), "--lifted", str(stage),
             "--out", str(stage / "spu_workloads.c"),
             "--skip-lift", "--constructor",
             "--register-fn", "fob_spu_register_all",
             "--title", "Festival of Blood - local ELF SPU"])
        registry = (stage / "spu_workloads.c").read_text(encoding="utf-8")
        expected_symbol = IMAGE_NAME + "_spu_func_" + f"{EXPECTED_ENTRY:08X}"
        if expected_symbol not in registry or EXPECTED_FINGERPRINT not in registry:
            die("registro SPU não contém a entrada/fingerprint esperado.")
        (stage / ".fob-spu-managed").write_text(
            "Generated locally; contains proprietary game-derived files. DO NOT COMMIT.\n",
            encoding="utf-8",
        )
        # Stage is complete. Only replace a previously generated output tree.
        if destination.exists():
            destination.rename(backup)
        try:
            # TemporaryDirectory cleans the original stage name after move.
            stage.rename(destination)
        except Exception:
            if backup.exists():
                backup.rename(destination)
            raise
        if backup.exists():
            shutil.rmtree(backup)

    print("\nSUCESSO: SPU ELF preparado e registrado localmente.")
    print("Funções:", len(functions), "| Unsupported: 0 | Destinos ausentes: 0")
    print("Arquivos locais:", destination)
    print('PRÓXIMO: cmake -S "out\\port" -B "out\\build" -DPORT_ENABLE_SPU=ON "-DPORT_SPU_INPUTS:STRING="')
    print('DEPOIS:  cmake --build "out\\build" --parallel 1')
    print("Atenção: o segundo módulo SPURS raw e os arquivos VFS ainda faltam.")


if __name__ == "__main__":
    main()
