#!/usr/bin/env python3
"""Opt-in A/B test of upstream ps3recomp PR #766 (SPURS LFQueue push).

Downloads the TWO-COMMIT pinned patch into local out/ (gitignored). Never
uploads game files, does not touch generated SPU/PPU code and does not build
automatically. Requires a Git checkout and clean target files in ../ps3recomp.

  py tools/try_lfqueue_pr766.py --apply
  py tools/try_lfqueue_pr766.py --status
  py tools/try_lfqueue_pr766.py --revert

WARNING: PR #766 is open and unmerged. Its queue wake-up heuristic may be
incorrect for this title. Test it; do not assume correctness.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

PR_URL = "https://github.com/sp00nznet/ps3recomp/pull/766"
BASE = "de4f090328ea08bef6b2f15caec0b85e343a7ece"
HEAD = "b2d050a06dbb297e595271f95364db2e0dbe68f9"
PINNED_PATCH_URL = (
    "https://github.com/DriifterSelf/ps3recomp/compare/"
    + BASE + "..." + HEAD + ".patch"
)
FILES = (
    "libs/spurs/cellSpurs.c",
    "libs/spurs/cellSpurs.h",
    "tools/nid_database.py",
)


def fail(why: str) -> None:
    raise SystemExit("ERRO: " + why)


def git(sdk: Path, *args: str, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(sdk), *args],
        check=check, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def ensure_patch(path: Path) -> bytes:
    if path.exists():
        raw = path.read_bytes()
        print("Patch previamente baixado:", path)
    else:
        try:
            req = urllib.request.Request(
                PINNED_PATCH_URL,
                headers={"User-Agent": "FoB-PR766-local-experiment/1.0"},
            )
            with urllib.request.urlopen(req, timeout=40) as res:
                raw = res.read(120_000)
        except (OSError, urllib.error.URLError) as exc:
            fail("nao foi possivel baixar o PR fixado: " + str(exc))
        path.parent.mkdir(parents=True, exist_ok=True)
    if len(raw) < 1000 or len(raw) >= 120_000:
        fail(f"tamanho suspeito do patch: {len(raw)} bytes")
    try:
        body = raw.decode("utf-8")
    except UnicodeDecodeError:
        fail("o patch nao e texto UTF-8")
    changes = re.findall(
        r"^diff --git a/([^\n ]+) b/([^\n ]+)\s*$",
        body, flags=re.MULTILINE,
    )
    if not changes or {a for a, b in changes} != set(FILES) or any(a != b for a, b in changes):
        fail("o patch nao modifica somente os tres arquivos do PR #766; abortando.")
    if "_cellSpursLFQueuePushBody" not in body or "0x08" not in body:
        fail("assinatura/indices de LFQueue esperados nao aparecem no patch.")
    if not path.exists():
        path.write_bytes(raw)
    print("PR:", PR_URL)
    print("Revisao fixada:", HEAD)
    print("SHA256 do patch:", hashlib.sha256(raw).hexdigest())
    print("Arquivos permitidos:", ", ".join(FILES))
    return raw


def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__)
    mode = cli.add_mutually_exclusive_group(required=True)
    mode.add_argument("--apply", action="store_true",
                      help="Apply the pinned, experimental patch to ../ps3recomp")
    mode.add_argument("--revert", action="store_true",
                      help="Undo only the exact pinned patch when possible")
    mode.add_argument("--status", action="store_true",
                      help="Show whether the patch applies / is already present")
    args = cli.parse_args()

    root = Path(__file__).resolve().parent.parent
    sdk = root.parent / "ps3recomp"
    for name in FILES:
        if not (sdk / name).is_file():
            fail("SDK ausente ou incompleto: " + str(sdk / name))
    if not shutil.which("git"):
        fail("Git nao encontrado no PATH. Nenhum arquivo foi alterado.")
    if git(sdk, "rev-parse", "--show-toplevel").returncode:
        fail("o SDK ../ps3recomp precisa ser um checkout Git para reversao segura.")
    patchfile = root / "out" / "diagnostics" / "pr766-fixed-head.patch"
    ensure_patch(patchfile)

    if args.status:
        if git(sdk, "apply", "-R", "--check", str(patchfile)).returncode == 0:
            print("STATUS: patch PR #766 JA ESTA APLICADO.")
        elif git(sdk, "apply", "--check", str(patchfile)).returncode == 0:
            print("STATUS: patch PR #766 disponivel para aplicar.")
        else:
            print("STATUS: SDK divergiu; nao e seguro aplicar nem reverter automaticamente.")
        return

    reverse = args.revert
    if args.apply:
        dirty = git(sdk, "status", "--porcelain", "--", *FILES)
        if dirty.returncode:
            fail(dirty.stderr.strip())
        if dirty.stdout.strip():
            if git(sdk, "apply", "-R", "--check", str(patchfile)).returncode == 0:
                print("STATUS: o patch ja esta aplicado. Nao repita.")
                return
            fail("existem alteracoes locais nos tres arquivos; nao vou sobrescrever:\n"
                 + dirty.stdout)

    cmd = ["apply"]
    if reverse:
        cmd.append("-R")
    cmd += ["--check", str(patchfile)]
    result = git(sdk, *cmd)
    if result.returncode:
        fail(("o patch nao pode ser revertido" if reverse
              else "o patch nao e compativel com seu SDK")
             + ":\n" + (result.stderr or result.stdout))

    if args.apply:
        backup = root / "out" / "diagnostics" / "pr766-backup"
        if backup.exists():
            fail("backup da revisao anterior ja existe; nao vou substituir.")
        for name in FILES:
            target = backup / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(sdk / name, target)
        print("Backup de fontes preservado em:", backup)

    action = ["apply"]
    if reverse:
        action.append("-R")
    action.append(str(patchfile))
    result = git(sdk, *action)
    if result.returncode:
        fail("git apply retornou erro; confira o SDK:\n"
             + (result.stderr or result.stdout))
    print("SUCESSO: PR #766", "revertido." if reverse else "aplicado como TESTE.")
    print("Nenhum arquivo do jogo foi publicado, nenhum executavel foi recompilado.")
    print('PROXIMO: cmake -S "out\\port" -B "out\\build" -DPORT_ENABLE_SPU=ON "-DPORT_SPU_INPUTS:STRING="')
    print('DEPOIS:  cmake --build "out\\build" --parallel 1')
    if args.apply:
        print("IMPORTANTE: PR nao revisado pelo upstream; compare o novo log.")
        print("REVERSAO: py tools/try_lfqueue_pr766.py --revert")


if __name__ == "__main__":
    main()
