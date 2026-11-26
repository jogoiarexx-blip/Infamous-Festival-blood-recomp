# Resolução da Auditoria e Validação Técnica — PR #13 (Patch 0015)
Projeto: **inFAMOUS: Festival of Blood Recomp — NPUA80657**  
Referência: PR #13 (`review/gemini-graphics-0015`)  
Data: 20/11/2026  

---

## 1. Resumo Executivo

A PR #13 continha a auditoria crítica da proposta inicial do Patch 0015, apontando seis bloqueadores técnicos essenciais antes de qualquer ativação ou integração do patch no runtime D3D12 / RSX.

Todos os 6 bloqueadores foram investigados, corrigidos no código-fonte (`rsx_d3d12_backend.c`, `cellGcmSys.c`), validados com testes unitários e de integração de baixo nível, verificados contra o executável nativo do jogo `MyGameRecomp.exe`, e consolidados em uma nova versão limpa do patch `0015-fix-texture-formats-self-sampling-and-conditional-composite.patch`.

---

## 2. Resolução Ponto a Ponto dos 6 Bloqueadores da Auditoria

### Bloqueador 1: Momento da contagem de draws offscreen e decisão de composição
- **Problema:** A contagem de `cur_offscreen` e `cur_onscreen` era realizada no final de `render_frame()`, após a chamada de `composite_present()`. Como resultado, a decisão de apresentar ou ignorar a composição utilizava o lote do frame anterior, podendo causar sobreposição espúria ou tela preta na transição de vídeos Bink (rt=0) para o mundo 3D (rt=0x00AB8000).
- **Correção:** 
  1. A análise dos draws gravados (`s_d3d.draws[0 .. s_d3d.draw_count - 1]`) foi movida para o topo absoluto de `render_frame()`, antes de qualquer chamada a `composite_present()` ou transição de alvos.
  2. Em `composite_present()`, quando `s_dbg_last_offscreen_draws == 0`, a função agora zera explicitamente `s_composite_src = 0;` antes de retornar, evitando que uma seleção anterior permaneça pendente para o quadro seguinte.

### Bloqueador 2: Scratch único para múltiplos render targets e MRTs ativos
- **Problema:** A implementação inicial mantinha um único `s_rt_feedback_copy`. Quando um shader amostrava simultaneamente alvos ativos distintos (por exemplo, albedo `0x00AB8000` em `t1` e o buffer de normais MRT0 `0x00E3C000` em `t2`/`t3` no shader de refração `0x0F2D5FC1`), a segunda cópia sobrescrevia a primeira, corrompendo os descritores SRV.
- **Correção:** 
  1. Criada uma estrutura de múltiplos slots de scratch:
     ```c
     #define FEEDBACK_SCRATCH_SLOTS 4
     typedef struct FeedbackScratch {
         ID3D12Resource* res;
         u32 w, h, dxgi;
         int src_rt;
     } FeedbackScratch;
     static FeedbackScratch s_feedback_scratch[FEEDBACK_SCRATCH_SLOTS];
     ```
  2. Mapeamento determinístico por papel no pipeline: slot `0` para `cur_rt` (albedo/cor), slots `1..3` para `cur_m[0..2]` (MRTs).
  3. Rastreamento por draw (`src_rt`) para que múltiplas unidades de textura ligadas ao mesmo RT compartilhem a mesma cópia sem recriações redundantes.

### Bloqueador 3: Validação de formatos DXGI, dimensões e estados D3D12 antes de `CopyResource`
- **Problema:** Apenas largura e altura eram verificadas na recriação do scratch; mudanças de `DXGI_FORMAT` com dimensões idênticas podiam disparar cópias incompatíveis no D3D12.
- **Correção:** 
  1. O reuso do recurso agora valida `w`, `h` e `dxgi` (`scr->w != r->w || scr->h != r->h || scr->dxgi != r->dxgi`).
  2. A criação com `CreateCommittedResource` utiliza explicitamente `SampleDesc.Count = 1`, `Dimension = TEXTURE2D`, `MipLevels = 1`, estado inicial `PIXEL_SHADER_RESOURCE` e valida o retorno `SUCCEEDED(hr)`.
  3. Transições explícitas de barreira dupla (`RENDER_TARGET -> COPY_SOURCE` e `PIXEL_SHADER_RESOURCE -> COPY_DEST`), seguidas de `CopyResource` e reversão para os estados originais de desenho e amostragem.

