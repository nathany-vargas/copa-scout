"""
4_agent_setup.py — Configura o Agent Builder via API do Kibana

Cria o agent "Copa Scout" com o system prompt e associa as tools.
Se as tools já foram criadas manualmente no Kibana, pula a criação.
"""

import requests
import json

# ============================================================
# CONFIG
# ============================================================

KIBANA_URL = "chavinha_expirada"
API_KEY = "chavinha_expirada"

HEADERS = {
    "Authorization": f"ApiKey {API_KEY}",
    "kbn-xsrf": "true",
    "Content-Type": "application/json",
}

# ============================================================
# TOOLS (pula se já existirem no Kibana)
# ============================================================

TOOLS = [
    {
        "id": "team-match-stats",
        "type": "esql",
        "description": "Busca todas as partidas de uma seleção específica com métricas detalhadas. Use quando perguntarem sobre um time específico.",
        "tags": ["copa", "stats"],
        "configuration": {
            "query": "FROM match_stats | WHERE team == ?team | SORT match_date DESC",
            "params": {
                "team": {
                    "type": "string",
                    "description": "Nome da seleção em inglês (ex: Brazil, Croatia, Morocco, Japan)",
                }
            }
        }
    },
    {
        "id": "match-comparison",
        "type": "esql",
        "description": "Retorna os dados dos dois times em uma partida específica para comparação direta. Use quando perguntarem sobre um jogo específico.",
        "tags": ["copa", "comparison"],
        "configuration": {
            "query": "FROM match_stats | WHERE match_id == ?match_id",
            "params": {
                "match_id": {
                    "type": "string",
                    "description": "ID da partida (ex: 3869420 para Croácia vs Brasil)",
                }
            }
        }
    },
    {
        "id": "team-profile",
        "type": "esql",
        "description": "Retorna o perfil agregado de uma seleção em um torneio, com médias de todas as métricas. Use para visão geral do desempenho.",
        "tags": ["copa", "profile"],
        "configuration": {
            "query": "FROM team_profiles | WHERE team == ?team",
            "params": {
                "team": {
                    "type": "string",
                    "description": "Nome da seleção em inglês (ex: Brazil, France, Argentina)",
                }
            }
        }
    },
    {
        "id": "ranking-defensivo",
        "type": "esql",
        "description": "Ranking das seleções por Índice de Sobrevivência médio. Mostra quais times tiveram a melhor performance defensiva no torneio.",
        "tags": ["copa", "ranking"],
        "configuration": {
            "query": "FROM team_profiles | WHERE tournament == ?tournament | SORT avg_survival_index DESC | LIMIT ?limit",
            "params": {
                "tournament": {
                    "type": "string",
                    "description": "Nome do torneio (ex: FIFA World Cup 2022, FIFA World Cup 2018)",
                    "optional": True,
                    "defaultValue": "FIFA World Cup 2022"
                },
                "limit": {
                    "type": "integer",
                    "description": "Número de resultados",
                    "optional": True,
                    "defaultValue": 10
                }
            }
        }
    },
    {
        "id": "confronto-direto",
        "type": "esql",
        "description": "Busca todos os confrontos entre dois times específicos. Use para análise de rivalidades ou histórico de confrontos.",
        "tags": ["copa", "confronto"],
        "configuration": {
            "query": "FROM match_stats | WHERE team == ?team AND opponent == ?opponent",
            "params": {
                "team": {
                    "type": "string",
                    "description": "Primeiro time (ex: Brazil)",
                },
                "opponent": {
                    "type": "string",
                    "description": "Segundo time (ex: Croatia)",
                }
            }
        }
    },
]

# ============================================================
# AGENT
# ============================================================

