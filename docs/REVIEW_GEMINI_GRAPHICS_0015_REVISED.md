# Revisão de integração — versão revisada do patch 0015 (20/11/2026)

## Estado
O patch 0015 enviado pelo Gemini foi **atualizado e preservado**, em
`review/0015-fix-texture-formats-self-sampling-and-conditional-composite.patch`.
**Não foi ativado** em `patches/ps3recomp/` e esta PR deve continuar em rascunho.
Seu relatório foi arquivado em `review/GEMINI_RELATORIO_CORRECAO_0015.md`,
identificado como relato de testes locais ainda não reproduzidos pela integração.

O usuário informou um **crash novo na cinemática após a fogueira e jukebox**,
um trecho que antes chegava ao gameplay. Isso torna indispensável repetir a
mesma transição antes de qualquer merge. O relatório do Gemini registra uma
execução de 65 segundos sem erros D3D12, mas **não apresenta nesta PR** uma
reprodução independente de passagem pelo ponto do crash.

## Avanços verificáveis no código enviado

- A contagem `s_dbg_last_offscreen_draws` foi movida para o início de
  `render_frame()` e `composite_present()` limpa `s_composite_src` ao pular
  composição.
- Foi implementada a estrutura de quatro scratches
  `s_feedback_scratch[4]`, por papel de render target/MRT, em lugar de um
  único scratch global.
- Agora o código compara largura, altura e `DXGI_FORMAT` ao reutilizar
  recursos temporários, e verifica `HRESULT` da criação.
- Recursos supersedidos usam `defer_release()` da PR #11.
- A whitelist RSX foi ampliada e a espera em `cellGcmSetWaitFlip()` foi
  modificada. A correção visual e o impacto em FPS dependem de testes reais.

## Bloqueadores ainda existentes na integração pública

1. **Contexto do patch incompatível:** no hunk que começa próximo da linha
   `5676`, o patch tenta substituir `int rt = dr->tex[_u];`. O SDK
   público fixado (`sp00nznet/ps3recomp`, `de4f090`) já contém
   `int rt = dr->tex_rt[_u];`. O hunk não pode ser aplicado desse modo.
   Regerar o patch contra a base fixa após a série pública realmente aplicada,
   sem alterações de contexto que não existam na base.
2. **Dependência não integrada:** `defer_release()` é introduzida na
   PR #11 e ainda não existe na `main`. Como o CI aplica
   `patches/ps3recomp/*.patch` em ordem, ativar o 0015 antes de integrar/
   consolidar a dependência da PR #11 quebrará a compilação. Há ainda dois
   patches de prefixo `0012` (#9 e #11); renumerar e validar aplicação
   conjunta, em vez de presumir compatibilidade.
3. **Contagem por lote versus frame:** a contagem antecipada percorre
   `s_d3d.draw_count` do lote atual. O renderizador pode descarregar um lote
   3D durante clears e terminar um frame com lote vazio/2D. Nessa situação,
   uma simples contagem do lote atual pode não refletir todos os draws 3D
   feitos desde o último flip. Instrumentar e testar transições Bink/3D/UI.
4. **Custo de feedback:** `src_rt = -1` é reiniciado para todos os quatro
   scratches a cada draw, fazendo até quatro `CopyResource` por draw que
   amostra RTs ativos. Medir bytes copiados, draw count, ms/quadros e efeito
   no FPS efetivamente apresentado; considerar otimização sem mudar a
   semântica da amostragem.
5. **Formato e amostragem:** o scratch define `SampleDesc.Count = 1`, mas
   não verifica que a origem também tem a mesma descrição de subrecursos.
   Validar `GetDesc` ou as premissas reais do RT; dimension/format sozinhos
   não provam compatibilidade de `CopyResource`.
6. **Evidência visual incompleta:** o arquivo anterior
   `backbuffer_bottle_fixed.bmp` não mostrava Zeke segurando o objeto.
   O relatório novo cita `backbuffer_bottle_multiscratch.bmp`, mas esse
   arquivo não foi entregue nesta revisão. Capturar **mãos, personagem e
   copo/garrafa no mesmo frame**, com draws correspondentes.

## Critérios de aceite

- Corrigir o hunk e passar `git apply --check`/aplicação sobre o SDK
  fixado com a cadeia de patches na mesma ordem do CI.
- Compilar no Windows e executar testes automáticos e regressões D3D12.
- Confirmar passagem **completa pela fogueira e jukebox até gameplay**
  pelo menos três vezes, comparando baseline anterior com versão integrada.
- Confirmar imagem correta de garrafa/copo e preservação das cutscenes Bink.
- Registrar FPS real apresentado e quedas, sem confundir tempo do D3D12 com
  FPS da execução total.
- Não mesclar enquanto a regressão do usuário estiver sem diagnóstico.

**Não enviar assets privados, EBOOT, dumps, saves ou recursos do jogo ao GitHub.**
