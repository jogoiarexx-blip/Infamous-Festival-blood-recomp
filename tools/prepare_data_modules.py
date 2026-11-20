#!/usr/bin/env python3
"""Prepare five verified NPUA80657 DA7ABA5E kernels using the existing SDK.

Run from the project root: py tools/prepare_data_modules.py
Use --audit-only to validate without writing. Outputs stay under ignored out/.
No tools, dependencies, or game files are downloaded.
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile

LOAD_LSA = 0x6C00


@dataclass(frozen=True)
class ModuleSpec:
    offset: int
    size: int
    sha256: str
    ea: int
    image: int


MODULES = (
    ModuleSpec(0x8B5500, 784, "01af2856ddf625423673c629a640a6fb89879652ab2251f2b5a1e985371c5cb0", 0x8C5500, 300),
    ModuleSpec(0x8B5880, 2960, "bd6aa8b296bc8d99957ef3ab51c2d272cf9410ede470f87a0f2d7238e4d8aa85", 0x8C5880, 301),
    ModuleSpec(0x8B6480, 1936, "7f3b3e64d1939558e42cdbdb174139d68accd7af3b81de1f55e2648ac2723927", 0x8C6480, 302),
    ModuleSpec(0x8B6C80, 2960, "216c4062e68703b78949453cebf91243af2e249e6b2073f146d195e615221692", 0x8C6C80, 303),
    ModuleSpec(0x8B7880, 5392, "cc7142e974454a56efdf4526c1358ad42ee277fd7f0618d731b97529c5a219fd", 0x8C7880, 304),
)


def mapped_address(elf: bytes, offset: int, size: int) -> int:
    if len(elf) < 64 or elf[:6] != b"\x7fELF\x02\x02":
        raise ValueError("Expected a big-endian ELF64")
    phoff = struct.unpack_from(">Q", elf, 32)[0]
    entsize, count = struct.unpack_from(">HH", elf, 54)
    if entsize != 56 or not count or phoff + entsize * count > len(elf):
        raise ValueError("Invalid ELF program header table")
    if offset < 0 or size <= 0 or offset + size > len(elf):
        raise ValueError("Module extent outside file")
    matches = []
    for index in range(count):
        kind, _, fileoff, vaddr, _, filesz, memsz, _ = struct.unpack_from(
            ">IIQQQQQQ", elf, phoff + index * entsize)
        if kind != 1:
            continue
        if filesz > memsz:
            raise ValueError("PT_LOAD file size exceeds memory size")
        if fileoff + filesz > len(elf):
            raise ValueError("Truncated PT_LOAD segment")
        if fileoff <= offset and offset + size <= fileoff + filesz:
            matches.append(vaddr + offset - fileoff)
    if len(matches) != 1:
        raise ValueError("Module needs one unambiguous file-backed PT_LOAD")
    return matches[0]


def validate_module(elf: bytes, spec: ModuleSpec) -> dict:
    if mapped_address(elf, spec.offset, spec.size) != spec.ea:
        raise ValueError("Guest EA does not match the verified edition")
    raw = elf[spec.offset:spec.offset + spec.size]
    if hashlib.sha256(raw).hexdigest() != spec.sha256:
        raise ValueError("Module fingerprint mismatch")
    if len(raw) < 0x30:
        raise ValueError("Truncated module header")
    prefix = struct.unpack_from(">4I", raw)
    magic, entry, image_size = struct.unpack_from(">III", raw, 0x10)
    code_end = struct.unpack_from(">I", raw, 0x20)[0]
    if (not all(word >> 24 in (0x42, 0x43) for word in prefix)
            or magic != 0xDA7ABA5E or entry != 0x30 or image_size != spec.size
            or code_end <= entry or code_end > image_size or code_end % 4):
        raise ValueError("Invalid DA7ABA5E module header")
    return {"spec": spec, "raw": raw, "entry": entry, "code_end": code_end,
            "name": f"datamod_{spec.offset:08X}"}


def registration_source(modules: list[dict]) -> str:
    lines = ["/* GENERATED from the user's ELF; game-derived, DO NOT COMMIT. */",
             '#include "spu_overlay_residency.h"', '#include <stdio.h>',
             "extern void spu_begin_image(int);"]
    for index, module in enumerate(modules):
        code = module["raw"][module["entry"]:module["code_end"]]
        lines.append(f"extern void fobdata{index}_spu_recomp_register(void);")
        lines.append(f"static const unsigned char code_{index}[{len(code)}] = {{")
        for at in range(0, len(code), 16):
            lines.append("    " + ",".join(f"0x{byte:02X}" for byte in code[at:at+16]) + ",")
        lines.append("};")
    lines.append("__attribute__((constructor)) static void fob_datamods_ctor(void) {")
    for index, module in enumerate(modules):
        spec = module["spec"]
        lines.extend([
            f"    {{ const spu_overlay_code_segment seg = {{0x{LOAD_LSA + module['entry']:X}u, sizeof code_{index}, code_{index}}};",
            f"      spu_begin_image({spec.image}); fobdata{index}_spu_recomp_register();",
            f"      if (!spu_overlay_register_verified_region(0x{spec.ea:08X}u, 0x{LOAD_LSA:X}u, 0x{module['code_end']:X}u, {spec.image}, &seg, 1))",
            f'          fprintf(stderr, "[datamod] registration failed: image {spec.image}\\n"); }}',
        ])
    lines.extend(["    spu_begin_image(0);", "}", ""])
    return "\n".join(lines)


def resolve_elf_path(root: Path, specified: Path | None = None) -> Path:
    """Find the local decrypted EBOOT without downloading or copying it."""
    if specified is not None:
        if not specified.is_file():
            raise FileNotFoundError(f"EBOOT not found: {specified}")
        return specified
    candidates = tuple(
        root / folder / name
        for folder in ("private/game", "private/PS3_GAME/USRDIR")
        for name in ("EBOOT.elf", "EBOOT.ELF")
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "Decrypted EBOOT not found. Put your own EBOOT.elf under "
        "'private/game/' or provide an explicit path with --elf."
    )


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, help="Local decrypted EBOOT.elf (default: auto-detect under private/)")
    parser.add_argument("--sdk", type=Path, default=root.parent / "ps3recomp")
    parser.add_argument("--port", type=Path, default=root / "out/port")
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()
    elf_data = resolve_elf_path(root, args.elf).read_bytes()
    modules = [validate_module(elf_data, spec) for spec in MODULES]
    metadata = [{"name": m["name"], "guest_ea": hex(m["spec"].ea),
                 "sha256": m["spec"].sha256, "image": m["spec"].image,
                 "entry_lsa": hex(LOAD_LSA + m["entry"]),
                 "code_end_lsa": hex(LOAD_LSA + m["code_end"])} for m in modules]
    if args.audit_only:
        print(json.dumps(metadata, indent=2))
        return
    port = args.port.resolve()
    if not port.is_relative_to(root.resolve() / "out"):
        raise ValueError("Generated game code must stay inside the project's ignored out/")
    cmake = port / "CMakeLists.txt"
    original = cmake.read_text(encoding="utf-8")
    match = re.search(r"foreach\(gen IN ITEMS\s+([^)]+)\)", original)
    if match is None:
        raise ValueError("Generated port CMake registration list not found")
    cmake_text = original
    if "datamods_register.c" not in match[1].split():
        cmake_text = (original[:match.end(1)] + " datamods_register.c"
                      + original[match.end(1):])
    sdk_tools = args.sdk.resolve() / "tools"
    for tool in ("wrap_spu_elf.py", "spu_lifter.py"):
        if not (sdk_tools / tool).is_file():
            raise ValueError(f"Existing SDK tool missing: {tool}")
    with tempfile.TemporaryDirectory(prefix="fob-data-", dir=root / "out") as temporary:
        stage = Path(temporary)
        for index, module in enumerate(modules):
            raw = stage / (module["name"] + ".bin")
            wrapped = raw.with_suffix(".elf")
            report = raw.with_suffix(".json")
            raw.write_bytes(module["raw"][module["entry"]:])
            subprocess.run([sys.executable, str(sdk_tools / "wrap_spu_elf.py"), str(raw),
                            "--base", hex(LOAD_LSA + module["entry"]),
                            "--entry", hex(LOAD_LSA + module["entry"]), "--out", str(wrapped)], check=True)
            subprocess.run([sys.executable, str(sdk_tools / "spu_lifter.py"),
                            "--auto-functions", str(wrapped), "--base", hex(LOAD_LSA + module["entry"]),
                            "--code-end", hex(LOAD_LSA + module["code_end"]),
                            "--symbol-prefix", f"fobdata{index}_", "--output", str(stage / module["name"]),
                            "--report", str(report)], check=True)
            diagnostics = json.loads(report.read_text(encoding="utf-8"))
            starts = {start for start, _ in diagnostics.get("functions", [])}
            targets = set(diagnostics.get("call_targets", [])) | set(diagnostics.get("branch_targets", []))
            if diagnostics.get("unsupported") or targets - starts or LOAD_LSA + module["entry"] not in starts:
                raise ValueError(f"Incomplete lift: {module['name']}")
        output = port / "spu"
        output.mkdir(parents=True, exist_ok=True)
        for module in modules:
            shutil.copytree(stage / module["name"], output / module["name"], dirs_exist_ok=True)
        (output / "datamods_register.c").write_text(registration_source(modules), encoding="utf-8", newline="\n")
        (output / "datamods_manifest.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        if cmake_text != original:
            cmake.write_text(cmake_text, encoding="utf-8")
    print("Prepared 5 static kernels and CMake registration; reconfigure and build the port.")


if __name__ == "__main__":
    main()
