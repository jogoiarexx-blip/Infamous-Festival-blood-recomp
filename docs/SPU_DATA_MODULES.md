# Cinco kernels SPU DA7ABA5E — NPUA80657

`tools/prepare_data_modules.py` traduz os cinco módulos locais para LS 0x6C00,
com entrada 0x6C30. Os registros usam IDs 300–304 e verificam os bytes executáveis
no carregamento. O script exige SHA-256, cabeçalho e mapeamento PT_LOAD exatos;
qualquer divergência nesses dados é rejeitada. Todos os arquivos derivados ficam em `out/`.

No terminal de compilação já configurado para este projeto:

```powershell
py tools/prepare_data_modules.py --audit-only
py tools/prepare_data_modules.py
cmake -S out/port -B out/build
cmake --build out/build --target MyGameRecomp
py -m unittest discover -s tests -v
```

O gerador acrescenta `datamods_register.c` à lista de registros do CMake existente.
As cinco pastas entram no glob de fontes SPU. Não instala ferramentas e não altera
a simulação nem sinaliza conclusão de jobs.

Para repetir a comparação com entradas capturadas localmente:

```powershell
py tools/test_data_module_replay.py --sdk ../ps3recomp --spu-dir out/port/spu --snapshots out/data-kernel-replays-20261120 --output-dir out/data-replay --cc gcc
```

Cada arquivo privado `0.bin` a `4.bin` contém os 128 registradores de 16 bytes,
em representação nativa little-endian, seguidos dos 262144 bytes de LS, coletados
imediatamente antes da entrada 0x6C30, na ordem de `MODULES` do gerador. Esses dados
não são distribuídos. O teste exige o registro real, rejeita código divergente,
verifica o proprietário de cada overlay e compara todos os registradores, toda a
LS e o PC de retorno com interpretação sem funções nativas registradas na imagem
de referência. Fronteiras externas abortam se forem alcançadas.

Validação local em 20/11/2026: cinco entradas reais passaram, inclusive SSE4.1;
a compilação Windows padrão terminou. Na comparação com os mesmos diagnósticos,
a interpretação caiu de aproximadamente 25–30 milhões para 0,1 milhão de passos/s.
O runtime local foi mantido constante entre as duas execuções, incluindo o patch
0011 do PR #7, ainda em avaliação. O replay passou também na base pública do
SDK com os patches 0001–0010.
A superfície 3D intermediária salva antes e depois foi idêntica byte a byte.
Isso mede a remoção desse trabalho interpretado, não FPS sustentado do jogo.

Limites: somente uma entrada por kernel foi comparada, e interpretador e código
nativo compartilham os helpers do SDK. O teste não é um oráculo de hardware.
Os backbuffers ainda ficaram pretos e há esperas pendentes de áudio e de jobs.
30 FPS, menu funcional e correção da composição final não foram demonstrados.
