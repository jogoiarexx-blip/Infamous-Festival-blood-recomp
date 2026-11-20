#!/usr/bin/env python3
"""Compare five generated kernels with pure interpretation on private inputs.

Requires prepare_data_modules.py outputs and locally captured entry snapshots.
Does not create or download snapshots or game code. The reference uses the
SDK's instruction helpers: this checks translation/flow equivalence, not the
correctness of those helpers against PS3 hardware.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from test_spu_policy_image_collision import SOURCES



def private_output_dir(path: Path) -> Path:
    root = Path(__file__).resolve().parent.parent
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve() / "out"):
        raise ValueError("Replay binaries contain game code and must stay under ignored out/")
    return resolved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", type=Path, required=True)
    parser.add_argument("--spu-dir", type=Path, required=True)
    parser.add_argument("--snapshots", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cc", default="gcc")
    args = parser.parse_args()
    output = private_output_dir(args.output_dir)
    if sys.byteorder != "little":
        raise SystemExit("Snapshots require a little-endian host")
    for index in range(5):
        snapshot = args.snapshots / f"{index}.bin"
        if snapshot.stat().st_size != 128 * 16 + 0x40000:
            raise SystemExit(f"Invalid entry snapshot size: {snapshot}")
    modules = sorted(args.spu_dir.glob("datamod_*/spu_recomp.c"))
    if len(modules) != 5:
        raise SystemExit("Expected exactly the five generated data modules")
    compiler = shutil.which(args.cc)
    if compiler is None:
        raise SystemExit("Existing C compiler not found: " + args.cc)
    sdk = args.sdk.resolve()
    spu = sdk / "runtime/spu"
    output.mkdir(parents=True, exist_ok=True)
    binary = output / ("data_module_replay.exe" if os.name == "nt" else "data_module_replay")
    registry = args.spu_dir / "datamods_register.c"
    if not registry.is_file():
        raise SystemExit("Verified data-module registration source missing")
    source = Path(__file__).parent / "tests/data_module_replay.c"
    command = [compiler, "-std=gnu17", "-O1", "-fno-strict-aliasing", "-fwrapv",
               "-ffp-contract=off", "-msse4.1", "-I" + str(sdk / "include"),
               "-I" + str(spu), "-I" + str(sdk / "runtime/platform"), str(source),
               *map(str, modules), str(registry),
               *[str(spu / (name + ".c")) for name in SOURCES],
               str(sdk / "runtime/platform/win32_compat.c"), "-pthread", "-lm", "-o", str(binary)]
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("SPU_", "SPURS_", "YDKJ_", "LBP_", "GH3_"))}
    env["PATH"] = str(Path(compiler).parent) + os.pathsep + env.get("PATH", "")
    build = subprocess.run(command, capture_output=True, text=True, env=env, timeout=120)
    (output / "build.log").write_text(build.stdout + build.stderr, encoding="utf-8")
    if build.returncode:
        raise SystemExit("Build failed; see " + str(output / "build.log"))
    result = subprocess.run([str(binary), str(args.snapshots.resolve())], env=env,
                            capture_output=True, text=True, timeout=120)
    (output / "replay.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    (output / "result.json").write_text(json.dumps({"build": command,
        "returncode": result.returncode, "cases": 5}, indent=2), encoding="utf-8")
    print(result.stdout, end="")
    if result.returncode:
        print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode)
    print("PASS: 5 captured inputs, all registers, LS bytes and return PCs match")


if __name__ == "__main__":
    main()