AGENT = {
    "name": "Copa Scout",
    "description": "Analista tático de futebol com dados das Copas 2018 e 2022",
    "configuration": {
        "instructions": (
            "Você é um analista tático de futebol que trabalha para uma empresa de inteligência esportiva. "
            "Você tem acesso a dados detalhados de TODAS as partidas das Copas do Mundo de 2018 e 2022 "
            "(128 jogos, 256 registros — um por time por partida).\n\n"
            "Seu papel é explicar o que aconteceu em cada partida usando dados reais, "
            "sempre de forma visual e didática, como se estivesse explicando para uma comissão técnica.\n\n"
            "REGRAS:\n"
            "1. SEMPRE use as tools para buscar dados antes de responder. Nunca invente estatísticas.\n"
            "2. Cite números específicos: xG, chutes, interceptações, posse de bola, Índice de Sobrevivência.\n"
            "3. O Índice de Sobrevivência (IS) mede a resiliência defensiva: quanto maior, melhor a defesa. "
            "Acima de 120 = Fortaleza Impenetrável, 80-120 = Muro Sólido, 50-80 = Resistência Competitiva.\n"
            "4. Quando comparar dois times, destaque as diferenças mais gritantes.\n"
            "5. Sugira ao usuário olhar as visualizações (heatmap, shot map, radar) quando relevante.\n"
            "6. Responda sempre em português do Brasil.\n"
            "7. Seja direto e objetivo — comissão técnica quer fatos, não enrolação.\n"
            "8. Quando perguntarem 'por que o Brasil perdeu', analise os dados defensivos E ofensivos dos dois times.\n\n"
            "DADOS DISPONÍVEIS:\n"
            "- match_stats: métricas por time por partida (pressões, interceptações, bloqueios, xG, posse, chutes, etc.)\n"
            "- team_profiles: médias por seleção por torneio\n"
            "- Índice de Sobrevivência: métrica proprietária que combina ações defensivas ponderadas menos penalidades por gols/chutes sofridos"
        ),
        "tools": {
            "tool_ids": [
                "team-match-stats",
                "match-comparison",
                "team-profile",
                "ranking-defensivo",
                "confronto-direto",
            ]
        }
    }
}

# ============================================================
# FUNÇÕES
# ============================================================

def api_call(method, endpoint, body=None):
    """Faz chamada à API do Kibana."""
    url = f"{KIBANA_URL}{endpoint}"
    if method == "GET":
        r = requests.get(url, headers=HEADERS)
    elif method == "POST":
        r = requests.post(url, headers=HEADERS, json=body)
    elif method == "PUT":
        r = requests.put(url, headers=HEADERS, json=body)

    if r.status_code >= 400:
        print(f"  ⚠ Erro {r.status_code}: {r.text[:200]}")
    return r


def list_tools():
    """Lista tools existentes."""
    r = api_call("GET", "/api/agent_builder/tools")
    if r.status_code == 200:
        return r.json()
    return []


def create_tool(tool):
    """Cria uma tool."""
    r = api_call("POST", "/api/agent_builder/tools", tool)
    if r.status_code in [200, 201]:
        print(f"  ✓ Tool criada: {tool['id']}")
    else:
        print(f"  ⚠ Tool {tool['id']}: {r.status_code}")
    return r


def create_agent(agent):
    """Cria o agent."""
    r = api_call("POST", "/api/agent_builder/agents", agent)
    if r.status_code in [200, 201]:
        data = r.json()
        agent_id = data.get("id", "desconhecido")
        print(f"  ✓ Agent criado! ID: {agent_id}")
        return agent_id
    else:
        print(f"  ⚠ Erro ao criar agent: {r.status_code}")
        print(f"  {r.text[:300]}")
    return None


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("FASE 4: CONFIGURAÇÃO DO AGENT BUILDER")
    print("=" * 60)

    # 1. Verifica tools existentes
    print("\nVerificando tools existentes...")
    existing = list_tools()
    existing_ids = []

    if isinstance(existing, list):
        existing_ids = [t.get("id", "") for t in existing]
    elif isinstance(existing, dict) and "tools" in existing:
        existing_ids = [t.get("id", "") for t in existing["tools"]]

    print(f"  Tools encontradas: {existing_ids}")

    # 2. Cria tools que não existem
    print("\nCriando tools...")
    for tool in TOOLS:
        if tool["id"] in existing_ids:
            print(f"  → {tool['id']} já existe, pulando")
        else:
            create_tool(tool)

    # 3. Cria o agent
    print("\nCriando agent...")
    agent_id = create_agent(AGENT)

    # 4. Resumo
    print("\n" + "=" * 60)
    print("RESUMO")
    print("=" * 60)
    if agent_id:
        print(f"  AGENT_ID: {agent_id}")
        print(f"  Manda esse ID pra Pessoa 2 (frontend)")
        print(f"\n  Testa no Kibana:")
        print(f"  → Abre Agents no menu lateral")
        print(f"  → Seleciona 'Copa Scout' no dropdown do chat")
        print(f"  → Pergunta: 'Por que o Brasil perdeu pra Croácia em 2022?'")