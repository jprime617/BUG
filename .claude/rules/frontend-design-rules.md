# DIRETRIZES: DESIGN ORGÂNICO E ANTI-IA LOOK (HUMAN-CENTRIC UX/UI)

## Antes de codificar
- Para qualquer tela, componente visual ou artifact novo (ou redesign), invoque a skill `frontend-design` antes de escrever código. Ela força um processo de brainstorm → plano → autocrítica → build → autocrítica, em vez de ir direto para HTML/CSS genérico.
- Sem a skill disponível, siga pelo menos o processo abaixo manualmente.

## Os 3 clichês de "cara de IA" (evite como padrão)
1. Fundo creme quente (~`#F4F1EA`) + serifada de alto contraste + accent terracota.
2. Fundo quase preto + um único accent neon (verde ácido/vermelhão).
3. Layout "broadsheet": hairlines, zero border-radius, colunas densas tipo jornal.
- **Atenção**: a diretriz antiga deste arquivo ("fundo off-white quente") caía direto no clichê nº 1. Paleta off-white/slate continua uma opção legítima, mas só quando for uma escolha deliberada derivada do briefing — nunca o default automático.

## Processo (plano antes do código)
- Monte um sistema de tokens compacto e específico do briefing, não genérico:
  - **Cor**: 4–6 hex nomeados (não "paleta muta" vaga).
  - **Tipografia**: 2+ papéis — display com caráter (usada com moderação), texto complementar, e uma face utilitária para dados/legendas se necessário. Evite a combinação óbvia que qualquer projeto similar usaria.
  - **Layout**: conceito em uma frase + wireframe ASCII para comparar opções.
  - **Assinatura**: o elemento único pelo qual essa tela será lembrada.
- Releia o plano contra o briefing: se qualquer parte parece a resposta padrão que você daria para qualquer briefing parecido, revise antes de construir.

## Estrutura e conteúdo
- Estrutura é informação: numeração, eyebrows, divisores e labels devem codificar algo real do conteúdo (ex: uma sequência de fato). Marcadores numerados (01/02/03) só fazem sentido se a ordem importa — questione antes de usar por padrão.
- Movimento é deliberado: prefira um momento orquestrado (page-load, scroll-reveal) a microinterações espalhadas. Excesso de animação é um dos sinais mais fortes de "gerado por IA".
- Gaste ousadia em um único lugar: deixe o elemento-assinatura ser o ponto memorável; mantenha o resto disciplinado e corte decoração que não serve ao briefing.

## Piso de qualidade (não negociável)
- Responsivo até mobile.
- Foco de teclado visível (focus ring de alto contraste).
- Respeita `prefers-reduced-motion`.
- Contraste WCAG AA (mínimo 4.5:1 em texto).
- Espaçamento em grade de 8pt (4/8/16/24/32/48/64) — sem valores arbitrários.
- Cuidado com especificidade de seletores CSS (ex: `.section` genérico vs `.cta` específico cancelando padding/margin um do outro).

## Estados obrigatórios (todo componente interativo)
1. Default
2. Hover / Active (feedback tátil, ex.: leve `scale`)
3. Focus-visible (foco de teclado nítido)
4. Disabled (opacidade reduzida, cursor bloqueado)
5. Loading (skeleton/spinner sem layout shift)
6. Empty / Error (fallback acionável, não pedido de desculpas)

## Micro-interações (craft)
- Duração 150–200ms; easing `ease-out` ou `cubic-bezier(0.16, 1, 0.3, 1)`.
- Anime propriedades específicas (`transform`, `opacity`, `color`), nunca `all`.
- Prefira bordas nítidas e semitransparentes a sombras difusas pesadas.
- **Reconciliação**: isto é piso de ofício, não um look pronto. Paleta, tipografia e o elemento-assinatura continuam derivados do briefing (seção Processo) — não caia nos defaults genéricos (zinc/slate + accent único, gradiente roxo/índigo) por automatismo.

## Copy / texto de interface
- Nomeie pelo que a pessoa controla e reconhece, nunca por como o sistema é construído (ex: "notificações", não "webhook config").
- Voz ativa: um botão nomeia exatamente a ação ("Salvar alterações", não "Enviar"); mantenha o mesmo verbo do início ao fim do fluxo (o botão "Publicar" gera um toast "Publicado").
- Erros são específicos sobre o que aconteceu e como resolver, na voz da interface — nunca vagos, nunca se desculpam.
- Estados vazios são um convite a agir, não um pedido de desculpas.
