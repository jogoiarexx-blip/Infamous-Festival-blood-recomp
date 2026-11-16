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

## Identificação dos formatos — próxima etapa

O usuário confirmou via análise local de cabeçalho:

```text
spujob_00E729804474449A_38100.bin 38100 ELF32-SPU
spujob_B3523C4B17650EF8_11904.bin 11904 RAW-OUTRO
```

- O primeiro arquivo foi reconhecido como ELF32 big-endian, máquina SPU. Agora é candidato a `build_spu_workloads.py --input`, com validação adicional de layout/segmentos pelo gerador.
- O segundo **não** passou nem na identificação de ELF nem na assinatura `C0DEC0DE` em `+0x20`; é um policy module SPURS raw, cujo caminho de lifting/registro precisará ser construído/validado separadamente. Não passar esse arquivo a `lift_jobmods.py --jobmods` indiscriminadamente.

### Configuração incremental (somente ELF-SPU)

No **x64 Native Tools Command Prompt** já configurado, a partir da raiz do projeto:

```bat
cmake -S "out\port" -B "out\build" -DPORT_ENABLE_SPU=ON "-DPORT_SPU_INPUTS:STRING=%CD%\out\spu-misses\spujob_00E729804474449A_38100.bin"
```

Esse comando **apenas reconfigura e gera o C SPU**, se a entrada passar nas validações. Ele reutiliza o cache do CMake que já tem Ninja/clang-cl/SDK e fontes PPU existentes. Não acionar `cmake --build` até analisar o resultado e eventuais relatórios de programa não suportado em `out/build/generated_spu/inventory.json`. O campo `PORT_ENABLE_SPU` não significa que todo o suporte do jogo foi concluído.

Depois da validação, compilar incrementalmente e continuar investigação dos arquivos PSARC e `PARAM.SFO` a partir de uma cópia legal local.


### Lifter SPU: 213 `.word` gerados (diagnóstico novo)

A inspeção local de `out/build/generated_spu/inventory.json` mostrou `diagnostics.unsupported = {".word": 213}`. O C recompilado contém instruções não decodificadas a partir de `0xB2A4`; os primeiros exemplos incluem `0x65646765` (ASCII `edge`) e `0x7A6C6962` (`zlib`). Isso é **evidência de possível região de dados/strings indevidamente decodificada como código**, não prova de 213 opcodes SPU ausentes. O `spu_lifter.py` upstream suporta `--code-end`, mas o pipeline automatizado `build_spu_workloads --input` não repassa hoje esse limite; se for confirmado um limite seguro, será necessário ajustar a detecção/geração mantendo `code_ranges`, entradas, alvos e sua validação. Não substituir `.word` por NOPs.

**Próximo dado:** obter menor/maior endereço de `spu_unsupported`, quantidade antes de `0xB2A4` e limites finais das funções detectadas. Nenhum ELF ou .bin deve ser enviado ao repositório.

## Dados de limite de código SPU (inspeção local)

O lifter reportou **213 instruções não suportadas, todas `.word`**. Os endereços variam de **0xB2A4** até **0xC20C**; **0 ocorrências antes de 0xB2A4**. Há falsas entradas candidatas até `0xC244`, por exemplo `0xC1F0..0xC22C`. Várias palavras contêm texto legível (`edge`, `zlib`), sugerindo que a área foi erroneamente disassemblada como instruções.

**Hipótese forte:** sufixo de dados/strings dentro da região PF_X do SPU ELF. O `spu_lifter.py` possui `--code-end`, mas o pipeline `build_spu_workloads.py --input` ainda não oferece parâmetro para repassá-lo. **Não usar automaticamente 0xB2A4 como corte** até conferir se alguma função legítima cruza a fronteira ou se existem alvos reais de chamadas/saltos posteriores. Validar esses dois pontos antes de modificar a geração, para evitar exclusão de código real. Nenhum código ou asset do jogo foi publicado.

