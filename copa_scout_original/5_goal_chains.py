"""
5_goal_chains.py — Análise de cadeias de gol
Extrai os eventos que levaram a cada gol, categoriza o padrão,
e busca padrões similares. Indexa no Elastic.
"""

import os
import pickle
import pandas as pd
from statsbombpy import sb
from elasticsearch import Elasticsearch, helpers

CACHE_DIR = "cache"
TOURNAMENTS = [
    (43, 106, "FIFA World Cup 2022"),
    (43, 3, "FIFA World Cup 2018"),
]

es = Elasticsearch(
    cloud_id="chavinha_expirada",
    api_key="chavinha_expirada"
)

def find_trigger(chain_events, scoring_team):
    """Identifica o evento-gatilho que causou o gol."""
    opponent_events = chain_events[chain_events["team"] != scoring_team]
    
    for _, ev in opponent_events.iterrows():
        if ev["type"] in ["Ball Recovery", "Interception"]:
            return "Recuperação de bola"
        if ev["type"] == "Miscontrol":
            return "Erro de controle"
        if ev["type"] == "Dispossessed":
            return "Perda de posse"
    
    team_events = chain_events[chain_events["team"] == scoring_team]
    types = team_events["type"].tolist()
    
    if "Foul Won" in types:
        return "Falta sofrida"
    if len(team_events) <= 3:
        return "Jogada rápida/direta"
    return "Construção de jogada"

def process_match_goals(match_id, tournament):
    cache_path = os.path.join(CACHE_DIR, f"{match_id}.pkl")
    if not os.path.exists(cache_path):
        return []
    
    with open(cache_path, "rb") as f:
        events = pickle.load(f)
    
    shots = events[(events["type"] == "Shot") & (events["shot_outcome"] == "Goal")]
    records = []
    
    for _, goal in shots.iterrows():
        possession_num = goal.get("possession")
        scoring_team = goal["team"]
        
        chain = events[events["possession"] == possession_num].sort_values(["minute", "second"])
        chain_types = chain["type"].tolist()
        chain_teams = chain["team"].tolist()
        play_pattern = goal.get("play_pattern", "Unknown")
        
        chain_desc = " → ".join([
            f"{r['type']}({r['team'][:3]})" 
            for _, r in chain.tail(8).iterrows()
        ])
        
        trigger = find_trigger(chain, scoring_team)
        
        loc = goal.get("location")
        shot_x = loc[0] if isinstance(loc, list) else None
        shot_y = loc[1] if isinstance(loc, list) else None
        
        records.append({
            "match_id": str(match_id),
            "tournament": tournament,
            "minute": int(goal["minute"]),
            "scoring_team": scoring_team,
            "conceding_team": [t for t in events["team"].unique() if t != scoring_team][0],
            "play_pattern": play_pattern,
            "trigger_event": trigger,
            "chain_length": len(chain),
            "chain_description": chain_desc,
            "xg": round(float(goal.get("shot_statsbomb_xg", 0) or 0), 3),
            "shot_x": shot_x,
            "shot_y": shot_y,
        })
    
    return records

