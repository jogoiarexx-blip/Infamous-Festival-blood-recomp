#!/usr/bin/env python3
"""Prepare the local Festival of Blood raw SPURS policy for an opt-in test build.

Never writes into ../ps3recomp; source dump and generated guest-derived C stay
under out/ (gitignored). Refuses unknown images, changed layouts, and existing
unmanaged registration files. A successful build is NOT proof of correct PM
execution or game playability.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

BASE = 0xA00
SIZE = 11904
FP = 0xB3523C4B17650EF8
ENTRY = BASE
REMOVE = (0x15C0, 0x15D0, 0x15E0, 0x15F0)
SMC_TARGET = 0x3FEC0
IMAGE_NAME = "fob_policy"
IMAGE_ID = 2

# Observed local data signatures (not functions) in the user's captured image.
DATA_WORDS = {
    0x15C0: 0x2C000000, 0x15C8: 0x5757534A,  # WWSJ
    0x15D0: 0x2D000000, 0x15D8: 0xAAAABBBB,
    0x15E0: 0x2C000000, 0x15F0: 0x2D000000,
}


def die(reason: str) -> None:
    raise SystemExit("ERRO: " + reason)


def fp_fnv(data: bytes) -> int:
    h = 1469598103934665603
    for value in data:
        h = ((h ^ value) * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return h


def subprocess_checked(args: list[str]) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run(args, check=True)


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    tools = root.parent / "ps3recomp" / "tools"
    raw_path = root / "out/spu-misses/spujob_B3523C4B17650EF8_11904.bin"
    bounds_path = root / "out/spurs-policy-probe/functions.json"
    port = root / "out/port"
    spu_dir = port / "spu"
    dest = spu_dir / IMAGE_NAME
    reg = spu_dir / "jobmods_register.c"

    for p in (raw_path, bounds_path, tools / "spu_lifter.py",
              tools / "spu_disasm.py", port / "CMakeLists.txt"):
        if not p.is_file():
            die("arquivo exigido não encontrado: " + str(p))
    if not (spu_dir / "fob_spu" / "spu_recomp.c").exists():
        die("o primeiro SPU não está em out/port/spu/fob_spu; preserve a compilação anterior.")
    if not (spu_dir / "spu_workloads.c").exists():
        die("registro do primeiro SPU ausente; execute prepare_spu_elf.py antes.")
    if dest.exists() or reg.exists():
        die("já existe política ou registro em out/port/spu; não sobrescrever.")

    data = raw_path.read_bytes()
    if len(data) != SIZE or fp_fnv(data) != FP:
        die("fingerprint/tamanho do módulo bruto não coincide com o diagnosticado.")
    for addr, expected in DATA_WORDS.items():
        word = int.from_bytes(data[addr-BASE:addr-BASE+4], "big")
        if word != expected:
            die(f"marcador em 0x{addr:X} mudou; abortando filtro sem alterar arquivos.")

    bounds = json.loads(bounds_path.read_text(encoding="utf-8"))
    if len(bounds) != 194:
        die(f"esperadas 194 funções detectadas, encontradas {len(bounds)}.")
    by_start = {int(b["start"]): (int(b["start"]), int(b["end"])) for b in bounds}
    if len(by_start) != len(bounds) or ENTRY not in by_start:
        die("intervalos de funções duplicados ou entrada 0xA00 ausente.")
    for addr in REMOVE:
        if by_start.get(addr) != (addr, addr + 8):
            die(f"função de dados 0x{addr:X} não tem o intervalo esperado.")
    filtered = [
        b for b in bounds if int(b["start"]) not in REMOVE
    ]
    kept_ranges = [(int(b["start"]), int(b["end"])) for b in filtered]
    # Never remove an address reachable by a direct call/branch from code
    # we still lift. The source is not included in the public repository.
    sys.path.insert(0, str(tools))
    from spu_disasm import disassemble_spu

    instructions = disassemble_spu(data, base_addr=BASE)
    branch_mnemonics = {"br", "bra", "brsl", "brasl",
                        "brz", "brnz", "brhz", "brhnz"}
    inbound = []
    for ins in instructions:
        if ins.mnemonic not in branch_mnemonics:
            continue
        if not any(start <= ins.addr < end for start, end in kept_ranges):
            continue
        token = ins.operands.split(",")[-1].strip()
        if not token.lower().startswith("0x"):
            continue
        try:
            target = int(token, 16)
        except ValueError:
            continue
        if target in REMOVE:
            inbound.append((ins.addr, target))
    if inbound:
        die("funções preservadas saltam diretamente para pseudo-funções: "
            + repr([(hex(a), hex(b)) for a, b in inbound]))

    channels_path = root.parent / "ps3recomp/runtime/spu/spu_channels.c"
    if not channels_path.is_file():
        die("runtime spu_channels.c indisponível.")
    runtime_text = channels_path.read_text(encoding="utf-8", errors="replace")
    if "0x3FEC0" not in runtime_text or "spu_smc_microstep" not in runtime_text:
        die("o runtime não confirma suporte ao trampoline SMC em 0x3FEC0.")

    with tempfile.TemporaryDirectory(prefix="fob-policy-", dir=root / "out") as td:
        stage = Path(td)
        dst = stage / IMAGE_NAME
        dst.mkdir()
        filtered_bounds = stage / "functions.filtered.json"
        filtered_bounds.write_text(json.dumps(filtered, indent=2), encoding="utf-8")
        report = stage / "policy-report.json"
        subprocess_checked([
            sys.executable, str(tools / "spu_lifter.py"), str(raw_path),
            "--base", hex(BASE),
            "--functions", str(filtered_bounds),
            "--symbol-prefix", IMAGE_NAME + "_",
            "--output", str(dst),
            "--report", str(report),
        ])

        diag = json.loads(report.read_text(encoding="utf-8"))
        functions = diag.get("functions", [])
        emitted = {int(start) for start, _ in functions}
        unresolved = (set(diag.get("call_targets", []))
                      | set(diag.get("branch_targets", []))) - emitted
        if (diag.get("unsupported") or
                unresolved != {SMC_TARGET} or ENTRY not in emitted or
                any(addr in emitted for addr in REMOVE) or
                len(functions) != len(filtered)):
            die("resultado ainda inseguro: unsupported="
                + repr(diag.get("unsupported"))
                + ", pendentes=" + repr([hex(x) for x in sorted(unresolved)])
                + ", funções=" + str(len(functions)))
        c = dst / "spu_recomp.c"
        h = dst / "spu_recomp.h"
        for file in (c, h):
            text = file.read_text(encoding="utf-8")
            if "TODO spu:" in text:
                die("o lifter deixou instruções TODO; abortando integração.")
            text = re.sub(
                r'#include\s+"(?:\.\./)+runtime/spu/([A-Za-z0-9_]+\.h)"',
                r'#include "\1"', text
            )
            file.write_text(text, encoding="utf-8", newline="\n")
        stub_symbol = IMAGE_NAME + "_spu_func_0003FEC0"
        if stub_symbol not in c.read_text(encoding="utf-8"):
            die("stub de dispatch para código SMC 0x3FEC0 ausente.")

        registration = """/* Policy module registration for local Festival of Blood testing.
 * This file intentionally uses the template's optional jobmods_register.c
 * slot; it registers a SPURS POLICY, not a WWS job-module binary.
 * Original program bytes stay in the guest's memory.
 * Generated locally; never publish game-derived C or executables.
 */
