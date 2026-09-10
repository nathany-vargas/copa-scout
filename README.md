# Copa Scout

Análise tática das Copas do Mundo de 2018 e 2022 com Python, Elasticsearch e Elastic Agent Builder. A pergunta que guia o projeto é: **“o que teria acontecido se...?”**

O Copa Scout nasceu na **primeira participação da nossa equipe em uma hackathon**, em 29 de maio de 2026. Em cerca de **4 horas**, dividimos o trabalho entre o código do pipeline, o ambiente Elastic e uma interface para apresentar as análises. O resultado ficou abaixo do que esperávamos, mas a experiência trouxe muito aprendizado sobre dados, colaboração e desenvolvimento sob pressão de tempo.

No dia seguinte, decidi retomar o projeto sozinho e me dei **mais 4 horas**, simulando uma nova participação no mesmo desafio. Reaproveitei o trabalho da equipe e concentrei a revisão na integração com o Kibana. Este repositório preserva as duas etapas e registra aprendizados que eu levaria adiante, inclusive para minha atuação e para o resultado posterior no Desafio Quant AI 2026.

O deployment de demonstração era um trial e expirou. Ficaram o código, os dados processados e duas especificações Vega recuperadas. Não há demonstração online ativa nem um export completo do dashboard.

Quem tiver interesse em explorar a implementação pode configurar um novo ambiente no Elastic Cloud com Kibana e Agent Builder, inclusive usando um [trial, conforme as condições da Elastic](https://www.elastic.co/cloud/cloud-trial-overview). O caminho é preencher as URLs e a chave de API no `.env` da versão de revisão, executar o pipeline para carregar os dados e, por último, rodar `4_agent_setup.py` para cadastrar as ferramentas de consulta e configurar o agente `copa-scout`. O ambiente também precisa ter um modelo de linguagem disponível para o Agent Builder. As duas especificações Vega são carregadas separadamente no Kibana, conforme o [guia de execução](copa_scout_review/README.md) e o [guia do dashboard](copa_scout_review/dashboard/README.md).

Esses arquivos permitem reconstruir as duas visualizações personalizadas e investigar como os dados alimentam as análises. Para remontar o dashboard completo, os outros três painéis precisam ser criados manualmente a partir da configuração documentada. Não refiz o ambiente após o fim do trial, então esse processo pode exigir ajustes de compatibilidade; preservei o material para que a implementação possa ser estudada e reconstruída por quem tiver interesse.

## Duas versões, um aprendizado

| | Hackathon | Revisão solo |
|---|---|---|
| Pasta | [`copa_scout_original/`](copa_scout_original/) | [`copa_scout_review/`](copa_scout_review/) |
| Quando | 29 de maio de 2026 | Dia seguinte ao evento |
| Tempo de trabalho | Cerca de 4 horas em equipe | Mais 4 horas, sozinho |
| Foco | Scout de zebras com interface externa | Análise contrafactual dentro do Kibana |
| Arquitetura pretendida | Pipeline → Elastic → agent → Streamlit | Pipeline → Elastic → agent e dashboard no Kibana |
| Resultado | Dados integrados e UI básica; apresentação pouco alinhada ao uso esperado do Kibana | Agent, análise contrafactual e dashboard concentrados no Kibana |

### O dia da hackathon

Nossa primeira hackathon foi o **Hack Night Rio — Copa do Mundo Edition**, na ESPM Rio. O evento foi organizado pela Elastic Community Rio de Janeiro, com ACE Laboratory e ESPM Rio, e exigia o uso do Elastic Agent Builder e dos dados da StatsBomb. [Repositório do evento](https://github.com/salgado/hacknight-copa-2026).

A ideia inicial, **“Underdog Scout: o DNA da zebra na Copa 2026”**, nasceu de uma proposta da nossa colega de equipe **Nathany Vargas**. Ela trouxe o olhar para as “zebras” do futebol e a ideia de um Índice de Sobrevivência para investigar como seleções menos favoritas conseguem resistir a adversários mais fortes, tomando como referência as campanhas de Marrocos, Japão e Arábia Saudita na Copa de 2022.

O resultado da primeira versão foi um trabalho em equipe, com responsabilidades divididas:

- **Eu:** todo o código do dia — preparação dos eventos, cálculo das métricas, carga no Elasticsearch e os scripts que cadastram as tools e o agent pela API do Kibana.
- **João Gabriel de Oliveira:** o ambiente Elastic. Criou o deployment, gerou as credenciais que o código usava e ajustou, na interface do Agent Builder, como o agent utilizava esses dados. Esses ajustes não ficaram registrados no código.
- **Nathany Vargas e Alexandre Braga:** apresentação dos resultados por meio de uma interface de usuário em Streamlit.

O escopo cresceu de alguns casos de 2022 para todas as 128 partidas das Copas de 2018 e 2022. Era nossa primeira experiência tentando transformar uma ideia em uma entrega demonstrável em tão pouco tempo.

Ao final da hackathon, entendemos que a expectativa da avaliação era ver essa representação dos dados dentro do Kibana, explorando os recursos da plataforma. Havíamos dedicado parte importante do esforço a uma interface externa e, na nossa avaliação, essa escolha nos custou muitos pontos.

O tempo também limitou o acabamento: a UI ficou bastante básica. Ainda assim, na nossa opinião, ela apresentava os resultados de forma visualmente mais interessante do que conseguíamos obter com os recursos do Kibana que conhecíamos naquele momento. Essa preferência visual não compensou o desalinhamento com a entrega esperada. O primeiro resultado foi ruim, mas aprendemos muito sobre a importância de entender os critérios do desafio e orientar o trabalho da equipe por eles.

A pasta original preserva o código recuperado, com as credenciais substituídas por `chavinha_expirada`. Ela contém o pipeline Python e seus dados; **o frontend Streamlit não está entre os arquivos recuperados**. Ajustes feitos diretamente no Kibana também não estão todos representados no código.

Ficaram problemas conhecidos nessa versão: `config.py` é uma cópia de `4_agent_setup.py`, a configuração inicial de tools usa um objeto em vez da lista adotada no `fix_agent.py`, e as contagens incluem a disputa de pênaltis. Esses arquivos foram mantidos como registro do evento.

### O dia seguinte

No dia seguinte, decidi fazer uma nova tentativa por conta própria. Reservei mais 4 horas, como se estivesse novamente na hackathon, para testar o que conseguiria melhorar com o aprendizado do dia anterior. Usei um deployment próprio no Elastic Cloud Serverless e mantive o trabalho com dados como ponto de partida.

Meu foco passou a ser integrar toda a experiência ao Kibana: o agent, as consultas e a apresentação das análises. Considerei o resultado dessa segunda tentativa um avanço importante, tanto na entrega quanto no meu entendimento da plataforma. Eu ainda achava limitadas as opções de gráficos e dashboards que havia explorado, mas procurei trabalhar essa questão dentro do ambiente proposto pelo desafio.

As especificações **Vega e Vega-Lite foram criadas somente na revisão solo**. Eu não tinha experiência prévia com essas linguagens e usei o **Claude Opus disponível na época** como apoio para construir gráficos mais bonitos, legíveis e visualmente limpos. O uso de modelos de linguagem (LLMs) era incentivado no evento, considerando o tempo curto de desenvolvimento. Na revisão, esse apoio me permitiu experimentar uma tecnologia com a qual eu ainda não tinha tido contato.

As decisões foram buscar situações parecidas na base, medir o que aconteceu depois delas e apresentar os números como **frequências condicionais**, com linguagem cautelosa. Mantive somente partidas de seleções das duas Copas, sem misturar competições de clubes, e reaproveitei o pipeline para acrescentar a análise contrafactual e o dashboard.

## O que está preservado

```text
Copa Scout/
├── README.md
├── copa_scout_original/
│   ├── 1_extract.py ... 6_advanced_analysis.py
│   ├── config.py
│   ├── fix_agent.py
│   ├── cache/
│   └── *.csv
└── copa_scout_review/
    ├── README.md
    ├── config.py
    ├── .env.example
    ├── requirements.txt
    ├── 1_extract.py ... 7_contrafactual.py
    ├── *.csv
    ├── tests/
    └── dashboard/
        ├── README.md
        └── vega/
            ├── scatter_xg.json
            └── heatmap_zonas_perda.json
```

A versão original serve como registro do trabalho no evento. A pasta da revisão inclui correções posteriores feitas ao organizar este repositório; seus CSVs refletem essas correções, não um retrato exato dos índices do trial.

## Como a revisão funciona

```text
StatsBomb → cache local → métricas e CSVs → Elasticsearch
                                              ├── Agent Builder: perguntas e tools ES|QL
                                              └── Kibana: dashboard Lens + Vega
```

### Análise contrafactual

Este foi nosso primeiro contato, ainda básico e exploratório, com perguntas contrafactuais: tentar compreender o que poderia ter acontecido se um evento tivesse sido diferente. Na revisão solo, dei mais espaço a essa ideia. A implementação usa frequências observadas em situações semelhantes como referência para discutir possibilidades; não estima, por si só, o efeito causal de mudar uma jogada.

O [`7_contrafactual.py`](copa_scout_review/7_contrafactual.py) registra perdas (`Dispossessed`, `Miscontrol`, `Error`) e recuperações (`Ball Recovery`, `Interception`). Cada evento recebe uma zona pela coordenada x da StatsBomb:

| Zona | Coordenada x |
|---|---|
| `own_third` | x < 40 |
| `mid_third` | 40 ≤ x < 80 |
| `final_third` | x ≥ 80 |

O script observa os eventos posteriores nos **30 segundos seguintes, dentro do mesmo período**. Para uma perda, procura finalizações do adversário; para uma recuperação, finalizações do próprio time. Registra `goal`, `shot` ou `nothing` e o xG gerado.

Depois agrupa por zona, tipo de evento e perspectiva. Cada registro recebe o tamanho do grupo e as frequências de chute, gol e ausência de chute. `pct_resulted_shot` inclui os chutes que terminaram em gol; não deve ser somado a `pct_resulted_goal` como se fossem resultados exclusivos.

A resposta pretendida é: “Em X situações similares nas Copas 2018/2022, Y% resultaram em chute e Z% em gol.” Isso descreve o histórico de situações agrupadas; não calcula o resultado de uma partida alternativa.

### Índice de Sobrevivência

É uma métrica exploratória com pesos definidos à mão:

| Componente | Peso |
|---|---:|
| Bloqueios | +2,5 |
| Interceptações e desarmes | +2,0 cada |
| Recuperações de bola | +1,5 |
| Pressões e cortes | +1,0 cada |
| Chutes no gol sofridos | −3 |
| Gols sofridos | −10 |

O valor bruto é ajustado por `IS × 90 / minutos_jogados`. Uma normalização min-max coloca os 256 registros de time por partida na escala de 0 a 100. Na base atual, o mínimo é a Suíça contra Portugal em 2022.

| Faixa final | Classificação |
|---|---|
| IS > 85 | Fortaleza Impenetrável |
| 65 < IS ≤ 85 | Muro Sólido |
| 40 < IS ≤ 65 | Resistência Competitiva |
| 20 < IS ≤ 40 | Sobrevivência Precária |
| IS ≤ 20 | Defesa Colapsada |

Os campos `is_top_strength`, `is_second_strength`, `is_top_weakness` e `is_second_weakness` mostram as maiores contribuições positivas e negativas do cálculo bruto. São parcelas em pontos, não percentuais da escala final.

### Dados disponíveis

As contagens abaixo são dos CSVs locais corrigidos. Os scripts usam os mesmos nomes para os índices no Elasticsearch.

| Arquivo / índice | Um registro representa | Registros | Script |
|---|---|---:|---|
| `match_stats` | Um time em uma partida | 256 | 2 e 3 |
| `team_profiles` | Uma seleção em um torneio | 64 | 2 e 3 |
| `goal_chains` | Um chute convertido em gol e sua cadeia de eventos | 326 | 5 |
| `turnovers` | Uma perda de bola e o perigo nos 15 eventos seguintes do período | 5.975 | 6 |
| `player_impact` | Um jogador em uma partida, após o filtro mínimo de atividade | 3.670 | 6 |
| `match_momentum` | Um time em um intervalo de até 15 minutos | 1.832 | 6 |
| `counterfactual_events` | Uma perda ou recuperação e seus desdobramentos em 30 segundos | 20.121 | 7 |

### Agent e dashboard

Usamos o **Elastic Agent Builder para configurar um agente personalizado**, o `copa-scout`. A plataforma fornece a infraestrutura de conversação e de execução das ferramentas. Nossa implementação prepara os dados e define as instruções do agente, as consultas disponíveis e os parâmetros que ele pode preencher para buscar informações no Elasticsearch. Não houve treinamento de um modelo próprio.

Na versão de revisão, o [`4_agent_setup.py`](copa_scout_review/4_agent_setup.py) registra, pela API do Kibana, **10 ferramentas de consulta ES|QL** e cria ou atualiza o agente, associando essas ferramentas às suas instruções. Por exemplo, uma pergunta sobre o Brasil pode acionar uma consulta com `team = Brazil`; os resultados retornados servem de contexto para a resposta. Esse é o papel das tools descritas abaixo:

| Tool | Uso |
|---|---|
| `counterfactual` | Frequências históricas por zona e tipo de evento |
| `goal-chain-analysis` | Sequência de eventos associada aos gols sofridos |
| `turnover-analysis` | Perdas de bola e nível de perigo |
| `player-impact` | Impacto de jogadores por partida |
| `match-momentum` | Evolução das métricas ao longo do jogo |
| `team-match-stats` | Métricas da seleção em cada partida |
| `match-comparison` | Comparação dos dois times de uma partida |
| `team-profile` | Perfil agregado por seleção e torneio |
| `ranking-defensivo` | Ranking do Índice de Sobrevivência médio |
| `confronto-direto` | Partidas entre duas seleções |

O prompt orienta o agent a consultar as tools, responder em português e usar linguagem cautelosa. As queries completas estão no código.

O dashboard reunia ranking defensivo, comparativo entre times, diagnóstico em tabela, dispersão de xG e mapa de eventos no campo. Agent e dashboard eram usados em abas separadas; este código não implementa controle do dashboard pelo agent.

As duas specs recuperadas e as instruções para reconstruir as visualizações estão no [guia do dashboard](copa_scout_review/dashboard/README.md). As visualizações Lens não foram exportadas, e não há screenshots do deployment original.

## Executar ou explorar

Para conhecer o projeto, é possível ler os CSVs, o código e as specs sem uma conta Elastic. Para executar a integração, é necessário um novo deployment com Agent Builder e credenciais próprias.

O [guia da revisão](copa_scout_review/README.md) contém instalação, configuração por `.env`, ordem dos scripts e testes locais. O `.env.example` tem apenas `chavinha_expirada`; não contém acesso a nenhum ambiente.

## Correções ao organizar o repositório

Alguns problemas só ficaram claros ao revisar os resultados. Os ajustes abaixo estão na versão de revisão, preservando o código original do evento:

- O filtro da disputa de pênaltis era sobrescrito em `count_threat()`. A correção também exclui essas cobranças das análises de gols, jogadores e momentum e do cálculo de duração. Brasil × Croácia de 2022 passa a ter 1 gol de cada time nas métricas.
- As perdas de bola passam a olhar os eventos em ordem cronológica e dentro do mesmo período. A análise contrafactual respeita essa sequência, inclusive para eventos no mesmo segundo.
- O momentum inclui eventos no minuto que coincide com o limite final do último intervalo.
- A narrativa textual de cada partida usa o mesmo índice e a mesma classificação final das colunas numéricas.
- Credenciais antigas foram substituídas por marcadores. A revisão usa variáveis de ambiente, com suporte a `.env`.

Os testes locais cobrem esses cálculos; não substituem a validação da integração em um novo Kibana. A spec do heatmap recebeu duas correções de renderização; essas correções e as limitações restantes estão descritas no guia do dashboard.

## Limitações

- Frequência condicional não demonstra causalidade. A definição de “similar” não considera placar, minuto, pressão ou qualidade dos jogadores.
- A janela contrafactual não verifica mudanças de posse entre o evento e a finalização. Alguns grupos têm poucos exemplos.
- Gols e cadeias são derivados de eventos `Shot` com resultado `Goal`; gols contra não entram nessas contagens. O placar dos metadados pode diferir da métrica de gols por finalização.
- Os pesos do Índice de Sobrevivência são arbitrários. A escala depende desta base, e o tempo jogado usa o maior minuto observado nos eventos, incluindo acréscimos.
- Posse de bola é uma aproximação pela proporção de passes. O ranking de impacto retorna registros por partida, não uma soma de toda a competição por jogador.
- `team_profiles` não contém `match_id`; seu ranking de torneio não deve ser interpretado como análise de uma partida selecionada.
- O heatmap recuperado mistura perdas e recuperações e busca até 5.000 documentos. A dispersão fixa a Copa 2022 e não incorpora o contexto dos controles do dashboard.
- Não há ambiente ativo para validar novamente as APIs, a importação das specs ou o comportamento dos controles.

## O que aprendi e levei adiante

Foi a primeira hackathon de todos nós. Apesar do resultado inicial abaixo do esperado, aprendemos muito ao dividir responsabilidades, integrar as partes do projeto e tentar apresentar uma solução em poucas horas. Para mim, a revisão do dia seguinte foi uma forma de transformar essa experiência em prática imediatamente: ajustar o foco, explorar melhor o Kibana e conferir com mais cuidado o que os dados realmente sustentavam.

O trabalho com eventos de partidas também me ajudou a desenvolver mais atenção à qualidade dos dados e à ordem temporal das informações. A contagem dos pênaltis, a sequência das jogadas e a diferença entre uma métrica calculada e sua interpretação mostraram como detalhes do tratamento podem mudar uma conclusão. Esse primeiro contato com perguntas contrafactuais foi simples, mas me ajudou a formular perguntas melhores e a separar o que observei nos dados daquilo que só posso apresentar como hipótese.

**Eu levei esses aprendizados para os projetos seguintes, inclusive para minha atuação no Desafio Quant AI 2026.** O resultado que obtivemos lá também foi fruto do que aprendi nesta primeira hackathon. Essa experiência contribuiu para a forma como passei a tratar dados, validar análises e lidar com o risco de *look-ahead bias*: usar, em uma análise ou decisão situada em determinado instante, informações que só estariam disponíveis no futuro.

No Copa Scout, observar os 30 segundos posteriores a uma perda de bola serve para registrar seu desfecho histórico. O cuidado, ao construir uma análise preditiva, é não usar esse desfecho como informação de entrada para uma decisão que deveria ocorrer no instante da perda. Essa distinção entre o que era conhecido naquele momento e o que aconteceu depois foi um aprendizado que levei comigo; este projeto permanece uma exploração retrospectiva, sem um protocolo de validação preditiva temporal.

A experiência também me ensinou a alinhar a apresentação aos critérios do desafio, conferir respostas de um agent contra os dados e reservar tempo para preservar a entrega. Manter credenciais fora do código e exportar os saved objects do Kibana antes do fim do trial passaram a fazer parte dessa preocupação.

## Créditos

- Dados: [StatsBomb Open Data](https://github.com/statsbomb/open-data).
- Evento: [Hack Night Rio — Copa do Mundo Edition](https://github.com/salgado/hacknight-copa-2026).
- Equipe da primeira hackathon: eu, no código do pipeline e da integração; João Gabriel, no ambiente Elastic e nos ajustes do agent no Agent Builder; Nathany e Alexandre, na interface de apresentação.
- Revisão no dia seguinte: trabalho individual, desenvolvido a partir da primeira versão da equipe.
- Apoio de LLMs: usei o Claude (Anthropic) no desenvolvimento e na revisão de código. As especificações Vega e Vega-Lite da revisão solo foram feitas com apoio do Claude Opus disponível na época, durante meu primeiro contato com essas linguagens.
