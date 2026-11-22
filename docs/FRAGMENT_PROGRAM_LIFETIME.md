# Fragment-program lifetime during deferred D3D12 preparation

The backend recorded a guest fragment-program address with each draw, captured
its inline constants immediately, then read the instructions again when
preparing the batch. Festival of Blood reuses shader-ring allocations in that
interval. Consequently a draw could compile a different program with constants
belonging to its original program.

## Confirmed evidence

A private diagnostic compared code hashes, program sizes and the first 32 bytes
at record and preparation time. It observed instruction changes, including a
96-byte program becoming a different 704-byte program. This was not merely a
constant update. Original programs, byte dumps and generated game shaders remain
outside the public repository.

Patch 0015 captures bounded instruction bytes in each draw record. Pipeline
identity, decompilation and inline-constant extraction use those same bytes.
The existing 4096-byte decode limit is preserved. A source without an END flag
keeps the former bounded decode behavior. No effects, guest work, geometry,
simulation steps or shader calculations are substituted.

The primary 2048-record array uses about 8 MiB more storage for instruction
bytes. Existing static diagnostic arrays that copy draw records also grow.
Copies during normal recording stop at the decoded program end, including
inline payloads. This introduces no GPU copy or additional GPU wait.

## Validation

Using an existing C compiler and a patched SDK:

```text
python tools/test_fp_program_lifetime.py --sdk /path/to/ps3recomp --cc gcc --output-dir out/fp-lifetime-test
```

Nine checks compile the actual backend capture helper and actual SDK fragment
decompiler against synthetic RAM. They cover shader and constant preservation
after guest reuse, distinct versions at the same address, draw-record copying,
unbound and unmapped programs, complete inline payloads, precise short programs,
and the existing bounded behavior for unterminated sources.

`--legacy-control` deliberately models the previous deferred address read and
is expected to fail: eight checks fail. This negative control is a model of the
old read policy, not an execution of the complete old D3D12 backend.

Both the modified game executable and the public SDK runtime compiled on Windows.
The nine checks passed against the local SDK and a separate public SDK checkout.
The patch also applied independently to the public baseline and alongside the
Gemini compositor/cache and GPU retirement patches.

Private game runs used a 95-second limit, default presentation timing, six RSX
captures and no compositor override. An initial pre-fix run without shader
dumping captured six black backbuffers. However, a second pre-fix run WITH
shader dumping already captured the bar scene in three of six backbuffers.
The post-fix run with shader dumping also captured three nonblack backbuffers.
Therefore scene visibility cannot be attributed to this patch from these runs;
diagnostic timing and scene progression must be controlled more closely.
Captured shader variants contained three unhandled-opcode comments before and
none after, but the captured variants and scene progression differ. The proven
result is instruction/constant lifetime preservation, not a confirmed visual
repair or FPS gain. These runs do not provide pixel-equivalence evidence.

## Remaining limits

Colors and lighting are still visibly incorrect. Frame captures include
offscreen-only submission batches; a black captured backbuffer does not by
itself prove that a black image was presented. No stable 30 or 60 FPS claim is
made. Saving also reports an error in the corrected run and needs separate
investigation.

The tests do not execute a real D3D12 driver or the complete PSO preparation
path. The pre-existing draw-concatenation logic still assumes a program remains
unchanged within one BEGIN/END epoch. Mutation within an already merged epoch
has not been demonstrated or covered by this fix. Texture lifetime, feedback
between sampled and written surfaces, depth conversion and final color
composition remain separate investigations.
