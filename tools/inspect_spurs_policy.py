#!/usr/bin/env python3
"""Diagnose the local raw SPURS policy captured from NPUA80657.

Run from the repository root:
    py tools/inspect_spurs_policy.py

Reads the PRIVATE raw module only from out/spu-misses, writes diagnostics and
derived code only under out/spurs-policy-probe (gitignored). Does not register
the policy or alter any files in ../ps3recomp. This is NOT a playable port.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys

EXPECTED_SIZE = 11904
EXPECTED_FINGERPRINT = 0xB3523C4B17650EF8
LS_BASE = 0xA00


def fingerprint(data: bytes) -> int:
    h = 1469598103934665603
    for byte in data:
        h = ((h ^ byte) * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return h


def run(cmd: list[str]) -> None:
    completed = subprocess.run(cmd, check=False)
    if completed.returncode:
        raise SystemExit(
            f"ERRO: a ferramenta retornou codigo {completed.returncode}; "
            "nenhum arquivo do SDK foi alterado."
        )


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    source = root / "out/spu-misses/spujob_B3523C4B17650EF8_11904.bin"
    sdk_tools = root.parent / "ps3recomp/tools"
    detector = sdk_tools / "find_spu_functions.py"
    lifter = sdk_tools / "spu_lifter.py"
    output = root / "out/spurs-policy-probe"
    if not source.is_file():
        raise SystemExit("ERRO: modulo SPURS nao encontrado em " + str(source))
    if not detector.is_file() or not lifter.is_file():
        raise SystemExit("ERRO: pasta ../ps3recomp/tools nao encontrada")
    data = source.read_bytes()
    fp = fingerprint(data)
    if len(data) != EXPECTED_SIZE or fp != EXPECTED_FINGERPRINT:
        raise SystemExit(
            f"ERRO: modulo inesperado: tamanho={len(data)}, fp=0x{fp:016X}; "
            "nao vou traduzir um arquivo de identidade diferente."
        )
    print(f"Modulo SPURS: {len(data)} bytes; fp=0x{fp:016X}", flush=True)
    print(f"Base LS de teste: 0x{LS_BASE:X} (documentada por spurs_policy.c)", flush=True)
    output.mkdir(parents=True, exist_ok=True)
    bounds = output / "functions.json"
    lifted = output / "lifted"
    report = lifted / "lift.json"
    lifted.mkdir(parents=True, exist_ok=True)
    # The stock detector knows about flat SPU LS images with --raw.
    run([sys.executable, str(detector), str(source),
         "--raw", "--base", hex(LS_BASE), "--out", str(bounds)])
    funcs = json.loads(bounds.read_text(encoding="utf-8"))
    if not funcs:
        raise SystemExit("ERRO: nenhuma funcao SPURS identificada")
    starts = {int(f["start"]) for f in funcs}
    if LS_BASE not in starts:
        raise SystemExit("ERRO: a funcao de entrada LS 0xA00 nao foi identificada")

    run([sys.executable, str(lifter), str(source),
         "--base", hex(LS_BASE),
         "--functions", str(bounds),
         "--symbol-prefix", "fob_policy_",
         "--output", str(lifted),
         "--report", str(report)])
    d = json.loads(report.read_text(encoding="utf-8"))
    emitted = {start for start, end in d.get("functions", [])}
    dangling = sorted(
        (set(d.get("call_targets", [])) | set(d.get("branch_targets", []))) - emitted
    )
    unsupported = d.get("unsupported", {})
    snippets = []
    generated = lifted / "spu_recomp.c"
    for line in generated.read_text(encoding="utf-8", errors="replace").splitlines():
        if "spu_unsupported(" in line and "/* TODO spu:" in line:
            m = re.search(r"spu_unsupported\(0x([0-9A-Fa-f]+)", line)
            if m:
                snippets.append(int(m.group(1), 16))
    print("\n=== DIAGNOSTICO SPURS RAW (SEM REGISTRAR/COMPILAR) ===")
    print(f"FUNCOES_DETECTADAS: {len(funcs)}")
    print(f"FUNCOES_TRADUZIDAS: {len(emitted)}")
    print(f"ENTRADA_A00: {LS_BASE in emitted}")
    print(f"UNSUPPORTED: {unsupported}")
    print(f"ALVOS_AUSENTES: {[hex(a) for a in dangling[:20]]}")
    print(f"TOTAL_ALVOS_AUSENTES: {len(dangling)}")
    print(f"PRIMEIROS_ENDERECOS_UNSUPPORTED: {[hex(a) for a in sorted(snippets)[:12]]}")
    print(f"ULTIMOS_ENDERECOS_UNSUPPORTED: {[hex(a) for a in sorted(snippets)[-12:]]}")
    # Focused control-flow diagnostic: an unresolved *external* LS jump may
    # still be legitimate (local store extends to 0x3FFFF, not just raw image).
    sys.path.insert(0, str(sdk_tools))
    from spu_disasm import disassemble_spu

    insns = disassemble_spu(data, base_addr=LS_BASE)
    active_funcs = [(int(s), int(e)) for s, e in d.get("functions", [])]

    def owner(addr: int) -> str:
        return ", ".join(
            f"0x{s:X}..0x{e:X}" for s, e in active_funcs if s <= addr < e
        ) or "FORA DAS FUNCOES TRADUZIDAS"

    print("\n=== PONTOS ESPECIFICOS (RESUMO SEGURO) ===")
    for addr in (0x15C0, 0x15D0, 0x15E0, 0x15F0):
        ins = next((item for item in insns if item.addr == addr), None)
        if ins is not None:
            print(f"OPCODE_0x{addr:X}: {ins.mnemonic} | funcao={owner(addr)}")

    raw_tail = 0x3FEC0
    print(f"ALVO_0x{raw_tail:X}_DENTRO_DO_LOCAL_STORE: {raw_tail < 0x40000}")
    for ins in insns:
        if ins.mnemonic in ("br", "bra", "brsl", "brasl",
                            "brz", "brnz", "brhz", "brhnz"):
            if ins.operands.lower().split(",")[-1].strip() == f"0x{raw_tail:x}":
                print(f"ORIGEM_ALVO_0x{raw_tail:X}: "
                      f"0x{ins.addr:X} {ins.mnemonic} {ins.operands}"
                      f" | funcao={owner(ins.addr)}")
    for i in insns:
        if 0x15A0 <= i.addr < 0x1610:
            print(f"VIZINHO_0x{i.addr:X}: {i.mnemonic} {i.operands}"
                  f" | funcao={owner(i.addr)}")
    print("FIM_RESUMO_SPURS")
    print("RELATORIO_LOCAL:", report)
    print("AVISO: diagnostico somente; nenhuma politica SPURS foi integrada ao EXE.")
    print("NAO PUBLICAR: out/spurs-policy-probe, out/spu-misses ou binarios do jogo.")


if __name__ == "__main__":
    main()
