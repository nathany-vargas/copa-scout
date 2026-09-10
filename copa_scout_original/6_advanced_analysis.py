"""
6_advanced_analysis.py — Análises avançadas

Gera 3 novos índices no Elastic:
  1. pressing_analysis   — onde cada time recupera/perde a bola e o que acontece depois
  2. player_impact       — quais jogadores mais impactaram cada partida
  3. match_momentum      — como o jogo evoluiu por períodos de 15 min

Roda DEPOIS do 5_goal_chains.py.
"""

import os
import pickle
import pandas as pd
import numpy as np
from statsbombpy import sb
from elasticsearch import Elasticsearch, helpers
import requests

CACHE_DIR = "cache"
TOURNAMENTS = [
    (43, 106, "FIFA World Cup 2022"),
    (43, 3, "FIFA World Cup 2018"),
]

es = Elasticsearch(
    cloud_id="chavinha_expirada",
    api_key="chavinha_expirada"
)

KIBANA_URL = "chavinha_expirada"
API_KEY = "chavinha_expirada"
HEADERS = {"Authorization": f"ApiKey {API_KEY}", "kbn-xsrf": "true", "Content-Type": "application/json"}


def load_events(match_id):
    path = os.path.join(CACHE_DIR, f"{match_id}.pkl")
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return pickle.load(f)


# ============================================================
# ANÁLISE 1: TURNOVERS (perdas e recuperações de bola)
# ============================================================

def analyze_turnovers(events, match_id, tournament, home, away):
    """
    Analisa onde cada time perde a bola e o que acontece nos 10 segundos seguintes.
    Identifica turnovers perigosos (que resultam em chute do adversário).
    """
    records = []
    
    # Eventos que indicam perda de posse
    loss_types = ["Dispossessed", "Miscontrol", "Error"]
    # Eventos que indicam recuperação
    recovery_types = ["Ball Recovery", "Interception"]
    
    for team in [home, away]:
        opponent = away if team == home else home
        
        # Perdas de bola do time
        losses = events[
            (events["team"] == team) & 
            (events["type"].isin(loss_types))
        ]
        
        for _, loss in losses.iterrows():
            loss_minute = loss["minute"]
            loss_second = loss.get("second", 0) or 0
            loss_time = loss_minute * 60 + loss_second
            
            loc = loss.get("location")
            loss_x = loc[0] if isinstance(loc, list) else None
            loss_y = loc[1] if isinstance(loc, list) else None
            
            # Zona onde perdeu
            if loss_x is not None:
                if loss_x >= 80:
                    loss_zone = "Terço ofensivo"
                elif loss_x >= 40:
                    loss_zone = "Meio-campo"
                else:
                    loss_zone = "Terço defensivo"
            else:
                loss_zone = "Desconhecida"
            
            # O que aconteceu nos 30 segundos seguintes
            window = events[
                (events["minute"] * 60 + events["second"].fillna(0)) > loss_time
            ].head(15)
            
            resulted_in_shot = len(window[
                (window["type"] == "Shot") & (window["team"] == opponent)
            ]) > 0
            
            resulted_in_goal = len(window[
                (window["type"] == "Shot") & 
                (window["team"] == opponent) & 
                (window["shot_outcome"] == "Goal")
            ]) > 0
            
            records.append({
                "match_id": str(match_id),
                "tournament": tournament,
                "team": team,
                "opponent": opponent,
                "minute": int(loss_minute),
                "loss_type": loss["type"],
                "loss_zone": loss_zone,
                "loss_x": loss_x,
                "loss_y": loss_y,
                "resulted_in_shot": resulted_in_shot,
                "resulted_in_goal": resulted_in_goal,
                "danger_level": "CRITICO" if resulted_in_goal else ("PERIGOSO" if resulted_in_shot else "NORMAL"),
            })
        
        # Recuperações do time
        recoveries = events[
            (events["team"] == team) & 
            (events["type"].isin(recovery_types))
        ]
        
        for _, rec in recoveries.iterrows():
            loc = rec.get("location")
            rec_x = loc[0] if isinstance(loc, list) else None
            
            if rec_x is not None:
                if rec_x >= 80:
                    rec_zone = "Terço ofensivo"
                elif rec_x >= 40:
                    rec_zone = "Meio-campo"
                else:
                    rec_zone = "Terço defensivo"
            else:
                rec_zone = "Desconhecida"
            
            rec_minute = rec["minute"]
            rec_time = rec_minute * 60 + (rec.get("second", 0) or 0)
            
            window = events[
                (events["minute"] * 60 + events["second"].fillna(0)) > rec_time
            ].head(10)
            
            led_to_shot = len(window[
                (window["type"] == "Shot") & (window["team"] == team)
            ]) > 0
            
            records.append({
                "match_id": str(match_id),
                "tournament": tournament,
                "team": team,
                "opponent": opponent,
                "minute": int(rec_minute),
                "loss_type": f"RECOVERY_{rec['type']}",
                "loss_zone": rec_zone,
                "loss_x": rec_x,
                "loss_y": None,
                "resulted_in_shot": led_to_shot,
                "resulted_in_goal": False,
                "danger_level": "OPORTUNIDADE" if led_to_shot else "RECUPERAÇÃO",
            })
    
    return records


