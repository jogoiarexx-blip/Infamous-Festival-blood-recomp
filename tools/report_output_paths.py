"""Keep diagnostic reports separate from their input files."""
from pathlib import Path
from typing import Iterable


def check_report_destination(output: Path | None, inputs: Iterable[Path]) -> None:
    if output is None:
        return
    destination = output.resolve()
    for source in inputs:
        # resolve handles relative paths and symlinks; samefile also covers
        # hard links, whose path names differ while sharing the input's bytes.
        if destination == source.resolve() or (
                destination.exists() and source.exists()
                and destination.samefile(source)):
            raise ValueError("O relatÃ³rio JSON nÃ£o pode sobrescrever um arquivo de entrada")
