# Desempenho do recomp — 22/11/2026

## Estado e escopo

Esta medição cobre a cena 3D após a cinemática, com entrada automatizada por contagem de flips. O jogo ainda não foi validado como jogável. A PR #15 permanece em draft. O relatório não inclui executável, assets, saves, dumps ou código decompilado do jogo.

Hardware: Intel Core i5-11400, NVIDIA GeForce RTX 4060 (8 GB), driver 610.88, Windows build 26300. Build Windows com clang-cl/CMake/Ninja. Cache de shaders previamente aquecido em cada variante.

## Comparação controlada

O mesmo roteiro de 12 comandos, indexados pelos flips do jogo, foi aplicado à build anterior e à candidata integrada. A janela comparável foi de 70 pedidos de flip na cena 3D, dividida em sete blocos de 10. Cada variante teve **uma execução**; os dados ainda não estabelecem ganho estatístico ou fluidez sustentada.

- Build anterior: 3,133 pedidos de flip/s; mediana de 3.188 ms por bloco de 10; pior bloco 3.234 ms.
- Candidata integrada (main atual + série da PR #15): 3,333 pedidos de flip/s; mediana de 3.016 ms por bloco de 10; pior bloco 3.046 ms.
- Diferença observada: +6,4% na taxa de pedidos de flip da janela. Isto **não é FPS de apresentação confirmado**. O contador [PERF] de renderização ficou por volta de 6 chamadas/s nessa fase, mas mede outra coisa.
- Os registros só fornecem marcas a cada 10 flips; portanto não há base para calcular 1% low por quadro. São necessários mais runs, marcas por apresentação e uma cena jogável reproduzível.

A candidata local incluiu correções de runtime já incorporadas à main para Bink, SPU e LFQueue, além da série da PR #15. Ela não isola o efeito do patch 0020. Duas falhas de sintaxe de um caractere nos arquivos PPU gerados foram reparadas apenas no diretório privado de build, com backups locais; nenhum arquivo gerado foi publicado.

## Perfil de latência

Um rastreamento diagnóstico de 15 segundos na mesma fase registrou 29 intervalos entre pedidos de flip, mediana 501 ms (cerca de 2,0 pedidos/s **sob instrumentação**). A thread PPU principal esteve bloqueada, em média, 490,8 ms por intervalo; 467,1 ms ocorreram em um único laço que aguarda o estado de uma tarefa. Foram registradas aproximadamente 1,38 milhão de chamadas de espera de 10 µs nesse laço ao longo dos 15 segundos. A thread que conduz tarefas leves de SPU também permaneceu esperando durante quase todo o intervalo. O processamento da fila RSX ocupou em média 31,6 ms por intervalo. O rastreador usado não instrumenta os fences e o tempo de execução da GPU no backend D3D12; portanto, esta coleta não permite excluir um gargalo de GPU.

O rastreamento introduz custo elevado e não deve ser comparado numericamente com a execução sem diagnóstico. A amostragem de CPU atribuiu parte do tempo a uma função que retorna imediatamente, por limitação do mapa de símbolos do executável recompilado; esse percentual isolado foi descartado. A evidência útil é a linha do tempo das chamadas e a leitura do laço recompilado.

O perfil agregado de jobs SPU em 80 segundos apontou como maiores acumulados as imagens 7 (3,55 s em 2.678 jobs), 8 (1,85 s em 3.403) e 17 (1,29 s em 658). Isto ainda não identifica qual job impede o avanço do quadro. O hash seguro de fingerprint SPU medido localmente custou 28,7 ms para 37.000 consultas e 193 MB examinados em 80 segundos; não é o gargalo observado.

## Decompilação focal e experimento descartado

O Ghidra 12.2, executado localmente sobre o ELF do usuário, confirmou a máquina de estados: a rotina da thread principal só avança quando o estado chega a 4; a thread que conduz tarefas leves reavalia contadores de fila e a conclusão dos jobs antes de publicar esse estado. O REA instalado recusou esse ELF PowerPC no provedor Windows, então a análise focal foi feita diretamente no Ghidra. Nenhum trecho decompilado foi publicado.

Uma contagem temporária no arquivo PPU gerado mostrou que aproximadamente 188,6 mil de 200 mil consultas sucessivas do worker na cena 3D (94,3%) ocorreram no estado 2. A decompilação liga esse estado à consulta de conclusão da cadeia de jobs e de seus contadores, e não a uma simples espera de GPU. O teste instrumentado marcou 2,60 pedidos de flip/s na janela 1030–1100; como o arquivo gerado foi instrumentado, esse número não substitui o benchmark sem diagnóstico. A fonte gerada foi restaurada byte a byte a partir de backup local antes da recompilação.

Um teste **local e reversível** acrescentou uma pausa de 1 ms após cada 256 chamadas curtas consecutivas de espera. Com o mesmo roteiro, o pedido de flip 1030 apareceu a 96,8 s, contra 52,3 s na candidata integrada sem a pausa. Esse experimento piorou muito a transição e foi descartado. O arquivo original do timer foi restaurado por comparação de hash e a build Windows foi recompilada; a alteração experimental não integra a PR.

## Correções publicadas e validação

- PR #16: publicação atômica do índice LFQueue, incorporada à main.
- PR #17: README com estado real do projeto e requisitos, incorporada à main.
- PR #15: patch 0020 com cache persistente de shaders protegido por chave versionada, checksum, validação do bytecode e gravação atômica; fingerprint SPU revalidado pelo conteúdo; preservação dos draws novos em flip repetido. Continua em draft.
- Teste Windows do cache: o bytecode corrompido era aceito antes da correção; depois houve recompilação, hit válido e distinção entre entry points.
- Sequência de patches aplicada sobre a base testada; compilação Windows do runtime e do jogo; 49 testes Python aprovados, 2 pulados; CI da PR #15 aprovado. A execução local alcançou a cena 3D, mas ainda não comprovou estabilidade de gameplay nem compatibilidade fora do Windows.

## Próximos passos

1. Correlacionar a transição de estado aguardada pela PPU com a conclusão real das tarefas SPU; medir a cadeia causadora dos aproximadamente 467 ms sem simular conclusão ou descartar jobs.
2. Reduzir a espera ativa somente após identificar um mecanismo de notificação que preserve memória, ordem e semântica de SPURS/PPU.
3. Medir quadro apresentado real, tempo de GPU/fences e latência por quadro sem o custo do rastreamento amplo.
4. Repetir cada variante pelo menos três vezes, registrar distribuição de intervalos por apresentação e calcular 1% low em uma sequência longa.
5. Validar gameplay, animações e outras plataformas antes de mesclar a PR #15. Não usar o ganho de 6,4% de uma única janela como justificativa de merge.

## Medição de 23/11/2026 — jobs SPURS e custo do rastreador

O patch 0023 (PR #20) inclui os jobs SPURS executados pelo caminho HLE na linha do tempo por pedido de flip. Na captura de 20 s, a PPU principal passou em média 247,7 ms por intervalo aguardando a conclusão da tarefa, enquanto os jobs HLE medidos somaram 25,5 ms por intervalo. Esta soma pode conter trabalho paralelo e não identifica, sozinha, a dependência que limita cada quadro. Uma sonda local mostrou contadores de progresso avançando, com uma posição uma unidade atrás durante o job ativo; o escritor decisivo ainda não foi identificado. Nenhum contador foi forçado.

O rastreador passou a aplicar seu limite mínimo de 20 µs também às esperas curtas isoladas. Na captura anterior, 1.357.831 spans de `usleep` eram menores que esse limite e somavam 1,55 s entre todas as threads, diante de 43,27 s de espera total somada. Uma nova captura do mesmo período registrou 19.207 spans e 796.787 bytes, contra 1.376.511 spans e 55.091.337 bytes antes do filtro, sem registros descartados. As execuções distintas tiveram medianas de 287,1 e 310,2 ms por intervalo; essa variação não comprova ganho de FPS do jogo.

Com o rastreamento desligado, a build restaurada e recompilada levou 21,797 s para 70 pedidos de flip na mesma janela (3,21 pedidos/s). Duas execuções anteriores comparáveis levaram 23,750 s e 22,375 s. Há apenas uma amostra por variante, portanto o resultado não estabelece melhora estatística. A fonte PPU gerada usada na sonda foi restaurada pelo hash e não integra o patch público. O próximo trabalho é atribuir a latência entre o avanço dos contadores da fila e a publicação do estado final a um produtor concreto, antes de alterar a sincronização.

## Medição de 24/11/2026 — fila SPU, RADG5 e entrega de eventos

Uma reconstrução limpa da PR #15 (patches 0001–0020 e 0022–0027) compilou o SDK, mas a ligação do jogo falhou porque o NID `_cellSpursLFQueuePushBody` estava registrado sem implementação. O patch 0028 (PR #24) implementou o produtor da LFQueue e permitiu ligar o jogo. Em uma execução real, foram observadas 20 chamadas à função; não houve ganho de FPS atribuído a esse patch.

O RADG5 criou sua única thread no slot 5 de um grupo de capacidade 1. Antes do patch 0029 (PR #25), o grupo relatava `none spawned`; depois, `1 host threads running`. Com o mesmo roteiro, o flip 300 passou de 10,782 s para 5,093 s, mas a taxa após o flip 350 permaneceu em torno de 3,85 pedidos/s.

Uma sonda no runtime encontrou chamadas repetidas de `STOP 0x110` da thread RADG5 sem resposta, com 12 pedidos acumulados na mailbox. O patch 0030 (PR #26) liga a fila de eventos à thread SPU, entrega mensagens reais, aplica backpressure à mailbox e espera de forma bloqueante no Windows e POSIX. Com o mesmo roteiro e cache de shaders, o flip 400 passou de 18,437 s (com 0028–0029) para 7,453 s; o flip 900 ocorreu em 23,9 s. A cinemática registrou aproximadamente 30–33 pedidos de flip/s. A sequência alcançou draws 3D e houve pausas por criação de PSOs na transição. O valor de 6–7/s lido em `[PERF]` era throughput de renderização, **não** pedidos de flip do jogo; a medição específica desses pedidos está abaixo. Não há confirmação de FPS de gameplay nem de ausência de frames repetidos.

A análise de tempo após o aquecimento dos PSOs atribuiu cerca de 92–95% do intervalo medido ao código guest na cena 3D. Ainda faltam timestamps de GPU, intervalos entre quadros distintos, amostras repetidas e 1% low. A prioridade seguinte é perfilar PPU/SPU nessa cena e separar espera por sincronização de trabalho de simulação, sem fabricar conclusão de jobs ou alterar o relógio do jogo.

Validação: `git apply --check` dos patches 0028–0030, compilação limpa Windows do runtime e do jogo, teste Windows de recebimento/cancelamento da fila e CI Linux das PRs #24–#26 passaram. As três PRs foram incorporadas à PR #15. A PR #15 continua draft e `main` permanece sem essa série.


## Rastreamento de 24/11/2026 — trecho 3D após o patch 0030

Uma build Windows limpa da série até o patch 0030 foi executada com o mesmo roteiro de entrada por contagem de flips e cache de shaders aquecido. O rastreador `PS3_FTRACE=27:26` registrou 31.164 spans, sem perdas, em 26 s da cena 3D. Entre 66 pedidos consecutivos de flip, a mediana foi **315,6 ms**, equivalente a **3,2 pedidos/s sob rastreamento**; isto não mede quadros distintos apresentados e não deve ser comparado diretamente com uma execução sem instrumentação.

A thread PPU principal passou em média 322,6 ms por intervalo em chamadas bloqueantes; 316,1 ms foram atribuídos ao laço chamado em `0x001FFADC`, que espera o contador da tarefa em `objeto + 0x318` atingir 4. Foram registrados 2.086.030 polls desse laço em 26 s, agrupados em 68 spans com mediana de 268,8 ms. O RSX consumiu em média 53,7 ms por intervalo drenando comandos. O traço identificou 6,33 s acumulados nos jobs SPURS HLE durante 26 s de parede; não cobre todo o trabalho das SPUs persistentes nem mede os fences ou a execução da GPU D3D12. Assim, ainda não está comprovado que esses jobs, o spin de GETLLAR observado ou o backend gráfico sejam a causa única da espera.

O commit paralelo do patch 0031 ativa AVX2/FMA com base no suporte do compilador. Esta captura foi feita **sem** esse patch, e não valida as taxas publicadas para ele. Antes de integrá-lo à `main`, é necessário comparar no mesmo hardware a versão 0030 e a 0031 por pedidos de flip e apresentações efetivas, além de definir o comportamento em CPUs sem AVX2/FMA. O próximo instrumento deve correlacionar cada mudança real do contador `+0x318` com o job ou a thread que a produziu, sem abreviar a espera ou simular conclusão.


Uma segunda execução da mesma build até 0030, desta vez sem `PS3_FTRACE` e com `RSX_PRESENT_TRACE=1`, registrou os índices de flip e as submissões D3D12. Nos índices 1000–1080, houve 81 valores distintos de flip e **162 submissões `Present` bem-sucedidas: exatamente duas para cada índice**. A primeira submissão de cada índice ficou separada da seguinte por mediana de 297,0 ms nos índices 1000–1040; nos índices 1040–1080, a mediana subiu para 563,0 ms. A segunda submissão do mesmo índice ocorreu após mediana de 94 ms. A contagem de draws nas duas submissões variou e aumentou na cena; não é seguro tratar a segunda como duplicata descartável. `Present` bem-sucedido confirma envio à API, não exibição física nem quadro de simulação novo. Essa execução também tem custo de logging e cena variável; as janelas não são um A/B controlado.


A análise focal da rotina recompilada confirmou que a mudança de `objeto+0x318` para os estados 2, 3 e 4 é feita pela thread PPU que conduz as tarefas leves (`0x0036B128`). A fase 2 não consulta `0x00582DC4` nem o meio-palavra em `objeto+0x100`; esse caminho é só o estado 3. Uma execução até o flip 1100 com sonda de DMA no endereço concreto de `+0x318` não registrou escrita SPU nesse campo. O laço de espera de `+0x318` permanece como está.


## Medição de 25/11/2026 — contenção do workload SpuLight

Executável do lançador: `Infamous-Festival-blood-recomp-main\out\build\MyGameRecomp.exe` (25/11/2026 12:38, 213291520 bytes), com `SPURS_LT_MEASURE=1`. Esta execução carrega a sonda e não é comparação de velocidade com os cerca de 9 fps medidos sem ela.

O workload da tarefa de luz é `Wws_Job/SpuLight`, wid 2, instância SPURS `0x00A8F680`, `maxContention` 1. Na cena 3D estável, oito janelas de cerca de 4 s (32,344 s no total), com 84.463 e depois 86.770 chamadas de textura, cerca de 7,6 a 8,9 fps de render, guest cerca de 93% e `render_frame` cerca de 7%. Entre o flip 1010 (43.828 ms) e o flip 1090 (64.313 ms) houve cerca de 3,9 pedidos de flip por segundo.

Nesse intervalo a contenção do wid 2 ficou diferente de zero por 27.510 ms, 85% do tempo de parede. Foram 9.424 spans, média de 2,9 ms, máximo de 207 ms. O módulo de política que ocupa esse tempo é a imagem SPU 2: 27.390 ms somados em 9.424 execuções, praticamente o mesmo tempo de parede, como esperado com um único SPU. `ctx->image_id` no fim de cada execução continuou 2. A imagem residente no overlay, contada por execução e não por tempo, foi a 215 em 7.613 das 9.424 execuções.

Nas mesmas janelas, `cellSpursGetWorkloadInfo` desse wid foi chamado 2.956 vezes: 2.202 com contenção diferente de zero e `readyCount` 0, 754 com os dois em zero, e nenhuma com `readyCount` diferente de zero. O retorno da fase 2 (`0x003A9C3C` / `0x003A9C5C`) não chegou a essa consulta; a checagem das pistas devolve antes. O laço de `+0x318` não foi encurtado.

## Medição de 25/11/2026 — passos do interpretador na corrida SpuLight

A mesma sonda, agora contando passos do interpretador só dentro da corrida do wid 2. Continua desligada sem `SPURS_LT_MEASURE=1`. Esta execução também não serve de comparação com os cerca de 9 fps.

O pad parou numa cena estável mais pesada que a amostra anterior: oito janelas de 4 s, render cerca de 4,1 a 4,5 fps, guest cerca de 97%, `render_frame` cerca de 3%, chamadas de textura paradas em 63.550. Não é o mesmo enquadramento dos 84 mil a 86 mil.

Nessas janelas a corrida da luz ocupou 29.017 ms de 32.000 ms (91%). A média do span fechado foi 2 ms e o máximo de cada janela ficou entre 188 e 231 ms. O máximo antigo de 4,7 s é da travada de carga, fora dessas janelas.

O interpretador fez 121.098 passos nesses 32 s. 86.928 foram no corpo da política (endereço local abaixo de 0x4000), todos na página 0x800. 34.170 foram no buffer do módulo de trabalho. A entrada que mais apareceu foi 0xA68, 43.464 vezes, sempre com 2 passos. Esse endereço é o store no meio do laço lifted `fob_policy_spu_func_00000A60`, que reescreve código e volta para a entrada 0xA60. Dois passos por vez, contra 29 s de corrida, não explicam o frame. O tempo está no código já compilado da imagem 2, com o módulo 215 residente na maior parte das execuções.

0xE4A8 não é esse caminho. É o meio da função lifted da imagem 219 e um trampolim da imagem 217. O módulo 215 termina em 0x9780 e não contém esse endereço. O laço de `+0x318` não foi encurtado. Nenhum ganho de fps foi medido.

## Medição de 25/11/2026 — amostragem nativa da corrida SpuLight

Amostra só da thread do wid 2, 4367 pontos, com o jogo em cena. A thread estava executando o executável, não parada numa espera. O maior tempo exclusivo foi `fobdata4_spu_func_00007320` (34,5%), depois `fobdata3_spu_func_00006F80` (19,1%) e `jobmod_d128dc7fa99a_e5400_spu_func_00007568` (9,5%). As funções `fobdata*` juntas ficam perto de 70%. `mfc_do_transfer` ficou em 3,5%. A política em 0xA60 aparece em quase toda a pilha porque chama esse núcleo, não porque o store dela seja o custo. A janela dessa amostra travou em 23.130 chamadas de textura e cerca de 8 fps; esse número não é a linha de base.

O núcleo já era AVX2. O custo era a sequência exata de ponto flutuante, cerca de 38 ciclos por fma no banco, contra cerca de 4 na forma nativa com arredondamento para zero. Essa forma coincide com o SPU quando as entradas e o resultado são números normais. Faixa estendida, denormal e o padrão de saturação continuam no caminho exato, inteiro. A mudança vale para todo código lifted compilado com ela, não só para uma função.

O modo do processador fica em arredondamento para zero só durante `spu_run_with_halt`, sem flush-to-zero. O interpretador, quando corre fora dessa janela, continua no caminho exato. As operações de double devolvem o arredondamento para o mais próximo só enquanto executam. A função quente passou de 13.720 para 12.535 instruções; as 264 conversões para double saíram e entraram 51 fma nativas.

Executável medido sem sonda: 25/11/2026 20:46, 211.916.800 bytes, SHA256 `997F3272CE9A76C96F8FFDBCC2F73290E7132A3A25C0E52C8986A6D16263B0AE`. Uma execução, o mesmo roteiro de pad. Cena estável em 84.120 chamadas de textura, 0 miss de shader, 66 janelas de 20 quadros: média 11,30 fps de render, mínimo 10,50, máximo 11,84. Do flip 1030 (43.313 ms) ao 1630 (149.469 ms), 5,65 pedidos de flip/s. A medição anterior sem sonda, no mesmo tipo de cena (cerca de 80 a 87 mil texturas), era cerca de 9,0 fps e cerca de 4,5 pedidos/s. O executável antigo não foi repetido hoje ao lado deste. Esse binário é a forma anterior do caminho, antes do teste de faixa mais curto e antes do shufb na ordem do host. O patch 0034 é a forma medida no dia seguinte.

## Medição de 26/11/2026 — patch 0034

O patch `0034-native-round-toward-zero-singles.patch` aplica-se com `git apply` depois de 0001–0033. Em AVX2, pistas normais de fa, fs, fm, fma, fms e fnms usam uma operação single nativa com o MXCSR em arredondamento para zero. Denormal, infinito, NaN e o máximo finito ficam na trilha exata. FTZ e DAZ permanecem desligados. O modo vale só dentro de `spu_run_with_halt`. O longjmp do caso 2 reaplica os dois bits de arredondamento, porque neste CRT o longjmp recarrega o MXCSR gravado no setjmp. O shufb SSE4.1 não inverte mais o quadword na entrada nem na saída.

O teste diferencial de float, depois do teste de faixa mais curto, deu 446.840.832 pistas e 0 divergências, e 200.000 vetores de double com 0 divergências. O shufb passou em 200.000 vetores aleatórios. O teste de float não foi repetido depois do shufb, que é inteiro.

Uma corrida sem sonda, só com o teste de faixa mais curto: 83.440 chamadas de textura, 0 miss. As primeiras 62 janelas de 20 quadros deram média 12,25 fps de render (mínimo 11,15, máximo 12,99). As cinco seguintes caíram para 9,81–10,76. Do flip 1020 (40.500 ms) ao 1680 (149.859 ms), 6,04 pedidos/s.

Uma corrida sem sonda, já com o shufb na ordem do host: 85.680 texturas, 0 miss. As primeiras 66 janelas deram média 12,29 (mínimo 11,13, máximo 13,03). Do flip 1020 (39.906 ms) ao 1700 (150.656 ms), 6,14 pedidos/s. Não saiu da variação de uma corrida. A função quente ficou com 11.486 instruções, e os vpshufb dela passaram de 454 para 248.

Não houve três corridas pareadas contra a build sem o patch. A imagem não foi conferida. O guest continuou em cerca de 91%. Em 26/11/2026 os patches 0031–0034 entraram na main a pedido. A imagem e o par de três corridas continuam por fazer.
