# Decompilação parcial do caminho de vídeo

Edição `NPUA80657`. Nomes de campos e funções abaixo descrevem o comportamento observado no código PPU recompilado. Os endereços valem para o EBOOT local desta edição.

## Como o endereço chega ao SPU

1. `0x001F3EAC` lê o endereço inicial dos planos de vídeo em `objeto + 0x4C` e calcula os demais endereços pelo tamanho dos planos. O trecho em `0x001F40DC` grava o offset da primeira textura após consultar a tabela EA → IO.
2. O trecho em `0x001F4320` prepara os campos finais da textura. A rotina consulta a tabela IO → EA conforme as flags da textura e grava os endereços dos planos no descritor do decodificador.
3. O SPU RADG5 lê o descritor. No boot com falha, o primeiro campo do descritor, em `0x00AC581C`, ficou zerado. A imagem SPU tentou emitir PUTs de `0x2800` bytes começando em zero, e o MFC do runtime os rejeitou.

No rastreio que reproduziu a falha, a primeira conversão recebeu EA zero, a tabela em `0x20003000` devolveu `0xFFFF` e a textura ficou com offset `0xFFFFFFFF`. A conversão reversa recebeu esse offset e o descritor terminou com zero. Em outro boot o mesmo campo do descritor recebeu o EA `0x11271400`.

## Quem publica o campo +0x4C

- `0x001F3B54`, nos blocos `0x001F3D54` e `0x001F3DC0`, lê um recurso compartilhado pela TOC e copia a palavra em `recurso + 4` para `objeto + 0x4C`.
- `0x001F6524`, no caminho que inicia em `0x001F6674`, grava `1` em `+0x48`, chama `sys_lwcond_wait` e avança para a preparação de texturas quando o campo tem valor diferente de zero. Outro caminho da mesma função grava zero em `+0x4C` e `-1` em `+0x48` no bloco `0x001F6714`.
- `0x001F2C5C` também grava zero em `+0x4C` ao limpar os campos associados à liberação do recurso.
- A thread principal, em `0x001433BC`, alterou `+0x48` para `2` e publicou o buffer em `+0x4C` antes da chamada a `sys_lwcond_signal`. A instância rastreada começa em `0x00AC5430`.

No runtime anterior, `sys_lwcond_wait` liberava o mutex, dormia por 1 ms e retornava sucesso após readquiri-lo. As chamadas de sinalização retornavam sucesso sem acordar uma thread. O rastreio da falha mostrou o Movie Player preparando a textura no estado `1`, com o buffer zerado.

Em `runtime/ppu/ppu_sysprx.cpp`, a espera passou a registrar a thread antes de liberar o mutex e aguardar sinalização ou timeout. As variantes de sinalização acordam as threads elegíveis. A espera readquire o mutex antes de retornar. No boot com a alteração, o Movie Player observou o estado `2`, EA `0x11271400` e offset `0x00271400`.

## Critério para a correção

O ponto de intervenção é o runtime ou a tradução da operação que primeiro divergir. A lógica PPU e SPU continua recompilada. Para confirmar uma correção, o descritor deve receber os três endereços válidos antes do primeiro pedido ao Bink. O teste de boot também precisa verificar os quadros apresentados e a chegada ao menu.

## Apresentação dos planos YUV no Direct3D 12

Com a sincronização corrigida, a imagem RADG5 já escrevia nos buffers mapeados. O RSX vinculava uma textura B8 de 1280×720 e duas de 640×360. O backend padrão descartava a geometria enviada como valores imediatos dos atributos do vértice no FIFO, incluindo a posição de dois floats.

O processador de métodos passou a compartilhar a decodificação desses atributos com o dispatcher. Ele captura os valores correntes quando a posição é completada e envia a primitiva ao Direct3D 12 no fim do grupo. O backend usa a mesma expansão de triângulos e o mesmo caminho de shaders das outras primitivas.

O primeiro draw de vídeo revelou que o backend ainda substituía o plano Y por uma cópia do quadro anterior devido ao tamanho de 1280×720. Texturas B8 agora passam pelo upload da própria memória. O teste do executável com as duas mudanças registrou uploads de luminância a partir dos buffers do Bink e apresentou o logo da Sucker Punch em cores.

