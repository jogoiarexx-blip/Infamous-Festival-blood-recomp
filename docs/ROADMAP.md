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
- [ ] Registrar commit exato do ps3recomp instalado localmente (loader já validado e funcional no EBOOT do jogo).
- [ ] Mapear módulos PRX e imagens SPU, quando presentes.
- [ ] Comparar **arquitetura e interfaces**, não endereços assumidos, com inFAMOUS 2.
- [ ] Documentar bloqueios por edição/versão.

**Gate:** relatórios reproduzíveis (sem código proprietário) e teste mínimo de loader local.

## Fase 2 — Pipeline de recompilação
- [x] Preparar ambiente Windows: Python 3.12.10, CMake 4.4.3, Ninja 1.13.2, clang-cl 23.1.5, VS Build Tools 2022 x64 e fonte do ps3recomp (confirmado pelo usuário em 2026-11-16).
- [x] Executar loader oficial no ELF do proprietário: 16.578 OPD, 14.789 funções, 302 imports/21 bibliotecas (log verificado em 2026-11-16).
- [x] Executar lifter PPU com `--functions` e `--hle-stubs`: 40.085 entradas traduzidas, 12.848 wrappers e 32 arquivos C++ gerados localmente. **Três avisos de continuação pendentes**; ver [relatório](PPU_LIFT_RESULT_NPUA80657.md).
- [x] Gerar tabela HLE: `ppu_hle_nids.cpp`, 1.238 handlers de 93 módulos (execução local confirmada em 2026-11-16).
- [ ] Comparar os 302 imports do jogo com os handlers disponíveis e verificar eventuais funções HLE faltantes.
- [ ] Descobrir e tratar trabalho SPU de modo incremental.
- [x] Configuração CMake e compilação/link inicial em Windows sem erro fatal relatado: `[200/201] Linking CXX executable MyGameRecomp.exe`; prompt retornou (448 avisos). **Arquivo confirmado pelo usuário** em `out/build/MyGameRecomp.exe` (515.762.176 bytes, 16/11/2026 14:59).
- [x] Executar primeiro teste de boot local: runner entrou no PPU, inicializou runtime/threads/SPURS/GCM/FIOS e encerrou com `sys_process_exit(code=0)` **sem chegar ao menu** (log fornecido em 2026-11-16).
- [ ] Corrigir bloqueios de boot confirmados: [SPU não recompilado, assets ausentes no VFS e metadados](BOOT_DIAGNOSTIC_NPUA80657.md).

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
**Objetivo imediato:** primeiro boot executado e log analisado. O runtime iniciou código recompilado, GCM, SPURS e múltiplas threads, mas houve **SPU async dispatch MISS** (`fp=0x00E729804474449A`, tamanho 38100), workloads não traduzidos (`fp=0xB3523C4B17650EF8`, tamanho 11904) e acessos a arquivos não encontrados. Próximo passo: coletar dumps de SPU localmente com `SPU_DUMP_MISS`, investigar VFS e mapear imagens SPU. Ver [diagnóstico](BOOT_DIAGNOSTIC_NPUA80657.md). O menu e jogabilidade ainda não foram alcançados.
