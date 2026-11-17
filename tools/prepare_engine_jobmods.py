#!/usr/bin/env python3
"""Lift the WWS SPU job modules that are embedded in the PPU ELF (engine modules).

Run from the project root:
    py tools/prepare_engine_jobmods.py

Why: the Wws_Job policy module streams each job module into LS 0x4000 from an
effective address inside the EBOOT's own data. Without lifted code for them the
job runs in the SPU interpreter and never completes, which kept the title in
its boot-time teardown waits and left the window black. With them lifted the
title reaches its first rendered screen.

Uses ../ps3recomp/tools/lift_jobmods.py --engine-elf, then installs the output
under out/port/spu (game-derived, gitignored, DO NOT COMMIT) and writes
out/port/spu/jobmods_engine_register.c. Add that file to the `foreach` list of
generated sources in out/port/CMakeLists.txt, then re-run cmake and build.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


# Library routines (atomic add, DMA split, memset/memcpy) sit past each module's
# "code_end" and are reached only through indirect calls, so the lifter does not
# find them and they run in the SPU interpreter (~15M steps/s of one core, 58k
# calls in 5 s). Seeding them extends the lifted span: ~8 -> ~44 FPS here.
# Addresses are LS addresses for the NPUA80657 modules; find more with
# SPU_INTERP_STATS=5 ("top entries"). Override with LBP_JOBMOD_EXTRA_FUNCS.
DEFAULT_EXTRA_FUNCS = "0x9548,0x95D8,0x9690"


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    tool = root.parent / "ps3recomp" / "tools" / "lift_jobmods.py"
    elf = root / "private/game/EBOOT.elf"
    spu_dir = root / "out/port/spu"
    if not tool.is_file():
        raise SystemExit("ERRO: ferramenta ausente: " + str(tool))
    if not elf.is_file():
        raise SystemExit("ERRO: ELF local ausente: " + str(elf))
    if not (spu_dir / "fob_spu").is_dir():
        raise SystemExit("ERRO: rode prepare_spu_elf.py antes (out/port/spu/fob_spu ausente).")

    with tempfile.TemporaryDirectory(prefix="fob-engine-jm-", dir=root / "out") as td:
        stage = Path(td)
        reg = stage / "jobmods_register.c"
        cmd = [sys.executable, str(tool), "--engine-elf", str(elf), "--out", str(stage),
               "--register", str(reg), "--symbol-prefix", "fobjm"]
        env = dict(os.environ)
        env.setdefault("LBP_JOBMOD_EXTRA_FUNCS", DEFAULT_EXTRA_FUNCS)
        print("+", " ".join(cmd), " (LBP_JOBMOD_EXTRA_FUNCS=%s)" % env["LBP_JOBMOD_EXTRA_FUNCS"], flush=True)
        subprocess.run(cmd, check=True, env=env)
        modules = sorted(p for p in stage.glob("jobmod_*") if p.is_dir())
        if not modules or not reg.is_file():
            raise SystemExit("ERRO: nenhum módulo liftado.")
        for module in modules:
            dst = spu_dir / module.name
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(module, dst)
        shutil.copyfile(reg, spu_dir / "jobmods_engine_register.c")
    print(f"\nSUCESSO: {len(modules)} módulos de job liftados em {spu_dir}")
    print("PRÓXIMO: inclua jobmods_engine_register.c no foreach de out/port/CMakeLists.txt,"
          " rode cmake e recompile.")


if __name__ == "__main__":
    main()
