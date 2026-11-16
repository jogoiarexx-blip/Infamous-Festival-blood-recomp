#!/usr/bin/env python3
"""Read-only inspection of FoB SPURS LFQueue dispatch and policy DMA loop.

Uses the user's own local captured SPURS raw and out/boot_lfqueue_v2.log.
Prints small summaries, decoded instruction *mnemonics* around 0x2514,
and a queue/taskset consistency check. Never edits the toolkit, executable,
or any game file. Do not publish the raw image or generated lifted code.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "out/spu-misses/spujob_B3523C4B17650EF8_11904.bin"
LOG = ROOT / "out/boot_lfqueue_v2.log"
SIZE = 11904
FP = 0xB3523C4B17650EF8
BASE = 0xA00
KEY_PC = 0x2514


def fingerprint(data: bytes) -> int:
    h = 1469598103934665603
    for byte in data:
        h = ((h ^ byte) * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return h


def subset(lines: list[str], term: str, cap: int = 6) -> list[str]:
    hits = [x.strip() for x in lines if term in x]
    print(f"{term}: {len(hits)}")
    chosen = hits[:cap]
    if len(hits) > cap:
        chosen.append(f"... +{len(hits) - cap} ocorrencia(s) omitida(s)")
    for line in chosen:
        print("   ", line[:360])
    return hits


def parse_hex(text: str, label: str) -> int | None:
    m = re.search(r"\b" + re.escape(label) + r"=0x([0-9a-fA-F]+)", text)
    return int(m.group(1), 16) if m else None


def analyze_log() -> None:
    if not LOG.is_file():
        raise SystemExit("ERRO: falta o log local " + str(LOG))
    lines = LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    print("=== SITUACAO DE EXECUCAO (log local) ===")
    for term in (
        "PM resolved",
        "_LFQueueInitialize(",
        "_cellSpursLFQueuePushBody#",
        "[spu_workload] signal task",
        "WAIT_SIGNAL#",
        "EventFlagWait BLOCKED",
        "[spu-dma] img=2 pc=0x02514",
        "[pm-end]",
        "unresolved NID 0x8A85674D",
    ):
        subset(lines, term, cap=4 if term != "[spu_workload] signal task" else 10)

    pushes = [x for x in lines if "_cellSpursLFQueuePushBody#" in x]
    waiters = [x for x in lines if "WAIT_SIGNAL#" in x]
    waits = [x for x in lines if "EventFlagWait BLOCKED" in x]
    print("\n=== CRUZAMENTO DE ENDERECOS ===")
    seen_tasksets = sorted({
        parse_hex(x, "taskset") for x in waiters if parse_hex(x, "taskset") is not None
    })
    print("TASKSET(S) da(s) tarefa(s) SPU em WAIT_SIGNAL:",
          ", ".join(f"0x{x:08X}" for x in seen_tasksets) or "nao localizados")
    flag_eas = sorted({
        parse_hex(x, "flagEA") for x in waits if parse_hex(x, "flagEA") is not None
    })
    print("EVENT FLAG(S) aguardadas:",
          ", ".join(f"0x{x:08X}" for x in flag_eas) or "nao localizadas")

    for line in pushes[:4]:
        q = parse_hex(line, "q")
        owner = parse_hex(line, "taskset")
        if q is None:
            continue
        print(f"LFQUEUE=0x{q:08X}, owner_ou_sinal=0x{owner:08X}" if owner is not None
              else f"LFQUEUE=0x{q:08X} (owner nao encontrado)")
        if owner is not None and owner in seen_tasksets:
            print("  owner coincide com taskset WAIT_SIGNAL")
        elif owner is not None and seen_tasksets:
            print("  ATENCAO: owner informado pelo PR nao coincide com o taskset da tarefa aguardando")
        if owner is not None and owner & 0x7F:
            print("  ATENCAO: owner nao esta alinhado a 128 bytes (pode ser handle/ponteiro marcado)")
        if q - 0x80 in flag_eas:
            print(f"  EVENT FLAG no endereco adjacente 0x{q-0x80:08X} (fila - 0x80)")
    print("NOTA: nao alterar owner, filas, atomicos ou sinais sem confirmar o protocolo.")


def disasm() -> None:
    if not RAW.is_file():
        print("AVISO: raw SPURS nao encontrado; disassembly omitido.")
        return
    data = RAW.read_bytes()
    if len(data) != SIZE or fingerprint(data) != FP:
        raise SystemExit("ERRO: modulo local possui tamanho/fingerprint diferente; nao analisado.")
    lib = ROOT.parent / "ps3recomp/tools"
    if not (lib / "spu_disasm.py").is_file():
        raise SystemExit("ERRO: ../ps3recomp/tools/spu_disasm.py nao encontrado.")
    sys.path.insert(0, str(lib))
    from spu_disasm import disassemble_spu
    instructions = {i.addr: i for i in disassemble_spu(data, BASE)}
    print("\n=== INSTRUCOES SPURS - PONTO DO DMA REPETIDO ===")
    print(f"Modulo FP=0x{FP:016X}, PC=0x{KEY_PC:X}")
    for pc in range(KEY_PC - 0x40, KEY_PC + 0x34, 4):
        ins = instructions.get(pc)
        if ins:
            mark = " <<< DMA LOOP" if pc == KEY_PC else ""
            print(f"0x{pc:05X} {ins.mnemonic:<11} {ins.operands}{mark}")
    print("\n=== PONTOS DE CONTROLE / SALTOS RECENTES ===")
    for pc in (0x2298, 0x22A0, 0x2B60, 0x2C68, 0x2CB0, 0x2CB8, 0x2CD8):
        ins = instructions.get(pc)
        if ins:
            print(f"0x{pc:05X} {ins.mnemonic:<11} {ins.operands}")
    print("FIM_ANALISE_SPURS")
    print("Nao publique o modulo binario, o ELF, nem o C recompilado.")


if __name__ == "__main__":
    analyze_log()
    disasm()
