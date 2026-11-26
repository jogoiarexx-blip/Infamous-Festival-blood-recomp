# Auditoria dos patches Gemini 0013–0017 — inFAMOUS FoB Recomp

## Escopo e fonte
O usuário entregou os patches locais renumerados `0013`–`0017` e o `LICENSE`.
A presente branch registra **somente** a proposta inédita 0017 em `review/`,
para não alterar os patches ativos nem a versão funcional. Verificações
estáticas realizadas em 22/11/2026, usando o SDK público fixado
`sp00nznet/ps3recomp@de4f090328ea08bef6b2f15caec0b85e343a7ece`.
Não houve build Windows nem execução do EBOOT nesta revisão.

## Compatibilidade com PRs existentes

| Arquivo local | Fonte no GitHub | Decisão |
|---|---|---|
| `0013-retire-gpu-resources-after-completed-fences.patch` | PR #11, arquivo `0012-retire-gpu-resources-after-completed-fences.patch` | Renumeração; conservar PR original até integração ordenada |
| `0014-expand-pso-cache-and-mitigate-atomic-spin.patch` | PR #10, `0013-expand-pso-cache-and-mitigate-atomic-spin.patch` | **NÃO substituir** a revisão da PR #10; arquivo local está malformado e a PR havia corrigido yield antes da liberação de lock |
| `0015-snapshot-fragment-programs-at-draw-record.patch` | PR #12, `0014-snapshot-fragment-programs-at-draw-record.patch` | Mesmas alterações de código; difere apenas numeração/cabeçalho e terminação |
| `0016-fix-texture-formats-self-sampling-and-conditional-composite.patch` | PR #13, arquivado como `review/0015-fix-texture-formats-self-sampling-and-conditional-composite.patch` | Mesmo texto após renumerar o cabeçalho; ainda **NÃO habilitar** sem corrigir contexto e validar dependência PR #11 |
| `0017-shader-disk-cache-and-spu-pacing-optimization.patch` | Não existe na série ativa | **Novo**, preservado nesta branch para reparos |

O `LICENSE` enviado corresponde ao MIT LICENSE do SDK de
`sp00nznet/ps3recomp`. Não adicionar como licença do repositório do jogo
sem avaliar a atribuição correta e a política do projeto.

## Bloqueadores técnicos do 0017

1. **Patch malformado:** `git apply --numstat 0017-...` falha com
   `error: corrupt patch at line 25`. Vários cabeçalhos `@@` declaram
   número de linhas incompatível com as linhas do hunk (9 hunks encontrados
   com contagens inconsistentes). Regerar via diff contra o SDK fixado **após
   aplicar os patches realmente integrados**, e passar `git apply --check`.
2. **Fingerprint SPU inseguro:** `spu_workload_fingerprint_cached()` retorna
   `s_fp[i].fp` quando **só endereço e tamanho** coincidirem, sem verificar
   `s_fp[i].content`/conteúdo atual. O SDK já documenta a possibilidade de
   imagens diferentes compartilharem endereço/tamanho; isto pode selecionar
   um módulo SPU errado. Aumentar o cache de 8 para 64 slots é separável,
   mas **não** eliminar a verificação de hash de conteúdo em memória mutável.
   Criar regressão sintética que modifica a imagem no mesmo buffer e mantém
   o tamanho; ambos devem ter fingerprints distintos.
3. **Cache em disco sem validação suficiente:** o identificador usa
   `target + HLSL`, mas não inclui `entry`, flags de compilação nem versão
   de schema/compilador. O cache abre blobs sem verificar conteúdo,
   integridade ou completude além do tamanho; `CREATE_ALWAYS` escreve
   diretamente o arquivo final e pode deixar arquivo parcial após crash.
   Acrescentar versão, chave completa, validação da carga, escrita temporária
   + troca atômica, tratamento de colisões e fallback para `D3DCompile`
   em cache inválido. Não confiar em arquivos de cache como fonte de verdade.
4. **Pacing/flip e portabilidade:** `ppu_gcm_pump()` dentro de
   `cellGcmSetWaitFlip()` e `cellGcmGetFlipStatus()` pode executar callbacks
   guest em contexto reentrante. O runtime contém comentários de bugs reais
   de deadlocks com handlers aninhados. O `SetEvent(s_gcm_kick_ev)`
   recém-adicionado está sem `#ifdef _WIN32` numa fonte multiplataforma.
   Validar sincronização e evitar chamar rotinas dependentes de Win32 em
   builds POSIX.
5. **SPURS TLS:** `s_tls_ls[SPU_LS_SIZE]` com `memset` pode evitar
   `calloc/free`, mas necessita teste de jobs sequenciais e concorrentes,
   callbacks/reentrância e de vazamento de referências ao LS após o job.
   Não declarar equivalência só com ausência de alocações.

## Bloqueadores herdados do 0016

- Hunk de amostragem ainda tenta remover `int rt = dr->tex[_u];` embora
  o SDK de referência já tenha `int rt = dr->tex_rt[_u];` — há conflito
  contextual. O próprio patch ainda não está aplicado no CI da PR #13.
- `defer_release()` só vem da PR #11 e não da `main` atual.
- Múltiplos `CopyResource` por draw podem reduzir o FPS; medir custo
  e transições RTV/SRV, além de verificar o corpo da garrafa no frame correto.
- O relatório local do Gemini menciona 5,5–6,2 FPS: **não foi medido
  independentemente** aqui, e não prova 30 FPS sustentados.

## Critérios mínimos antes de aplicar/mesclar

- [ ] Corrigir sintaxe do patch 0017 e regenerar série 0011–0017 sem
      sobrescrever alterações revisadas das PRs #10/#11/#12.
- [ ] Compilar SDK/runtime e executável Windows com ferramentas existentes.
- [ ] Executar testes de alteração de imagem SPU com mesmo ponteiro/tamanho,
      e comparar fingerprints e resultados de despacho.
- [ ] Testar disco: cache frio/quente/corrompido/parcial, alteração de shader,
      flags, versão e compilação de fallback.
- [ ] Testar frame pacing em transições Bink → fogueira → jukebox → gameplay,
      em três execuções e sem deadlocks de callbacks.
- [ ] Confirmar 0016 com PR #11, verificação D3D12, corpo/rótulo da garrafa,
      e validade de snapshots MRT.
- [ ] Medir FPS apresentado e 1% low com mesmo hardware/cena; distinguir
      tempo GPU de FPS total.
- [ ] Não publicar assets, EBOOT, saves, dumps nem shader bytecodes do jogo.

**Status: RASCUNHO PARA REVISÃO, NÃO PRONTO PARA MERGE.** CI verde desta
branch apenas prova que os arquivos de `review/` não interferem no projeto;
**não prova que o patch 0017 foi compilado, aplicado ou testado**.
