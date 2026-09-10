"""
7_counterfactual.py — Análise contrafactual

Para cada perda/recuperação de bola nas Copas 2018+2022:
  1. Registra zona, tipo, contexto
  2. Rastreia o que aconteceu nos 30 seg seguintes (nada, chute, gol)
  3. Calcula probabilidade condicional por zona+tipo
  4. Indexa no Elastic como counterfactual_events

O agent usa isso para responder:
  "O que teria acontecido se o Brasil não tivesse perdido a bola no min 115?"
  → "Em 847 turnovers similares no terço ofensivo, 12% resultaram em chute
     e 2% em gol. A Croácia converteu uma situação estatisticamente inofensiva."
"""

import os
import pickle
import pandas as pd
from statsbombpy import sb
from elasticsearch import helpers
from config import es, CACHE_DIR, TOURNAMENTS

LOSS_TYPES = ["Dispossessed", "Miscontrol", "Error"]
RECOVERY_TYPES = ["Ball Recovery", "Interception"]
ALL_TYPES = LOSS_TYPES + RECOVERY_TYPES

def classify_zone(x):
    if x < 40: return "own_third"
    if x < 80: return "mid_third"
    return "final_third"

def analyze_match(match_id, tournament, home, away):
    path = os.path.join(CACHE_DIR, f"{match_id}.pkl")
    if not os.path.exists(path):
        return []
    with open(path, "rb") as f:
        events = pickle.load(f)
    events = events[events["period"] != 5].copy()

    records = []
    events["_time"] = events["minute"] * 60 + events["second"].fillna(0)

    relevant = events[events["type"].isin(ALL_TYPES)].copy()
    relevant = relevant.dropna(subset=["location"])

    for _, ev in relevant.iterrows():
        team = ev["team"]
        opponent = away if team == home else home
        ev_time = ev["_time"]
        loc = ev["location"]
        x = loc[0] if isinstance(loc, list) else None
        if x is None:
            continue

        zone = classify_zone(x)
        is_loss = ev["type"] in LOSS_TYPES

        # O que aconteceu nos 30 segundos seguintes
        window = events[(events["period"] == ev["period"]) & (events["index"] > ev["index"]) & (events["_time"] >= ev_time) & (events["_time"] <= ev_time + 30)]

        if is_loss:
            # Time perdeu a bola — o adversário pode ter criado perigo
            opp_shots = window[(window["type"] == "Shot") & (window["team"] == opponent)]
            resulted_shot = len(opp_shots) > 0
            resulted_goal = len(opp_shots[opp_shots["shot_outcome"] == "Goal"]) > 0 if resulted_shot else False
            xg_generated = float(opp_shots["shot_statsbomb_xg"].fillna(0).sum()) if resulted_shot else 0.0
            perspective = "loss"
        else:
            # Time recuperou a bola — pode ter criado perigo
            own_shots = window[(window["type"] == "Shot") & (window["team"] == team)]
            resulted_shot = len(own_shots) > 0
            resulted_goal = len(own_shots[own_shots["shot_outcome"] == "Goal"]) > 0 if resulted_shot else False
            xg_generated = float(own_shots["shot_statsbomb_xg"].fillna(0).sum()) if resulted_shot else 0.0
            perspective = "recovery"

        if resulted_goal:
            outcome = "goal"
        elif resulted_shot:
            outcome = "shot"
        else:
            outcome = "nothing"

        records.append({
            "match_id": str(match_id),
            "tournament": tournament,
            "team": team,
            "opponent": opponent,
            "minute": int(ev["minute"]),
            "event_type": ev["type"],
            "event_zone": zone,
            "event_x": round(x, 1),
            "event_y": round(loc[1], 1) if isinstance(loc, list) and len(loc) > 1 else None,
            "perspective": perspective,
            "outcome": outcome,
            "resulted_in_shot": resulted_shot,
            "resulted_in_goal": resulted_goal,
            "xg_generated": round(xg_generated, 3),
        })

    return records

