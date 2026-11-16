# Primeiro boot Windows — diagnóstico do runtime (NPUA80657)

**Data:** 2026-11-16  
**Base:** log textual enviado pelo proprietário após executar `"out\build\MyGameRecomp.exe" "private\game\EBOOT.elf"`.  
**Confiança:** são fatos do log; hipóteses sobre causas estão explicitamente assinaladas.  
**Privacidade:** não incluir neste repositório binários, dumps ou assets extraídos do título.

## Resultado confirmado

O executável Windows `MyGameRecomp.exe` (515.762.176 bytes) foi criado e **executado**. O runner não se limitou a iniciar: entrou no código recompilado de fato, criou threads, inicializou HLE e dispositivos PS3 e chegou à inicialização de recursos de jogo.

Trechos de diagnóstico:

```text
=== ps3recomp game runner ===
[ppu] loaded 2 PT_LOAD segments, entry OPD 0x009FEE40
[boot] VFS root: private
[boot] dispatching entry OPD 0x009FEE40
[ppu] run: code 0x00010230, toc 0x00A27440, sp 0x0FEFFF20
[SPU] initialize(nspu=6, nrawspu=0)
[cellSpurs] Initialize ... nSpus=5
[cellGcmSys] Init(cmdSize=0x10000, ioSize=0x7900000, ioAddr=0x11000000)
[cellGcmSys] SetDisplayBuffer(id=0, offset=0x3B0000, pitch=5120, 1280x720)
[SYS] sys_ppu_thread_create ... name="fios mediathread 2"
[sysPrxForUser] sys_process_exit(code=0)
```

O log termina com `sys_process_exit(code=0)` e volta ao prompt, **não comprova inicialização do menu, renderização de uma cena ou jogo jogável**. O motivo do encerramento não é confirmado por um código de erro único.

## Bloqueios relevantes

### 1. SPU sem código traduzido/registrado (comprovado, prioritário)

```text
[cellSpurs] wid=0 PM NOT LIFTED (fp=0xB3523C4B17650EF8 size=11904) -- workload will not run
[cellSpurs] wid=1 PM NOT LIFTED (fp=0xB3523C4B17650EF8 size=11904) -- workload will not run
[cellSpurs] wid=2 PM NOT LIFTED (fp=0xB3523C4B17650EF8 size=11904) -- workload will not run
[spu_workload] async dispatch MISS fp=0x00E729804474449A size=38100
[spu_workload] ERROR: async task dispatch of an SPU program with no lifted image ... program is DROPPED
```

O CMake foi configurado com `PORT_ENABLE_SPU=OFF` para isolar a primeira compilação, então não há registro de workloads SPU nesta build. É necessário levantar imagens SPU do ELF e arquivos adicionais, bem como capturar módulos dinâmicos de execução. **Não inventar stub de sucesso para tarefa SPU:** ela deve produzir efeitos reais.

O runtime `ps3recomp/runtime/spu/spu_workload.c` permite configurar **`SPU_DUMP_MISS=<diretório local>`** para registrar imagens SPU desconhecidas, inclusive no caminho assíncrono.

No **Developer Command Prompt x64** (CMD), na raiz do projeto:

```bat
if not exist "out\spu-misses" mkdir "out\spu-misses"
set "SPU_DUMP_MISS=%CD%\out\spu-misses"
"out\build\MyGameRecomp.exe" "private\game\EBOOT.elf"
dir /b "out\spu-misses"
```

O `dir` mostra **somente nomes de arquivos**. Dumps `.bin` contêm material derivado do jogo e **não podem ser enviados ao GitHub**. Posteriormente analisar a pertinência de `tools/lift_jobmods.py --jobmods` (código+dados sem cabeçalho ELF) ou `tools/build_spu_workloads.py --input` (programas ELF SPU embutidos). Não equiparar os dois tipos automaticamente; confirmar formato localmente primeiro.

### 2. Arquivos / VFS não encontrados (comprovado, obrigatório investigar)

A raiz VFS **observada** foi `private`, com mapeamento do `/dev_hdd0/game` para `private/game`. Há falhas ao abrir:

```text
.\USRDIR\ne.bv
private/PS3_GAME/USRDIR/cache_fob/psarc/install1/infamous1.psarc_s
private/PS3_GAME/USRDIR/cache_fob/psarc/install2/infamous2.psarc_s
private/game/NPUA80657_INSTALL/USRDIR/all_shaders.xpps
private/PS3_GAME/USRDIR/all_shaders.xpps
private/game/BLES00000/USRDIR/patch/psarc/patch1.psarc_s
private/game/BLES00000/USRDIR/patch/psarc/patch3.psarc_s
private/game/BLES00000/USRDIR/patch/psarc/patch4.psarc_s
```