# ============================================================
# ANÁLISE 2: IMPACTO DE JOGADORES
# ============================================================

def analyze_players(events, match_id, tournament, home, away):
    """
    Calcula o impacto de cada jogador numa partida.
    """
    records = []
    
    for team in [home, away]:
        team_events = events[events["team"] == team]
        players = team_events["player"].dropna().unique()
        
        for player in players:
            p = team_events[team_events["player"] == player]
            
            passes = p[p["type"] == "Pass"]
            passes_completed = len(passes[passes["pass_outcome"].isna()])
            passes_total = len(passes)
            
            shots = p[p["type"] == "Shot"]
            goals = len(shots[shots["shot_outcome"] == "Goal"])
            xg = float(shots["shot_statsbomb_xg"].fillna(0).sum())
            
            pressures = len(p[p["type"] == "Pressure"])
            interceptions = len(p[p["type"] == "Interception"])
            tackles = len(p[(p["type"] == "Duel") & (p["duel_type"] == "Tackle")])
            blocks = len(p[p["type"] == "Block"])
            recoveries = len(p[p["type"] == "Ball Recovery"])
            
            carries = p[p["type"] == "Carry"]
            dribbles = p[p["type"] == "Dribble"]
            dribbles_success = len(dribbles[dribbles["dribble_outcome"] == "Complete"])
            
            key_passes = len(passes[passes["pass_goal_assist"].fillna(False)])
            
            # Perdas
            dispossessed = len(p[p["type"] == "Dispossessed"])
            miscontrols = len(p[p["type"] == "Miscontrol"])
            
            # Score de impacto
            impact = (
                goals * 20 +
                xg * 5 +
                key_passes * 10 +
                passes_completed * 0.1 +
                pressures * 0.5 +
                interceptions * 2 +
                tackles * 2 +
                blocks * 3 +
                recoveries * 1.5 +
                dribbles_success * 2 -
                dispossessed * 3 -
                miscontrols * 2
            )
            
            if passes_total + len(shots) + pressures < 5:
                continue  # Pula jogadores com participação mínima
            
            records.append({
                "match_id": str(match_id),
                "tournament": tournament,
                "team": team,
                "player": player,
                "position": p["position"].mode().iloc[0] if len(p["position"].dropna()) > 0 else "Unknown",
                "passes_completed": passes_completed,
                "passes_total": passes_total,
                "pass_pct": round(passes_completed / passes_total * 100, 1) if passes_total > 0 else 0,
                "shots": len(shots),
                "goals": goals,
                "xg": round(xg, 3),
                "pressures": pressures,
                "interceptions": interceptions,
                "tackles": tackles,
                "blocks": blocks,
                "recoveries": recoveries,
                "dribbles_success": dribbles_success,
                "key_passes": key_passes,
                "dispossessed": dispossessed,
                "miscontrols": miscontrols,
                "impact_score": round(impact, 1),
            })
    
    return records


# ============================================================
# ANÁLISE 3: MOMENTUM POR PERÍODO
# ============================================================

