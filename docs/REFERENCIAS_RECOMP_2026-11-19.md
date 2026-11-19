# Auditoria tÃ©cnica: trÃªs referÃªncias para RECOMP de Festival of Blood (Windows)

**Data:** 19/11/2026. **Jogo:** inFAMOUS: Festival of Blood, NPUA80657 (PSN EUA).  
**Arquitetura inegociÃ¡vel:** PPU e SPU traduzidos estaticamente por ps3recomp, com runtime nativo Windows. DECOMP apenas para interpretar comportamento. RPCS3 apenas como referÃªncia, nÃ£o como emulador embutido.

**Escopo realizado:** leitura de cÃ³digo e documentaÃ§Ã£o pÃºblicos, comparaÃ§Ã£o com os relatÃ³rios do nosso projeto e ferramenta offline original com cinco testes sintÃ©ticos. Esta revisÃ£o NÃƒO executou o jogo no PC, NÃƒO corrigiu FPS, NÃƒO corrigiu a composiÃ§Ã£o 3D e NÃƒO prova independemente os FPS relatados por terceiros.

## ReferÃªncias fixadas

| Origem | Commit inspecionado | Trechos relevantes |
| --- | --- | --- |
| [A â€” inFAMOUS: ReCharged](https://github.com/ChaosTheory1075/infamous-ps5) | [8e07d8f](https://github.com/ChaosTheory1075/infamous-ps5/tree/8e07d8ff373b19e37a9b6d45f6b437f48833754b) | [README](https://github.com/ChaosTheory1075/infamous-ps5/blob/8e07d8ff373b19e37a9b6d45f6b437f48833754b/README.md), [fob_build.sh](https://github.com/ChaosTheory1075/infamous-ps5/blob/8e07d8ff373b19e37a9b6d45f6b437f48833754b/tools/fob_build.sh), [fob_spu.sh](https://github.com/ChaosTheory1075/infamous-ps5/blob/8e07d8ff373b19e37a9b6d45f6b437f48833754b/tools/fob_spu.sh), [fob_jobmods.py](https://github.com/ChaosTheory1075/infamous-ps5/blob/8e07d8ff373b19e37a9b6d45f6b437f48833754b/tools/fob_jobmods.py), [fob_jobextra.py](https://github.com/ChaosTheory1075/infamous-ps5/blob/8e07d8ff373b19e37a9b6d45f6b437f48833754b/tools/fob_jobextra.py), [fob_gpu_hooks.sh](https://github.com/ChaosTheory1075/infamous-ps5/blob/8e07d8ff373b19e37a9b6d45f6b437f48833754b/tools/fob_gpu_hooks.sh), [SPU contention](https://github.com/ChaosTheory1075/infamous-ps5/blob/8e07d8ff373b19e37a9b6d45f6b437f48833754b/tools/patch_spu_contention.py), [DONTFLIP](https://github.com/ChaosTheory1075/infamous-ps5/blob/8e07d8ff373b19e37a9b6d45f6b437f48833754b/DONTFLIP.md) |
| [B â€” inFAMOUS 2 Recomp](https://github.com/erikomis/infamous2-recomp) | [61ad6ff](https://github.com/erikomis/infamous2-recomp/tree/61ad6ffd826dc6d1f32bf78ccbaa4ab98352f980) | [main.cpp](https://github.com/erikomis/infamous2-recomp/blob/61ad6ffd826dc6d1f32bf78ccbaa4ab98352f980/infamous2-lle/main.cpp), [rebuild.py](https://github.com/erikomis/infamous2-recomp/blob/61ad6ffd826dc6d1f32bf78ccbaa4ab98352f980/infamous2-lle/tools/rebuild.py), [README LLE](https://github.com/erikomis/infamous2-recomp/blob/61ad6ffd826dc6d1f32bf78ccbaa4ab98352f980/infamous2-lle/README.md), [game_clock.c](https://github.com/erikomis/infamous2-recomp/blob/61ad6ffd826dc6d1f32bf78ccbaa4ab98352f980/infamous2-lle/game_clock.c) |
| [C â€” RPCS3 Optimizations](https://github.com/ttmx/rpcs3-infamous2) | [22c57ff](https://github.com/ttmx/rpcs3-infamous2/tree/22c57ff052c142667f7856ea44e123ab58776237) | [Festival README](https://github.com/ttmx/rpcs3-infamous2/blob/22c57ff052c142667f7856ea44e123ab58776237/festival/README.md), [infamous_titles.h](https://github.com/ttmx/rpcs3-infamous2/blob/22c57ff052c142667f7856ea44e123ab58776237/rpcs3/Emu/infamous_titles.h), [SSAO](https://github.com/ttmx/rpcs3-infamous2/blob/22c57ff052c142667f7856ea44e123ab58776237/rpcs3/Emu/RSX/VK/VKNativeSSAO.cpp), [Lighting](https://github.com/ttmx/rpcs3-infamous2/blob/22c57ff052c142667f7856ea44e123ab58776237/rpcs3/Emu/RSX/VK/VKNativeLighting.cpp) |

## A: componentes aproveitÃ¡veis â€” recomp da mesma ediÃ§Ã£o americana

O projeto A descreve um recomp para PS5 de inFAMOUS 1, 2 e **Festival of Blood NPUA80657**, exatamente nosso Title ID. Usa um fork de ps3recomp no commit base 770660a3971b87a453677e46125e5e01ac7891c0, alÃ©m dos templates do projeto B. Nosso runtime atual estÃ¡ baseado na sÃ©rie de patches destinada ao ps3recomp de4f090: **nÃ£o fazer merge de forks sem revisÃ£o de APIs, conflitos e testes**.

A script fob_build.sh declara 302 imports de firmware, ajuste de limite de cÃ³digo PPU para 0x781AA0, mÃ³dulo policy SPU em guest 0x0092D900 e imagem SPU inicial em 0x00842080. Esses nÃºmeros sÃ£o dados do port A e **nÃ£o foram reverificados contra o EBOOT local do usuÃ¡rio nesta revisÃ£o**. Cada offset deve ser conferido contra versÃ£o/hash e layout carregado.

fob_spu.sh compara hash de imagens extraÃ­das; fob_jobmods.py usa correspondÃªncias entre palavras de 32 bits; fob_jobextra.py confere sequÃªncias nos destinos adicionais de job modules. fob_gpu_hooks.sh adapta um job de oclusÃ£o e outro de iluminaÃ§Ã£o entre jogos, com mudanÃ§as conscientes de IDs e endereÃ§os. **AproveitÃ¡vel:** estratÃ©gia de verificar fingerprints e destinos antes de relift, nÃ£o copiar cegamente endereÃ§os ou corpos recompilados.

O script patch_spu_contention.py aponta trÃªs candidatos de contenÃ§Ã£o PPU/SPU: contador atÃ´mico de PUTLLC, marcaÃ§Ã£o compartilhada de linhas de reserva e acordar esperadores apÃ³s gravaÃ§Ãµes. O prÃ³prio arquivo afirma usar profiling de FoB. A investigaÃ§Ã£o Ã© pertinente ao nosso tempo de espera de jobs. **Cuidado mÃ¡ximo:** DONTFLIP.md registra travamentos por perda de ordenaÃ§Ã£o de memÃ³ria e outros ajustes SPU, inclusive sinalizaÃ§Ã£o SPURS. NÃ£o desativar fences, sinais, validaÃ§Ã£o ou coerÃªncia para simular avanÃ§o.

O README A relata aproximadamente 30 FPS no PS5, mas tambÃ©m usa geraÃ§Ã£o de quadros; o autor deixa claro que frame generation NÃƒO aumenta a velocidade real de simulaÃ§Ã£o. NÃ£o usar esses FPS como benchmark do nosso Windows.

**DecisÃ£o:** prioridade alta ao estudo de SPURS, conclusÃ£o de jobs, entry points e profiling de coerÃªncia; baixa a launcher PS5, FSR e frame generation antes de resolver travamento e imagem.

## B: componentes aproveitÃ¡veis â€” arquitetura estÃ¡tica e rebuild

O main.cpp LLE registra funÃ§Ãµes PPU levantadas, carrega o ELF guest, configura HLE/NIDs, inicializa VM/relÃ³gio e despacha o entry OPD. O prÃ³prio comentÃ¡rio do arquivo indica boot_main.cpp do toolkit para watchdog e profiling. Isto **confirma RECOMP**, nÃ£o reescrita manual de gameplay.

rebuild.py separa preparaÃ§Ã£o, firmware, traduÃ§Ã£o PPU/SPU/jobs e compilaÃ§Ã£o; verifica versÃ£o e hashes antes de aplicar pontos fixos; usa cache de estado para rebuild incremental; diferencia falhas e etapas em formato estruturado. A ediÃ§Ã£o alvo de B Ã© NPUA80638 (inFAMOUS 2): nÃ£o importar diretamente offsets, checksums, stubs ou nomes de funÃ§Ãµes no FoB NPUA80657.

game_clock.c expÃµe a diferenÃ§a entre taxa de apresentaÃ§Ã£o, vblank e delta temporal de simulaÃ§Ã£o. Os endereÃ§os guest nesse arquivo sÃ£o do inFAMOUS 2. Para FoB, medir contadores de quadros e ritmo de jobs separadamente: Draws 79/80 nÃ£o demonstra sozinho CPU travada.

**DecisÃ£o:** aproveitar estrutura de verificaÃ§Ã£o de versÃ£o, rebuild incremental, guardas, testes sintÃ©ticos e investigaÃ§Ã£o de pontos de retorno SPU. NÃ£o trocar o firmware/runtime funcional inteiro sem regressÃ£o isolada.

## C: componentes aproveitÃ¡veis â€” sem usar emulador

A implementaÃ§Ã£o C investiga **NPEA00322 (Europa)**, e NÃƒO NPUA80657. infamous_titles.h separa por Title ID os buffers de normais, depth, scratch SSAO, matriz, parÃ¢metros de luz e cinco kernels SPU. EndereÃ§os europeus (como buffers e entrada de jobs) **nÃ£o sÃ£o portÃ¡veis por suposiÃ§Ã£o**.

VKNativeSSAO.cpp documenta cinco passes GPU para profundidade linear, amostragem de oclusÃ£o, dois blurs e upsampling. VKNativeLighting.cpp usa tiles 40Ã—18, luzes e parÃ¢metros extraÃ­dos das estruturas guest, calcula o equivalente de trabalho SPU em compute passes e usa fallback quando o tipo de luz nÃ£o Ã© suportado. A motivaÃ§Ã£o Ã© eliminar viagens redundantes GPU â†’ RAM guest â†’ SPU â†’ GPU.

O relatÃ³rio do autor registra 29,5 â†’ 89,2 FPS *uncapped* no corredor inicial em RPCS3 Vulkan/Linux, Radeon 780M, com um conjunto de otimizaÃ§Ãµes. SÃ£o nÃºmeros do **emulador** e de **outra ediÃ§Ã£o/hardware**, nÃ£o uma promessa para nosso recomp Windows D3D12. O relatÃ³rio tambÃ©m documenta flicker de glare com sincronizaÃ§Ã£o ZCULL relaxada e que as cenas fora das catacumbas nÃ£o foram validadas. NÃ£o sacrificar sincronizaÃ§Ã£o visual.

**DecisÃ£o:** usar como referÃªncia de semÃ¢ntica de texturas, G-buffer, iluminaÃ§Ã£o, oclusÃ£o e readback. Implementar substituiÃ§Ã£o opcional dos jobs por GPU somente apÃ³s testes de equivalÃªncia e fallback para cÃ³digo recompilado; nÃ£o Ã© prioridade enquanto a composiÃ§Ã£o de cor estÃ¡ errada.

## Nosso estado e prioridades

| EvidÃªncia nossa | HipÃ³tese aproveitÃ¡vel | Gate exigido |
| --- | --- | --- |
| PPU repete func_002B0B74 â†’ func_003A9E68 â†’ func_00580A40; mÃ­nimo de sete campos u16 abaixo do alvo, observado objeto geral 0x00B50C80, alvo 0x01D6 e mÃ­nimo 0x01D2 | A: SPURS/coerÃªncia; B: pontos extras de jobs | Rastrear cada campo, trabalhador, Ãºltimo escritor e PUTLLC; identificar divergÃªncia real; NÃƒO incrementar o contador artificialmente |
| Lotes D3D12 de ~70â€“74 ms GPU, composiÃ§Ã£o ~23 ms GPU, mas pausas prÃ³ximas de dois segundos; usuÃ¡rio observou ~0,71 FPS | A: wait-site profiling e coerÃªncia; B: relÃ³gio real da simulaÃ§Ã£o | CPU, SPU, GPU e intervalos entre lotes na mesma janela, sem overhead de dump; provar que otimizaÃ§Ã£o preserva estados e melhora FPS sustentado |
| Corredor 3D aparece mas em verde/laranja e quadros pretos | C: tipos color/depth, SSAO, lighting, conversÃµes | Capturar mesmo frame nos render targets, sampler e backbuffer; localizar primeira passagem divergente; Bink splash nÃ£o pode regredir |
| Jobs raw capturados no boot | A: correspondÃªncias com IF2 | Validar bytes, tamanhos, hash e pontos de entrada com a cÃ³pia local; sem upload de cÃ³digo do jogo |

Registro de contexto: docs/BINK-VIDEO-NPUA80657.md, branch do PR #5. O patch 0009 jÃ¡ procura reduzir trabalho duplicado de PSO; nÃ£o repetir cegamente.

### SequÃªncia de trabalho recomendada

**P0 / sincronizaÃ§Ã£o:** trace limitado do objeto geral de jobs, seus sete contadores, target, guest-PC e worker SPU; correlacionar com alteraÃ§Ãµes de linha de reserva. Repetir dois boots e identificar o job cujo progresso Ã© esperado mas nÃ£o chega. Alterar apenas a primeira divergÃªncia comprovada.

**P0 / fidelidade visual:** mapear passes color/depth desde G-buffer atÃ© backbuffer, preservando 0004â€“0009 e registrando custo da instrumentaÃ§Ã£o. Nenhum bypass de draws ou cores forÃ§adas.

**P1 / FPS real:** A/B idÃªntico no Windows, diagnÃ³sticos pesados off, tempos CPU/GPU por estÃ¡gio, medianas e p95 de frames, progresso real da simulaÃ§Ã£o. SÃ³ entÃ£o avaliar reduÃ§Ã£o de contenda atÃ´mica e readbacks; validar coerÃªncia PPU/SPU, save, Ã¡udio, menu e boot.

**P2 / fingerprint local:** ferramenta nova tools/compare_spu_modules.py com testes sintÃ©ticos. Com **ambas as ediÃ§Ãµes legalmente disponÃ­veis localmente**, comparar raw job modules *.bin de 4 bytes por palavra. SHA-256 igual confirma identidade de bytes; score alto do SequenceMatcher indica apenas candidato (precisa validar branches, relocations, estado e efeitos). NÃ£o Ã© necessÃ¡rio possuir inFAMOUS 2 para continuar as tarefas P0.

Exemplo, se essas pastas existirem localmente:

    py tools/compare_spu_modules.py --left out/if2-jobmods --right out/fob-jobmods --json out/spu-cross-title-report.json
    py -m unittest discover -s tests -v

### LicenÃ§as e limites

Projeto A: GPL-3.0 com componentes de diversas licenÃ§as; C: GPL-2.0; B: MIT declarado em LICENSE. **NÃ£o copiar implementaÃ§Ãµes GPL A/C para nosso runtime sem revisÃ£o e cumprimento de obrigaÃ§Ãµes**. A ferramenta SPU desta branch Ã© implementaÃ§Ã£o original de uma verificaÃ§Ã£o genÃ©rica, sem incorporar fonte A/C. NÃ£o enviar EBOOT, PKG, assets, firmware, logs com cÃ³digo ou dados guest, dumps SPU ou gerados de recomp para GitHub. Usar pastas privadas ignoradas pelo Git.

**Resultado desta branch:** documentaÃ§Ã£o auditÃ¡vel + testes sintÃ©ticos; nenhum ganho de FPS ou fix de render foi alegado.

## Aprofundamento: execuÃ§Ã£o de SPU, reaproveitamento seguro e desempenho

A segunda inspeÃ§Ã£o examinou implementaÃ§Ãµes em vez de apenas arquitetura e README:

1. **A: [patch_spu_contention.py](https://github.com/ChaosTheory1075/infamous-ps5/blob/8e07d8ff373b19e37a9b6d45f6b437f48833754b/tools/patch_spu_contention.py)** mostra contenÃ§Ã£o causada por um contador global de PUTLLC, marcaÃ§Ã£o de linhas de reserva e geraÃ§Ã£o de wake-up. Ã‰ candidato **P1 de benchmark A/B**, nÃ£o um ajuste automÃ¡tico: mudanÃ§as em ordenaÃ§Ã£o atÃ´mica devem respeitar o modelo SPU/PPU. [DONTFLIP.md](https://github.com/ChaosTheory1075/infamous-ps5/blob/8e07d8ff373b19e37a9b6d45f6b437f48833754b/DONTFLIP.md) registra regressÃµes reais ao enfraquecer fences/coerÃªncia.
2. **A: [patch_spu_pollwake.py](https://github.com/ChaosTheory1075/infamous-ps5/blob/8e07d8ff373b19e37a9b6d45f6b437f48833754b/tools/patch_spu_pollwake.py)** distingue SPU acordada por produtor de SPU que detectou mudanÃ§a sÃ³ no re-poll. Abordagem apropriada para a investigaÃ§Ã£o do job geral: instrumentar a linha guest especÃ­fica do contador e confirmar se o produtor emite evento LR. NÃ£o adicionar polling global sem prova.
3. **A: [patch_spin_waits.py](https://github.com/ChaosTheory1075/infamous-ps5/blob/8e07d8ff373b19e37a9b6d45f6b437f48833754b/tools/patch_spin_waits.py)** implementa espera curta configurÃ¡vel antes de bloquear em condiÃ§Ã£o. SÃ³ testar depois de medir a frequÃªncia e o tipo de wake; um spin excessivo pode consumir nÃºcleos SPU e piorar a latÃªncia.
4. **B: [lift_relocmods.py](https://github.com/erikomis/infamous2-recomp/blob/61ad6ffd826dc6d1f32bf78ccbaa4ab98352f980/infamous2-lle/tools/lift_relocmods.py)** documenta cerca de 30 overlays SPU position-independent carregados em diferentes LS; a ausÃªncia de traduÃ§Ã£o relocÃ¡vel provocou queda para 11â€“14 FPS no inFAMOUS 2 do autor. **Isso nÃ£o prova que FoB tem os mesmos overlays**, mas justifica buscÃ¡-los no EBOOT local antes de atribuir toda lentidÃ£o ao D3D12.
5. **B: [relift_jobmod.py](https://github.com/erikomis/infamous2-recomp/blob/61ad6ffd826dc6d1f32bf78ccbaa4ab98352f980/infamous2-lle/tools/relift_jobmod.py)** aceita --extra para pontos de entrada adicionais detectados em retornos para cÃ³digo nÃ£o traduzido. **A: [fob_jobextra.py](https://github.com/ChaosTheory1075/infamous-ps5/blob/8e07d8ff373b19e37a9b6d45f6b437f48833754b/tools/fob_jobextra.py)** localiza janelas exatas entre dois jobmods, mas requer checar base da LS e offsets relativos. A ferramenta nova abaixo aplica esse critÃ©rio, rejeitando janelas ambÃ­guas.
6. **C: [VKNativeLighting.cpp](https://github.com/ttmx/rpcs3-infamous2/blob/22c57ff052c142667f7856ea44e123ab58776237/rpcs3/Emu/RSX/VK/VKNativeLighting.cpp)** e [VKNativeSSAO.cpp](https://github.com/ttmx/rpcs3-infamous2/blob/22c57ff052c142667f7856ea44e123ab58776237/rpcs3/Emu/RSX/VK/VKNativeSSAO.cpp) documentam substituiÃ§Ã£o da computaÃ§Ã£o SPU por passes GPU com fallback, remoÃ§Ã£o de readbacks redundantes e limites de semÃ¢ntica. **NÃ£o portar agora**: enquanto nossa saÃ­da tem cores verdes/laranjas, substituir iluminaÃ§Ã£o poderia encobrir a divergÃªncia primÃ¡ria.

### Novo diagnÃ³stico local, sem mexer no runtime

O utilitÃ¡rio [tools/inspect_spu_overlays.py](../tools/inspect_spu_overlays.py), de implementaÃ§Ã£o original, oferece três subcomandos **somente leitura**:

```bat
py tools/inspect_spu_overlays.py scan "private\game\EBOOT.elf" --json "out\spu-overlay-candidates.json"
py tools/inspect_spu_overlays.py entries "out\if2-jobmods\exemplo.bin" "out\fob-jobmods\exemplo.bin" --offsets 0x30,0x40 --json "out\spu-extra-entry-candidates.json"
```

O primeiro busca assinatura potencial de overlay; **nÃ£o considera o match uma funÃ§Ã£o comprovada** e nÃ£o assume a conversÃ£o file offset â†’ guest EA sem validar o PT_LOAD. O segundo localiza janelas de instruÃ§Ãµes byte-idÃªnticas e Ãºnicas para orientar relift; **nÃ£o traduz**, nÃ£o altera o jogo e nÃ£o atribui automaticamente base LS. Arquivos de exemplo e caminhos precisam existir; o segundo comando Ã© ilustrativo. SÃ³ publique a *ferramenta e testes sintÃ©ticos*, nunca os insumos proprietÃ¡rios ou relatÃ³rios com dados de memÃ³ria.

### PortÃ£o antes de otimizar o jogo

1. Em dois boots limpos, obter o Ãºltimo evento que mudou o mÃ­nimo dos sete campos para o objeto geral e identificar qual lane ficou atrÃ¡s.
2. Relacionar a lane atrasada com job, worker, local store, PUTLLC e wake-up. Determinar se o progresso cai no interpretador por overlay nÃ£o registrado ou se existe erro de coerÃªncia/sinalizaÃ§Ã£o.
3. Corrigir apenas divergÃªncia comprovada; comparar FPS real e integridade de quadros com as mesmas configuraÃ§Ãµes. NÃ£o forÃ§ar o contador, pular trabalho SPU nem maquiar o FPS.

## Terceira inspeÃ§Ã£o de cÃ³digo: falhas concretas que se parecem com nosso boot

**Revisado em 19/11/2026.** A anÃ¡lise anterior jÃ¡ identificava o problema de conclusÃ£o de jobs e a composiÃ§Ã£o D3D12. Esta seÃ§Ã£o detalha **trÃªs famÃ­lias** de mÃ³dulos SPU e confirma o que nossa base *jÃ¡ implementa*, para evitar duplicaÃ§Ã£o.

### 1. CÃ³digo SPU por trÃªs mecanismos (nÃ£o confundir)

| Formato/condiÃ§Ã£o | ReferÃªncia do cÃ³digo | Risco se faltar | SituaÃ§Ã£o do nosso projeto |
| --- | --- | --- | --- |
| MÃ³dulo WWS de EBOOT com marcador **C0DEC0DE** e LS base 0x4000 | [B: extract_eboot_jobmods.py](https://github.com/erikomis/infamous2-recomp/blob/61ad6ffd826dc6d1f32bf78ccbaa4ab98352f980/infamous2-lle/tools/extract_eboot_jobmods.py) | Job cai no interpretador ou nÃ£o acha funÃ§Ã£o | JÃ¡ hÃ¡ **27 mÃ³dulos WWS** traduzidos por `tools/prepare_engine_jobmods.py`, com entradas adicionais 0x9548, 0x95D8 e 0x9690. Resultado histÃ³rico local ~8â†’44 FPS; conferir se o build atual ainda os inclui. |
| Segundo mÃ³dulo WWS com marcador **DA7ABA5E**, entrada em LS **0x6C00** | [B: lift_datamods.py](https://github.com/erikomis/infamous2-recomp/blob/61ad6ffd826dc6d1f32bf78ccbaa4ab98352f980/infamous2-lle/tools/lift_datamods.py) | No inFAMOUS 2 do autor, ~22.000 instruÃ§Ãµes interpretadas por chamada e menu ~17 FPS, ~30 apÃ³s lift | **NÃ£o foi comprovado para NPUA80657**. Nova anÃ¡lise read-only com `tools/inspect_spu_overlays.py data`; saÃ­da somente metadados e offsets. |
| Overlay SPU relocÃ¡vel, carregado em **LS variÃ¡vel** | [B: lift_relocmods.py](https://github.com/erikomis/infamous2-recomp/blob/61ad6ffd826dc6d1f32bf78ccbaa4ab98352f980/infamous2-lle/tools/lift_relocmods.py) | EndereÃ§o LS fixo traduzido nÃ£o encontra bloco carregado em outra posiÃ§Ã£o | `tools/inspect_spu_overlays.py scan` jÃ¡ procura candidatos com prologue especÃ­fico, nÃ£o prova identidade. Validar pelo guest EA/GET e registro do runtime. |

**Importante:** examinado o cÃ³digo real da base `sp00nznet/ps3recomp` em commit `de4f090328ea08bef6b2f15caec0b85e343a7ece`:
- `runtime/spu/spu_channels.c`, em `spu_lifted_lookup_full`, considera `resident_code`, `resident_ovl` e offset relocÃ¡vel. A checagem de rejoin apÃ³s `spu_interp_run_until` tambÃ©m chama `spu_lifted_lookup`.
- Portanto **jÃ¡ existe a infraestrutura para reentrar no cÃ³digo recompilado**; o defeito descrito no B (0,4 FPS por rejoin errado) nÃ£o deve ser assumido como ainda presente aqui. Precisamos medir `SPU_INTERP_STATS`, resolver ou nÃ£o cada PC em `resident_code`, e conferir cobertura de mÃ³dulos/entry points no build local.
- `DONTFLIP.md` do projeto A identifica regressÃµes provocadas por mexer em ordenaÃ§Ã£o de memÃ³ria, incluindo perda de sinais SPURS. NÃ£o alterar fences sÃ³ para conseguir progresso.

### 2. O problema conhecido de shader verde jÃ¡ tem uma correÃ§Ã£o na base

O [B: README LLE](https://github.com/erikomis/infamous2-recomp/blob/61ad6ffd826dc6d1f32bf78ccbaa4ab98352f980/infamous2-lle/README.md) registra que fragment shader pack/unpack de `PK4UB/UP4UB/PKG/UPG` ausentes fizeram personagem ficar verde. Contudo o nosso [`rsx_fp_decompiler.c` na base de4f090](https://github.com/sp00nznet/ps3recomp/blob/de4f090328ea08bef6b2f15caec0b85e343a7ece/libs/video/rsx_fp_decompiler.c) **jÃ¡ contÃ©m case OP_PK4UB/OP_UP4UB/OP_PKG/OP_UPG** e as funÃ§Ãµes HLSL de pack/unpack. NÃ£o propor patch duplicado.

Na mesma base, [`rsx_texture_layout.c`](https://github.com/sp00nznet/ps3recomp/blob/de4f090328ea08bef6b2f15caec0b85e343a7ece/libs/video/rsx_texture_layout.c) jÃ¡ decodifica formatos B8, X16 e depth e trabalha com remapeamento de componentes. NÃ£o assumir ausÃªncia total de crossbar.

**Testar agora**: na mesma draw do corredor capturado, comparar entradas de textura com o sampler efetivamente vinculado, bytes A/R/G/B ou depth, valores de FP constantes (`FP_CONSTBUF`), saÃ­da do fragment shader e destino. O caso onde render target de cor e exportaÃ§Ã£o depth ficaram byte-identicamente iguais continua exigindo uma explicaÃ§Ã£o especÃ­fica. A origem do erro de cor Ã© **desconhecida** atÃ© provar a primeira etapa divergente.

### 3. Testes de equivalÃªncia em vez de otimizaÃ§Ã£o por tentativa

[B: `spu_equiv/run_eq.sh`](https://github.com/erikomis/infamous2-recomp/blob/61ad6ffd826dc6d1f32bf78ccbaa4ab98352f980/infamous2-lle/tools/spu_equiv/run_eq.sh) gera a mesma imagem SPU de duas formas e compara hashes dos estados, callbacks e transfers com registros/LS pseudorrandÃ´micos. O projeto inclui um teste de erro deliberado para mostrar que o harness detecta divergÃªncias. O conceito Ã© Ãºtil para testar **mudanÃ§as do lifter**, mas as amostras sintÃ©ticas nÃ£o provam que o jogo completo foi preservado.

[A: `spu_jobreplay.c`](https://github.com/ChaosTheory1075/infamous-ps5/blob/8e07d8ff373b19e37a9b6d45f6b437f48833754b/toolkit/added/runtime/spu/spu_jobreplay.c) registra tempos por job/overlay, contagem de dispatch sem lift e prevÃª captura/replay de DMA e canal. A abordagem permite identificar se o worker do contador atrasado Ã© um job compilado, interpreter fallback ou nÃ£o foi acordado. Os dumps de replay contÃªm **dados proprietÃ¡rios de execuÃ§Ã£o**: manter somente localmente.

[B: `log_triage.py`](https://github.com/erikomis/infamous2-recomp/blob/61ad6ffd826dc6d1f32bf78ccbaa4ab98352f980/infamous2-lle/tools/log_triage.py) agrupa erros de shader, render targets, texturas, SPU, hangs e hitch, gerando resumo legÃ­vel e JSON. [`profile_report.py`](https://github.com/erikomis/infamous2-recomp/blob/61ad6ffd826dc6d1f32bf78ccbaa4ab98352f980/infamous2-lle/tools/profile_report.py) separa CPU ativa, thread parada, frames apresentados e tempo do interpretador SPU. O modelo de relatÃ³rio Ã© Ãºtil, mas nÃ£o devemos interpretar um simples contador de draws como FPS ou tempo de simulaÃ§Ã£o.

### 4. C: renderizaÃ§Ã£o de iluminaÃ§Ã£o como segunda fase, nÃ£o gambiarra

O [relatÃ³rio do fork RPCS3 para Festival europeu NPEA00322](https://github.com/ttmx/rpcs3-infamous2/blob/22c57ff052c142667f7856ea44e123ab58776237/festival/README.md) apresenta otimizaÃ§Ãµes de SSAO e iluminaÃ§Ã£o com passagens GPU e reduÃ§Ã£o de readback, mas alerta que sincronizaÃ§Ã£o relaxada de ZCULL gerou flicker. Seu diagnÃ³stico da dependÃªncia CPU/GPU Ã© relevante para nosso D3D12; nÃ£o podemos portar constantes de endereÃ§os europeus para NPUA80657, nem usar tempos de Vulkan/Radeon como previsÃ£o de FPS Windows/RTX.

### Como validar agora (sÃ³ no PC com os arquivos legais)

ApÃ³s atualizar a branch do PR #6, na raiz do projeto:

```bat
py tools/inspect_spu_overlays.py data "private\game\EBOOT.elf" --json "out\spu-datamods.json"
```

A ferramenta **nÃ£o extrai bytes** nem envia o jogo a lugar nenhum; informa cabeÃ§alhos plausÃ­veis. Marcador encontrado nÃ£o prova que o bloco Ã© executado. Se houver candidatos, correlacionÃ¡-los ao histÃ³rico de GET, LS e `SPU_INTERP_STATS`, e sÃ³ entÃ£o implementar o lift da imagem realmente necessÃ¡ria.

**Gate principal do recomp:** provar o worker/job que nÃ£o eleva um dos sete campos para o alvo; validar se existe fallback interpretado e se o cÃ³digo recompilado pÃ³s-interrupt continua correto. SÃ³ depois reavaliar FPS mÃ©dio/p95. O target de 30 FPS continua aberto.

**O que mudou de fato no PR #6:** varredura read-only do formato `DA7ABA5E` e quatro testes adicionais. Nenhuma alteraÃ§Ã£o no runtime ou na funÃ§Ã£o de renderizaÃ§Ã£o foi aplicada; nenhuma melhora de FPS foi alegada.


## Integração das PRs #5 e #6

A investigação de despacho da PR #5 identificou uma escolha de imagem SPU sem identidade comprovada. O patch 0010 remove esse fallback; os testes sintéticos preservam o despacho recompilado válido e verificam os casos sem função correspondente. Isso atualiza a hipótese anterior de que a infraestrutura de rejoin, sozinha, bastaria para excluir erros de despacho. Consulte o diagnóstico e os limites em [BINK-VIDEO-NPUA80657.md](BINK-VIDEO-NPUA80657.md).

Antes da integração, foi reproduzido um defeito nas duas ferramentas da PR #6: apontar `--json` para um arquivo de entrada sobrescrevia seus bytes. A validação agora rejeita o próprio arquivo, caminhos equivalentes e aliases por links. Relatórios distintos continuam funcionando. Os testes usam somente dados sintéticos; os casos de links dependem do suporte do sistema operacional. Essa proteção não altera código nem dados de execução do jogo.

As limitações gráficas e a meta de 30 FPS continuam abertas. Integrar estas PRs incorpora as correções e ferramentas validadas, sem declarar o jogo concluído.
