# SPURS: wake da LFQueue, jobs e imagem RADG5 (NPUA80657)

Resultado de testes locais (2026-11-16). Nenhum código ou dado do jogo está neste repositório.

## 1. Causa do travamento em `0x02514` (resolvido)

O loop de DMA idêntico em `pc=0x02514` era só o policy module `Wws_Job` ocioso (job list vazia). O bloqueio real:

- a tarefa SPU 0 (taskset `0x10481200`) esperava em `WAIT_SIGNAL` pela LFQueue `0x10482B80`;
- a fila foi criada com o **SPURS como dono** (`+0x70` = SPURS|1 = `0x00A8F681`), então o push do PPU sinalizava um taskset inexistente;
- um segundo defeito: se a tarefa estava ocupada (não estacionada), o sinal se perdia, pois o taskset real não era conhecido (estado observado: `pop=11`, `push=12`, tarefa dormindo).

Correção (no SDK ps3recomp, não neste repositório): [patches/ps3recomp-spurs-owner-wake.patch](patches/ps3recomp-spurs-owner-wake.patch).
O runtime guarda o último `(taskset, task)` que esperou em cada linha de wait-object e o push sinaliza por essa linha (o sinal fica latched no bit `signalled` do guest).
Resultado: EventFlag deixa de bloquear; 79+ ciclos de `WAIT_SIGNAL` em 60 s (antes 0 progresso); o jogo chega à inicialização D3D12/RSX.
É uma correção local de teste; ainda não enviada ao upstream.

## 2. Jobs SPURS e imagem RADG5

- Dois jobs SPURS brutos (1040 e 272 bytes, `fp=054414E2CCD626FF` e `64D9D14299A2B7AB`) foram capturados com `SPU_DUMP_MISS` e liftados com [tools/prepare_spurs_jobs.py](../tools/prepare_spurs_jobs.py). Resultado: 5247 `dispatch HIT`, 0 `MISS`.
- A imagem SPU "RADG5" (ELF embutido no EBOOT, 101596 bytes, `fp=7117B11EE89D75F0`) foi extraída com `tools/extract_spu_images.py` e liftada com `tools/build_spu_workloads.py --input ... --image-ids`: 824 funções, sem `TODO`. O runtime registra a entrada.

## 3. Pendências

- `null-call` no PPU ("Job Manager Event Handler") e leituras de NULL persistem; provável efeito de arquivos ausentes do VFS (`core.psarc`, `infamous2.psarc_s`, `patch*.psarc_s`, `all_shaders.xpps`, `lang_english.xpps`, ...). Copie a instalação completa do jogo para `private/`.
- Métodos RSX "unknown" são ruído do despachante legado; só tratar quando houver draw com erro visual.
- Não confirmado: execução correta do áudio RADG5 e qualquer saída de vídeo.
