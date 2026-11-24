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
