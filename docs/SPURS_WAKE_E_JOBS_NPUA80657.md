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

## 3. Módulos de job WWS embutidos no EBOOT (primeira imagem)

Os jobs do `Wws_Job` (General, EdgeGeom, SpuLight) carregam módulos de código em LS `0x4000` a partir de endereços do próprio EBOOT (ex.: EA `0x8BD500`, descoberto com `SPU_DUMP_OVL=<dir>,0x4000`). Sem código liftado, o módulo roda no interpretador e nunca termina: a thread principal ficava em esperas de teardown (`SPU Light Task Kicker` nunca chegava ao estado 4) e a janela ficava preta.

`tools/prepare_engine_jobmods.py` roda `lift_jobmods.py --engine-elf` do ps3recomp: **27 módulos, 0 instruções não suportadas** (imagens 200–226). Com isso:
- `CLEAR_SURFACE` e `DRAW_ARRAYS` aparecem a cada frame (quads texturizados, atlas 512x256);
- a janela D3D12 apresenta a **primeira tela real do jogo: o aviso de epilepsia** (ainda em fade-in), a ~8 FPS.

Diagnóstico útil: `PS3_SAMPLE=5 PS3_SAMPLE_MAIN=1` (profiler de código guest; exige chamar `ps3_sampler_start()` em `main.cpp`), `PPU_WWATCH=<ea hex>`, `SPU_DUMP_MISS`, `SPU_DUMP_OVL`. O resultado varia entre execuções (uma em três travou cedo): há corrida de threads a investigar.

## 4. Desempenho: 8 → ~100 FPS

Duas causas, medidas com `SPU_INTERP_STATS=5` e o profiler:

1. **Rotinas de biblioteca de cada módulo WWS rodavam no interpretador SPU.** Depois do `code_end` de cada módulo há memset/memcpy, atômicas e divisão de DMA, alcançadas só por chamadas indiretas, que o lifter não vê. Uma thread consumia um núcleo inteiro (15 M passos/s, ~58 mil chamadas em 5 s a `0x9690`). `tools/prepare_engine_jobmods.py` agora semeia `LBP_JOBMOD_EXTRA_FUNCS=0x9548,0x95D8,0x9690`; o interpretador caiu a ~0 passos/s e o FPS foi de ~8 para ~44.
2. **Build em Debug (PPU em -O0).** Reconfigurar com `-DCMAKE_BUILD_TYPE=None` aplica o `-O1` do template (~12 min de compilação) e leva a ~100 FPS.

Mais endereços de biblioteca podem aparecer em "top entries"; adicione-os à lista.

## 5. Investigação: por que o aviso de epilepsia não avança

Achados (teste local, build -O1, ~100 FPS):

- O jogo **está em loop de frames** (a ~60–100 flips/s, `GCM_FLIPCOUNT=1`), mas o aviso fica com alpha baixo e estático por 70+ s.
- A thread principal passa a maior parte do tempo no bloco de **fim de frame** de `func_001FF83C`, que espera (`func_0036B5A4`, poll com `usleep(10)`) o objeto "SPU Light Task Kicker" (`0xAE2700`) chegar ao **estado 4** (`+0x318`). O worker (thread `tid=5`, `func_0036B128`) percorre os estados 0→1→2→3 e para no 3.
- A transição 3→4 exige `func_00582DC4(obj+0x100)` verdadeiro, isto é, o `u16` em `0xAE2800` valer `0xFFFF` (sentinela de "lista vazia" nas filas lock-free de índices `u16` do SPURS/WWS). Esse campo fica em `0` o tempo todo.
- O código SPU (módulo WWS `d128…`, EA `0x8BD500`) faz GETLLAR/PUTLLC em `0xAE2800` o tempo todo (~1800 em 30 s, quase todos com sucesso): só incrementa contadores `u16` em `+2` e `+4` (até o limite `0x2D0`) e nunca toca em `+0`. O PPU só lê; `PPU_CASWATCH` e `PPU_WWATCH` não mostram escritas do PPU ali.
- Forçar o estado 4 (`PPU_POKE_ADDR=AE2A18 PPU_POKE_VAL=4`) ou o sentinela (`AE2800=FFFF0000`) **não** mudou a tela, então a espera não é a única barreira (há outros kickers, p.ex. "Edge Geom Task Kicker" em `0xAE2C00`).
- Hipóteses em aberto: o consumo/retorno de jobs do SpuLight não completa (a lista do workload em `0xB51E00` é inicializada com `0xFFFF` e só é consultada pelo PM); ou o alpha baixo seria um erro de renderização (shader/formato `0x85`) e não de estado.


### 5.1 O render não é a causa (verificado)

- A tela fica **idêntica por 72 s** (fundo `(0,0,25)`, texto com brilho máx. 10/255, medido capturando a janela a cada 6 s).
- Os vértices do texto estão certos: posições plausíveis (quads de ~30x33 px, `VTX_POS`), cor `ubyte4` clara (`VP_ATTRS_DUMP`), draw args normais (`DRAWARGS`). O fragment shader de 16 instruções (`FP_DUMP`) multiplica a cor por fatores vindos de `tc1`/`tc2` do vertex shader (constantes de fade/recorte), logo o alpha baixo é entrada do jogo, não erro de formato de textura.
- O toggle por frame do estado do motor (`0xA7AF30`, escrito por `func_0008A8B8`) ocorre só **40 vezes** nos primeiros segundos e depois para (`PPU_WWATCH=A7AF30 PPU_WWATCH_MAX=0`). Ou seja, o loop de lógica do jogo **congela depois de ~20 frames**; os flips continuam porque vêm de outra thread. O congelamento é a espera do fim de frame pelo "SPU Light Task Kicker" (seção acima).

Ferramentas úteis (SDK): `PS3_SAMPLE=5 PS3_SAMPLE_MAIN=1`, `PS3_SCTRACE=1`, `PPU_WWATCH`, `PPU_CASWATCH`, `SPU_ATOM_EA=0x…`, `SPU_ATOMTRACE`, `SPU_INTERP_STATS`, `GCM_FLIPCOUNT=1`, `PPU_POKE_ADDR` (valor fabricado, só diagnóstico).

## 6. Pendências

- `null-call` no PPU ("Job Manager Event Handler") e leituras de NULL persistem; provável efeito de arquivos ausentes do VFS (`core.psarc`, `infamous2.psarc_s`, `patch*.psarc_s`, `all_shaders.xpps`, `lang_english.xpps`, ...). Copie a instalação completa do jogo para `private/`.
- Métodos RSX "unknown" são ruído do despachante legado; só tratar quando houver draw com erro visual.
- A tela do aviso de epilepsia fica parada e escura; ver a seção 5.
- Execuções não determinísticas (uma em três travou cedo).
- Não confirmado: execução correta do áudio RADG5.