if __name__ == "__main__":
    print("=" * 60)
    print("ANÁLISE CONTRAFACTUAL")
    print("=" * 60)

    all_records = []
    for comp_id, season_id, name in TOURNAMENTS:
        matches = sb.matches(competition_id=comp_id, season_id=season_id)
        total = len(matches)
        print(f"\n{name}: {total} jogos")
        for i, (_, row) in enumerate(matches.iterrows(), 1):
            recs = analyze_match(row["match_id"], name, row["home_team"], row["away_team"])
            all_records.extend(recs)
            if i % 20 == 0:
                print(f"  [{i}/{total}]")
        print(f"  [{total}/{total}] ✓")

    df = pd.DataFrame(all_records)
    print(f"\nTotal: {len(df)} eventos contrafactuais")

    # Calcula probabilidades por zona+tipo+perspectiva
    print("\nCalculando probabilidades condicionais...")
    for (zone, etype, persp), group in df.groupby(["event_zone", "event_type", "perspective"]):
        total = len(group)
        n_shot = group["resulted_in_shot"].sum()
        n_goal = group["resulted_in_goal"].sum()
        pct_shot = round(n_shot / total * 100, 1)
        pct_goal = round(n_goal / total * 100, 1)

        mask = (df["event_zone"] == zone) & (df["event_type"] == etype) & (df["perspective"] == persp)
        df.loc[mask, "total_similar"] = total
        df.loc[mask, "pct_resulted_shot"] = pct_shot
        df.loc[mask, "pct_resulted_goal"] = pct_goal
        df.loc[mask, "pct_nothing"] = round(100 - pct_shot, 1)

    # Converte pra int onde necessário
    df["total_similar"] = df["total_similar"].astype(int)

    # Salva CSV
    df.to_csv("counterfactual_events.csv", index=False)
    print(f"✓ counterfactual_events.csv: {len(df)} linhas")

    # Indexa no Elastic
    print("\nIndexando no Elastic...")
    if es.indices.exists(index="counterfactual_events"):
        es.indices.delete(index="counterfactual_events")

    es.indices.create(index="counterfactual_events", body={"mappings": {"properties": {
        "match_id": {"type": "keyword"}, "tournament": {"type": "keyword"},
        "team": {"type": "keyword"}, "opponent": {"type": "keyword"},
        "minute": {"type": "integer"}, "event_type": {"type": "keyword"},
        "event_zone": {"type": "keyword"}, "event_x": {"type": "float"},
        "event_y": {"type": "float"}, "perspective": {"type": "keyword"},
        "outcome": {"type": "keyword"}, "resulted_in_shot": {"type": "boolean"},
        "resulted_in_goal": {"type": "boolean"}, "xg_generated": {"type": "float"},
        "total_similar": {"type": "integer"}, "pct_resulted_shot": {"type": "float"},
        "pct_resulted_goal": {"type": "float"}, "pct_nothing": {"type": "float"},
    }}})

    # Converte NaN pra None
    df = df.where(pd.notna(df), None)
    actions = [{"_index": "counterfactual_events", "_source": row.to_dict()} for _, row in df.iterrows()]
    helpers.bulk(es, actions, raise_on_error=False)
    es.indices.refresh(index="counterfactual_events")
    count = es.count(index="counterfactual_events")
    print(f"✓ {count['count']} eventos indexados")

    # Mostra preview: turnovers do Brasil contra a Croácia
    print("\n" + "=" * 60)
    print("PREVIEW: Brasil perdendo a bola vs Croácia (Copa 2022)")
    print("=" * 60)
    preview = df[
        (df["team"] == "Brazil") & (df["opponent"] == "Croatia")
        & (df["perspective"] == "loss")
    ][["minute", "event_type", "event_zone", "outcome", "total_similar", "pct_resulted_shot", "pct_resulted_goal"]]
    print(preview.to_string(index=False))
