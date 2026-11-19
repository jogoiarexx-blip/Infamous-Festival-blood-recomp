#!/usr/bin/env python3
"""Run real SPU dispatch regressions using synthetic guest bytes.

Requires a C compiler with GNU C17 and pthreads (e.g. MinGW GCC on Windows).
No generated game source or game assets are needed.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

SOURCES = ["spu_channels", "spu_drain", "spu_lockstep", "spu_coherency",
           "spu_workload", "spurs_policy", "spurs_job", "spu_tsp_weak",
           "spu_vm_pagemap", "spurs_policy_blob_weak", "spu_interp"]

def run(args, output):
    sdk = args.sdk.resolve()
    spu = sdk / "runtime/spu"
    compiler = shutil.which(args.cc)
    if not compiler:
        raise SystemExit("C compiler not found: " + args.cc)
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("SPU_", "SPURS_", "YDKJ_", "LBP_", "GH3_"))}
    env["PATH"] = str(Path(compiler).parent) + os.pathsep + env.get("PATH", "")
    binary = output / ("test.exe" if os.name == "nt" else "test")
    source = Path(__file__).parent / "tests/spu_policy_image_collision.c"
    command = [compiler, "-std=gnu17", "-O1", "-fno-strict-aliasing", "-fwrapv",
               "-I" + str(sdk / "include"), "-I" + str(spu),
               "-I" + str(sdk / "runtime/platform"), str(source),
               *[str(spu / (name + ".c")) for name in SOURCES],
               str(sdk / "runtime/platform/win32_compat.c"),
               "-pthread", "-lm", "-o", str(binary)]
    build = subprocess.run(command, capture_output=True, text=True, env=env, timeout=120)
    (output / "build.log").write_text(build.stdout + build.stderr, encoding="utf-8")
    if build.returncode:
        raise SystemExit("Compilation failed; see " + str(output / "build.log"))
    results = []
    for cache in ("0", "1", "shadow"):
        for case in ("unbounded", "bounded", "owned", "rejected"):
            result = subprocess.run([str(binary), case], capture_output=True, text=True,
                                    env=dict(env, SPU_DISPATCH_CACHE=cache), timeout=10)
            name = cache + "-" + case
            (output / (name + ".log")).write_text(result.stdout + result.stderr, encoding="utf-8")
            results.append({"cache": cache, "case": case, "returncode": result.returncode})
            print(name + ": " + result.stdout.strip(), flush=True)
    (output / "results.json").write_text(json.dumps({"build": command, "runs": results}, indent=2) + "\n", encoding="utf-8")
    if any(item["returncode"] for item in results):
        raise SystemExit(1)
    print("PASS: 12 real-runtime dispatch cases")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", type=Path, required=True)
    parser.add_argument("--cc", default=os.environ.get("CC", "cc"))
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        run(args, args.output_dir.resolve())
    else:
        with tempfile.TemporaryDirectory(prefix="spu-policy-collision-") as temporary:
            run(args, Path(temporary))

if __name__ == "__main__":
    main()
