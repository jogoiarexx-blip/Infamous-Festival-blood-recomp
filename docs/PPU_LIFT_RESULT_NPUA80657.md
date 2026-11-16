# Resultado do lifter PPU — NPUA80657

**Data:** 2026-11-16
**Fonte:** saída de terminal do usuário após executar localmente o `ppu_lifter.py` do `ps3recomp` no seu próprio `EBOOT.elf`.
**Estado:** geração de C++ finalizada; compilação e execução **não** verificadas.

## Comando usado

```powershell
py ..\ps3recomp\tools\ppu_lifter.py "private\game\EBOOT.elf" --functions "out\loader\EBOOT.functions.json" --hle-stubs "out\loader\EBOOT.imports.json" --output "out\recompiled"
```

## Métricas informadas pelo tradutor

| Item | Resultado |
|---|---:|
| Descritores de função no loader | 16.578 |
| Funções únicas no loader | 14.789 |
| Mid-function tail-entry wrappers gerados | 12.848 |
| Entradas de função emitidas pelo lifter | 40.085 |
| Alvos únicos de chamadas encontrados | 17.287 |
| Arquivos de código gerados | 32 `ppu_recomp_000.cpp` até `ppu_recomp_031.cpp` |
| Arquivo de cabeçalho | `ppu_recomp.h` |
| Etapa | `Writing C source (split into chunks)...` concluída |

A contagem `40085 functions lifted` inclui entradas adicionais descobertas e wrappers gerados e **não equivale a 40.085 funções originais independentes**. Arquivos compilados ou executável jogável ainda **não** existem.

## Avisos a investigar

O lifter relatou três avisos de continuação inexistente e inseriu `halt` como fallback:

```text
WARNING: func_00781AA0 has no continuation at 0x0096FF68; emitting halt
WARNING: func_0096FCEC has no continuation at 0x0096FF68; emitting halt
WARNING: func_0096FECC has no continuation at 0x0096FF68; emitting halt
```

Os três apontam para `0x0096FF68`. Precisamos verificar se houve falta de função/alvo, fluxo intencional de saída de segmento ou falha heurística. A recompilação de C++ pode ter sucesso e esses caminhos ainda falharem durante gameplay; **não eliminar os avisos sem testes**.

## Próximas etapas locais

1. Gerar o registro HLE com `gen_hle_nids.py --all` (não contém assets nem executável do jogo).
2. Verificar disponibilidade de `cmake`, `ninja`, `clang-cl` e Build Tools do Visual Studio.
3. Criar projeto local a partir de `ps3recomp/templates/project`, apontando `RECOMP_DIR` para `out/recompiled`.
4. Configurar e compilar. Identificar erros de compilação, módulos e NIDs faltantes.
5. Detectar e tratar programas SPU e módulos PRX, testar boot e investigar todos os avisos.

**Não publicar** `EBOOT.elf`, `EBOOT.BIN`, código C++ traduzido do jogo, assets, chaves, licença ou firmware. Os arquivos `out/`, `private/` e `build/` estão ignorados pelo Git.
