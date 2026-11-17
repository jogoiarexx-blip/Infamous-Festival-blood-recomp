# SPURS: wake da LFQueue, jobs e imagem RADG5 (NPUA80657)

Resultado de testes locais (2026-11-16). Nenhum código ou dado do jogo está neste repositório.

## 1. Causa do travamento em `0x02514` (resolvido)

O loop de DMA idêntico em `pc=0x02514` era só o policy module `Wws_Job` ocioso (job list vazia). O bloqueio real:

- a tarefa SPU 0 (taskset `0x10481200`) esperava em `WAIT_SIGNAL` pela LFQueue `0x10482B80`;
- a fila foi criada com o **SPURS como dono** (`+0x70` = SPURS|1 = `0x00A8F681`), então o push do PPU sinalizava um taskset inexistente;
- um segundo defeito: se a tarefa estava ocupada (não estacionada), o sinal se perdia, pois o taskset real não era conhecido (estado observado: `pop=11`, `push=12`, tarefa dormindo).

Correção (no SDK ps3recomp, não neste repositório): [patches/ps3recomp-fob-all.patch](patches/ps3recomp-fob-all.patch).
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

## 5. A tela "parada" era o fim do aviso; o render está certo (corrigido)

Conclusões anteriores sobre um "Task Kicker travado" e uma "lógica congelada" estavam **erradas** e foram substituídas:

- O "SPU Light Task Kicker" cicla normalmente (estados 0→4 ~90 vezes/s, `PPU_WWATCH=AE2A18`); a espera da thread principal por ele é o ritmo de frame.
- O alpha do texto do aviso sobe de 3 a 255 em ~0,7 s, fica 4 s e desce a ~2 (log do alpha do vértice, `VTX_POS`). Aos 3 s a janela mostra o **aviso de epilepsia totalmente branco e nítido**. A tela escura "parada" é o estado depois do aviso, quando o jogo espera o próximo estágio (o vídeo de splash Bink).

## 6. Vídeo de splash (Bink) e a thread SPU RADG5

O Bink usa a thread SPU "RADG5" (imagem 5), que o jogo cria com `sys_spu_thread_initialize(... spu_num=5)` num grupo de **1** thread. Três defeitos do runtime impediam seu funcionamento (patch no SDK, ver `patches/ps3recomp-fob-all.patch`):

1. `group_start` e os demais laços só olhavam os primeiros `num_threads` slots, então a thread no slot 5 nunca iniciava ("none spawned"). Agora varrem os 8 slots.
2. A escrita no mailbox de saída não bloqueava quando cheio para threads com LS próprio, e a thread girava ~1 M vezes/s. Agora bloqueia também para threads de grupo.
3. `sys_spu_thread_bind_queue` era stub e o `stop 0x110` (`sys_spu_thread_receive_event`) não existia para threads lifadas. Agora o bind é registrado e o `stop 0x110` espera na fila ligada (fila 7, spuq `0x72616435`) e responde `{CELL_OK, d1, d2, d3}` pelo mailbox de entrada.

Com isso a RADG5 recebe os comandos do PPU (`port_send` na fila 7) e responde por `throw_event` na fila 8.

## 7. Pendências

- O vídeo de splash ainda não aparece: o Bink lê só o primeiro bloco de 128 KB do arquivo e a tela fica no estado pós-aviso. Falta ver se a decodificação na RADG5 produz quadros e por que o IO não avança.
- Esporadicamente (1 em 3 execuções) a thread principal bloqueia cedo num `cellSpursEventFlagWait` (padrão `0x0002`, flag `0x10482B00`).
- Os `null-call` do "Job Manager Event Handler" continuam; ainda não relacionados a travas.
- Áudio e a cobertura de demais imagens SPU não verificados.

Ferramentas úteis (SDK): `PS3_SAMPLE=5 PS3_SAMPLE_MAIN=1`, `PS3_SCTRACE=1`, `PPU_WWATCH`, `PPU_CASWATCH`, `SPU_ATOM_EA=0x…`, `SPU_INTERP_STATS`, `GCM_FLIPCOUNT=1`, `VTX_POS`, `VP_ATTRS_DUMP`, `DRAWARGS`, `FP_DUMP`, `SPU_MBOXTRACE`, `SPU_DBG_MBOX`, `PPU_POKE_ADDR` (valor fabricado, só diagnóstico).
