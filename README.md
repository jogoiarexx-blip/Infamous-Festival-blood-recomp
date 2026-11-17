# inFAMOUS: Festival of Blood — recompilação para PC

> **Estado: o jogo renderiza o aviso de epilepsia completo a ~100 FPS em teste local e chega ao vídeo de splash (Bink); SPU/SPURS liftados (política, tarefa, jobs, RADG5, 27 módulos WWS). Menu ainda não alcançado. Não jogável.**

Projeto comunitário e não oficial para estudar a viabilidade de uma recompilação estática de **inFAMOUS: Festival of Blood** (PlayStation 3) para PC, com base no ecossistema [ps3recomp](https://github.com/sp00nznet/ps3recomp).

**IMPORTANTE:** Este repositório **não** contém o jogo, código proprietário, chaves, firmware, arquivos de áudio ou arte. Não é um download do jogo. O usuário deve possuir sua própria cópia legal e manter os arquivos do jogo em seu computador.

## O que já existe

- Ferramenta de identificação e inspeção **local** de cabeçalhos ELF/SELF, com hash SHA-256, Title ID NPDRM e metadados do ELF embutido.
- Inventário local de arquivos por tamanho e hash (opcional; não publica arquivos).
- **Analisador PPU** que contabiliza descritores OPD, endereços de função, TOC e bibliotecas sem distribuir código do jogo. Validado em EBOOT.elf NPUA80657.
- Testes unitários e CI sem conteúdo do jogo.
- Plano de investigação com critérios de validação.

## O que não existe ainda

- Recompilação de funções PPU/SPU específicas deste jogo.
- Runtime de Festival of Blood, gráficos, áudio ou gameplay.
- Executável jogável ou suporte confirmado a uma edição específica.

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

**Atenção:** O pipeline oficial do ps3recomp e a tradução das funções ainda não foram executados; esta é somente a etapa de análise estática.

> **Privacidade:** relatórios de inventário contêm nomes, tamanhos e hashes dos arquivos. Revise antes de compartilhá-los; não envie os próprios arquivos do jogo.

## Por que precisamos identificar a edição primeiro?

Não podemos assumir que a edição, o endereço das funções, as importações do sistema, os módulos SPU ou os arquivos de Festival of Blood são os mesmos de inFAMOUS 2. A compatibilidade será comprovada com análise local e testes, nunca presumida.

## Organização

| Caminho | Finalidade |
|---|---|
| `tools/` | Inspeção local de executáveis e inventário |
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