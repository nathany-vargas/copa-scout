# Dashboard — Copa Scout

O dashboard **“Copa Scout — Análise Tática”** foi montado no Kibana durante a revisão solo, com cinco visualizações e controles de `match_id` e `team`.

As especificações Vega e Vega-Lite pertencem apenas a essa segunda etapa. Na hackathon, Nathany e Alexandre ficaram responsáveis pela UI externa da equipe. Ao retomar o projeto sozinho no dia seguinte, concentrei a apresentação no Kibana e busquei gráficos mais legíveis e visualmente limpos dentro da plataforma. Como era meu primeiro contato com Vega, usei o Claude Opus disponível na época como apoio na construção das specs. O uso de LLMs era incentivado no evento em razão do tempo curto de desenvolvimento.

O trial expirou. As três visualizações Lens não foram exportadas em NDJSON; sua configuração foi recuperada a partir dos relatos do desenvolvimento. O `scatter_xg.json` foi preservado sem alterações. No `heatmap_zonas_perda.json` corrigi dois defeitos de renderização, descritos adiante; o restante da spec é o que foi recuperado. Este material permite uma reconstrução manual, mas não é um export completo do dashboard nem uma reprodução validada em um novo deployment.

## Arquivos recuperados

| Visualização | Tipo | Arquivo |
|---|---|---|
| Mapa de eficiência: xG criado × xG sofrido | Vega-Lite v5 | [`vega/scatter_xg.json`](vega/scatter_xg.json) |
| Zonas de perda de bola | Vega v5 | [`vega/heatmap_zonas_perda.json`](vega/heatmap_zonas_perda.json) |

As URLs dos schemas são referências públicas das linguagens Vega. As fontes de dados usam nomes de índices, sem endpoints ou credenciais do antigo deployment.

## Índices e controles

| Índice | Registros no CSV atual | Painéis |
|---|---:|---|
| `match_stats` | 256 | Comparativo, diagnóstico, dispersão |
| `team_profiles` | 64 | Ranking defensivo |
| `counterfactual_events` | 20.121 | Mapa de eventos |

Os controles recuperados eram do tipo **Options list**: `match_id` com seleção única e `team` com seleção múltipla. Para reconstruir as visualizações Lens, use data views correspondentes aos índices, com campos agregáveis.

O comparativo precisa permitir os dois times da partida. Evite fixar um `match_id` dentro desse painel se pretende selecionar o jogo pelo controle.

- `team_profiles` não possui `match_id`. Seu ranking é de seleção por torneio; confira o alcance dos controles para que o filtro de partida não seja aplicado a esse painel.
- O heatmap usa `%context%` e recebe os filtros do dashboard. A dispersão tem uma query própria, sem marcadores de contexto, e não incorpora esses controles.

## 1. Ranking do Índice de Sobrevivência

- Tipo: Lens, barras.
- Índice: `team_profiles`.
- Eixo: `team`.
- Métrica: **Average de `avg_survival_index`**.
- Ordenação: decrescente pela métrica.
- Recorte: selecione um torneio, por exemplo `FIFA World Cup 2022`, para não misturar os dois perfis de uma seleção.

O texto recuperado indicava `survival_index_norm`, mas esse campo pertence a `match_stats`. Em `team_profiles`, o campo disponível é `avg_survival_index`; essa configuração foi corrigida na documentação.

## 2. Comparativo entre dois times

- Tipo: Lens, barras.
- Índice: `match_stats`.
- Eixo: `team`.
- Métricas: Sum de `pressures`, `interceptions`, `blocks`, `tackles` e `shots_for`.

Com uma partida selecionada, cada time tem um registro. Sem esse filtro, as métricas somam várias partidas e o gráfico muda de significado. Na experiência original, um filtro fixo de Brasil × Croácia no painel precisou ser retirado para permitir trocar o jogo pelo dashboard.

## 3. Diagnóstico defensivo — Copa 2022

- Tipo: Lens, tabela.
- Índice: `match_stats`.
- Filtro: `tournament: "FIFA World Cup 2022"`.
- Agrupamentos: `team`, `opponent`, `is_top_strength` e `is_top_weakness`, usando seus campos agregáveis.
- Métrica: Average de `survival_index_norm`.

No roteiro recuperado, os campos de texto eram colocados em **Rows**, com limite de 50 valores, e o índice numérico em **Metrics**. Os rótulos e opções da interface podem variar na instalação utilizada para reconstruir o painel. Nos campos de diagnóstico, verifique no data view se a variante agregável é o subcampo `.keyword`.

Cada linha pretende representar um time em uma partida. Para uma visualização geral da base, acrescente `match_id` ao agrupamento e confira os limites de valores, evitando juntar confrontos repetidos ou omitir linhas.

O índice final vai de 0 a 100. Já os textos de força e fraqueza, como “Pressões (+161pts)”, mostram contribuições ao cálculo bruto; não são parcelas percentuais do índice normalizado.

## 4. Mapa de eficiência: xG criado × xG sofrido

Cole [`scatter_xg.json`](vega/scatter_xg.json) no editor de uma visualização Vega do Kibana.

A spec usa Vega-Lite, consulta `match_stats` e fixa `tournament` em `FIFA World Cup 2022`. Solicita até 300 documentos, suficientes para os 128 registros de time por partida desse torneio na base atual.

