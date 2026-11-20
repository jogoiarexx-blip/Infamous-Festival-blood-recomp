#!/usr/bin/env python3
"""Exercise the SDK's actual jobchain walker with synthetic job publishers.

The worker stand-in emits an event only for its publisher descriptor. This
isolates walker ordering from SPU instruction execution and requires no game
files. The actual C function bodies are extracted from the selected SDK.
"""
from __future__ import annotations
import argparse
import os
import re
from pathlib import Path
import shutil
import subprocess


def extract_function(source: str, name: str) -> str:
    match = re.search(r"^static [^\n]*\b" + re.escape(name) + r"\(", source, re.MULTILINE)
    if match is None:
        raise ValueError(f"SDK function not found: {name}")
    start = match.start()
    return source[start:source.index("\n}", start) + 2]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", type=Path, required=True)
    parser.add_argument("--cc", default="gcc")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    source = (args.sdk / "libs/spurs/cellSpurs.c").read_text(encoding="utf-8")
    functions = []
    if "static void jc_signal_done(" in source:
        functions.append(extract_function(source, "jc_signal_done"))
    functions.append(extract_function(source, "jc_execute"))
    functions.append(extract_function(source, "jc_thread"))
    template = (Path(__file__).parent / "tests/jobchain_event_ordering.c").read_text(encoding="utf-8")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    generated = args.output_dir / "jobchain_event_ordering.c"
    generated.write_text(template.replace("@RUNTIME_WALKER@", "\n".join(functions)), encoding="utf-8")
    binary = args.output_dir / ("jobchain_event_ordering.exe" if os.name == "nt" else "jobchain_event_ordering")
    compiler = shutil.which(args.cc) or args.cc
    subprocess.run([compiler, "-std=c11", "-O2", str(generated), "-o", str(binary)], check=True)
    subprocess.run([str(binary.resolve())], check=True, timeout=10)


if __name__ == "__main__":
    main()
