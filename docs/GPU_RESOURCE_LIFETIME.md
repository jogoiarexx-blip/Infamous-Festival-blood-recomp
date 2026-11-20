# Vida dos recursos D3D12 e confirmação dos fences

O patch 0012 deve ser aplicado após a série pública 0001–0010 ao SDK fixado.
Recursos substituídos de textura, upload, render target e profundidade mantêm
suas referências numa lista por frame até a confirmação da GPU. A lista cresce
quando necessário; atingir 512 itens não autoriza liberar um recurso pendente.
O encerramento espera a fila, drena ambos os índices e libera as listas.

As esperas confirmam o valor do fence após o evento. Falhas de Signal,
SetEventOnCompletion, evento ou dispositivo encerram o processo com diagnóstico.
Uma espera sem conclusão após três tentativas de 2000 ms também encerra; o jogo
não continua reutilizando os recursos nessa condição. Não há recuperação automática
do dispositivo. O retorno UINT64_MAX representa remoção do dispositivo, conforme
[a documentação da Microsoft](https://learn.microsoft.com/en-us/windows/win32/api/d3d12/nf-d3d12-id3d12fence-getcompletedvalue).

Validação sem GPU ou arquivos do jogo, usando o compilador já instalado:

```powershell
py tools/test_gpu_resource_retirement.py --sdk ../ps3recomp --cc gcc --output-dir out/gpu-resource-tests
```

O runner compila os helpers reais do SDK com objetos CPU que controlam resultados
de fence e contam liberações. São oito casos: crescimento além de 512 recursos,
timeout, dispositivo removido, encerramento dos dois índices, falhas de Signal e
do evento, evento sinalizado sem conclusão e confirmação válida. O teste público
não valida agendamento do driver nem todo o pipeline gráfico.

Validação local: aplicação limpa, build Windows do runtime e oito casos passaram.
O executável completo com as demais alterações locais rodou por 90 segundos sem
falhas de sincronização ou jobs SPU desconhecidos. A superfície 3D intermediária
salva permaneceu idêntica; os backbuffers continuaram pretos. Não há ganho de FPS,
menu funcional ou correção da composição final comprovados por esta mudança.
