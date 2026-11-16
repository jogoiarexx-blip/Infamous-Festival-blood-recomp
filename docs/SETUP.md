# Instalação inicial — passo a passo no Windows

**Não é possível jogar ainda.** Este guia prepara a inspeção local da sua própria cópia.

## 1. Instalar Python
Instale Python 3.10+ em [python.org](https://www.python.org/downloads/). No PowerShell, confira:

```powershell
py --version
```

## 2. Baixar os scripts
No GitHub, escolha **Code > Download ZIP** e extraia para uma pasta. Opcionalmente use Git:

```powershell
git clone https://github.com/jogoiarexx-blip/Infamous-Festival-blood-recomp.git
cd Infamous-Festival-blood-recomp
```

## 3. Preparar os arquivos do jogo — somente local
Crie `private/game/` dentro da pasta do projeto. Coloque os arquivos **legalmente obtidos** da sua cópia nessa pasta. **Não os envie para o GitHub ou para este chat.** O Git ignora `private/` por padrão.

- Se possui um `EBOOT.BIN` retail, é provável que seja SELF/SCE. O analisador identifica o contêiner, mas **não o converte**.
- O pipeline ps3recomp requer um ELF já disponível legalmente. O guia oficial explica requisitos e formatos: [Getting Started](https://github.com/sp00nznet/ps3recomp/blob/master/docs/GETTING_STARTED.md).

## 4. Rodar a análise
No terminal aberto dentro da pasta do projeto:

```powershell
py tools/inspect_ps3_binary.py inspect "private/game/EBOOT.BIN" --output "out/eboot-report.json"
py tools/inspect_ps3_binary.py inventory "private/game" --output "out/inventory.json"
py -m unittest discover -s tests -v
```

Substitua `EBOOT.BIN` por `EBOOT.ELF` **somente se você realmente possui esse ELF**. Nunca renomeie um formato para o outro.

Abra `out/eboot-report.json`: ele deve informar `ELF`, `SELF/SCE` ou `unknown`. Para um ELF PPU candidato, veremos `class_bits=64`, `byte_order=big`, `machine=21`. Essa identificação ainda **não prova** que é Festival of Blood.

O inventário fornece caminhos relativos, tamanho e SHA-256 para comparar versões. **Revise qualquer relatório antes de compartilhá-lo**, pois nomes de arquivos podem ser sensíveis.

## 5. O que vem depois
Após identificarmos a edição alvo, prepararemos o SDK oficial do ps3recomp e compilação local. O ambiente completo requer Python, CMake, Ninja e compilador C++20; no Windows, o guia do ps3recomp recomenda clang-cl/Visual Studio 2022. Nada disso é exigido para o passo de inspeção acima.
