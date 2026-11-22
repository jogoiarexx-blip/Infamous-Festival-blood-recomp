#!/usr/bin/env python3
"""Test the actual D3D12 resource/fence helpers with synthetic CPU objects.

No Windows SDK, GPU, game files, or downloads are required. This checks the
runtime's ownership and error branches, not real driver scheduling.
"""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess


def extract_function(source: str, name: str) -> str:
    match = re.search(r"^static void " + re.escape(name) + r"\(", source, re.MULTILINE)
    if match is None:
        raise ValueError(f"Required SDK helper missing: {name}; apply runtime patch 0013")
    return source[match.start():source.index("\n}", match.start()) + 2]


def generate_fixture(source: str) -> str:
    names = ("gpu_fence_sync_failed", "wait_for_fence_value", "wait_for_gpu")
    parts = [extract_function(source, name) for name in names]
    start = source.index("#define GRAVE_INITIAL")
    possible_ends = [source.find(marker, start) for marker in (
        "static void dred_report(void)\n{", "static void move_to_next_frame(void)")]
    end = min(index for index in possible_ends if index >= 0)
    parts.append(source[start:end])
    parts.append(extract_function(source, "move_to_next_frame"))
    start = source.index("void rsx_d3d12_backend_shutdown(void)")
    start = source.index("{", start) + 1
    end = source.index("    /* Release D3D12 resources */", start)
    parts.append("static void shutdown_retire_only(void){" + source[start:end] + "}")
    template = (Path(__file__).parent / "tests/gpu_resource_retirement.c").read_text(encoding="utf-8")
    return template.replace("/* INSERT_RUNTIME_IMPLEMENTATION */", "\n".join(parts))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", type=Path, required=True)
    parser.add_argument("--cc", default="gcc")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    compiler = shutil.which(args.cc)
    if compiler is None:
        raise SystemExit("Existing C compiler not found: " + args.cc)
    source = (args.sdk / "libs/video/rsx_d3d12_backend.c").read_text(encoding="utf-8")
    fixture = generate_fixture(source)
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    code = output / "gpu_resource_retirement.c"
    code.write_text(fixture, encoding="utf-8")
    binary = output / "gpu_resource_retirement.exe"
    env = dict(os.environ)
    env["PATH"] = str(Path(compiler).parent) + os.pathsep + env.get("PATH", "")
    subprocess.run([compiler, "-std=c11", "-O0", str(code), "-o", str(binary)], check=True, timeout=60, env=env)
    result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10, env=env)
    (output / "result.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    print(result.stdout, end="")
    if result.returncode:
        print(result.stderr)
        raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
