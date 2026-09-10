# Copa Scout — versão da revisão

Pipeline de análise tática das Copas de 2018 e 2022, com Elasticsearch e Agent Builder. A história das duas etapas está no [README principal](../README.md); o [guia do dashboard](dashboard/README.md) reúne as visualizações recuperadas.

O trial original expirou. As credenciais foram removidas e os CSVs locais foram recalculados após as correções descritas no README principal.

## Instalação

Os cálculos locais foram validados com Python 3.12. Execute os comandos abaixo a partir desta pasta.

No PowerShell, começando pela raiz do projeto:

```powershell
cd copa_scout_review
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

No macOS ou Linux:

```bash
cd copa_scout_review
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

O `requirements.txt` declara as dependências sem fixar versões. A instalação em outro ambiente pode exigir ajustes de compatibilidade. `pyarrow` permite ler os caches recuperados que utilizam tipos Arrow do pandas.

## Configuração

Preencha no `.env` as variáveis `ES_URL`, `KIBANA_URL` e `API_KEY` de um novo deployment. Use os endpoints fornecidos pelo seu ambiente; os marcadores `chavinha_expirada` não são URLs ou chaves válidas.

O [`config.py`](config.py) carrega o `.env` desta pasta. Variáveis já definidas no ambiente têm precedência. O `.env` e o `.venv` estão no `.gitignore`; o `.env.example` deve permanecer sem credenciais reais.

Um `.venv` isola dependências, não protege segredos escritos em arquivos. Para acessar o agent, o novo ambiente precisa disponibilizar as APIs do Agent Builder.

## Ordem de execução

Os caminhos dos caches e CSVs são relativos à pasta de execução. No PowerShell, ainda dentro de `copa_scout_review/`:

```powershell
.\.venv\Scripts\python.exe 1_extract.py
.\.venv\Scripts\python.exe 2_transform.py
.\.venv\Scripts\python.exe 3_load.py
.\.venv\Scripts\python.exe 5_goal_chains.py
.\.venv\Scripts\python.exe 6_advanced_analysis.py
.\.venv\Scripts\python.exe 7_contrafactual.py
.\.venv\Scripts\python.exe 4_agent_setup.py
```

No macOS/Linux, use `.venv/bin/python` no lugar de `.\.venv\Scripts\python.exe`.

| Etapa | Saída / efeito |
|---|---|
| 1 | Baixa eventos e guarda `cache/*.pkl`; reaproveita arquivos já existentes |
| 2 | Gera `match_stats.csv` e `team_profiles.csv` |
| 3 | Recria e preenche os índices `match_stats` e `team_profiles` |
| 5 | Gera `goal_chains.csv` e recria seu índice |
| 6 | Gera `turnovers.csv`, `player_impact.csv` e `match_momentum.csv` e recria seus índices |
| 7 | Gera `counterfactual_events.csv` e recria seu índice |
| 4 | Cria as tools e cria ou atualiza o agent `copa-scout` |

O script 4 roda por último porque suas tools consultam os índices anteriores. Os scripts 3, 5, 6 e 7 **apagam e recriam os índices de mesmo nome** no ambiente configurado. O script 4 tenta criar as tools; a atualização do agent existente não atualiza automaticamente as queries das tools já cadastradas.

O dashboard não é criado por esses scripts. Siga o [guia de reconstrução](dashboard/README.md).

## Configuração do agente

Carregar os dados e montar os gráficos não cadastra o agente. Depois de criar os índices, execute `4_agent_setup.py`, como indicado na sequência acima. Ele envia à API do Kibana as definições das 10 tools ES|QL, suas descrições e parâmetros, além das instruções do agente `copa-scout` e da lista de ferramentas que ele pode utilizar.

O projeto configura um agente personalizado sobre o Elastic Agent Builder: prepara os dados e fornece instruções e ferramentas de consulta para que o agente busque informações e componha suas respostas. Não treina nem hospeda um modelo de linguagem próprio.

O novo ambiente precisa oferecer um modelo de linguagem ao Agent Builder. Conforme a configuração disponível, pode ser um modelo gerenciado pela Elastic ou um provedor conectado ao Kibana. O script deste repositório não configura esse acesso nem cadastra credenciais de um provedor de modelos. Consulte a [configuração de modelos do Agent Builder](https://www.elastic.co/docs/explore-analyze/ai-features/agent-builder/models).

Após executar o script, confira no Agent Builder se o `copa-scout` e suas 10 ferramentas foram cadastrados e teste uma consulta simples, como “Quais foram as partidas do Brasil na Copa 2022?”. Os códigos de resposta impressos pelo script ajudam a identificar falhas de cadastro; a confirmação do funcionamento exige testar no novo ambiente.

## Dados preservados

Os sete CSVs permitem explorar os resultados sem Elastic. O cache recuperado das 128 partidas está em `../copa_scout_original/cache/`. Para reutilizá-lo na revisão, copie seus arquivos para `cache/` antes de executar os scripts. Esse cache ocupa aproximadamente 418 MB e contém objetos pickle: utilize apenas arquivos de origem conhecida.

Os scripts que pedem os metadados das partidas ainda consultam a StatsBomb, mesmo quando o cache de eventos já existe. Os scripts 5, 6 e 7 também importam a configuração do Elastic e fazem indexação quando executados normalmente; não têm um modo offline pela linha de comando.

## Testes locais

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Os testes isolam as funções de análise, sem importar a configuração de serviços nem executar indexação. Cobrem exclusão da disputa de pênaltis, duração do jogo, ordem dos eventos, separação de períodos, janela de 30 segundos, momentum, impacto de jogadores, coerência das narrativas e o cache real de Brasil × Croácia.

O caso com cache real depende de `../copa_scout_original/cache/3869420.pkl`. A validação das narrativas lê o CSV local. Os testes não validam as APIs de um deployment nem os gráficos no Kibana.
