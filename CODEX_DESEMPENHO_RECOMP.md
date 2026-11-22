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

Um rastreamento diagnóstico de 15 segundos na mesma fase registrou 29 intervalos entre pedidos de flip, mediana 501 ms (cerca de 2,0 pedidos/s **sob instrumentação**). A thread PPU principal esteve bloqueada, em média, 490,8 ms por intervalo; 467,1 ms ocorreram em um único laço que aguarda o estado de uma tarefa. Foram registradas aproximadamente 1,38 milhão de chamadas de espera de 10 µs nesse laço ao longo dos 15 segundos. A thread que conduz tarefas leves de SPU também permaneceu esperando durante quase todo o intervalo. O processamento da fila RSX ocupou em média 31,6 ms por intervalo; o rastreamento não apontou uma espera de fence de GPU como causa principal nessa janela.

O rastreamento introduz custo elevado e não deve ser comparado numericamente com a execução sem diagnóstico. A amostragem de CPU atribuiu parte do tempo a uma função que retorna imediatamente, por limitação do mapa de símbolos do executável recompilado; esse percentual isolado foi descartado. A evidência útil é a linha do tempo das chamadas e a leitura do laço recompilado.

O perfil agregado de jobs SPU em 80 segundos apontou como maiores acumulados as imagens 7 (3,55 s em 2.678 jobs), 8 (1,85 s em 3.403) e 17 (1,29 s em 658). Isto ainda não identifica qual job impede o avanço do quadro. O hash seguro de fingerprint SPU medido localmente custou 28,7 ms para 37.000 consultas e 193 MB examinados em 80 segundos; não é o gargalo observado.

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