if __name__ == "__main__":
    print("Analisando cadeias de gol...")
    
    all_goals = []
    for comp_id, season_id, name in TOURNAMENTS:
        matches = sb.matches(competition_id=comp_id, season_id=season_id)
        total = len(matches)
        for i, (_, row) in enumerate(matches.iterrows(), 1):
            mid = row["match_id"]
            goals = process_match_goals(mid, name)
            all_goals.extend(goals)
            if goals:
                print(f"  [{i}/{total}] {row['home_team']} vs {row['away_team']}: {len(goals)} gols")
    
    print(f"\nTotal: {len(all_goals)} gols analisados")
    
    # Conta padrões similares
    pattern_counts = {}
    for g in all_goals:
        key = (g["play_pattern"], g["trigger_event"])
        pattern_counts[key] = pattern_counts.get(key, 0) + 1
    
    for g in all_goals:
        key = (g["play_pattern"], g["trigger_event"])
        g["similar_goals_count"] = pattern_counts[key]
        g["pattern_label"] = f"{g['play_pattern']} / {g['trigger_event']}"
    
    # Salva CSV
    df = pd.DataFrame(all_goals)
    df.to_csv("goal_chains.csv", index=False)
    print(f"✓ goal_chains.csv salvo")
    
    # Indexa no Elastic
    print("Indexando no Elastic...")
    if es.indices.exists(index="goal_chains"):
        es.indices.delete(index="goal_chains")
    
    es.indices.create(index="goal_chains", body={"mappings": {"properties": {
        "match_id": {"type": "keyword"}, "tournament": {"type": "keyword"},
        "minute": {"type": "integer"}, "scoring_team": {"type": "keyword"},
        "conceding_team": {"type": "keyword"}, "play_pattern": {"type": "keyword"},
        "trigger_event": {"type": "keyword"}, "chain_length": {"type": "integer"},
        "chain_description": {"type": "text"}, "xg": {"type": "float"},
        "similar_goals_count": {"type": "integer"}, "pattern_label": {"type": "keyword"},
        "shot_x": {"type": "float"}, "shot_y": {"type": "float"},
    }}})
    
    actions = [{"_index": "goal_chains", "_source": g} for g in all_goals]
    helpers.bulk(es, actions)
    es.indices.refresh(index="goal_chains")
    count = es.count(index="goal_chains")
    print(f"✓ {count['count']} gols indexados")
    
    # Cria tool
    import requests
    KIBANA_URL = "chavinha_expirada"
    API_KEY = "chavinha_expirada"
    
    tool = {
        "id": "goal-chain-analysis",
        "type": "esql",
        "description": "Analisa como cada gol aconteceu: a cadeia de eventos, o padrão de jogo, o gatilho, e quantos gols similares ocorreram no torneio. Use quando perguntarem POR QUE um gol aconteceu ou como um time sofreu/fez gol.",
        "tags": ["copa", "goals"],
        "configuration": {
            "query": "FROM goal_chains | WHERE conceding_team == ?team | SORT minute ASC",
            "params": {
                "team": {"type": "string", "description": "Time que SOFREU o gol (ex: Brazil, Spain)"}
            }
        }
    }
    
    r = requests.post(f"{KIBANA_URL}/api/agent_builder/tools", json=tool,
        headers={"Authorization": f"ApiKey {API_KEY}", "kbn-xsrf": "true", "Content-Type": "application/json"})
    print(f"Tool: {r.status_code}")
    
    # Atualiza agent com nova tool
    r = requests.put(f"{KIBANA_URL}/api/agent_builder/agents/copa-scout",
        headers={"Authorization": f"ApiKey {API_KEY}", "kbn-xsrf": "true", "Content-Type": "application/json"},
        json={
            "name": "Copa Scout",
            "description": "Analista tatico de futebol com dados das Copas 2018 e 2022",
            "configuration": {
                "instructions": """Voce e um analista tatico de futebol de uma empresa de inteligencia esportiva. Tem dados de TODAS as partidas das Copas 2018 e 2022. Use as tools para buscar dados. Cite numeros: xG, chutes, interceptacoes, posse, Indice de Sobrevivencia. Responda em portugues do Brasil. Seja direto. NOVO: voce agora pode analisar a CADEIA DE EVENTOS que levou a cada gol - o play_pattern, o trigger_event (o que causou), e quantos gols similares aconteceram no torneio. Quando perguntarem POR QUE um gol aconteceu, use a tool goal-chain-analysis.""",
                "tools": [
                    {"tool_ids": ["team-match-stats", "match-comparison", "team-profile", "ranking-defensivo", "confronto-direto", "goal-chain-analysis"]}
                ]
            }
        })
    print(f"Agent atualizado: {r.status_code}")
    print("\nPronto! Testa no Kibana: 'Como foi o gol que o Brasil tomou da Croacia?'")