# inFAMOUS: Festival of Blood — recompilação para PC

> **Estado da edição NPUA80657 (28/11/2026):** a build Windows reproduz as cinemáticas e chega à cena 3D. O patch 0034, numa corrida sem sonda, ficou em cerca de 12 fps de render. Essa corrida não teve a imagem conferida e não houve três corridas pareadas. Em 28/11/2026 o verde da cena foi localizado no terceiro alvo da geometria; o primeiro alvo tinha cor normal. Isso não é correção e não foi comparado ao RPCS3. Controle contínuo de Cole, combate, missões e salvamento ainda não foram validados.

Projeto comunitário e não oficial para estudar a viabilidade de uma recompilação estática de **inFAMOUS: Festival of Blood** (PlayStation 3) para PC, com base no ecossistema [ps3recomp](https://github.com/sp00nznet/ps3recomp).

**IMPORTANTE:** Este repositório **não** contém o jogo, código proprietário, chaves, firmware, arquivos de áudio ou arte. Não é um download do jogo. O usuário deve possuir sua própria cópia legal e manter os arquivos do jogo em seu computador.

## Estado verificado

- **VALIDADO** — A build local de Windows x64 com D3D12 inicia, reproduz a abertura e alcança uma cena 3D. Os testes automatizados do repositório concluíram 47 casos e pularam 2 em 22/11/2026.
- **PARCIAL** — A cena 3D ainda apresenta pausas e baixa taxa de avanço. O usuário observou aproximadamente 5 FPS em partes recentes. Na build de diagnóstico até o patch 0030, 66 intervalos entre pedidos de flip tiveram mediana de 315,6 ms (3,2 pedidos/s **sob rastreamento**). O contador de renderização mede outra coisa; houve duas submissões D3D12 para cada pedido de flip na janela 1000–1080. Nenhuma dessas medidas comprova 5 FPS sustentados de gameplay.
- **NA MAIN** — As correções até o patch 0034 estão na main. O 0031 liga AVX2/FMA só quando o compilador aceita. Não houve medição numa CPU sem essas instruções. A corrida de 12 fps do 0034 não teve a imagem conferida nem três corridas pareadas. As aberturas posteriores estão no relatório de desempenho.
- **PENDENTE** — Fluidez e estabilidade no 3D, vidro da garrafa, materiais translúcidos, controle de Cole, gameplay, combate, missões e save/load. Não há medição atual que comprove 30 FPS sustentados em gameplay.

Os logs e executáveis usados nesses testes ficam apenas na máquina de desenvolvimento. O repositório contém ferramentas, testes e patches para aplicar ao SDK ps3recomp. Para reproduzir o teste Windows, é necessário compilar o SDK e o port com CMake, Ninja, Visual Studio Build Tools e Direct3D 12, usando uma cópia legal do jogo em `private/game/`. Consulte [SETUP](docs/SETUP.md) e os [patches do runtime](patches/ps3recomp/) antes de compilar. REA e Ghidra foram usados localmente para inspecionar rotinas PPU, e são opcionais para executar a build.

As correções de runtime até o patch 0034 estão na main. Os outros pedidos abertos, de revisão e de rascunho, não foram fundidos. Consulte [o relatório de desempenho](CODEX_DESEMPENHO_RECOMP.md) para as medições, seus limites e as pendências antes de considerar o jogo jogável.

## O que já existe

- Ferramenta de identificação e inspeção **local** de cabeçalhos ELF/SELF, com hash SHA-256, Title ID NPDRM e metadados do ELF embutido.
- Inventário local de arquivos por tamanho e hash (opcional; não publica arquivos).
- **Analisador PPU** que contabiliza descritores OPD, endereços de função, TOC e bibliotecas sem distribuir código do jogo. Validado em EBOOT.elf NPUA80657.
- Testes unitários e CI sem conteúdo do jogo.
- Plano de investigação com critérios de validação.

## Boot local

- O código PPU e SPU foi recompilado localmente a partir dos arquivos do jogo.
- As correções de sincronização, vídeo e diagnóstico do SPU estão nos [patches do ps3recomp](patches/ps3recomp/).
- O patch 0034 liga, em AVX2, a soma, a multiplicação e o FMA de precisão simples com arredondamento para zero, e tira as inversões extras do shufb em SSE4.1. Aplica-se depois de 0001–0033. A medição e o que ainda não foi conferido estão em [CODEX_DESEMPENHO_RECOMP.md](CODEX_DESEMPENHO_RECOMP.md).
- O [rastreio do vídeo NPUA80657](docs/BINK-VIDEO-NPUA80657.md) documenta a transição após o splash e como aplicar os patches.

## Começar (Windows, Python 3.10+)

1. Instale Python 3.10+.
2. Faça um clone deste repositório.
3. Coloque **somente em sua máquina** os arquivos da sua cópia legal dentro de `private/game/`; essa pasta é ignorada pelo Git.
4. Se tiver um **ELF já obtido legalmente**, examine o cabeçalho (o script não descriptografa SELF):

```powershell
py tools/inspect_ps3_binary.py inspect "private/game/EBOOT.ELF" --output "out/eboot-report.json"
py tools/inspect_ps3_binary.py inventory "private/game" --output "out/inventory.json"
py tools/analyze_ppu.py "private/game/EBOOT.ELF" --output "out/ppu-summary.json"
py -m unittest discover -s tests -v
```

Se você só tiver um `EBOOT.BIN` no formato SELF, o script mostrará a identificação NPDRM e os metadados do cabeçalho ELF embutido. **Ele não extrai nem descriptografa o programa.** Não renomeie SELF para ELF: isso não o converte.

**Resultados reais:** [identificação SELF/NPDRM](docs/REPORT-NPUA80657.md) e [análise do ELF decodificado](docs/ELF_ANALYSIS_NPUA80657.md), da edição NPUA80657 de Festival of Blood.

> **Privacidade:** relatórios de inventário contêm nomes, tamanhos e hashes dos arquivos. Revise antes de compartilhá-los; não envie os próprios arquivos do jogo.

## Por que precisamos identificar a edição primeiro?

Não podemos assumir que a edição, o endereço das funções, as importações do sistema, os módulos SPU ou os arquivos de Festival of Blood são os mesmos de inFAMOUS 2. A compatibilidade será comprovada com análise local e testes, nunca presumida.

## Organização

| Caminho | Finalidade |
|---|---|
| `tools/` | Inspeção local de executáveis e preparação das imagens SPU |
| `patches/ps3recomp/` | Correções do runtime para aplicar ao ps3recomp |
| `tests/` | Testes sem conteúdo proprietário |
| `docs/ROADMAP.md` | Etapas e critérios de conclusão |
| `docs/RESEARCH.md` | Fontes, hipóteses e decisões |
| `docs/SETUP.md` | Instruções para iniciantes |
| `.github/workflows/` | Validação automática |

## Projetos de referência

- [ps3recomp](https://github.com/sp00nznet/ps3recomp) — ferramentas PPU/SPU e runtime HLE.
- [inFAMOUS 2 recomp](https://github.com/bhuiyah/infamous2-recomp) — arquitetura de projeto PC que usa ps3recomp; **não** é prova de compatibilidade com Festival of Blood.
- [Guia ps3recomp](https://github.com/sp00nznet/ps3recomp/blob/master/docs/GETTING_STARTED.md) — requisitos e pipeline.

Não copiamos arquivos protegidos nem código de outros projetos sem verificar sua licença.

## Aviso

Projeto não afiliado à Sony Interactive Entertainment ou Sucker Punch Productions. Marcas e jogos pertencem aos respectivos titulares.