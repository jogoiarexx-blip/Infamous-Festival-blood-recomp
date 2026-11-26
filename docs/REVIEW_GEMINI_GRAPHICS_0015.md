# Revisão de integração — patch Gemini 0015 (NPUA80657)

## Situação
Esta branch **arquiva a proposta original** em `review/`, fora do diretório
`patches/ps3recomp/`. **O patch não está ativado**, pois ainda tem problemas
técnicos que podem regredir vídeo, texturas ou execução da GPU. O CI desta
branch valida apenas o código já integrado e **não prova o patch 0015**.

O Gemini relatou correções de objetos transparentes, formatos RSX, composição
Bink e espera de flip. A imagem enviada `backbuffer_bottle_fixed.bmp`
mostra o bar e uma máquina de música, **não** mostra o personagem com o copo;
portanto não prova a correção desse objeto.

## Bloqueadores encontrados na auditoria estática

1. **Contagem do frame errado:** `composite_present()` verifica
   `s_dbg_last_offscreen_draws`, mas o novo valor é calculado mais tarde em
   `render_frame()`, após `composite_present(fi)`. A decisão utiliza o lote
   anterior, causando possível sobreposição indevida ou ausência de composição
   em mudanças entre cutscene Bink e cena 3D. Computar o estado do lote atual
   antes da composição e limpar a seleção de composição ao ignorá-la.
2. **Scratch único em múltiplas amostragens:** o mesmo
   `s_rt_feedback_copy` é reutilizado por todas as unidades de textura.
   Se uma draw amostrar dois MRTs ativos diferentes, a cópia do segundo alvo
   pode sobrescrever o primeiro antes da draw, deixando os dois SRVs apontando
   ao conteúdo do último alvo. Usar snapshots distintos por recurso/uso, com
   estados e descritores adequados.
3. **Formato e dimensões incompatíveis:** a recriação do scratch só verifica
   largura e altura, não `DXGI_FORMAT`, número de amostras e demais condições
   de `CopyResource`. Uma mudança de formato com mesmas dimensões pode
   gerar cópia inválida. Verificar criação, suporte SRV e resultados HRESULT.
4. **Tempo de vida perigoso:** o patch chama `Release()` no scratch anterior
   quando altera dimensões, possivelmente antes da conclusão dos comandos GPU
   que o referenciam. Integrar a aposentadoria por fence da PR #11.
   Tratar igualmente shutdown e falhas de criação.
5. **Whitelist não comprova decodificação:** aceitar mais valores RSX não
   garante que `rsx_texture_layout` implemente corretamente sua conversão;
   validar cada formato em testes de textura, descriptor e renderização.
6. **Dependência de outras branches:** o hunk de `composite_present()` utiliza
   o comportamento `GCM_COMPOSITE_RT` da PR #9 e deve ser testado com os
   patches de D3D12 das PRs #11 e #12. Há dois patches intitulados `0012`
   em branches diferentes; renumerar na integração para evitar sobrescritas.

## Antes de ativar o patch

- Preparar uma versão corrigida em branch separada, com testes CPU para
  estados D3D12, múltiplos RTs, incompatibilidade de formato e aposentadoria.
- Executar `git apply --check` no SDK fixado com a série de patches integrada.
- Compilar no Windows com as ferramentas existentes.
- Capturar a **mesma animação** do copo/garrafa antes e depois, exibindo mãos,
  objeto e manifesto das draws associadas.
- Testar transição Bink → 3D → UI e comparar os quadros realmente apresentados.
- Medir FPS apresentado, 1% low, draw calls, erros D3D12 e custo das novas
  cópias de textura; não equiparar ausência de warnings a correção total.

## Evitar duplicação

O arquivo `0014-snapshot-fragment-programs-at-draw-record.patch` enviado pelo
usuário possui o mesmo Git blob SHA-1 `38a43ceb4a7f2b8f15d76c03e43f2e1abcd48e4d`
da PR #12. Não o republicar em outra branch.

Nenhum EBOOT, asset original, dump privado ou screenshot com caminho pessoal
foi enviado nesta revisão.
