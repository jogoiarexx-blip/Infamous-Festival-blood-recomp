# Windows: primeira configuração de compilação (NPUA80657)

> Esta etapa **não cria automaticamente um jogo jogável**. Ela configura o projeto de CMake que tentará compilar o código PPU já gerado.

## Contexto confirmado (16/11/2026)
- Prompt: **x64 Native Tools Command Prompt for VS 2022**, Build Tools 2022 v17.14.41, MSVC 14.44.
- Python 3.12.10, Ninja 1.13.2, LLVM clang-cl 23.1.5 e CMake 4.4.3.
- Pasta atual: `D:\infamous recomp\Infamous-Festival-blood-recomp-main`.
- `ps3recomp` extraído em `D:\infamous recomp\ps3recomp`.
- `out\recompiled` contém `ppu_recomp.h`, 32 arquivos `ppu_recomp_*.cpp` e `ppu_hle_nids.cpp`.
- Arquivos originais e código gerado **permanecem locais**; `out/` e `private/` estão ignorados pelo Git.

## Passo 1 — copiar o projeto de referência (não copia o jogo)

No **Developer Command Prompt x64**, dentro da pasta do projeto:

```bat
xcopy /E /I /Y "..\ps3recomp\templates\project" "out\port"
```

Isso cria a pasta local `out\port` com `CMakeLists.txt`, `main.cpp`, `stubs.cpp` e os outros arquivos de exemplo necessários à configuração.

## Passo 2 — configurar sem compilar

Execute em **uma linha** no mesmo prompt:

```bat
cmake -S "out\port" -B "out\build" -G Ninja -DCMAKE_C_COMPILER=clang-cl -DCMAKE_CXX_COMPILER=clang-cl "-DPS3RECOMP_DIR:PATH=%CD%\..\ps3recomp" "-DRECOMP_DIR:PATH=%CD%\out\recompiled" -DPORT_ENABLE_SPU=OFF
```

**Por que `PORT_ENABLE_SPU=OFF`?** Somente para isolar a **primeira compilação de estrutura e PPU**: ainda não identificamos/programamos todos os workloads SPU desta edição. Isto não pode ser considerado uma versão jogável; depois reativaremos SPU e investigaremos dependências PRX.

- Se aparecer `Configuring done` e `Generating done`, o projeto está configurado.
- Se aparecer `CMake Error` / `FAILED`, guardar somente a mensagem e o trecho relevante do erro (sem arquivos do jogo).
- Caso `clang-cl` não seja reconhecido, garantir nesta janela:
  ```bat
  set "PATH=C:\Program Files\LLVM\bin;%PATH%"
  ```
- Em caso de erro sobre `ppu_recomp.h`, verificar `dir out\recompiled\ppu_recomp.h`.

## Passo 3 — primeira tentativa de compilação (configuração confirmada como concluída)

A execução local do CMake exibiu `Configuring done` / `Generating done` e detectou `ps3recomp runtime v0.19.0` e `33` fontes recompiladas. O modo de build foi `Debug`. Em 16/11/2026 o usuário relatou que o Ninja chegou a `[200/201] Linking CXX executable MyGameRecomp.exe` e retornou ao prompt **sem erro fatal** após 448 avisos. Confirmar a existência física do executável e executar primeiro boot local.

```bat
cmake --build "out\build" --parallel 2
```

**Atenção:** são arquivos C++ gigantes (centenas de milhares de linhas); a compilação pode consumir muita RAM, disco e CPU. `--parallel 1` reduz a pressão de memória em relação à compilação paralela. Caso haja falha, registrar as primeiras linhas de erro e o resumo do compilador.

O alvo do template chama-se `MyGameRecomp`; isso é **temporário**. Mesmo se o linker produzir um executável, o boot de Festival of Blood não estará validado até executarmos e corrigirmos HLE, SPU, sistemas de arquivos, gráficos e incompatibilidades. Não distribuir um executável derivado dos arquivos de jogo.

## Referências
- [ps3recomp: template/project/README.md](https://github.com/sp00nznet/ps3recomp/blob/master/templates/project/README.md)
- [ps3recomp: Getting Started](https://github.com/sp00nznet/ps3recomp/blob/master/docs/GETTING_STARTED.md)

## Passo 4 — conferir o executável e testar o primeiro boot

O próprio usuário deve executar estes comandos **somente na máquina que possui o jogo**:

```bat
dir "out\build\MyGameRecomp.exe"
```

Depois, caso exista e com o projeto atual como diretório de trabalho:

```bat
"out\build\MyGameRecomp.exe" "private\game\EBOOT.elf"
```

É um smoke test do runner e do runtime, **não uma indicação de que o jogo já funciona**. O template usa o ELF de entrada, tenta montar a raiz VFS a partir desse caminho e pode abrir uma janela D3D12; com o ELF em `private\game\EBOOT.elf`, a raiz inferida provavelmente será o diretório atual, e não um dump de `PS3_GAME`. Se a inicialização reclamar de arquivos não encontrados, localizar a cópia legal completa localmente e ajustar `PS3_VFS_ROOT` na próxima tentativa. A API `main.cpp` do template consulta `PS3_VFS_ROOT` e não lê um segundo argumento para VFS no código verificado.

Se travar, fechar a janela gráfica ou usar `Ctrl+C` no prompt. Salvar os logs de erro (sem anexar ou publicar binários e assets). Não publicar o executável derivado do jogo.