- X: `xg_for`; Y: `xg_against`.
- Domínio dos dois eixos: 0 a 6.
- Cor: seleção, sem legenda.
- Tooltip: seleção, adversário, fase e os dois valores de xG.

Cada ponto é um time em uma partida. Mais à direita indica mais xG criado; mais acima indica mais xG sofrido. A legenda foi retirada na versão recuperada, mantendo o nome da seleção no tooltip.

Esse painel não incorpora filtros do dashboard porque a spec não declara `%context%` nem os placeholders de contexto. Se a base crescer ou os valores excederem os domínios fixos, será preciso rever esses limites.

## 5. Zonas de perda de bola

Cole [`heatmap_zonas_perda.json`](vega/heatmap_zonas_perda.json) no editor de outra visualização Vega.

A spec desenha um campo vertical de 400 × 600 px, com fundo verde `#1a472a`, e agrega eventos em células de 10 × 10 unidades StatsBomb. A cor representa a contagem de eventos da célula. O tooltip mostra a posição da célula e sua contagem.

As coordenadas originais vão de 0 a 120 em x e de 0 a 80 em y. A transformação usada é:

```text
px = event_y
py = 120 - event_x
```

Depois, a grade é calculada com `floor(coordenada / 10) * 10`, com as células de borda limitadas por `min`. O campo nominal comporta 8 × 12 células e `py = 0` fica no topo, de modo que o ataque aponta para cima. Não trate esse mapa como coordenadas geográficas.

### Histórico recuperado

As tentativas relatadas passaram por pontos com densidade `kde2d`, pontos coloridos pelo resultado e, por fim, a grade de retângulos deste arquivo. A transformação de densidade não funcionou no ambiente utilizado; a grade foi a solução adotada durante a revisão.

### Correções aplicadas

Dois defeitos de renderização foram corrigidos; o restante da spec está como foi recuperado.

- **Deslocamento da grade.** A escala `y` usava `"range": "height"`, que em Vega equivale a `[height, 0]` e é invertida. Como cada retângulo ancora em `scale(gy)` e cresce `height / 12` para baixo, toda célula era desenhada uma fileira abaixo do lugar: a faixa `gy = 0` caía fora do campo e o topo ficava sempre vazio. A escala passou a ser `[0, {"signal": "height"}]`, o que alinha as células e coloca `py = 0` no topo, como a transformação `120 - event_x` pressupõe. O campo desenhado é simétrico nas duas metades, então esse erro não era perceptível a olho nu.
- **Células de borda.** `gx` e `gy` agora passam por `min(..., 70)` e `min(..., 110)`. Sem esse limite, uma coordenada na borda máxima gerava uma célula fora da grade nominal: na base atual são 18 dos 20.121 eventos, todos com `event_y = 80`.

### Limitações da spec

- **Mistura perdas e recuperações.** Apesar do título, a query não filtra `perspective`. Um filtro de `team = Brazil` inclui tanto perdas quanto recuperações do Brasil.
- **Busca até 5.000 documentos.** Sem um recorte suficiente, o mapa mostra somente parte dos 20.121 eventos. Essa seleção não deve ser interpretada como amostra aleatória.
- **Atualização das marcas.** Os retângulos definem posição e cor em `enter`; o comportamento ao trocar filtros precisa ser conferido numa reconstrução com dados dinâmicos.

Para visualizar somente perdas sem editar a spec, inclua um filtro de dashboard ou de painel `perspective: "loss"` com o alcance adequado ao heatmap. Esse campo não existe em todos os índices dos outros painéis.

Se preferir alterar a query da spec, a integração Query DSL do Kibana não permite combinar `%context%: true` com uma query própria em `body`. A alternativa documentada é usar os placeholders `%dashboard_context-must_clause%`, `%dashboard_context-filter_clause%` e `%dashboard_context-must_not_clause%` na query. [Referência oficial de Vega no Kibana](https://www.elastic.co/docs/explore-analyze/visualize/custom-visualizations-with-vega#writing-elasticsearch-queries-in-vega).

Para representar a base completa sem truncar os hits, uma evolução possível é agregar as células no Elasticsearch. Essa mudança não foi aplicada. Nem ela nem as duas correções acima foram validadas em um novo Kibana; a geometria das células foi conferida apenas por cálculo.

## Reconstrução manual

1. Configure um novo ambiente e execute o pipeline conforme o [guia da revisão](../README.md).
2. Crie os data views e as três visualizações Lens descritas acima.
3. Crie duas visualizações Vega e cole o conteúdo dos JSONs recuperados.
4. Reúna os cinco painéis em um dashboard e configure os controles respeitando o escopo de cada índice.
5. Confira Brasil × Croácia de 2022 (`match_id = 3869420`): os dados corrigidos de `match_stats` têm um gol para cada seleção, sem a disputa de pênaltis.
6. Confira filtros, limites de documentos e campos agregáveis no novo ambiente; depois exporte os saved objects em NDJSON.

O código do projeto configura tools ES|QL para o agent. Não há integração implementada para que ele altere os filtros desse dashboard. A demonstração original usava agent e dashboard em abas separadas.