## Verificação adicional de fronteira — 2026-11-16

O usuário examinou `diagnostics.functions`, `call_targets` e `branch_targets` com candidato de corte `0xB2A4` e obteve:

```text
ENTRY: 0x3050
FUNCOES CRUZANDO LIMITE: [('0xb290', '0xb2b0')]
ULTIMAS ANTES: [('0xb178','0xb1b0'), ..., ('0xb260','0xb290'), ('0xb290','0xb2b0')]
FUNCOES APOS: 39
CHAMADAS APOS: ['0x17190', '0x22614']
SALTOS APOS: ['0x1bf60','0x1f69c','0x2a41c','0x2bd2c',...]
```

O relatório indica que cortar em `0xB2A4` **atravessaria uma função detectada** e excluiria 39 outras candidatas. Os alvos mostrados a partir desse limite estão acima do fim das funções listadas (até `0xC244`), consistentemente com interpretação indevida de dados, mas ainda não é prova de que nenhum byte anterior é dado. Próximo passo: inspecionar **somente localmente** as instruções e o padrão ASCII nos bytes `0xB260..0xB2E0`, mais contagem exaustiva de targets dentro do intervalo `0xB2A4..0xC244`. Só então propor limite seguro para lifting.

O `code.bin` do gerador mantém bytes da imagem SPU local e não pode ser comitado. Um script de inspeção local pode imprimir hex, mnemônicos e resumo de endereços sem publicar o binário.

## Teste isolado do limite SPU `--code-end 0xB2A4`

O usuário executou uma experiência **local** com `spu_lifter.py --code-end 0xB2A4` em `out/spu-tail-test` (sem alterar fontes do SDK nem o EXE já compilado).

```text
[spu_lifter] code-end 0xB2A4: kept 622/661 bound(s), data tail left un-disassembled
622 function(s) lifted
37 call target(s)
EXIT: 0
UNSUPPORTED: {}
MISSING_TARGETS: ['0x2bd2c']
FUNCTIONS: 622
```

**Interpretação:** o limite removia toda a ocorrência de 213 pseudo-instruções `.word`, coerente com hipótese de strings e dados na cauda do segmento executável. **Ainda não valida a imagem**: o código gerado contém uma referência a `0x2BD2C` sem função traduzida com tal endereço. `spu_lifter.py` gera um stub de indireção para destinos ausentes, portanto esse resultado não é necessariamente uma falha de compilação, mas é um bloqueio de correção/execução.

**Próximo teste:** usar o disassembler oficial na máquina local para identificar a instrução e o endereço de origem da referência `0x2BD2C`, junto com `executable_ranges` do inventory. Evitar integrar ao CMake ou desabilitar validações até classificar a referência como correta ou espúria.

## Origem do salto externo (confirmação do usuário)

Inspeção de `image.elf` do programa SPU capturado, usando `find_spu_functions.text_image` + `spu_disasm.disassemble_spu`:

```text
BASE: 0x3000
FAIXAS_EXECUTAVEIS: [('0x3000', '0xc350')]
ORIGENS_DO_SALTO: [('0xb294', 'brz', '$r83, 0x2BD2C')]
```

O **único destino pendente** identificado no teste limitado em `0xB2A4` vem da instrução `brz` em `0xB294`; `0x2BD2C` fica fora da faixa executável do arquivo SPU, mas ainda pertence ao espaço de endereçamento possível do local store. Não assumir que é salto legítimo nem que é sempre erro de CPU. A instrução fica dentro da função candidata `0xB290..0xB2B0`, que começou imediatamente após `0xB260..0xB290`. **Hipótese forte:** a detecção de função em `0xB290` é falsa devido à região de dados.

Próxima validação **sem alterar o SDK**: testar `spu_lifter --code-end 0xB290` numa nova pasta `out/spu-tail-test-b290` e confirmar `unsupported={}`, destinos pendentes vazios e preservação da entrada `0x3050`. Isso **não prova jogabilidade**, e um corte só será incorporado depois de confirmar que os control flows legítimos não entram nessa área. Nenhum arquivo de jogo é publicado.

