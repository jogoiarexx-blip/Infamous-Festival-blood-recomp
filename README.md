# inFAMOUS: Festival of Blood — recompilação para PC

> **Estado da edição NPUA80657 (teste local de 22/11/2026):** a build Windows reproduz a abertura e chega a uma cena 3D. O controle de Cole, combate, missões, salvamento e exploração contínua ainda não foram confirmados. Esta página descreve uma build local gerada com ps3recomp e arquivos privados do próprio usuário.

Projeto comunitário e não oficial para estudar a viabilidade de uma recompilação estática de **inFAMOUS: Festival of Blood** (PlayStation 3) para PC, com base no ecossistema [ps3recomp](https://github.com/sp00nznet/ps3recomp).

**IMPORTANTE:** Este repositório **não** contém o jogo, código proprietário, chaves, firmware, arquivos de áudio ou arte. Não é um download do jogo. O usuário deve possuir sua própria cópia legal e manter os arquivos do jogo em seu computador.

## Estado verificado

- **VALIDADO** — A build local de Windows x64 com D3D12 inicia, reproduz a abertura e alcança uma cena 3D. Os testes automatizados do repositório concluíram 47 casos e pularam 2 em 22/11/2026.
- **PARCIAL** — A cena 3D ainda apresenta pausas e baixa taxa de apresentação. Uma execução sem o rastreio atômico mostrou 1,48 flips/s nos últimos 30 flips. Uma candidata com publicação atômica dos índices LFQueue mostrou 1,94 flips/s em uma execução equivalente. Esses números isolados não comprovam ganho sustentado.
- **EXPERIMENTAL** — A PR #15 reúne patches de runtime e permanece em revisão. A PR #16 corrigiu a publicação dos índices LFQueue no patch agregado e foi integrada à `main`. O cache persistente de shaders e outras mudanças da PR #15 ainda exigem validação antes de integrar.
- **PENDENTE** — Fluidez e estabilidade no 3D, vidro da garrafa, materiais translúcidos, controle de Cole, gameplay, combate, missões e save/load. Não há medição atual que comprove 30 FPS sustentados em gameplay.

Os logs e executáveis usados nesses testes ficam apenas na máquina de desenvolvimento. O repositório contém ferramentas, testes e patches para aplicar ao SDK ps3recomp. Para reproduzir o teste Windows, é necessário compilar o SDK e o port com CMake, Ninja, Visual Studio Build Tools e Direct3D 12, usando uma cópia legal do jogo em `private/game/`. Consulte [SETUP](docs/SETUP.md) e os [patches do runtime](patches/ps3recomp/) antes de compilar. REA e Ghidra foram usados localmente para inspecionar rotinas PPU, e são opcionais para executar a build.

As PRs #7, #9, #13 e #14 continuam abertas para revisão. As PRs #8, #10, #11, #12 e #16 foram mescladas. A PR #15 permanece aberta com dependências e riscos técnicos a resolver.

## O que já existe

- Ferramenta de identificação e inspeção **local** de cabeçalhos ELF/SELF, com hash SHA-256, Title ID NPDRM e metadados do ELF embutido.
- Inventário local de arquivos por tamanho e hash (opcional; não publica arquivos).
- **Analisador PPU** que contabiliza descritores OPD, endereços de função, TOC e bibliotecas sem distribuir código do jogo. Validado em EBOOT.elf NPUA80657.
- Testes unitários e CI sem conteúdo do jogo.
- Plano de investigação com critérios de validação.

## Boot local

- O código PPU e SPU foi recompilado localmente a partir dos arquivos do jogo.
- As correções de sincronização, vídeo e diagnóstico do SPU estão nos [patches do ps3recomp](patches/ps3recomp/).
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