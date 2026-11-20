#!/usr/bin/env python3
"""Compile the SDK's actual FP snapshot helper and decompiler against synthetic RAM."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sdk', type=Path, required=True)
    p.add_argument('--cc', default='gcc')
    p.add_argument('--output-dir', type=Path, required=True)
    p.add_argument('--legacy-control', action='store_true', help='Model the former address-only deferred read; expected to fail')
    a = p.parse_args()
    sdk = a.sdk.resolve()
    source = (sdk / 'libs/video/rsx_d3d12_backend.c').read_text(encoding='utf-8')
    if a.legacy_control:
        helper = 'static void fp_record_program(D3D12DrawRecord* dr) { dr->fp_ucode_ea = cellGcmResolveLocated((dr->fp_addr & 3u)==1, dr->fp_addr & ~3u); dr->fp_ucode_size=4096; }'
    else:
        anchor = 'static void fp_record_program(D3D12DrawRecord* dr)'
        if anchor not in source:
            raise SystemExit('FAIL: backend records only an FP address; immutable program snapshot is missing')
        start = source.index(anchor)
        helper = source[start:source.index('\n}', start) + 2]
        pso = source[source.index('static ID3D12PipelineState* vp_get_fp_pso('):]
        pso = pso[:pso.index('\n}') + 2]
        if 'vm_base +' in pso or 'cellGcmResolveLocated(' in pso:
            raise SystemExit('FAIL: pipeline preparation still reads mutable guest shader memory')
        if 'fp_record_program(dr);' not in source or 'dr->fp_ucode, dr->fp_ucode_size' not in source:
            raise SystemExit('FAIL: snapshot is not wired into record/preparation')
    template = (Path(__file__).parent / 'tests/fp_program_lifetime.c').read_text(encoding='utf-8')
    code = template.replace('/* ACTUAL_SNAPSHOT_HELPER */', helper)
    output = a.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    fixture = output / 'fp_program_lifetime.c'
    fixture.write_text(code, encoding='utf-8')
    compiler = shutil.which(a.cc)
    if not compiler:
        raise SystemExit('Existing C compiler not found: ' + a.cc)
    env = dict(os.environ)
    env['PATH'] = str(Path(compiler).parent) + os.pathsep + env.get('PATH', '')
    binary = output / 'fp_program_lifetime.exe'
    cmd = [compiler, '-std=c11', '-O1', '-I' + str(sdk / 'include'), '-I' + str(sdk / 'libs/video')]
    if a.legacy_control:
        cmd += ['-DLEGACY_CONTROL=1']
    subprocess.run(cmd + [str(fixture), str(sdk / 'libs/video/rsx_fp_decompiler.c'), '-lm', '-o', str(binary)], check=True, env=env, timeout=60)
    result = subprocess.run([str(binary)], capture_output=True, text=True, env=env, timeout=20)
    (output / 'result.log').write_text(result.stdout + result.stderr, encoding='utf-8')
    print(result.stdout + result.stderr, end='')
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