## Compilação com o primeiro ELF SPU — evidência local (16/11/2026)

Após executar `tools/prepare_spu_elf.py`, o usuário confirmou `SUCESSO: SPU ELF preparado e registrado localmente`, `621` funções, nenhuma instrução não suportada e nenhum destino direto ausente. O CMake foi reconfigurado para usar `out/port/spu` e `PORT_SPU_INPUTS` vazio.

O log de compilação enviado termina com:

```text
out/port/spu/spu_workloads.c: ... warning: declaration requires a global constructor
93 warnings generated.
[4/5] Linking CXX executable MyGameRecomp.exe
D:\infamous recomp\Infamous-Festival-blood-recomp-main>
```

Não há erro fatal ou falha de linker nas linhas recebidas. O terminal voltou ao prompt depois do link; **compilação aparentemente concluída com êxito**, sujeita a confirmação de data do EXE. As 93 mensagens são advertências de compilação, não prova de erro.

**Próximos passos:** conferir a presença e data de `out/build/MyGameRecomp.exe` e executar um teste de boot redirecionando stdout/stderr a `out/boot_spu.log`. Verificar se o fingerprint ELF `00E729804474449A` ainda mostra `async dispatch MISS`, se o módulo SPURS raw `B3523C4B17650EF8` permanece `PM NOT LIFTED`, se o VFS continua falhando e se há progressão além de `sys_process_exit(code=0)`. Não declarar o jogo jogável sem esses dados. Logs de diagnóstico podem ser compartilhados após revisar dados privados; não publicar EBOOT, `.bin`, PSARC ou C gerado.

## Boot com primeiro SPU registrado — evidência de mudança real (16/11/2026)

Resultado do segundo boot `out/boot_spu.log`, extraído pelo usuário:

```text
[cellSpurs] wid=0 PM NOT LIFTED (fp=0xB3523C4B17650EF8 size=11904)
[cellSpurs] wid=1 PM NOT LIFTED (fp=0xB3523C4B17650EF8 size=11904)
[cellSpurs] wid=2 PM NOT LIFTED (fp=0xB3523C4B17650EF8 size=11904)
[spu_workload] dispatch HIT (async) fp=0x00E729804474449A args=0x10480200 image=1 -> spawning thread
[spu_workload] WAIT_SIGNAL#1 enter task=0 taskset=0x10481200 ran=0ms
[sys_fs] open FAILED: .\USRDIR\ne.bv
[fs] open FAIL '/dev_bdvd/PS3_GAME/USRDIR/cache_fob/psarc/install1/infamous1.psarc_s' -> 'private/PS3_GAME/USRDIR/cache_fob/psarc/install1/infamous1.psarc_s'
[fs] open FAIL '/dev_bdvd/PS3_GAME/USRDIR/cache_fob/psarc/install2/infamous2.psarc_s' -> 'private/PS3_GAME/USRDIR/cache_fob/psarc/install2/infamous2.psarc_s'
[fs] open FAIL '/dev_hdd0/game/NPUA80657_INSTALL/USRDIR/all_shaders.xpps' -> 'private/game/NPUA80657_INSTALL/USRDIR/all_shaders.xpps'
[fs] open FAIL '/dev_bdvd/PS3_GAME/USRDIR/all_shaders.xpps' -> 'private/PS3_GAME/USRDIR/all_shaders.xpps'
[sysPrxForUser] sys_process_exit(code=0)
```

**Vitória confirmada:** o fingerprint SPU ELF antes descartado por `dispatch MISS` agora passa pelo lookup e inicia uma thread. Não confundir `dispatch HIT` com tarefa finalizada ou jogo jogável. A espera `WAIT_SIGNAL` e as três políticas SPURS `PM NOT LIFTED` continuam sem solução.

