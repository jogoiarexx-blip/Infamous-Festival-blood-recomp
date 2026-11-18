# Validação local Windows — NPUA80657 — 18/11/2026

Este registro reúne observações compartilhadas durante testes da recompilação estática do *inFAMOUS: Festival of Blood* no Windows. **Não é uma correção de código nem comprova que o jogo seja jogável.** Os logs, binários, EBOOT e dados do jogo permanecem exclusivamente no ambiente local.

## Compilação

- Comando usado: `cmake --build "out\build" --parallel 1` (prompt de ferramentas nativas x64 do VS 2022).
- O CMake detectou três novos arquivos locais `spu_recomp.c` em `out/port/spu/` correspondentes aos fingerprints `0x2BC127B9AAF9165A`, `0x5EC85F9D752F82D1` e `0x7FD662F57F44EC4C`.
- O CMake registrou **39 imagens SPU** no total e **33 arquivos PPU** em `out/recompiled/`.
- O build concluiu a etapa `Linking CXX executable MyGameRecomp.exe` e retornou ao prompt sem erro registrado.
- A inclusão no build **não comprova que os três jobs extras foram executados durante o boot**.

## Boots comparados

Dois testes locais produziram `out/boot_atualizado.log` e `out/boot_spu_stats.log`. O segundo foi executado com `SPU_INTERP_STATS=5`. Em ambos:

- O jogo abriu `/dev_bdvd/PS3_GAME/USRDIR/movies/cutscene/fob_logo.bik`, nas linhas 20653 e 20598, respectivamente.
- A primeira porta de áudio do vídeo abriu, iniciou e fechou; em seguida foi registrado um novo `cellAudio PortOpen(nChannel=2, nBlock=16)`, mas **sem novo `PortStart` nos logs observados**.
- O jogo não terminou normalmente: `[quit] requested (window closed)` precedeu a finalização.
- Não foi verificada a chegada ao menu principal.

No log com `SPU_INTERP_STATS=5`, após abrir `fob_logo.bik`, ocorreram comandos `DRAW_INDEX_ARRAY` no RSX e `draw_indexed` no D3D12. O backend registrou um destino offscreen de **1280 × 720**, e os fences de sincronização RSX progrediram de **1 a 8**. Isso confirma atividade de renderização e sincronização, **não** comprova que novos quadros visíveis foram apresentados.

## Jobs SPURS e interpretador

- No primeiro log, houve `dispatch HIT fp=0xB5EFEE742877FBAD image=8 job=0x00BDAD00` na linha 48802, **sem `RETURNED` posterior identificado para esse job até o encerramento**. O mesmo endereço de job havia retornado normalmente em várias chamadas anteriores.
- No segundo log, não ocorreu despacho desse fingerprint, mas os jobs das imagens 3, 4, 6 e 7 continuaram sendo despachados. **A imagem 8 isoladamente não explica o comportamento comum aos dois boots**.
- `[spu-spin] img=1 pc=0x0A29C ... GETLLAR ea=0x10482B80` apareceu em ambos os testes. Os valores da linha de memória variaram; a mensagem por si só não demonstra bloqueio permanente.
- `[spu-smc] microstep img=2 pc=0x00A68 ... handing to the interpreter` apareceu no segundo log. O diagnóstico de interpretador registrou até **30,6 milhões de passos/s** em uma janela de 5 segundos. A passagem ao interpretador não comprova falha.
- Não foram encontrados novos `dispatch MISS` nos trechos filtrados dos testes.

## Thread principal e próximo diagnóstico

- `[GSTACK:hot]` identificou repetidamente a thread principal (`tid=1`) numa cadeia de chamadas contendo `func_002B0B74+0xB8`.
- O endereço de retorno relevante é `0x002B0C2C`. O código local gerado em `out/recompiled/ppu_recomp_001.cpp`, função `func_002B0B74`, chama `func_003A9E68` nesse ponto e depois verifica o resultado para decidir se continua percorrendo uma estrutura.
- Essa função foi **localizada**, mas a implementação de `func_003A9E68` ainda precisa ser examinada. Não há prova de que a chamada espere diretamente a conclusão de um job SPU.
- Os próximos passos são identificar a condição verificada por `func_003A9E68`, correlacionar despachos e retornos do mesmo job em um único boot e investigar a cadeia dados Bink → DMA SPU → upload B8 → apresentação do quadro.

## Limites e cuidados

Os diagnósticos revelam um bloqueio ou falta de progresso na transição posterior a `fob_logo.bik`, mas **a causa-raiz ainda não foi confirmada**. Não aplicar alterações arbitrárias aos semáforos, filas SPURS, áudio ou shaders apenas com base nessas pistas. Não publicar `private/`, `out/`, EBOOT, dumps de memória, imagens SPU derivadas do jogo ou outros recursos proprietários.