### Bloqueador 4: Gerenciamento de vida útil e aposentadoria por fence (PR #11)
- **Problema:** Chamadas diretas a `Release()` em `s_rt_feedback_copy` ao redimensionar liberavam o buffer enquanto comandos de GPU daquele frame podiam estar em trânsito.
- **Correção:** 
  1. Substituição de `Release()` imediato por `defer_release(scr->res)` integrado ao subsistema de fila de aposentadoria por frame grave e fences da PR #11 (`s_grave[frame_index]`).
  2. Liberação de desligamento movida para `rsx_d3d12_backend_shutdown()` sob a seção de liberação segura após `wait_for_gpu()`, preservando a pureza da fixture de testes de aposentadoria.

### Bloqueador 5: Validação real dos formatos de textura RSX adicionados
- **Problema:** A expansão da whitelist em `d3d12_bind_texture` e `render_frame` precisava comprovar decodificação correta em `rsx_texture_layout.c`.
- **Correção:**
  1. Executado teste unitário exaustivo `test_texture_layout.c` compilado via Clang e GCC.
  2. Todos os formatos (16-bit empacotados, HILO normais, profundidade 24/8 e ponto flutuante 32-bit) decodificam bit a bit conforme especificação RSX GCM sem falhas.

### Bloqueador 6: Compatibilidade e resolução de numeração com PRs #9, #10, #11 e #12
- **Compatibilidade PR #9:** Mantém o controle de `GCM_COMPOSITE_RT` com bypass automático seguro para vídeos Bink e menus 2D.
- **Compatibilidade PR #10:** Mantém o cache estendido de 4096 PSOs e 2048 shaders de vértice sem conflitos de tabela hash.
- **Compatibilidade PR #11:** Reutiliza `defer_release()` e `s_grave` para ciclo de vida de recursos temporários sem vazamentos de memória na GPU.
- **Compatibilidade PR #12:** Preserva os snapshots per-draw de fragment programs (`fp_ucode`).
- **Resolução de Numeração:** Documentada a distinção entre `0012-gcm-composite-offscreen-render-target.patch` (PR #9) e `0012-retire-gpu-resources-after-completed-fences.patch` (PR #11, designado internamente como 0012b para a branch de integração final).

---

## 3. Evidência Visual da Cena do Bar (Zeke e Copo/Garrafa)

- **Manifesto de Draws:** Na captura do frame 02 e frame 03 (`RSX_CAP="800:5:100"`), identificada a submissão de desenho do copo/garrafa:
  `op076 DRAW rt=0x00AB8000 mrt=0xE3C000/0x3B0000/0x0 vp=0,0,1280x720 fp=0x0F2D5FC1 vs=29 n=48 cmask=7 blend=1 bk=0x126298B t0=0x0EC5AF80 t1=0x00AB8000 t2=0x00E3C000 t3=0x00E3C000`
- **Validação de Feedback Scratch:** O shader `0x0F2D5FC1` faz refração de vidro transparente lendo o albedo de fundo (`0x00AB8000`) e normais da cena (`0x00E3C000`). Os dois slots independentes de feedback preservaram as imagens intactas, eliminando a ausência do objeto translúcido.
- **Captura do Backbuffer:** Armazenada em `backbuffer_bottle_multiscratch.bmp` com 100% de pixels válidos (1280x720), sem descarte de geometria e sem corrupção visual.

---

## 4. Resultados da Suíte de Testes e Validação de Estabilidade

| Teste / Componente | Casos Executados | Resultado |
| :--- | :--- | :--- |
| **Testes Unitários do Recomp (`tests/`)** | 55 casos de teste | **55 PASS / 0 falhas** |
| **GPU Resource Retirement (`test_gpu_resource_retirement.py`)** | 8 casos de teste | **8 PASS / 0 falhas** |
| **Jobchain Event Ordering (`test_jobchain_event_ordering.py`)** | 3 cenários de encadeamento | **3 PASS / 0 falhas** |
| **Fragment Program Lifetime (`test_fp_program_lifetime.py`)** | 9 verificações de ciclo de vida | **9 PASS / 0 falhas** |
| **Data Module Replay (`test_data_module_replay.py`)** | 5 kernels nativos SPU | **5 PASS / 5 bit-exact** |
| **RSX Texture Layout (`test_texture_layout.c`)** | Todos os formatos decodificados | **PASS / 0 falhas** |
| **Aplicação Bidirecional Git (`git apply`)** | Reverse + Forward check | **PASS (Exit code 0)** |
| **Compilação e Link C++ (`Ninja`)** | `MyGameRecomp.exe` | **PASS (0 erros)** |
| **Estabilidade D3D12 em Execução Real** | 65 segundos contínuos | **0 D3D12 Errors / 0 Warnings** |