**Próxima prioridade:** inventariar **somente nomes e caminhos** dos arquivos originais presentes em `private/` (especialmente `PARAM.SFO`, `ne.bv`, `infamous1.psarc_s`, `infamous2.psarc_s` e `all_shaders.xpps`). Distinguir arquivo inexistente de arquivo presente sob raiz VFS errada, antes de qualquer mudança no mapper; checar `PS3_VFS_ROOT` conforme os caminhos no log. Depois, tratar o módulo SPURS policy raw por fluxo separado, sem tratá-lo como ELF ou jobmod com `C0DEC0DE`.

**Não publicar** arquivos do jogo, code dump SPU, executável ou fontes geradas.

## Diagnóstico filesystem (16/11/2026) — cinco arquivos ausentes em `private/`

O usuário executou uma busca recursiva **no diretório local `private/`** e reportou:

```text
PARAM.SFO: NAO ENCONTRADO
ne.bv: NAO ENCONTRADO
infamous1.psarc_s: NAO ENCONTRADO
infamous2.psarc_s: NAO ENCONTRADO
all_shaders.xpps: NAO ENCONTRADO
```

Isso comprova **ausência desses nomes sob `private/`**, não ausência na máquina inteira ou incompatibilidade de formato. O runtime traduziu os caminhos `/dev_bdvd/...` para `private/PS3_GAME/...` e `/dev_hdd0/...` para `private/game/...`; portanto trocar só o código SPU não poderá suprir recursos ausentes. A edição digital foi identificada como `NPUA80657`, mas o `BootCheck` ainda usa `BLES00000`; `PARAM.SFO` faltante pode ser relacionado, sem prova definitiva.

**Próxima ação:** procurar os recursos e a estrutura de instalação da cópia legítima em outra pasta da máquina, apenas listando nomes e caminhos, e definir `PS3_VFS_ROOT` / `PS3_HDD0_ROOT` conforme a disposição real em disco. Não criar arquivos vazios com os nomes ausentes, não baixar arquivos de terceiros e não commitar assets. A investigação do SPURS policy raw segue independente. Sem uma cópia íntegra, não é possível validar o menu.

## Busca mais ampla de recursos: pasta inteira da recompilação — ausência confirmada

O usuário executou busca recursiva na pasta `D:\infamous recomp` (pai do projeto), cobrindo `PARAM.SFO`, `ne.bv`, `infamous1.psarc_s`, `infamous2.psarc_s`, `all_shaders.xpps` e extensões `.pkg`/`.iso`. Resultado:

```text
BUSCA EM: D:\infamous recomp
NENHUM ARQUIVO ENCONTRADO
TOTAL: 0
```

Isso **não prova ausência em todo o PC**. A montagem VFS atual é insuficiente para chegar ao menu sem os recursos originais. Não criar arquivos falsos nem publicar dados protegidos.

### Avançar em paralelo: diagnóstico local do policy module SPURS

Publicado **script original sem binário do jogo**: [`tools/inspect_spurs_policy.py`](../tools/inspect_spurs_policy.py), que inspeciona `out/spu-misses/spujob_B3523C4B17650EF8_11904.bin` estritamente local, valida tamanho 11.904 e FNV-1a `B3523C4B17650EF8`, usa base LS `0xA00` conforme o runtime `spurs_policy.c`, executa detector `find_spu_functions.py --raw` e depois `spu_lifter.py` para gerar **somente um relatório experimental** em `out/spurs-policy-probe`. O script imprime contagens de funções, instruções não suportadas, destinos ausentes e primeiros endereços problemáticos.

**Não registra nem compila o módulo raw no EXE**; a integração definitiva exige validação adicional de semântica e possíveis regiões de dados. Não confundir policy raw com ELF ou jobmod `C0DEC0DE`.

Na raiz do checkout Windows:

```bat
curl.exe -fL "https://raw.githubusercontent.com/jogoiarexx-blip/Infamous-Festival-blood-recomp/main/tools/inspect_spurs_policy.py" -o "tools\inspect_spurs_policy.py"
py "tools\inspect_spurs_policy.py"
```

Enviar somente as linhas resumo produzidas pelo script, não os binários/arquivos C gerados. Se a cópia legítima completa do jogo existir fora de `D:\infamous recomp`, localizar pasta e montar VFS após validar a estrutura.

## Boot com tela preta e espera SPURS — 16/11/2026 (log do usuário)

Com `infamous1.psarc_s` copiado para o caminho VFS solicitado, o usuário executou `out/build/MyGameRecomp.exe`. A janela D3D12 abriu com FPS variando, **sem imagem**. O log de encerramento contém:

```text
[fs] open FAIL '/dev_hdd0/game/NPUA80657_INSTALL/USRDIR/all_shaders.xpps'
[fs] read fd=3 nbytes=10735 -> 10735 (magic=78DAED9D, total=109883)
[hle] unresolved NID 0x8A85674D
[D3D12] device: "NVIDIA GeForce RTX 4060"
[D3D12] Initialization complete (1280x720, 2 buffers, pipeline=ready)
[rsx] D3D12 backend init OK -- window open
[RSX] unknown method 0x0370 = 0x0000FFF0
[RSX] unknown method 0x1FCC = 0x0000006F
[RSX] unknown method 0x01A8 = 0xFEED0001
[RSX] unknown method 0x1450 = 0x00080004
[spu_workload] task 0 (taskset 0x10481200) sleeping 1s...16s in WAIT_SIGNAL
[cellSpurs] EventFlagWait BLOCKED tid=26160 24s on pattern 0x0001 (mode=AND, bits=0x0000) flagEA=0x10482B00
[quit] requested (window closed)
[quit] the game did not exit on its own; ending it ...
```

**Interpretação:** D3D12 inicializado não é frame desenhado. Uma thread de tarefa SPU estacionou em `WAIT_SIGNAL`, enquanto a thread PPU permaneceu esperando `cellSpursEventFlagWait` pelo bit `0x0001` que continuou zero por 24s. O processo **não** chegou a concluir essa sequência: o usuário fechou a janela. Os 3 workloads `PM NOT LIFTED` da execução anterior ainda não foram implementados. Ninguém deve forçar/fabricar esse bit para mostrar o menu: a tarefa precisa produzir os dados de fato.

**Nova descoberta importante:** o NID HLE não resolvido `0x8A85674D` é **`_cellSpursLFQueuePushBody`**, conforme listas de NID da PS3 Developer Wiki. O SDK já possui `_cellSpursLFQueueInitialize` e `cellSpursQueuePushBody` (esta última é uma API **diferente**) em `libs/spurs/cellSpurs.c`; não foi encontrada implementação de `_cellSpursLFQueuePushBody`. Isso acrescenta uma hipótese plausível para a ausência de sinal: uma operação de fila SPURS foi descartada por HLE ausente. É **necessário identificar ABI e layout da LFQueue real antes de implementar**; não substituir `_cellSpursLFQueuePushBody` pela `cellSpursQueuePushBody` sem validação.

**Próximas ações prioritárias:**
1. Rodar `tools/inspect_spurs_policy.py` (já publicado no repo) sobre o módulo RAW `B3523C4B17650EF8`, sem compilar/registrar prematuramente. Compartilhar só resumo de mnemônicos/limites, não binário.
2. Verificar a estrutura da LFQueue e a origem do NID `0x8A85674D`, incluindo chamada e parâmetros, antes de adicionar HLE com comportamento real. Evitar retorno de sucesso falso.
3. Verificar `all_shaders.xpps` e método RSX só após a conclusão das tarefas de inicialização, porque a tela preta pode ser consequência do bloqueio SPURS e da ausência de recursos.
