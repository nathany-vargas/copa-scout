"""5_goal_chains.py — Análise de cadeias de gol"""
import os
import pickle
import pandas as pd
from statsbombpy import sb
from elasticsearch import helpers
from config import es, CACHE_DIR, TOURNAMENTS

def find_trigger(chain_events, scoring_team):
    opponent_events = chain_events[chain_events["team"] != scoring_team]
    for _, ev in opponent_events.iterrows():
        if ev["type"] in ["Ball Recovery", "Interception"]:
            return "Recuperação de bola"
        if ev["type"] == "Miscontrol":
            return "Erro de controle"
        if ev["type"] == "Dispossessed":
            return "Perda de posse"
    team_events = chain_events[chain_events["team"] == scoring_team]
    if "Foul Won" in team_events["type"].tolist():
        return "Falta sofrida"
    if len(team_events) <= 3:
        return "Jogada rápida/direta"
    return "Construção de jogada"

def process_match_goals(match_id, tournament):
    path = os.path.join(CACHE_DIR, f"{match_id}.pkl")
    if not os.path.exists(path):
        return []
    with open(path, "rb") as f:
        events = pickle.load(f)
    events = events[events["period"] != 5]
    shots = events[(events["type"] == "Shot") & (events["shot_outcome"] == "Goal")]
    records = []
    for _, goal in shots.iterrows():
        chain = events[events["possession"] == goal.get("possession")].sort_values(["minute", "second"])
        scoring_team = goal["team"]
        loc = goal.get("location")
        chain_desc = " → ".join([f"{r['type']}({r['team'][:3]})" for _, r in chain.tail(8).iterrows()])
        records.append({
            "match_id": str(match_id), "tournament": tournament,
            "minute": int(goal["minute"]), "scoring_team": scoring_team,
            "conceding_team": [t for t in events["team"].unique() if t != scoring_team][0],
            "play_pattern": goal.get("play_pattern", "Unknown"),
            "trigger_event": find_trigger(chain, scoring_team),
            "chain_length": len(chain), "chain_description": chain_desc,
            "xg": round(float(goal.get("shot_statsbomb_xg", 0) or 0), 3),
            "shot_x": loc[0] if isinstance(loc, list) else None,
            "shot_y": loc[1] if isinstance(loc, list) else None,
        })
    return records

if __name__ == "__main__":
    print("FASE 5: CADEIAS DE GOL")
    all_goals = []
    for comp_id, season_id, name in TOURNAMENTS:
        matches = sb.matches(competition_id=comp_id, season_id=season_id)
        for i, (_, row) in enumerate(matches.iterrows(), 1):
            goals = process_match_goals(row["match_id"], name)
            all_goals.extend(goals)
            if goals: print(f"  [{i}/{len(matches)}] {row['home_team']} vs {row['away_team']}: {len(goals)} gols")

    # Conta padrões similares
    pattern_counts = {}
    for g in all_goals:
        key = (g["play_pattern"], g["trigger_event"])
        pattern_counts[key] = pattern_counts.get(key, 0) + 1
    for g in all_goals:
        key = (g["play_pattern"], g["trigger_event"])
        g["similar_goals_count"] = pattern_counts[key]
        g["pattern_label"] = f"{g['play_pattern']} / {g['trigger_event']}"

    pd.DataFrame(all_goals).to_csv("goal_chains.csv", index=False)
    print(f"✓ {len(all_goals)} gols analisados")

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
    helpers.bulk(es, [{"_index": "goal_chains", "_source": g} for g in all_goals])
    es.indices.refresh(index="goal_chains")
    print(f"✓ {es.count(index='goal_chains')['count']} gols indexados")