Nem toda tentativa de abertura deve existir (algumas são buscas opcionais ou fallback); contudo **o jogo não encontrou os arquivos de shaders e arquivos psarc nestes caminhos**. Verificar a disposição dos próprios arquivos de instalação do jogo na máquina. **Não misturar versões/regiões de assets**; o identificador analisado é `NPUA80657`. Para redefinir a raiz do VFS, o template lê `PS3_VFS_ROOT` do ambiente. **Não copiar arquivos indiscriminadamente para caminhos sugeridos sem primeiro descobrir a estrutura real.**

### 3. Metadados da edição

```text
[cellGame] BootCheck: type=1, titleId='BLES00000'
[cellGame] DataCheck(type=3, dir='NPUA80657_INSTALL')
[cellGame] DataCheck(type=3, dir='NPUA80657')
```

`BLES00000` pode indicar metadados ausentes e valor padrão. **Hipótese, não evidência de que o ELF é de outra edição**. Validar `PARAM.SFO` e o mapeamento VFS antes de concluir.

### 4. Outras mensagens

- `[D3D12] Debug layer requested but unavailable`: ausência de recurso opcional de diagnóstico, **não é prova de falha de renderização**.
- `[tty] suspicious len` e `[null-read] guest read8 from 0x0`: atividade anômala a investigar após corrigir arquivos e SPU; **não há prova direta da causa**.
- O processo chamou `sys_process_exit(code=0)`, mas não chegou ao menu; status 0 **não significa sucesso funcional**.

## Próximo experimento orientado por evidências

1. Capturar **nomes** de dumps `SPU_DUMP_MISS` usando a build atual, mantendo bytes apenas no PC.
2. Inspecionar diretórios locais de assets e `PARAM.SFO`; comparar com os caminhos VFS procurados e ajustar raiz.
3. Descobrir/levantar SPU ELF e jobmods específicos do jogo, ligar o suporte SPU no CMake, recompilar e testar novamente.
4. Coletar novo log e comparar até onde o boot avança. Separar avisos secundários de bloqueios reais.

## Captura confirmada na segunda execução — 2026-11-16

O usuário executou o comando `SPU_DUMP_MISS` e enviou **apenas o log textual**. O runtime escreveu dois arquivos locais:

| Arquivo local (dentro de `out/spu-misses/`) | Tamanho / identificador | Papel observado |
|---|---:|---|
| `spujob_B3523C4B17650EF8_11904.bin` | 11.904 bytes, fp=0xB3523C4B17650EF8 | SPURS policy module `Wws_Job`, três workloads `General`, `EdgeGeom`, `SpuLight` (mesmo fp) |
| `spujob_00E729804474449A_38100.bin` | 38.100 bytes, fp=0x00E729804474449A | Programa despachado por `spu_workload_dispatch_async`, sem registro |

A captura **não** faz lifting nem registra esses módulos. O segundo teste também terminou com `sys_process_exit(code=0)`, sem menu; as falhas de VFS persistem. A extensão `.bin` e o nome `spujob_` são nomes do dumper, **não prova de que ambos são overlays WWS da mesma classe**.

**Cuidado:** `tools/lift_jobmods.py --jobmods` trata todos os `*.bin` de entrada como módulos WWS com cabeçalho especial; os primeiros 96 bytes do primeiro policy module no log `PM@0x0092D900` **não apresentam assinatura `C0DEC0DE` no deslocamento +0x20**, então não processar ambos indiscriminadamente por essa ferramenta.

### Próximo experimento: identificar formato real, sem extrair nem enviar código

No Developer Command Prompt x64, na raiz do projeto:

```bat
py -c "from pathlib import Path; files=sorted(Path('out/spu-misses').glob('*.bin')); [(lambda b: print(p.name, len(b), 'ELF32-SPU' if b[:4]==bytes.fromhex('7F454C46') and b[4:6]==bytes([1,2]) and b[18:20]==bytes([0,23]) else 'JOBMOD-C0DE' if b[32:36]==bytes.fromhex('C0DEC0DE') else 'RAW-OUTRO'))(p.read_bytes()) for p in files]"
```

Esse comando imprime somente nome, tamanho e a classificação preliminar: `ELF32-SPU`, `JOBMOD-C0DE` ou `RAW-OUTRO`. `RAW-OUTRO` não é um erro; pode ser um policy module sem cabeçalho ELF. Se um arquivo for ELF, o caminho correto é `build_spu_workloads.py --input` com compilação/registro; se for raw policy, exige estratégia própria de wrapping/lifting e registro sob o fingerprint específico. Verificar também se os arquivos originais do jogo e `PARAM.SFO` estão disponíveis na raiz adequada para `PS3_VFS_ROOT`.
