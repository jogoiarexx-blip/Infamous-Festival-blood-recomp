# ROADMAP — Festival of Blood Recomp

Este documento registra **resultados verificáveis**, não porcentagens inventadas.

## Fase 0 — Preparação da pesquisa (concluída)
- [x] Criar repositório público independente.
- [x] Criar documentação inicial, política de não distribuição e arquivos ignorados.
- [x] Implementar inspeção local dos formatos ELF/SELF e SHA-256.
- [x] Implementar inventário de arquivos e testes sintéticos.
- [x] Confirmar o CI verde no GitHub Actions (testes sintéticos aprovados em 2026-11-16).
- [x] Receber metadados **não proprietários**: NPUA80657, SELF/NPDRM, cabeçalho ELF64 PowerPC; ver [relatório](REPORT-NPUA80657.md).

**Gate:** registrar formato de EBOOT, identificador da edição quando disponível, versão e hash local de referência. Não publicar o EBOOT.

## Fase 1 — Análise de executável e compatibilidade
- [x] Validar um ELF PPU PowerPC64 big-endian do próprio jogo (NPUA80657, SHA-256 registrado).
- [x] Identificar TOC, OPD, entry point, segmentos e bibliotecas importadas; binário sem tabela de nomes de seções utilizável e sem símbolos de função conhecidos.
- [ ] Confirmar ferramentas e versão exata de ps3recomp que suportam o binário.
- [ ] Mapear módulos PRX e imagens SPU, quando presentes.
- [ ] Comparar **arquitetura e interfaces**, não endereços assumidos, com inFAMOUS 2.
- [ ] Documentar bloqueios por edição/versão.

**Gate:** relatórios reproduzíveis (sem código proprietário) e teste mínimo de loader local.

## Fase 2 — Pipeline de recompilação
- [ ] Preparar ambiente Windows: Python, CMake, Ninja, clang-cl e SDK ps3recomp.
- [ ] Executar loader para obter metadados e importações no PC do proprietário.
- [ ] Executar lifter PPU e registrar total de funções traduzidas/falhas.
- [ ] Gerar mapeamento HLE, identificar funções de sistema faltantes.
- [ ] Descobrir e tratar trabalho SPU de modo incremental.
- [ ] Criar compilação local determinística e smoke test sem assets distribuídos.

**Gate:** executável local inicia pipeline de runtime com logs; não implica jogo rodando.

## Fase 3 — Boot e subsistemas
- [ ] Gerenciamento de memória e carregamento de módulos.
- [ ] Arquivos, perfis, salvamento, temporizadores e threads.
- [ ] Renderização RSX → backend PC.
- [ ] Entrada, áudio e vídeo.
- [ ] Sincronização PPU/SPU, jobs e eventos.
- [ ] Tela inicial do jogo (teste real, não mockup).

**Gate:** vídeo/log de boot reproduzível a partir da cópia legal.

## Fase 4 — Jogabilidade
- [ ] Primeira cena e controles.
- [ ] Navegação e câmera.
- [ ] Poderes, combate, NPCs e missões.
- [ ] Cidade, streaming de mundo, colisões e física.
- [ ] Persistência de progresso; áudio; sequências.
- [ ] Estabilidade, desempenho e compatibilidade.

**Gate:** trecho jogável com testes regressivos.

## Fase 5 — Publicação responsável
- [ ] Launcher detecta arquivos locais do usuário.
- [ ] Detectar edições/versões suportadas por hashes; rejeitar desconhecidas de forma clara.
- [ ] Reproduzir build, testes e instruções de instalação.
- [ ] Distribuir somente código original/licenciado e scripts, nunca arquivos do jogo.
- [ ] Testes em máquinas Windows diferentes.

## Próximo checkpoint
**Objetivo imediato:** ELF de NPUA80657 confirmado, 16.578 descritores OPD válidos, 14.789 endereços distintos e 302 imports em 21 bibliotecas. Ver [relatório ELF](ELF_ANALYSIS_NPUA80657.md). Próximo bloqueio: validar esses resultados com o **loader oficial ps3recomp** e mapear funções adicionais/SPU. Não reutilizar endereços ou hashes de inFAMOUS 2.