#include "spu_workload.h"
extern void spu_begin_image(int image_id);
extern void fob_policy_spu_func_00000A00(spu_context*);
extern void fob_policy_spu_recomp_register(void);

__attribute__((constructor))
static void fob_policy_register_ctor(void)
{
    spu_begin_image(2);
    fob_policy_spu_recomp_register();
    spu_workload_register_img(0xB3523C4B17650EF8ULL,
        fob_policy_spu_func_00000A00, 2, "fob_policy");
    spu_begin_image(0);
}
"""
        (dst / ".fob-policy-managed").write_text(
            "Local SPURS policy lift. DO NOT COMMIT.\n", encoding="utf-8"
        )
        # The template auto-includes jobmods_register.c if it exists. We
        # deliberately create this only after the candidate passed validation.
        dst.rename(dest)
        try:
            reg.write_text(registration, encoding="utf-8", newline="\n")
        except Exception:
            shutil.rmtree(dest)
            raise
        summary = root / "out/spurs-policy-probe/filtered-report.json"
        summary.write_text(
            json.dumps({
                "fingerprint": f"0x{FP:016X}",
                "functions": len(functions),
                "filtered_function_starts": [hex(x) for x in REMOVE],
                "unsupported": diag.get("unsupported"),
                "external_smc_targets": [hex(x) for x in sorted(unresolved)],
                "entry": hex(ENTRY),
            }, indent=2), encoding="utf-8"
        )
    print("\nSUCESSO: segunda política SPURS preparada localmente.")
    print("FUNCOES:", len(functions), "| UNSUPPORTED: {}")
    print("ALVO_EXTERNO_SMC:", hex(SMC_TARGET), "(interpretador já existente)")
    print("REGISTRO:", reg)
    print("AVISO: código gerado não testado em execução; o jogo pode continuar com tela preta.")
    print('PRÓXIMO: cmake -S "out\\port" -B "out\\build" -DPORT_ENABLE_SPU=ON "-DPORT_SPU_INPUTS:STRING="')
    print('DEPOIS:  cmake --build "out\\build" --parallel 1')


if __name__ == "__main__":
    main()
