# Checkpoint ELF decodificado — Festival of Blood NPUA80657

**Data:** 2026-11-16
**Estado:** ELF legítimo recebido para análise local, sem publicar binário, funções, assets ou instruções proprietárias.

## Evidências técnicas

| Medida | Valor |
|---|---|
| Arquivo | EBOOT.elf |
| Formato | ELF64, big-endian, PowerPC64, ET_EXEC |
| Tamanho | 10.927.304 bytes |
| SHA-256 | `184343936c98aa95321cca2202f827f2c78aa373f8ba7ff76b43a255ee155f51` |
| Entry OPD | `0x9fee40` |
| Entry real código | `0x10230` |
| Entry TOC (r2) | `0xa27440` |
| Program headers | 8 |
| PT_LOAD não vazios | 2 |
| Segmentos executáveis | 1 |
| Section headers | 40 |
| Seção contendo entry/OPD | índice 22, início `0x9fee30`, tamanho 132.624 bytes |
| Descritores OPD que apontam para código | 16.578 |
| Endereços únicos via OPD | 14.789 |
| TOC predominante | `0xa27440` |
| Bibliotecas importadas | 21 |
| Importações de funções | 302 |

**Nota de qualidade:** os nomes das seções ELF não estão disponíveis (a string table de nomes está zerada). A seção de descritores foi identificada pelo endereço da entrada e verificação de pares `(func, toc)`, como orienta o loader do ps3recomp. **14.789 são endereços distintos encontrados na OPD, não total definitivo de funções**; funções sem descritor podem existir.

## Contagem por biblioteca

| Biblioteca | Importações |
|---|---:|
| cellSpurs | 41 |
| cellSysmodule | 3 |
| sys_fs | 20 |
| sys_io | 15 |
| cellRtc | 8 |
| sys_net | 24 |
| cellNetCtl | 8 |
| cellHttp | 19 |
| cellHttpUtil | 1 |
| cellAudio | 8 |
| cellCamera | 13 |
| cellSysutil | 27 |
| cellGame | 8 |
| sceNpTrophy | 10 |
| sceNp | 16 |
| cellSysutilAvconfExt | 1 |
| cellGcmSys | 27 |
| libgem | 21 |
| cellSsl | 3 |
| cellSysutilNpEula | 2 |
| sysPrxForUser | 27 |

Todos os endereços de tabelas de NID e stubs destas importações apontam para dados acessíveis no ELF fornecido. Ainda é necessário verificar compatibilidade HLE por NID do runtime.

## Reproduzir localmente

Execute (com sua cópia do jogo, **não** suba o ELF ao GitHub):

```powershell
py tools/analyze_ppu.py "private/game/EBOOT.elf" --output "out/ppu-summary.json"
```

Validação futura com o [ps3recomp](https://github.com/sp00nznet/ps3recomp):

```powershell
py ps3recomp/tools/ppu_loader.py "private/game/EBOOT.elf" --output "out/loader"
```

O segundo comando exige uma instalação local do ps3recomp. **Não foi executado neste checkpoint**, portanto não foi validado neste jogo ainda.

## Próximos gates

- [x] ELF decodificado e metadados PPU plausíveis.
- [x] Recuperar entry/TOC e mapear OPD e imports.
- [x] Criar analisador reproduzível e testes sem conteúdo proprietário.
- [ ] Rodar o loader oficial ps3recomp e comparar contagens.
- [ ] Mapear funções sem OPD e desvios indiretos.
- [ ] Verificar módulos SPU e bibliotecas HLE ausentes.
- [ ] Primeiro lifter PPU completo e compilação local; **sem expectativa de jogo rodar ainda**.
