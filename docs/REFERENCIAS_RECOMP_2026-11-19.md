# Auditoria técnica: três referências para RECOMP de Festival of Blood (Windows)

**Data:** 19/11/2026. **Jogo:** inFAMOUS: Festival of Blood, NPUA80657 (PSN EUA).  
**Arquitetura inegociável:** PPU e SPU traduzidos estaticamente por ps3recomp, com runtime nativo Windows. DECOMP apenas para interpretar comportamento. RPCS3 apenas como referência, não como emulador embutido.

**Escopo realizado:** leitura de código e documentação públicos, comparação com os relatórios do nosso projeto e ferramenta offline original com cinco testes sintéticos. Esta revisão NÃO executou o jogo no PC, NÃO corrigiu FPS, NÃO corrigiu a composição 3D e NÃO prova independemente os FPS relatados por terceiros.

## Referências fixadas

| Origem | Commit inspecionado | Trechos relevantes |
| --- | --- | --- |
| [A — inFAMOUS: ReCharged](https://github.com/ChaosTheory1075/infamous-ps5) | [8e07d8f](https://github.com/ChaosTheory1075/infamous-ps5/tree/8e07d8ff373b19e37a9b6d45f6b437f48833754b) | [README](https://github.com/ChaosTheory1075/infamous-ps5/blob/8e07d8ff373b19e37a9b6d45f6b437f48833754b/README.md), [fob_build.sh](https://github.com/ChaosTheory1075/infamous-ps5/blob/8e07d8ff373b19e37a9b6d45f6b437f48833754b/tools/fob_build.sh), [fob_spu.sh](https://github.com/ChaosTheory1075/infamous-ps5/blob/8e07d8ff373b19e37a9b6d45f6b437f48833754b/tools/fob_spu.sh), [fob_jobmods.py](https://github.com/ChaosTheory1075/infamous-ps5/blob/8e07d8ff373b19e37a9b6d45f6b437f48833754b/tools/fob_jobmods.py), [fob_jobextra.py](https://github.com/ChaosTheory1075/infamous-ps5/blob/8e07d8ff373b19e37a9b6d45f6b437f48833754b/tools/fob_jobextra.py), [fob_gpu_hooks.sh](https://github.com/ChaosTheory1075/infamous-ps5/blob/8e07d8ff373b19e37a9b6d45f6b437f48833754b/tools/fob_gpu_hooks.sh), [SPU contention](https://github.com/ChaosTheory1075/infamous-ps5/blob/8e07d8ff373b19e37a9b6d45f6b437f48833754b/tools/patch_spu_contention.py), [DONTFLIP](https://github.com/ChaosTheory1075/infamous-ps5/blob/8e07d8ff373b19e37a9b6d45f6b437f48833754b/DONTFLIP.md) |
| [B — inFAMOUS 2 Recomp](https://github.com/erikomis/infamous2-recomp) | [61ad6ff](https://github.com/erikomis/infamous2-recomp/tree/61ad6ffd826dc6d1f32bf78ccbaa4ab98352f980) | [main.cpp](https://github.com/erikomis/infamous2-recomp/blob/61ad6ffd826dc6d1f32bf78ccbaa4ab98352f980/infamous2-lle/main.cpp), [rebuild.py](https://github.com/erikomis/infamous2-recomp/blob/61ad6ffd826dc6d1f32bf78ccbaa4ab98352f980/infamous2-lle/tools/rebuild.py), [README LLE](https://github.com/erikomis/infamous2-recomp/blob/61ad6ffd826dc6d1f32bf78ccbaa4ab98352f980/infamous2-lle/README.md), [game_clock.c](https://github.com/erikomis/infamous2-recomp/blob/61ad6ffd826dc6d1f32bf78ccbaa4ab98352f980/infamous2-lle/game_clock.c) |
| [C — RPCS3 Optimizations](https://github.com/ttmx/rpcs3-infamous2) | [22c57ff](https://github.com/ttmx/rpcs3-infamous2/tree/22c57ff052c142667f7856ea44e123ab58776237) | [Festival README](https://github.com/ttmx/rpcs3-infamous2/blob/22c57ff052c142667f7856ea44e123ab58776237/festival/README.md), [infamous_titles.h](https://github.com/ttmx/rpcs3-infamous2/blob/22c57ff052c142667f7856ea44e123ab58776237/rpcs3/Emu/infamous_titles.h), [SSAO](https://github.com/ttmx/rpcs3-infamous2/blob/22c57ff052c142667f7856ea44e123ab58776237/rpcs3/Emu/RSX/VK/VKNativeSSAO.cpp), [Lighting](https://github.com/ttmx/rpcs3-infamous2/blob/22c57ff052c142667f7856ea44e123ab58776237/rpcs3/Emu/RSX/VK/VKNativeLighting.cpp) |

## A: componentes aproveitáveis — recomp da mesma edição americana

O projeto A descreve um recomp para PS5 de inFAMOUS 1, 2 e **Festival of Blood NPUA80657**, exatamente nosso Title ID. Usa um fork de ps3recomp no commit base 770660a3971b87a453677e46125e5e01ac7891c0, além dos templates do projeto B. Nosso runtime atual está baseado na série de patches destinada ao ps3recomp de4f090: **não fazer merge de forks sem revisão de APIs, conflitos e testes**.

A script fob_build.sh declara 302 imports de firmware, ajuste de limite de código PPU para 0x781AA0, módulo policy SPU em guest 0x0092D900 e imagem SPU inicial em 0x00842080. Esses números são dados do port A e **não foram reverificados contra o EBOOT local do usuário nesta revisão**. Cada offset deve ser conferido contra versão/hash e layout carregado.

fob_spu.sh compara hash de imagens extraídas; fob_jobmods.py usa correspondências entre palavras de 32 bits; fob_jobextra.py confere sequências nos destinos adicionais de job modules. fob_gpu_hooks.sh adapta um job de oclusão e outro de iluminação entre jogos, com mudanças conscientes de IDs e endereços. **Aproveitável:** estratégia de verificar fingerprints e destinos antes de relift, não copiar cegamente endereços ou corpos recompilados.

O script patch_spu_contention.py aponta três candidatos de contenção PPU/SPU: contador atômico de PUTLLC, marcação compartilhada de linhas de reserva e acordar esperadores após gravações. O próprio arquivo afirma usar profiling de FoB. A investigação é pertinente ao nosso tempo de espera de jobs. **Cuidado máximo:** DONTFLIP.md registra travamentos por perda de ordenação de memória e outros ajustes SPU, inclusive sinalização SPURS. Não desativar fences, sinais, validação ou coerência para simular avanço.

O README A relata aproximadamente 30 FPS no PS5, mas também usa geração de quadros; o autor deixa claro que frame generation NÃO aumenta a velocidade real de simulação. Não usar esses FPS como benchmark do nosso Windows.

**Decisão:** prioridade alta ao estudo de SPURS, conclusão de jobs, entry points e profiling de coerência; baixa a launcher PS5, FSR e frame generation antes de resolver travamento e imagem.

## B: componentes aproveitáveis — arquitetura estática e rebuild

O main.cpp LLE registra funções PPU levantadas, carrega o ELF guest, configura HLE/NIDs, inicializa VM/relógio e despacha o entry OPD. O próprio comentário do arquivo indica boot_main.cpp do toolkit para watchdog e profiling. Isto **confirma RECOMP**, não reescrita manual de gameplay.

rebuild.py separa preparação, firmware, tradução PPU/SPU/jobs e compilação; verifica versão e hashes antes de aplicar pontos fixos; usa cache de estado para rebuild incremental; diferencia falhas e etapas em formato estruturado. A edição alvo de B é NPUA80638 (inFAMOUS 2): não importar diretamente offsets, checksums, stubs ou nomes de funções no FoB NPUA80657.

game_clock.c expõe a diferença entre taxa de apresentação, vblank e delta temporal de simulação. Os endereços guest nesse arquivo são do inFAMOUS 2. Para FoB, medir contadores de quadros e ritmo de jobs separadamente: Draws 79/80 não demonstra sozinho CPU travada.

**Decisão:** aproveitar estrutura de verificação de versão, rebuild incremental, guardas, testes sintéticos e investigação de pontos de retorno SPU. Não trocar o firmware/runtime funcional inteiro sem regressão isolada.

## C: componentes aproveitáveis — sem usar emulador

A implementação C investiga **NPEA00322 (Europa)**, e NÃO NPUA80657. infamous_titles.h separa por Title ID os buffers de normais, depth, scratch SSAO, matriz, parâmetros de luz e cinco kernels SPU. Endereços europeus (como buffers e entrada de jobs) **não são portáveis por suposição**.

VKNativeSSAO.cpp documenta cinco passes GPU para profundidade linear, amostragem de oclusão, dois blurs e upsampling. VKNativeLighting.cpp usa tiles 40×18, luzes e parâmetros extraídos das estruturas guest, calcula o equivalente de trabalho SPU em compute passes e usa fallback quando o tipo de luz não é suportado. A motivação é eliminar viagens redundantes GPU → RAM guest → SPU → GPU.

O relatório do autor registra 29,5 → 89,2 FPS *uncapped* no corredor inicial em RPCS3 Vulkan/Linux, Radeon 780M, com um conjunto de otimizações. São números do **emulador** e de **outra edição/hardware**, não uma promessa para nosso recomp Windows D3D12. O relatório também documenta flicker de glare com sincronização ZCULL relaxada e que as cenas fora das catacumbas não foram validadas. Não sacrificar sincronização visual.

**Decisão:** usar como referência de semântica de texturas, G-buffer, iluminação, oclusão e readback. Implementar substituição opcional dos jobs por GPU somente após testes de equivalência e fallback para código recompilado; não é prioridade enquanto a composição de cor está errada.

## Nosso estado e prioridades

| Evidência nossa | Hipótese aproveitável | Gate exigido |
| --- | --- | --- |
| PPU repete func_002B0B74 → func_003A9E68 → func_00580A40; mínimo de sete campos u16 abaixo do alvo, observado objeto geral 0x00B50C80, alvo 0x01D6 e mínimo 0x01D2 | A: SPURS/coerência; B: pontos extras de jobs | Rastrear cada campo, trabalhador, último escritor e PUTLLC; identificar divergência real; NÃO incrementar o contador artificialmente |
| Lotes D3D12 de ~70–74 ms GPU, composição ~23 ms GPU, mas pausas próximas de dois segundos; usuário observou ~0,71 FPS | A: wait-site profiling e coerência; B: relógio real da simulação | CPU, SPU, GPU e intervalos entre lotes na mesma janela, sem overhead de dump; provar que otimização preserva estados e melhora FPS sustentado |
| Corredor 3D aparece mas em verde/laranja e quadros pretos | C: tipos color/depth, SSAO, lighting, conversões | Capturar mesmo frame nos render targets, sampler e backbuffer; localizar primeira passagem divergente; Bink splash não pode regredir |
| Jobs raw capturados no boot | A: correspondências com IF2 | Validar bytes, tamanhos, hash e pontos de entrada com a cópia local; sem upload de código do jogo |

Registro de contexto: docs/BINK-VIDEO-NPUA80657.md, branch do PR #5. O patch 0009 já procura reduzir trabalho duplicado de PSO; não repetir cegamente.

### Sequência de trabalho recomendada

**P0 / sincronização:** trace limitado do objeto geral de jobs, seus sete contadores, target, guest-PC e worker SPU; correlacionar com alterações de linha de reserva. Repetir dois boots e identificar o job cujo progresso é esperado mas não chega. Alterar apenas a primeira divergência comprovada.

**P0 / fidelidade visual:** mapear passes color/depth desde G-buffer até backbuffer, preservando 0004–0009 e registrando custo da instrumentação. Nenhum bypass de draws ou cores forçadas.

**P1 / FPS real:** A/B idêntico no Windows, diagnósticos pesados off, tempos CPU/GPU por estágio, medianas e p95 de frames, progresso real da simulação. Só então avaliar redução de contenda atômica e readbacks; validar coerência PPU/SPU, save, áudio, menu e boot.

**P2 / fingerprint local:** ferramenta nova tools/compare_spu_modules.py com testes sintéticos. Com **ambas as edições legalmente disponíveis localmente**, comparar raw job modules *.bin de 4 bytes por palavra. SHA-256 igual confirma identidade de bytes; score alto do SequenceMatcher indica apenas candidato (precisa validar branches, relocations, estado e efeitos). Não é necessário possuir inFAMOUS 2 para continuar as tarefas P0.

Exemplo, se essas pastas existirem localmente:

    py tools/compare_spu_modules.py --left out/if2-jobmods --right out/fob-jobmods --json out/spu-cross-title-report.json
    py -m unittest discover -s tests -v

### Licenças e limites

Projeto A: GPL-3.0 com componentes de diversas licenças; C: GPL-2.0; B: MIT declarado em LICENSE. **Não copiar implementações GPL A/C para nosso runtime sem revisão e cumprimento de obrigações**. A ferramenta SPU desta branch é implementação original de uma verificação genérica, sem incorporar fonte A/C. Não enviar EBOOT, PKG, assets, firmware, logs com código ou dados guest, dumps SPU ou gerados de recomp para GitHub. Usar pastas privadas ignoradas pelo Git.

**Resultado desta branch:** documentação auditável + testes sintéticos; nenhum ganho de FPS ou fix de render foi alegado.

## Aprofundamento: execução de SPU, reaproveitamento seguro e desempenho

A segunda inspeção examinou implementações em vez de apenas arquitetura e README:

1. **A: [patch_spu_contention.py](https://github.com/ChaosTheory1075/infamous-ps5/blob/8e07d8ff373b19e37a9b6d45f6b437f48833754b/tools/patch_spu_contention.py)** mostra contenção causada por um contador global de PUTLLC, marcação de linhas de reserva e geração de wake-up. É candidato **P1 de benchmark A/B**, não um ajuste automático: mudanças em ordenação atômica devem respeitar o modelo SPU/PPU. [DONTFLIP.md](https://github.com/ChaosTheory1075/infamous-ps5/blob/8e07d8ff373b19e37a9b6d45f6b437f48833754b/DONTFLIP.md) registra regressões reais ao enfraquecer fences/coerência.
2. **A: [patch_spu_pollwake.py](https://github.com/ChaosTheory1075/infamous-ps5/blob/8e07d8ff373b19e37a9b6d45f6b437f48833754b/tools/patch_spu_pollwake.py)** distingue SPU acordada por produtor de SPU que detectou mudança só no re-poll. Abordagem apropriada para a investigação do job geral: instrumentar a linha guest específica do contador e confirmar se o produtor emite evento LR. Não adicionar polling global sem prova.
3. **A: [patch_spin_waits.py](https://github.com/ChaosTheory1075/infamous-ps5/blob/8e07d8ff373b19e37a9b6d45f6b437f48833754b/tools/patch_spin_waits.py)** implementa espera curta configurável antes de bloquear em condição. Só testar depois de medir a frequência e o tipo de wake; um spin excessivo pode consumir núcleos SPU e piorar a latência.
4. **B: [lift_relocmods.py](https://github.com/erikomis/infamous2-recomp/blob/61ad6ffd826dc6d1f32bf78ccbaa4ab98352f980/infamous2-lle/tools/lift_relocmods.py)** documenta cerca de 30 overlays SPU position-independent carregados em diferentes LS; a ausência de tradução relocável provocou queda para 11–14 FPS no inFAMOUS 2 do autor. **Isso não prova que FoB tem os mesmos overlays**, mas justifica buscá-los no EBOOT local antes de atribuir toda lentidão ao D3D12.
5. **B: [relift_jobmod.py](https://github.com/erikomis/infamous2-recomp/blob/61ad6ffd826dc6d1f32bf78ccbaa4ab98352f980/infamous2-lle/tools/relift_jobmod.py)** aceita --extra para pontos de entrada adicionais detectados em retornos para código não traduzido. **A: [fob_jobextra.py](https://github.com/ChaosTheory1075/infamous-ps5/blob/8e07d8ff373b19e37a9b6d45f6b437f48833754b/tools/fob_jobextra.py)** localiza janelas exatas entre dois jobmods, mas requer checar base da LS e offsets relativos. A ferramenta nova abaixo aplica esse critério, rejeitando janelas ambíguas.
6. **C: [VKNativeLighting.cpp](https://github.com/ttmx/rpcs3-infamous2/blob/22c57ff052c142667f7856ea44e123ab58776237/rpcs3/Emu/RSX/VK/VKNativeLighting.cpp)** e [VKNativeSSAO.cpp](https://github.com/ttmx/rpcs3-infamous2/blob/22c57ff052c142667f7856ea44e123ab58776237/rpcs3/Emu/RSX/VK/VKNativeSSAO.cpp) documentam substituição da computação SPU por passes GPU com fallback, remoção de readbacks redundantes e limites de semântica. **Não portar agora**: enquanto nossa saída tem cores verdes/laranjas, substituir iluminação poderia encobrir a divergência primária.

### Novo diagnóstico local, sem mexer no runtime

O utilitário [tools/inspect_spu_overlays.py](../tools/inspect_spu_overlays.py), de implementação original, oferece dois subcomandos **somente leitura**:

```bat
py tools/inspect_spu_overlays.py scan "private\game\EBOOT.elf" --json "out\spu-overlay-candidates.json"
py tools/inspect_spu_overlays.py entries "out\if2-jobmods\exemplo.bin" "out\fob-jobmods\exemplo.bin" --offsets 0x30,0x40 --json "out\spu-extra-entry-candidates.json"
```

O primeiro busca assinatura potencial de overlay; **não considera o match uma função comprovada** e não assume a conversão file offset → guest EA sem validar o PT_LOAD. O segundo localiza janelas de instruções byte-idênticas e únicas para orientar relift; **não traduz**, não altera o jogo e não atribui automaticamente base LS. Arquivos de exemplo e caminhos precisam existir; o segundo comando é ilustrativo. Só publique a *ferramenta e testes sintéticos*, nunca os insumos proprietários ou relatórios com dados de memória.

### Portão antes de otimizar o jogo

1. Em dois boots limpos, obter o último evento que mudou o mínimo dos sete campos para o objeto geral e identificar qual lane ficou atrás.
2. Relacionar a lane atrasada com job, worker, local store, PUTLLC e wake-up. Determinar se o progresso cai no interpretador por overlay não registrado ou se existe erro de coerência/sinalização.
3. Corrigir apenas divergência comprovada; comparar FPS real e integridade de quadros com as mesmas configurações. Não forçar o contador, pular trabalho SPU nem maquiar o FPS.
