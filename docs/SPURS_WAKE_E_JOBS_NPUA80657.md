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

## 7. Vídeo de splash: a decodificação funciona; a thread principal espera um job

Medido com `PPU_WWATCH`, `SPU_DMATRACE=5` e depuração temporária nas funções lifadas:

- **O Bink decodifica de verdade.** O objeto Bink (`0x194971C0`) avança a ~31 quadros/s (contador em `+0x460`, `BinkWait` = `func_00771260`), e a RADG5 (imagem 5) faz GET da estrutura e PUT de linhas de `0xF00` bytes dos planos decodificados.
- **Mas nada é desenhado depois do aviso.** Após os primeiros frames o jogo não envia mais draws (`DRAWARGS`); a janela só reapresenta o último buffer (~100 FPS), por isso a tela "dim" fica parada.
- **A thread principal está presa no `func_000B4A2C`**, o laço de espera do gerenciador de jobs do motor (poll de `usleep(3)`, `PS3_POLLTOP`). Ele só sai quando as filas em `mgr+0x3D0..0x3E0` esvaziam (`mgr=0x00A7B4C0`). A fila 1 (`+0x3D8`) fica com um nó em voo: um job de carga de **`ugc_message.sprig.xpps_a`** (nó em `0x10CE....`, vtable `0x97A588`, nome em `+0x1C`) com contador de dependências `+0x10 = 1` que nunca zera. O `open` desse arquivo retorna `ENOENT` (0x80010006), o esperado numa instalação nova; criar o arquivo vazio não resolve (o FIOS apenas registra `failed reading header`).
- Despejando todas as filas do gerenciador (`mgr+0x3D0..0x3FC`, laços `+0x14`) só existe esse nó (estado 1, `dep=1`); as demais filas estão vazias. A dependência é, portanto, **externa** às filas deste gerenciador (outro gerenciador, thread ou callback assíncrono).
- O `open` falha em threads "fios mediathread" (a falha vem de `func_0059F494`/`func_005900E0`, código do FIOS). Um PSARC mínimo válido (32 bytes, 0 entradas, preenchido a 64 KB) deixa o FIOS aceitar o arquivo (some o `failed reading header`), mas o nó continua em voo. Não é só a ausência do arquivo.
- Os métodos do nó são: destrutores (`0x68F5AC`/`0x68F5F8`) e `run` = `func_000B7CEC`, que é o laço de espera por conclusão (`ppu_timebase_now`).

Nota: o perfilador de PC (`PS3_SAMPLE`) atribui nomes de função errados a código SPU lifado (aqui apontou `spu_LS_00006CB4`, que nunca é chamada); confie nele só por módulo.

## 7b. Teste decisivo: soltar o nó destrava o jogo

- O laço `func_000B4A2C` sai quando as três filas do gerenciador (`mgr=0x00A7B4C0`, heads em `+0x3D0/+0x3D8/+0x3E0`) estão vazias. O gerenciador é estático.
- Teste de diagnóstico (estado fabricado, não é correção): `PPU_POKE_ADDR=0xA7B898 PPU_POKE_VAL=0 PPU_POKE_MS=12000` zera o head da fila 1 aos 12 s. Resultado: o jogo sai da espera, fecha o Bink, abre `load_menu_catalog.log`, os PSARC de texto e passa a **desenhar uma tela nova** (a tela de carregamento com o emblema, `draws: 8`, ~33 FPS). Logo, esse nó é o único portão entre o aviso e o carregamento.
- Depois do poke aparecem muitos `garbage vcall` (objeto liberado sendo usado), esperado por ser estado fabricado.
- As threads do jogo ficam todas ociosas (amostrador: `guest=0`); o nó espera por algo que nunca chega. Há duas hipóteses abertas: a falha de `open` do `ugc_message.sprig.xpps_a` (conteúdo de usuário, em geral baixado) não completa a operação do FIOS, ou a rede (`cellNetCtl GetState` devolve NOT_INITIALIZED no modo offline) deixa o carregamento sem desfecho.

## 7c. Rede e eventos do gerenciador de jobs (rodada seguinte)

