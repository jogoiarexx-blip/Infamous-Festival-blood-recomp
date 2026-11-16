#!/usr/bin/env python3
"""Safely test upstream ps3recomp PR #766 against a Windows SDK folder.

Supports both a plain extracted ZIP and a Git checkout at ../ps3recomp.
Applies the two-commit pinned candidate via git apply (Git CLI required, but a
Git *repository* is not). Also registers its NID in this game's existing HLE
table; rebuilding the runtime alone would leave the unresolved NID unchanged.

  py tools/try_lfqueue_pr766.py --status
  py tools/try_lfqueue_pr766.py --apply
  py tools/try_lfqueue_pr766.py --revert

Backups and pinned patch live under out/ (gitignored). This experimental patch
is UNMERGED and may not match the specific game's LFQueue protocol. It does NOT
copy, publish, modify, or upload any original PlayStation game assets.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

PR_URL = "https://github.com/sp00nznet/ps3recomp/pull/766"
BASE = "de4f090328ea08bef6b2f15caec0b85e343a7ece"
HEAD = "b2d050a06dbb297e595271f95364db2e0dbe68f9"
PATCH_URL = ("https://github.com/DriifterSelf/ps3recomp/compare/"
             + BASE + "..." + HEAD + ".patch")
SDK_FILES = (
    "libs/spurs/cellSpurs.c",
    "libs/spurs/cellSpurs.h",
    "tools/nid_database.py",
)
TABLE_REL = "out/recompiled/ppu_hle_nids.cpp"
NID = "0x8A85674D"
FUNC = "_cellSpursLFQueuePushBody"


def fail(reason: str) -> None:
    raise SystemExit("ERRO: " + reason)


def git(sdk: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(sdk), *args], check=False,
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )


def ensure_patch(path: Path) -> bytes:
    if path.is_file():
        raw = path.read_bytes()
    else:
        try:
            request = urllib.request.Request(
                PATCH_URL,
                headers={"User-Agent": "Festival-of-Blood-PR766-test/2.0"},
            )
            with urllib.request.urlopen(request, timeout=40) as response:
                raw = response.read(120_000)
        except (OSError, urllib.error.URLError) as exc:
            fail("nao foi possivel baixar a correcao fixada: " + str(exc))

    if not (1000 < len(raw) < 120_000):
        fail(f"patch com tamanho inesperado: {len(raw)} bytes")
    try:
        body = raw.decode("utf-8")
    except UnicodeDecodeError:
        fail("o patch nao e UTF-8")

    changes = re.findall(
        r"^diff --git a/([^\n ]+) b/([^\n ]+)\s*$",
        body, re.MULTILINE,
    )
    if (not changes or {a for a, b in changes} != set(SDK_FILES)
            or any(a != b for a, b in changes)):
        fail("o patch modifica caminhos nao esperados; nao foi aplicado")
    if FUNC not in body or "0x08" not in body:
        fail("o patch nao corresponde ao PR #766 identificado")

    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    print("PATCH PINNED:", HEAD)
    print("SHA256:", hashlib.sha256(raw).hexdigest())
    print("PR:", PR_URL)
    return raw


def install_hle_registration(text: str) -> str:
    """Only add the single missing handler; keep all existing NID mappings."""
    if NID.lower() in text.lower():
        fail("a tabela HLE ja inclui NID 0x8A85674D; nao vou duplicar")
    if "ps3_hle_register(" not in text:
        fail("a tabela HLE nao tem ps3_hle_register; formato nao reconhecido")
    match = re.search(
        r'extern\s+"C"\s+void\s+ppu_hle_register_all\s*\(\s*void\s*\)\s*\{',
        text,
    )
    if match is None:
        fail("funcao ppu_hle_register_all nao identificada na tabela HLE")
    declaration = f'extern "C" void {FUNC}(void);\n'
    registration = (f'\n    ps3_hle_register({NID}u, "{FUNC}", '
                    f'(void*){FUNC});')
    at = match.start()
    replaced = text[:at] + declaration + text[at:match.end()] + registration
    replaced += text[match.end():]
    if replaced.count(FUNC) != 3:
        fail("registro HLE nao esta na forma esperada, abortando")
    return replaced


def check_git_clean_if_repo(sdk: Path) -> None:
    probe = git(sdk, "rev-parse", "--show-toplevel")
    if probe.returncode:
        print("SDK extraido de ZIP (sem .git): modo seguro com git apply e backup.")
        return
    status = git(sdk, "status", "--porcelain", "--", *SDK_FILES)
    if status.returncode:
        fail("nao foi possivel examinar os arquivos do checkout Git")
    if status.stdout.strip():
        fail("SDK com modificacoes locais nos tres arquivos do patch:\n"
             + status.stdout.strip())
    print("SDK Git detectado: arquivos-alvo limpos.")


def patch_check(sdk: Path, patch: Path, reverse: bool = False) -> bool:
    args = ["apply"]
    if reverse:
        args.append("-R")
    args.extend(["--check", str(patch)])
    return git(sdk, *args).returncode == 0


def patch_execute(sdk: Path, patch: Path, reverse: bool = False) -> None:
    args = ["apply"]
    if reverse:
        args.append("-R")
    args.append(str(patch))
    result = git(sdk, *args)
    if result.returncode:
        fail("git apply falhou:\n" + (result.stderr or result.stdout))


def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__)
    options = cli.add_mutually_exclusive_group(required=True)
    options.add_argument("--apply", action="store_true")
    options.add_argument("--revert", action="store_true")
    options.add_argument("--status", action="store_true")
    args = cli.parse_args()

    root = Path(__file__).resolve().parent.parent
    sdk = root.parent / "ps3recomp"
    table = root / TABLE_REL
    patch = root / "out/diagnostics/pr766-fixed-head.patch"
    backup = root / "out/diagnostics/pr766-backup"

    for name in SDK_FILES:
        if not (sdk / name).is_file():
            fail("arquivo do SDK nao encontrado: " + str(sdk / name))
    if not table.is_file():
        fail("tabela HLE nao encontrada: " + str(table))
    if shutil.which("git") is None:
        fail("Git nao instalado no PATH; necessario para aplicar o patch com seguranca")
    ensure_patch(patch)

    sdk_is_patched = patch_check(sdk, patch, reverse=True)
    can_apply = patch_check(sdk, patch, reverse=False)
    current_table = table.read_text(encoding="utf-8")
    table_has_nid = NID.lower() in current_table.lower()

    if args.status:
        print("SDK PATCH:", "JA APLICADO" if sdk_is_patched else
              "PODE APLICAR" if can_apply else "INCOMPATIVEL")
        print("HLE NID:", "REGISTRADO" if table_has_nid else "AUSENTE")
        print("BACKUP:", "EXISTE" if backup.is_dir() else "NAO EXISTE")
        return

    if args.apply:
        if sdk_is_patched:
            if table_has_nid:
                print("STATUS: PR #766 ja aplicado e NID registrado.")
                return
            fail("SDK parece ja estar modificado, mas NID nao foi registrado. "
                 "Envie este erro; nao vou adivinhar a versao.")
        if not can_apply:
            fail("o patch nao combina com o SDK atual. NADA FOI ALTERADO. "
                 "Envie a mensagem para preparar um ajuste compativel.")
        if table_has_nid:
            fail("o NID ja estava registrado antes do patch; revisar manualmente")
        if backup.exists():
            fail("backup anterior ja existe; nao vou substituir")
        # Check the complete HLE edit before touching any SDK source.
        patched_table = install_hle_registration(current_table)
        check_git_clean_if_repo(sdk)

        for name in (*SDK_FILES, TABLE_REL):
            original = (sdk / name) if name in SDK_FILES else table
            target = backup / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, target)
        print("BACKUP:", backup)

        patch_execute(sdk, patch)
        try:
            table.write_text(patched_table, encoding="utf-8", newline="")
        except Exception as exc:
            # If writing the second stage fails, roll back the SDK patch.
            if patch_check(sdk, patch, reverse=True):
                patch_execute(sdk, patch, reverse=True)
            fail("erro ao registrar o NID; alteracao SDK revertida: " + str(exc))

        if FUNC not in (sdk / "libs/spurs/cellSpurs.c").read_text(
                encoding="utf-8", errors="replace"):
            fail("implementacao nao encontrada apos aplicar. Nao compile.")
        print("SUCESSO: correcao experimental PR #766 aplicada.")
        print("NID 0x8A85674D registrado na tabela HLE existente.")
        print("A correcao nao foi incorporada ao upstream e pode ter falhas.")
        print("NENHUM arquivo de jogo foi enviado ou alterado.")
        print('PROXIMO: cmake -S "out\\port" -B "out\\build" -DPORT_ENABLE_SPU=ON "-DPORT_SPU_INPUTS:STRING="')
        print('DEPOIS: cmake --build "out\\build" --parallel 1')
        print("REVERSAO: py tools/try_lfqueue_pr766.py --revert")
        return

    # Revert only a state that matches the exact backup + our one-line HLE edit.
    if not backup.is_dir():
        fail("backup deste script nao existe; reversao automatica insegura")
    saved_table = backup / TABLE_REL
    if not saved_table.is_file():
        fail("backup da tabela HLE ausente")
    saved_text = saved_table.read_text(encoding="utf-8")
    if current_table != install_hle_registration(saved_text):
        fail("tabela HLE foi alterada apos o teste; nao vou sobrescrever")
    if not sdk_is_patched:
        fail("patch no SDK nao corresponde ao aplicado; nao vou reverter cegamente")

    patch_execute(sdk, patch, reverse=True)
    shutil.copy2(saved_table, table)
    print("SUCESSO: SDK e registro HLE restaurados.")
    print("Backup preservado:", backup)
    print("Para reconstruir a versao anterior: cmake --build out\\build --parallel 1")


if __name__ == "__main__":
    main()
