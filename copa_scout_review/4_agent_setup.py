"""4_agent_setup.py — Cria tools e agent no Agent Builder"""
from config import kb_api

TOOLS = [
    {"id": "team-match-stats", "type": "esql", "description": "Busca todas as partidas de uma seleção com métricas detalhadas.",
     "configuration": {"query": "FROM match_stats | WHERE team == ?team | SORT match_date DESC",
                       "params": {"team": {"type": "string", "description": "Seleção em inglês (ex: Brazil, Croatia)"}}}},
    {"id": "match-comparison", "type": "esql", "description": "Dados dos dois times numa partida para comparação direta.",
     "configuration": {"query": "FROM match_stats | WHERE match_id == ?match_id",
                       "params": {"match_id": {"type": "string", "description": "ID da partida (ex: 3869420)"}}}},
    {"id": "team-profile", "type": "esql", "description": "Perfil agregado de uma seleção num torneio.",
     "configuration": {"query": "FROM team_profiles | WHERE team == ?team",
                       "params": {"team": {"type": "string", "description": "Seleção"}}}},
    {"id": "ranking-defensivo", "type": "esql", "description": "Ranking por Índice de Sobrevivência.",
     "configuration": {"query": "FROM team_profiles | WHERE tournament == ?tournament | SORT avg_survival_index DESC | LIMIT ?limit",
                       "params": {"tournament": {"type": "string", "description": "Torneio", "optional": True, "defaultValue": "FIFA World Cup 2022"},
                                  "limit": {"type": "integer", "description": "Resultados", "optional": True, "defaultValue": 10}}}},
    {"id": "confronto-direto", "type": "esql", "description": "Confrontos entre dois times.",
     "configuration": {"query": "FROM match_stats | WHERE team == ?team AND opponent == ?opponent",
                       "params": {"team": {"type": "string", "description": "Time 1"}, "opponent": {"type": "string", "description": "Time 2"}}}},
    {"id": "goal-chain-analysis", "type": "esql", "description": "Cadeia de eventos que levou a cada gol. Use para POR QUE um gol aconteceu.",
     "configuration": {"query": "FROM goal_chains | WHERE conceding_team == ?team | SORT minute ASC",
                       "params": {"team": {"type": "string", "description": "Time que sofreu o gol"}}}},
    {"id": "turnover-analysis", "type": "esql", "description": "Onde um time perde a bola e se resultou em perigo (CRITICO/PERIGOSO/NORMAL).",
     "configuration": {"query": "FROM turnovers | WHERE team == ?team | SORT danger_level ASC",
                       "params": {"team": {"type": "string", "description": "Time que perdeu a bola"}}}},
    {"id": "player-impact", "type": "esql", "description": "Ranking de jogadores por impacto.",
     "configuration": {"query": "FROM player_impact | WHERE team == ?team AND tournament == ?tournament | SORT impact_score DESC | LIMIT ?limit",
                       "params": {"team": {"type": "string", "description": "Seleção"},
                                  "tournament": {"type": "string", "description": "Torneio", "optional": True, "defaultValue": "FIFA World Cup 2022"},
                                  "limit": {"type": "integer", "description": "Quantos", "optional": True, "defaultValue": 10}}}},
    {"id": "match-momentum", "type": "esql", "description": "Evolução do jogo por períodos de 15min.",
     "configuration": {"query": "FROM match_momentum | WHERE match_id == ?match_id AND team == ?team | SORT period_start ASC",
                       "params": {"match_id": {"type": "string", "description": "ID da partida"}, "team": {"type": "string", "description": "Time"}}}},
    {"id": "counterfactual", "type": "esql",
     "description": "Análise contrafactual: busca turnovers similares na base histórica e calcula a probabilidade de cada outcome (gol, chute, nada). Use para 'O que teria acontecido se...'",
     "configuration": {"query": "FROM counterfactual_events | WHERE event_zone == ?zone AND event_type == ?event_type",
                       "params": {"zone": {"type": "string", "description": "Zona: own_third, mid_third, final_third"},
                                  "event_type": {"type": "string", "description": "Tipo: Dispossessed, Miscontrol, Interception, Ball Recovery"}}}},
]

INSTRUCTIONS = """Voce e o Copa Scout, analista tatico contrafactual. Dados completos das Copas 2018/2022.

ESPECIALIDADE: analise contrafactual — "O que teria acontecido se...?" usando probabilidade condicional de eventos similares.

1)REGRAS:
2. SEMPRE use tools antes de responder.
3. Para "o que teria acontecido se": use counterfactual para buscar situacoes similares e cite probabilidades.
4. Para gols: use goal-chain-analysis.
5. Para jogadores: use player-impact.
6. Para momentos: use match-momentum.
7. Formato contrafactual: "Em X situacoes similares, Y% resultaram em [outcome]. Isso significa que..."
8. Portugues do Brasil. Direto e tatico.
9. Nomes em ingles nas queries, resposta em portugues.
10. Use linguagem cautelosa: "os dados sugerem", "há indícios de", "a análise aponta para", "possivelmente". Voce NAO tem certeza absoluta — voce analisa padroes estatisticos e faz inferencias. Deixe isso claro quando fizer interpretacoes que vao alem dos numeros puros.
"""

if __name__ == "__main__":
    print("Criando tools...")
    for tool in TOOLS:
        r = kb_api("POST", "/api/agent_builder/tools", tool)
        s = "✓" if r.status_code in [200,201] else ("→ existe" if "already exists" in r.text else f"⚠ {r.status_code}")
        print(f"  {s} {tool['id']}")

    print("\nCriando agent...")
    all_ids = [t["id"] for t in TOOLS]
    r = kb_api("POST", "/api/agent_builder/agents", {
        "id": "copa-scout", "name": "Copa Scout",
        "description": "Analista contrafactual - Copas 2018/2022",
        "configuration": {"instructions": INSTRUCTIONS, "tools": [{"tool_ids": all_ids}]}
    })
    if "already exists" in (r.text or ""):
        r = kb_api("PUT", "/api/agent_builder/agents/copa-scout", {
            "name": "Copa Scout", "description": "Analista contrafactual - Copas 2018/2022",
            "configuration": {"instructions": INSTRUCTIONS, "tools": [{"tool_ids": all_ids}]}
        })
    print(f"  Agent: {r.status_code}")