- **Rede descartada.** Com `cellNetCtlGetState` devolvendo OK (Disconnected) em vez de erro, o jogo continua travado no mesmo ponto.
- **`ugc_message` não é FIOS.** A tentativa de abrir `ugc_message.sprig.xpps_a` (primeiro em `/dev_hdd0`, depois em `/dev_bdvd`) vem da thread do jogo "Splash movie Installation", que termina normalmente (`status=0`) mesmo com as duas falhas. O arquivo não existe em nenhum PSARC consultado, como se esperaria de conteúdo de usuário.
- **Os "Job Manager Event Handler" (filas 1 e 2) recebem eventos do tipo errado.** O laço (`func_00580548`) lê `d2`: se a palavra alta (`d2>>32`) vale 1 chama o tratador em `obj+0x24`; caso contrário chama o callback em `obj+0x20`, que o jogo inicializa com NULL (`func_005806C8` recebe `r7=0`). Isso explica os `null-call` que eu tinha tratado como sem relação.
- Eventos reais de job SPURS chegam pelo `spu_deliver_user_event` com `d1=0xFFFFFFFF53505501`, `d2=(porta<<32)|valor` e `d3=dado`. Com `d2>>32==1` (porta 1) o tratador correto seria chamado. Nesta execução **nenhum** evento real chega (contagem 0); só chegam os eventos sintéticos de `jc_signal_done` (`d2` = índice do job, palavra alta 0), que o jogo trata como callback NULL.
- O job `0x64D9...` (272 B) é um "enviar evento": porta lida de `desc+0x34` (valor 0x10, fila 6) e dado em `desc+0x3C` (0xC0CAFEED). Ele não alimenta as filas 1/2.
- A task 0 do taskset `0x10481200` fica dormindo em `WAIT_SIGNAL` por mais de 16 s: é o candidato a produzir o evento real de porta 1 que completa o nó. Falta descobrir em que objeto ela espera e quem deveria sinalizá-lo.

## 7d. A fila LFQueue funciona; o segundo travamento

- A task 0 do taskset `0x10481200` espera no objeto `0x10482B80` (a LFQueue de 12 posições de 32 bytes). Despejando a linha de 128 bytes a cada park, os índices avançam e dão a volta (pop e push em equilíbrio, 73 parks em 20 s): a fila **não** está travada, a task fica ociosa porque o PPU não empurra mais nada. O consumidor SPU e o `_cellSpursLFQueuePushBody` do HLE estão corretos para esse fluxo.
- Nenhum evento de SPU para a porta 1 é emitido em momento algum (só `INTR 0x50000000`, porta 16, do job `0x64D9...`).
- Com o poke que solta o nó (seção 7b) o jogo mostra a tela de carregamento e depois **trava de novo**: a thread principal fica na espera temporizada `func_000B5770` (poll de `usleep` ~257 mil chamadas/s, `lr=0x000B58A4`), tela do aviso apagada e só 1 draw. Ou seja, o problema não é um nó isolado: o gerenciador de jobs do motor não recebe as conclusões das suas tarefas.
- Próximo passo: ler o que as chamadas de `_cellSpursLFQueuePushBody` do PPU enviam (mensagens de 32 bytes) e o que o SPU devolve por DMA, para achar a conclusão que o motor espera.

## 7e. Correção: sinais contados na LFQueue (causa do bloqueio intermitente)

- **Causa encontrada.** O bloqueio intermitente em `cellSpursEventFlagWait` (padrão `0x0002`, flag `0x10482B00`) era uma perda de despertar. O consumidor SPU da `LFQueue` (`0x10482B80`) reserva um slot e espera **um** sinal por slot, mas o bit `signalled` do taskset coalesce: dois pushes seguidos (`set,set`) geravam um único despertar, a task processava um item, dormia de novo em `WAIT_SIGNAL` com um item pendente (`pop=5`, `push=6`) e o EventFlag que o PPU esperava nunca era setado. Medido com um log de sequência (`set` / `woke` / `enter wait`) e com o despejo da linha da fila no instante do bloqueio.
- **Correção** (`runtime/spu/spu_workload.c`, `libs/spurs/cellSpurs.c`; no patch consolidado): cada push conta (`pend++`) e o waiter consome um por despertar, re-armando o bit enquanto restar contagem. Além disso o push não sinaliza mais `spurs|1` como se fosse um taskset (escrevia bytes soltos na estrutura SPURS).
- **Resultado.** Antes ~1 em 3 execuções bloqueava; agora 0 em 26 execuções. Sem o poke de diagnóstico, o jogo chega a ler `load_menu_catalog.log` e fecha o Bink, mas a janela continua com o aviso apagado (1 draw): o nó `ugc_message` das seções 7/7b era, ao menos em parte, esse mesmo bloqueio.
- **Novo ponto de parada.** Depois de `load_menu_catalog.log` há 12 `garbage vcall` com `this=NULL`, vindos de `func_000BFBE4` chamada por `func_000B7CEC` (lista de nós do gerenciador de jobs, campo `obj+0x24`). A thread principal passa a girar em `func_003A9C84` (espera por barreira de lanes de SPU, `func_00581140`) em ~120 consultas/s.

## 7f. Savedata: `PS3_USRDIR_BASE` e a tela "Installing..."