def analyze_momentum(events, match_id, tournament, home, away):
    """
    Divide o jogo em períodos de 15 min e calcula quem dominou cada período.
    """
    records = []
    max_min = int(events["minute"].max())
    
    periods = list(range(0, max_min + 1, 15))
    if periods[-1] < max_min:
        periods.append(max_min + 1)
    
    for i in range(len(periods) - 1):
        start = periods[i]
        end = periods[i + 1]
        period_events = events[(events["minute"] >= start) & (events["minute"] < end)]
        
        for team in [home, away]:
            opponent = away if team == home else home
            t = period_events[period_events["team"] == team]
            o = period_events[period_events["team"] == opponent]
            
            passes = len(t[t["type"] == "Pass"])
            passes_total_both = len(period_events[period_events["type"] == "Pass"])
            possession = round(passes / passes_total_both * 100, 1) if passes_total_both > 0 else 50
            
            shots = len(t[t["type"] == "Shot"])
            shots_against = len(o[o["type"] == "Shot"])
            xg = float(t[t["type"] == "Shot"]["shot_statsbomb_xg"].fillna(0).sum())
            
            pressures = len(t[t["type"] == "Pressure"])
            recoveries = len(t[t["type"] == "Ball Recovery"])
            interceptions = len(t[t["type"] == "Interception"])
            
            # Domínio: score simples de quem controlou o período
            dominance = (
                possession * 0.3 +
                shots * 5 +
                pressures * 0.5 +
                recoveries * 1 -
                shots_against * 5
            )
            
            records.append({
                "match_id": str(match_id),
                "tournament": tournament,
                "team": team,
                "opponent": opponent,
                "period_start": start,
                "period_end": end,
                "period_label": f"{start}-{end} min",
                "possession_pct": possession,
                "shots": shots,
                "shots_against": shots_against,
                "xg": round(xg, 3),
                "pressures": pressures,
                "recoveries": recoveries,
                "interceptions": interceptions,
                "dominance_score": round(dominance, 1),
            })
    
    return records


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    all_turnovers = []
    all_players = []
    all_momentum = []
    
    for comp_id, season_id, name in TOURNAMENTS:
        matches = sb.matches(competition_id=comp_id, season_id=season_id)
        total = len(matches)
        
        print(f"\n{'='*50}")
        print(f"Processando: {name} ({total} jogos)")
        print(f"{'='*50}")
        
        for i, (_, row) in enumerate(matches.iterrows(), 1):
            mid = row["match_id"]
            home = row["home_team"]
            away = row["away_team"]
            
            events = load_events(mid)
            if events is None:
                continue
            
            turnovers = analyze_turnovers(events, mid, name, home, away)
            players = analyze_players(events, mid, name, home, away)
            momentum = analyze_momentum(events, mid, name, home, away)
            
            all_turnovers.extend(turnovers)
            all_players.extend(players)
            all_momentum.extend(momentum)
            
            if i % 20 == 0 or i == total:
                print(f"  [{i}/{total}] processados")
    
    # Salva CSVs
    pd.DataFrame(all_turnovers).to_csv("turnovers.csv", index=False)
    pd.DataFrame(all_players).to_csv("player_impact.csv", index=False)
    pd.DataFrame(all_momentum).to_csv("match_momentum.csv", index=False)
    print(f"\n✓ turnovers.csv: {len(all_turnovers)} eventos")
    print(f"✓ player_impact.csv: {len(all_players)} jogadores")
    print(f"✓ match_momentum.csv: {len(all_momentum)} períodos")
    
    # Indexa no Elastic
    print("\nIndexando no Elastic...")
    
    indices = {
        "turnovers": {
            "data": all_turnovers,
            "mapping": {"mappings": {"properties": {
                "match_id": {"type": "keyword"}, "tournament": {"type": "keyword"},
                "team": {"type": "keyword"}, "opponent": {"type": "keyword"},
                "minute": {"type": "integer"}, "loss_type": {"type": "keyword"},
                "loss_zone": {"type": "keyword"}, "loss_x": {"type": "float"},
                "loss_y": {"type": "float"}, "resulted_in_shot": {"type": "boolean"},
                "resulted_in_goal": {"type": "boolean"}, "danger_level": {"type": "keyword"},
            }}}
        },
        "player_impact": {
            "data": all_players,
            "mapping": {"mappings": {"properties": {
                "match_id": {"type": "keyword"}, "tournament": {"type": "keyword"},
                "team": {"type": "keyword"}, "player": {"type": "keyword"},
                "position": {"type": "keyword"},
                "passes_completed": {"type": "integer"}, "passes_total": {"type": "integer"},
                "pass_pct": {"type": "float"}, "shots": {"type": "integer"},
                "goals": {"type": "integer"}, "xg": {"type": "float"},
                "pressures": {"type": "integer"}, "interceptions": {"type": "integer"},
                "tackles": {"type": "integer"}, "blocks": {"type": "integer"},
                "recoveries": {"type": "integer"}, "dribbles_success": {"type": "integer"},
                "key_passes": {"type": "integer"}, "dispossessed": {"type": "integer"},
                "miscontrols": {"type": "integer"}, "impact_score": {"type": "float"},
            }}}
        },
        "match_momentum": {
            "data": all_momentum,
            "mapping": {"mappings": {"properties": {
                "match_id": {"type": "keyword"}, "tournament": {"type": "keyword"},
                "team": {"type": "keyword"}, "opponent": {"type": "keyword"},
                "period_start": {"type": "integer"}, "period_end": {"type": "integer"},
                "period_label": {"type": "keyword"}, "possession_pct": {"type": "float"},
                "shots": {"type": "integer"}, "shots_against": {"type": "integer"},
                "xg": {"type": "float"}, "pressures": {"type": "integer"},
                "recoveries": {"type": "integer"}, "interceptions": {"type": "integer"},
                "dominance_score": {"type": "float"},
            }}}
        },
    }
    
    for idx_name, idx_data in indices.items():
        if es.indices.exists(index=idx_name):
            es.indices.delete(index=idx_name)
        es.indices.create(index=idx_name, body=idx_data["mapping"])
        
        actions = [{"_index": idx_name, "_source": doc} for doc in idx_data["data"]]
        if actions:
            helpers.bulk(es, actions, raise_on_error=False)
        es.indices.refresh(index=idx_name)
        count = es.count(index=idx_name)
        print(f"  ✓ {idx_name}: {count['count']} documentos")
    
    # Cria tools
    print("\nCriando tools...")
    
    new_tools = [
        {
            "id": "turnover-analysis",
            "type": "esql",
            "description": "Analisa onde um time perde a bola e se isso resultou em perigo. Mostra turnovers CRITICOS (que viraram gol), PERIGOSOS (que viraram chute) e NORMAIS. Use para responder 'onde o time X é vulnerável' ou 'como o time Y perde a bola'.",
            "tags": ["copa", "turnovers"],
            "configuration": {
                "query": "FROM turnovers | WHERE team == ?team AND danger_level != 'RECUPERAÇÃO' | SORT danger_level ASC, minute ASC",
                "params": {"team": {"type": "string", "description": "Time que PERDEU a bola (ex: Brazil)"}}
            }
        },
        {
            "id": "player-impact",
            "type": "esql",
            "description": "Ranking de jogadores por impacto numa partida ou em todo o torneio. Mostra gols, xG, passes, ações defensivas e score de impacto. Use para perguntas sobre jogadores individuais.",
            "tags": ["copa", "players"],
            "configuration": {
                "query": "FROM player_impact | WHERE team == ?team AND tournament == ?tournament | SORT impact_score DESC | LIMIT ?limit",
                "params": {
                    "team": {"type": "string", "description": "Seleção (ex: Brazil, Croatia)"},
                    "tournament": {"type": "string", "description": "Torneio", "optional": True, "defaultValue": "FIFA World Cup 2022"},
                    "limit": {"type": "integer", "description": "Quantos jogadores", "optional": True, "defaultValue": 10}
                }
            }
        },
        {
            "id": "match-momentum",
            "type": "esql",
            "description": "Mostra como o jogo evoluiu período por período (a cada 15 min). Indica posse, chutes, pressões e score de dominância por período. Use para entender QUANDO um time perdeu o controle do jogo.",
            "tags": ["copa", "momentum"],
            "configuration": {
                "query": "FROM match_momentum | WHERE match_id == ?match_id AND team == ?team | SORT period_start ASC",
                "params": {
                    "match_id": {"type": "string", "description": "ID da partida (ex: 3869420)"},
                    "team": {"type": "string", "description": "Time a analisar (ex: Brazil)"}
                }
            }
        },
        {
            "id": "vulnerability-report",
            "type": "esql",
            "description": "Relatório de vulnerabilidade: mostra todas as perdas de bola CRITICAS e PERIGOSAS de um time em um torneio, agrupadas por zona do campo. Use para identificar padrões de fraqueza.",
            "tags": ["copa", "vulnerability"],
            "configuration": {
                "query": "FROM turnovers | WHERE team == ?team AND tournament == ?tournament AND (danger_level == 'CRITICO' OR danger_level == 'PERIGOSO') | STATS total=COUNT(*), gols_originados=SUM(CASE(resulted_in_goal, 1, 0)) BY loss_zone | SORT total DESC",
                "params": {
                    "team": {"type": "string", "description": "Seleção"},
                    "tournament": {"type": "string", "description": "Torneio", "optional": True, "defaultValue": "FIFA World Cup 2022"}
                }
            }
        },
    ]
    
    for tool in new_tools:
        r = requests.post(f"{KIBANA_URL}/api/agent_builder/tools", json=tool, headers=HEADERS)
        status = "✓" if r.status_code in [200, 201] else f"⚠ {r.status_code}"
        print(f"  {status} {tool['id']}")
    
    # Atualiza agent com TODAS as tools
    print("\nAtualizando agent...")
    all_tool_ids = [
        "team-match-stats", "match-comparison", "team-profile",
        "ranking-defensivo", "confronto-direto", "goal-chain-analysis",
        "turnover-analysis", "player-impact", "match-momentum", "vulnerability-report"
    ]
    
    r = requests.put(f"{KIBANA_URL}/api/agent_builder/agents/copa-scout",
        headers=HEADERS,
        json={
            "name": "Copa Scout",
            "description": "Analista tatico de futebol com dados completos das Copas 2018 e 2022",
            "configuration": {
                "instructions": """Voce e o Copa Scout, analista tatico de uma empresa de inteligencia esportiva. Tem acesso a dados COMPLETOS das Copas 2018 e 2022: metricas por time, por jogador, cadeias de gol, turnovers, e momentum por periodo.

REGRAS:
1. SEMPRE use tools antes de responder. Nunca invente dados.
2. Cite numeros especificos: xG, chutes, interceptacoes, Indice de Sobrevivencia.
3. Responda em portugues do Brasil. Seja direto e tatico.
4. Quando perguntarem POR QUE algo aconteceu, use goal-chain-analysis e turnover-analysis.
5. Quando perguntarem QUEM foi decisivo, use player-impact.
6. Quando perguntarem QUANDO o jogo virou, use match-momentum.
7. Quando perguntarem sobre vulnerabilidades, use vulnerability-report.
8. Sugira ao usuario olhar heatmaps e visualizacoes na interface.

FERRAMENTAS:
- team-match-stats: dados gerais por time por partida
- match-comparison: comparacao direta entre dois times num jogo
- team-profile: perfil medio de uma selecao no torneio
- ranking-defensivo: ranking por Indice de Sobrevivencia
- confronto-direto: historico entre dois times
- goal-chain-analysis: cadeia de eventos que levou a cada gol
- turnover-analysis: onde o time perde a bola e o que acontece
- player-impact: impacto individual de cada jogador
- match-momentum: evolucao do jogo por periodos de 15min
- vulnerability-report: zonas de vulnerabilidade por perda de bola""",
                "tools": [{"tool_ids": all_tool_ids}]
            }
        })
    print(f"Agent atualizado: {r.status_code}")
    
    print(f"""
{'='*50}
PRONTO! O Copa Scout agora responde:
{'='*50}
- "Por que o Brasil perdeu pra Croacia?" (goal chains + turnovers)
- "Quem foi o melhor jogador do Brasil na Copa 2022?" (player impact)
- "Em que momento o Brasil perdeu o controle contra a Croacia?" (momentum)
- "Onde o Brasil é vulnerável?" (vulnerability report)
- "Compare Neymar com Modric na Copa 2022" (player impact)
- "Qual time teve mais turnovers perigosos?" (turnovers)
""")