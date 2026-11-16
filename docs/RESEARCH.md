# Pesquisa técnica e decisões

**Atualizado:** 2026-11-16

## Fontes de referência (código público)
- [sp00nznet/ps3recomp](https://github.com/sp00nznet/ps3recomp), licença MIT. Guia: [GETTING_STARTED.md](https://github.com/sp00nznet/ps3recomp/blob/master/docs/GETTING_STARTED.md).
- [bhuiyah/infamous2-recomp](https://github.com/bhuiyah/infamous2-recomp). Referência arquitetural de pipeline específico para inFAMOUS 2; respeitar licença e atribuição antes de qualquer reaproveitamento.
- [erikomis/infamous2-recomp](https://github.com/erikomis/infamous2-recomp). Referência adicional, não presumir equivalência de binários.

## Confirmado
- **Festival of Blood / NPUA80657:** análise local de um EBOOT.BIN SELF/NPDRM com cabeçalho ELF64 PowerPC, sem decodificação dos segmentos. Ver [relatório da amostra](REPORT-NPUA80657.md).
- O ps3recomp dispõe de loader e lifter para PPU e de runtime com HLE para o ecossistema PlayStation 3.
- A recompilação PPU trabalha sobre **ELF**; um contêiner retail SELF não equivale a um ELF pronto.
- A implementação atual do repositório somente identifica cabeçalhos, calcula SHA-256 e gera inventário. Nenhum jogo foi testado.

## Hipóteses a verificar
- Festival of Blood pode compartilhar partes de tecnologia com inFAMOUS 2; **isso não confirma compatibilidade de código ou assets**.
- Versões/regiões de Festival of Blood podem alterar layout, endereços e importações; nenhuma está confirmada.
- O suporte do runtime aos módulos e interfaces que o jogo usa permanece desconhecido.

## Política
- Não adicionar EBOOT.BIN, EBOOT.ELF, DLL/PRX Sony, firmware, keys, discos, imagens, música, vozes, assets ou dumps ao repositório.
- Não incluir binários do jogo em issues, pull requests ou Actions/artifacts.
- Análise e builds somente com cópia legal no PC do usuário.
- Não copiar código de repositórios terceiros sem examinar licença e atribuir autores.
- Logs públicos devem ser revisados para não conter caminhos pessoais, segredos ou material do jogo.

## Checkpoints técnicos
1. Formato e identidade da edição alvo.
2. Compatibilidade loader e descoberta dos imports/OPD/TOC.
3. Primeira função PPU recompilada e testada localmente.
4. Bootstrap runtime com stubs.
5. Primeira cena real; depois gameplay.