- **Bug de configuração, não de código.** O jogo lê o ícone do savedata por `sys_fs` cru (`USRDIR/ui/xmb/savedata/icon.png`). Sem `PS3_USRDIR_BASE`, o `sys_fs` achata o caminho para `<raiz>/USRDIR/...`, que não existe, e o `AutoSave` falhava com `PARAM` (`size=0 buf=0`). O jogo entrava num laço infinito de "There was an error while loading/saving", exibindo a tela **"Installing..."** com o emblema (60 FPS, 9 draws). Com `PS3_USRDIR_BASE=private/PS3_GAME` o save grava `ICON0.PNG`, `STATE`, `PARAM.SFO` e `PARAM.PFD` e o laço termina. O launcher local passa a definir essa variável por padrão.
- **Atenção ao testar.** Diretórios de savedata incompletos de execuções anteriores (só `PARAM.SFO`) fazem o jogo tentar carregar um `STATE` inexistente; apague-os (ou mova) antes de testar.
- **Depois do save.** O jogo lê `load_menu_catalog.log`, as threads `SP Movie Loader/Player` e `Motion Controller Update` saem, e há 12 `garbage vcall` (`this=NULL`, ctr `0x101C0C6C`) com o nó `0x102E9FC0` (vtable `0x78B9D0`, campo `+0x50 = 0xFFFFFFFF`) passando por `func_000BFBE4`/`func_000B9C7C`. Em seguida `func_000B6C94` escreve em NULL (a base do array do gerenciador de jobs em `0x00A82DA0` fica 0) e as threads "Job Manager Event Handler" passam a receber de uma fila de id 0 (13 milhões de linhas de log). O guarda de vcall (`PPU_VCALL_BT=1`) agora também imprime a pilha guest.
- **Limite do diagnóstico.** O nome de função dado pelo guarda (`func_000B7CEC`) vem de um endereço de retorno do host e pode estar errado por fusão de código idêntico; o ponto exato do vcall ainda não foi confirmado.

## 7g. Causa dos NULLs: o decodificador de vídeo escrevia por cima do código do jogo

- **Achado.** A tabela de salto de `func_000BFBE4` (em `0xBFC5C`, dentro do segmento de código) estava preenchida com `0x10101010` em tempo de execução; o `ctr` calculado virava `0x101C0C6C` e caía no `default` do `switch` (o "garbage vcall"). A região `0x00000..0xE1000` inteira (691200 bytes, o tamanho do plano Y 1280x720) estava com `0x10` (preto).
- **Origem.** O decodificador Bink na SPU (imagem RADG5, `SPU_DMATRACE=5`) faz `PUT` dos planos YUV com destino `EA = 0, 0x2800, 0x5000...`. O descritor de planos do "SP Movie Player" (`0xAC5800`, montado por `func_0076EFF0`) usa o ponteiro base `[0xAC547C]`, que só recebe o valor real (`0x11771400`) depois, pela thread principal; a thread do player já tinha calculado os planos com base 0. O `MFC` da SPU já rejeitava `PUT` com `EA < 0x10000`, mas os blocos seguintes (`0x10000..0xE1000`) passavam e destruíam o código/tabelas do jogo.
- **Correção** (`runtime/spu/spu_dma.h`, `runtime/ppu/ppu_loader.cpp`, no patch): o loader registra o segmento de código (`PF_X` sem `PF_W`) em `g_ps3_ro_lo/hi` e o MFC rejeita `PUT` que o toque, como o hardware faz. Não corrige a ordem de inicialização do vídeo (o primeiro quadro continua com base 0), apenas impede a corrupção.
- **Resultado.** Sem `garbage vcall` nem `null-write`; o jogo passa a carregar o mundo (`imposter-*.xpps`, jobs Wws em execução) e a emitir 46 draws por quadro com shaders de fragmento reais.
- **Novo bloqueio, agora no renderizador.** Logo depois o dispositivo D3D12 é removido: `removedReason=0x887A0006` (DEVICE_HUNG) na GPU e `0x887A0020` (DRIVER_INTERNAL_ERROR) no WARP, ou seja, não é só tempo de GPU. Com `DRAW_LIMIT=11` não ocorre e com `DRAW_LIMIT=12` ocorre: a 12ª draw de algum quadro dispara a falha. `FP_OFF=1` e `VP_BYPASS=1` não a evitam (não são os shaders). A tela fica preta a ~0,8 FPS. O backend agora imprime o `removedReason` no primeiro `PSO FAIL`.

## 8. Pendências

- Corrigir de verdade (sem poke) a conclusão do job `ugc_message...`: testar o estado de `cellNetCtl` (Disconnected em vez de erro) e a conclusão por erro do FIOS.
- Esporadicamente (1 em 3 execuções) a thread principal bloqueia cedo num `cellSpursEventFlagWait` (padrão `0x0002`, flag `0x10482B00`).
- Os `null-call` do "Job Manager Event Handler" continuam.
- Áudio e a cobertura de demais imagens SPU não verificados.
