# Relatório de identificação — NPUA80657

**Data:** 2026-11-16
**Origem:** metadados extraídos de um EBOOT.BIN fornecido pelo proprietário para análise local.
**Estado:** arquivo identificado; **ainda não é um ELF decodificado nem um jogo recompilado**.

## Identificação

| Propriedade | Valor |
|---|---|
| Título identificado | inFAMOUS: Festival of Blood |
| Title ID | `NPUA80657` (edição PSN americana) |
| Content ID público | `UP9000-NPUA80657_00-BLOODSHP10041043` |
| Formato externo | SCE/SELF |
| Assinatura | `53 43 45 00` (`SCE\0`) |
| Tipo SELF | 8 (NPDRM) |
| Versão do cabeçalho SCE | 2 |
| Arquivo em bytes | 4.969.024 |
| SHA-256 | `bf5751470c3bcbbc2ad22af1af81504ee01ffd0718d1adae075d5f704e002049` |
| Tamanho ELF declarado no SELF | 10.927.304 bytes |
| Comprimento do cabeçalho SELF | 2.688 bytes |
| Offset de cópia do cabeçalho ELF | `0x90` |
| ELF interno: classe | ELF64 |
| ELF interno: endian | Big-endian |
| ELF interno: e_machine | 21 (PowerPC64) |
| ELF interno: entry point | `0x9fee40` |
| Cabeçalhos de programa internos | 8 |
| Cabeçalhos de seção internos | 40 |

**Importante:** o cabeçalho ELF embutido descreve o ELF original; ele **não prova** que código e dados estejam acessíveis em formato ELF. O arquivo recebido é SELF/NPDRM e não pode ser passado diretamente ao lifter como ELF completo.

## Validação de identidade

O Title ID `NPUA80657` foi encontrado na estrutura de identificação do executável e confrontado com:
- https://www.psdevwiki.com/ps3/Game_ID
- https://www.gametdb.com/PS3/NPUA80657

Isso **identifica o título**, não prova uma versão exata de atualização (1.00/1.xx); ainda não atribuiremos uma versão.

## O que está confirmado vs. pendente

- [x] Identificador Festival of Blood reconhecido.
- [x] SELF/NPDRM confirmado.
- [x] Metadados do ELF64 PowerPC e entry point recuperados.
- [x] Hash para referência da amostra.
- [ ] ELF com segmentos efetivamente acessíveis para análise no ps3recomp.
- [ ] Mapa de funções PPU, TOC/OPD, imports, código SPU.
- [ ] Comparação real de funções/módulos com projetos inFAMOUS 2.
- [ ] Compilação, runtime e boot do jogo.

## Próximo passo

O proprietário deve gerar ou localizar **localmente**, a partir de sua cópia legal, um ELF decodificado; confira o guia do [ps3recomp](https://github.com/sp00nznet/ps3recomp/blob/master/docs/GETTING_STARTED.md). Não carregar EBOOT, jogos, firmware ou chaves para GitHub. Após isso, executar o analisador no ELF e iniciar o loader na máquina local. Os relatórios podem ser comparados pelo hash sem distribuir o binário.

**Nenhum byte do conteúdo protegido do jogo foi publicado neste relatório.**
