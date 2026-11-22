# Integração do runtime D3D12 e SPU

A série incorpora as PRs #10, #11 e #12 e a expansão do cache de fingerprints da #15. A numeração mantém 0012 e 0016 livres para os candidatos de composição, que dependem de validação em execução. O checkpoint `checkpoint/main-before-verified-8df5f4a` preserva a base anterior.

- 0013 mantém recursos D3D12 vivos até a conclusão confirmada da GPU. Falhas de fence são reportadas e interrompem o uso dos recursos.
- 0014 amplia os caches em memória e cede a execução fora do bloqueio de reserva do SPU.
- 0015 preserva o bytecode e as constantes de fragmentos no registro do desenho.
- 0017 amplia o cache SPU de 8 para 64 entradas e mantém o hash do conteúdo atual antes de aceitar um hit.

A validação cobre aplicação da série, compilação do runtime no Windows e testes sintéticos. A compilação e os testes do runtime não medem FPS, apresentação real ou equivalência audiovisual em jogo.

A PR #13 e as mudanças gráficas dependentes seguem em revisão. O cache persistente de shaders, o pumping de flip e a sincronização de jobs SPURS exigem validação própria. Os patches de alpha test e cadência da #15 ainda precisam de testes na cena afetada.