## Transição para o menu

Depois do splash, a edição local abriu `fob_logo.bik`. Em execuções com `SPU_MISS_FATAL=1`, o dispatcher também encontrou imagens SPURS sem registro, incluindo `0x5EC85F9D752F82D1` (18 960 bytes) e `0x7FD662F57F44EC4C` (2 192 bytes) em execuções diferentes. Essas ocorrências dependem da execução. Ainda falta identificar os jobs e verificar se explicam a tela preta após o splash.

Na captura anterior, o modo fatal abortava antes de salvar a imagem do job. O segundo patch move a captura para antes do aviso fatal, permitindo usar `SPU_DUMP_MISS` com `SPU_MISS_FATAL=1`. A pasta de destino precisa existir. Mantenha os dumps em `out/` e use-os somente no build local. No teste de boot após recompilar com esse patch, o executável chegou a `fob_logo.bik` e registrou esperas de semáforo até o fim da janela de 65 segundos. Esse teste não voltou a encontrar as imagens sem registro.

Nesse mesmo teste, o RSX vinculou a textura B8 de 1280×720 no offset local `0x0F800000` antes de o rastreio SPU registrar escritas DMA de 160 bytes em `0xCF800000` e nas linhas seguintes, com passo de 1280 bytes. O endereço também aparece no relatório sobre o buffer de oclusão da edição europeia. A ordem das chamadas no log é uma pista para verificar quando o backend atualiza essa textura na edição americana. [Notas do fork de RPCS3 para a edição europeia](https://github.com/ttmx/rpcs3-infamous2/blob/infamous2-optimizations/festival/README.md)

## Remapeamento B8 e rastreio da transição

O backend D3D12 usava o mesmo mapeamento de canais em todos os uploads B8. Com `TEXTURE_CONTROL1=0xA9FF`, a textura de `0xCF800000` deve fornecer o byte B8 em RGB e valor 1 em alfa. O backend fornecia o byte B8 em todos os canais. O terceiro patch usa o decodificador de remapeamento existente. Com `0xAAFF`, usado para replicar o byte B8 nos quatro canais, o resultado continua sendo `0x1000` no D3D12. O teste do mapeamento observado em `0xA9FF` passou de `0x1000` para `0x1A00`. [Mapeamento B8 no RPCS3](https://github.com/RPCS3/rpcs3/blob/master/rpcs3/Emu/RSX/VK/VKFormats.cpp)

No teste com o terceiro patch, a abertura da Sucker Punch apareceu em cores. Depois de abrir `fob_logo.bik`, a captura tardia continuou sem mostrar o menu. O rastreio registrou pedidos de PUT para `0xCF800000` antes de um upload em que as amostras da textura ainda estavam zeradas. A origem dos zeros precisa ser verificada entre os bytes na LS do SPU, a conclusão do DMA e a leitura do D3D12.

Com `SEMTID=1`, as esperas repetidas de 5 ms no semáforo `RADGAME` foram atribuídas à thread `Bink Snd`. No mesmo intervalo, `PS3_SAMPLE_MAIN=1` amostrou a thread principal executando funções PPU. O log de áudio mostrou a reabertura da porta Bink após o splash, e a segunda abertura ficou sem um `PortStart` registrado durante esse teste.

## Jobs SPURS capturados na transição

Uma execução com `SPU_DUMP_MISS` capturou `0x2BC127B9AAF9165A` (5 520 bytes), `0x5EC85F9D752F82D1` (18 960 bytes) e `0x7FD662F57F44EC4C` (2 192 bytes) após abrir `fob_logo.bik`. Os 2 192 bytes correspondem a outro job além de `0x8927C5C0BC233071`, que tem o mesmo tamanho. O tradutor encontrou as três entradas e resolveu todos os alvos diretos registrados no relatório. O teste no executável recompilado confirmou os três registros SPU.

Passe a pasta com as capturas locais para `--transition-dumps` em conjunto com `--boot-dumps` e `--later-dumps`. O script gera e registra nove jobs com os três grupos adicionais habilitados.

Em um boot de 95 segundos com as nove imagens registradas e `SPU_MISS_FATAL=1`, houve abertura de `fob_logo.bik` sem novos misses. O log desse boot também ficou sem chamadas para os três jobs adicionais. Entre os quadros tardios capturados, a imagem alternou entre saída preta e um quadro claro com artefato no topo. O menu permaneceu ausente.

## O que chega ao decodificador depois do splash

Dois boots de 65 segundos do build local de `NPUA80657` reproduziram a mesma sequência. `splash_fob_america.bik` toca, `tv_fob_feed_2x2.bik` abre e fecha, e `fob_logo.bik` reusa o descritor 8. Para `fob_logo.bik`, cada uma das 20 leituras entregou os 128 KiB pedidos. A cobertura é contínua entre o início do arquivo e o offset `0x280000` (2,5 MiB), onde as leituras pararam durante a observação. O índice Bink local coloca 39 quadros compactados completos dentro desse trecho. Esse número mede os dados carregados, e a saída de vídeo precisa ser verificada à parte. [Leitura do índice Bink no FFmpeg](https://github.com/FFmpeg/FFmpeg/blob/master/libavformat/bink.c)

No rastreio do `SP Movie Player` com base em `0x00AC5430`, a abertura inicial fez `+0x48` passar de `1` para `2` e publicou `0x11771400` em `+0x4C`. Depois de abrir `fob_logo.bik`, os dois campos daquela instância ficaram sem novas gravações registradas. O outro rastreio registrou os planos YUV da abertura inicial e, depois da troca, uma textura B8 de cena com outro remapeamento. O log de áudio mostrou a porta 1 ser reaberta sem um segundo `PortStart` registrado. A investigação segue na passagem dos dados carregados para o primeiro pedido de decodificação e na identificação da instância que controla `fob_logo.bik`.

Para repetir o rastreio de I/O no build local, habilite `FS_CALLER=1` e `PS3_FSLOG_READS=8` e acompanhe as leituras entre a abertura de `fob_logo.bik` e o fechamento ou fim da captura. Use o descritor retornado em `open` se a execução escolher outro número. Para repetir a observação do objeto, use `PPU_WWATCH=00AC5470`, `PPU_WWATCH_LEN=0x20` e `PPU_WWATCH_MAX=400`. O endereço se refere à instância capturada nessa edição.

## Aplicar as correções do runtime

Os patches usam o commit [`de4f090` do ps3recomp](https://github.com/sp00nznet/ps3recomp/tree/de4f090328ea08bef6b2f15caec0b85e343a7ece) como base. A partir da raiz deste repositório, com uma cópia limpa do ps3recomp nesse commit em `../ps3recomp`, execute no PowerShell.

```powershell
$patches = Get-ChildItem patches/ps3recomp -Filter '*.patch' | Sort-Object Name
foreach ($patch in $patches) {
    git -C ../ps3recomp apply --check $patch.FullName
    if ($LASTEXITCODE -ne 0) { throw "Patch incompatível: $($patch.Name)" }
    git -C ../ps3recomp apply $patch.FullName
    if ($LASTEXITCODE -ne 0) { throw "Falha ao aplicar: $($patch.Name)" }
}
```

O script `tools/prepare_spurs_jobs.py` aceita as capturas dos jobs adicionais com `--boot-dumps` e `--later-dumps`, depois de `prepare_spu_elf.py`. Ele valida tamanho e fingerprint antes de registrar a função recompilada. Use `--help` para as opções. Os patches cobrem sincronização, apresentação do splash e captura para diagnóstico. A execução local usa outras preparações do port e imagens PPU/SPU geradas a partir da cópia local do jogo.

Na comparação com o RPCS3, a thread é adicionada à fila de `lwcond` antes de liberar o mutex associado. Essa sequência é o comportamento usado como referência no patch do runtime. [Implementação de `sys_lwcond` no RPCS3](https://github.com/RPCS3/rpcs3/blob/master/rpcs3/Emu/Cell/lv2/sys_lwcond.cpp)
