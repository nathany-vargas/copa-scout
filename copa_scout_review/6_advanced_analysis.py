"""6_advanced_analysis.py — Turnovers, Player Impact, Momentum"""
import os
import pickle
import pandas as pd
from statsbombpy import sb
from elasticsearch import helpers
from config import es, CACHE_DIR, TOURNAMENTS

def load_events(match_id):
    path = os.path.join(CACHE_DIR, f"{match_id}.pkl")
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return pickle.load(f)

def analyze_turnovers(events, match_id, tournament, home, away):
    events = events[events["period"] != 5].sort_values("index")
    records = []
    loss_types = ["Dispossessed", "Miscontrol", "Error"]
    for team in [home, away]:
        opponent = away if team == home else home
        losses = events[(events["team"] == team) & (events["type"].isin(loss_types))]
        for _, loss in losses.iterrows():
            loc = loss.get("location")
            loss_x = loc[0] if isinstance(loc, list) else None
            if loss_x is None: continue
            zone = "Terço ofensivo" if loss_x >= 80 else ("Meio-campo" if loss_x >= 40 else "Terço defensivo")
            window = events[(events["period"] == loss["period"]) & (events["index"] > loss["index"])].head(15)
            shots = window[(window["type"] == "Shot") & (window["team"] == opponent)]
            resulted_shot = len(shots) > 0
            resulted_goal = len(shots[shots["shot_outcome"] == "Goal"]) > 0 if resulted_shot else False
            danger = "CRITICO" if resulted_goal else ("PERIGOSO" if resulted_shot else "NORMAL")
            records.append({"match_id": str(match_id), "tournament": tournament, "team": team,
                "opponent": opponent, "minute": int(loss["minute"]), "loss_type": loss["type"],
                "loss_zone": zone, "loss_x": loss_x, "resulted_in_shot": resulted_shot,
                "resulted_in_goal": resulted_goal, "danger_level": danger})
    return records

def analyze_players(events, match_id, tournament, home, away):
    events = events[events["period"] != 5]
    records = []
    for team in [home, away]:
        t = events[events["team"] == team]
        for player in t["player"].dropna().unique():
            p = t[t["player"] == player]
            passes = p[p["type"] == "Pass"]
            shots = p[p["type"] == "Shot"]
            passes_total = len(passes)
            if passes_total + len(shots) + len(p[p["type"] == "Pressure"]) < 5: continue
            goals = len(shots[shots["shot_outcome"] == "Goal"])
            xg = float(shots["shot_statsbomb_xg"].fillna(0).sum())
            pressures = len(p[p["type"] == "Pressure"])
            interceptions = len(p[p["type"] == "Interception"])
            tackles = len(p[(p["type"] == "Duel") & (p["duel_type"] == "Tackle")])
            blocks = len(p[p["type"] == "Block"])
            recoveries = len(p[p["type"] == "Ball Recovery"])
            completed = len(passes[passes["pass_outcome"].isna()])
            dribbles = p[p["type"] == "Dribble"]
            drib_ok = len(dribbles[dribbles["dribble_outcome"] == "Complete"])
            dispos = len(p[p["type"] == "Dispossessed"])
            miscon = len(p[p["type"] == "Miscontrol"])
            impact = goals*20 + xg*5 + completed*0.1 + pressures*0.5 + interceptions*2 + tackles*2 + blocks*3 + recoveries*1.5 + drib_ok*2 - dispos*3 - miscon*2
            pos = p["position"].mode()
            records.append({"match_id": str(match_id), "tournament": tournament, "team": team,
                "player": player, "position": pos.iloc[0] if len(pos) > 0 else "Unknown",
                "passes_completed": completed, "passes_total": passes_total,
                "pass_pct": round(completed/passes_total*100, 1) if passes_total > 0 else 0,
                "shots": len(shots), "goals": goals, "xg": round(xg, 3),
                "pressures": pressures, "interceptions": interceptions, "tackles": tackles,
                "blocks": blocks, "recoveries": recoveries, "dribbles_success": drib_ok,
                "dispossessed": dispos, "miscontrols": miscon, "impact_score": round(impact, 1)})
    return records

def analyze_momentum(events, match_id, tournament, home, away):
    events = events[events["period"] != 5]
    records = []
    max_min = int(events["minute"].max())
    periods = list(range(0, max_min + 1, 15))
    periods.append(max_min + 1)
    for i in range(len(periods) - 1):
        pe = events[(events["minute"] >= periods[i]) & (events["minute"] < periods[i+1])]
        for team in [home, away]:
            opponent = away if team == home else home
            t, o = pe[pe["team"] == team], pe[pe["team"] == opponent]
            all_p = len(pe[pe["type"] == "Pass"])
            poss = round(len(t[t["type"] == "Pass"]) / all_p * 100, 1) if all_p > 0 else 50
            shots = len(t[t["type"] == "Shot"])
            sa = len(o[o["type"] == "Shot"])
            xg = float(t[t["type"] == "Shot"]["shot_statsbomb_xg"].fillna(0).sum())
            records.append({"match_id": str(match_id), "tournament": tournament, "team": team,
                "opponent": opponent, "period_start": periods[i], "period_end": periods[i+1],
                "period_label": f"{periods[i]}-{periods[i+1]} min", "possession_pct": poss,
                "shots": shots, "shots_against": sa, "xg": round(xg, 3),
                "pressures": len(t[t["type"] == "Pressure"]),
                "recoveries": len(t[t["type"] == "Ball Recovery"]),
                "interceptions": len(t[t["type"] == "Interception"]),
                "dominance_score": round(poss*0.3 + shots*5 + len(t[t["type"]=="Pressure"])*0.5 - sa*5, 1)})
    return records

if __name__ == "__main__":
    print("FASE 6: ANÁLISES AVANÇADAS")
    all_t, all_p, all_m = [], [], []
    for comp_id, season_id, name in TOURNAMENTS:
        matches = sb.matches(competition_id=comp_id, season_id=season_id)
        print(f"\n{name}: {len(matches)} jogos")
        for i, (_, row) in enumerate(matches.iterrows(), 1):
            ev = load_events(row["match_id"])
            if ev is None: continue
            all_t.extend(analyze_turnovers(ev, row["match_id"], name, row["home_team"], row["away_team"]))
            all_p.extend(analyze_players(ev, row["match_id"], name, row["home_team"], row["away_team"]))
            all_m.extend(analyze_momentum(ev, row["match_id"], name, row["home_team"], row["away_team"]))
            if i % 20 == 0: print(f"  [{i}/{len(matches)}]")
        print(f"  [{len(matches)}/{len(matches)}] ✓")

    pd.DataFrame(all_t).to_csv("turnovers.csv", index=False)
    pd.DataFrame(all_p).to_csv("player_impact.csv", index=False)
    pd.DataFrame(all_m).to_csv("match_momentum.csv", index=False)
    print(f"\n✓ turnovers: {len(all_t)} | players: {len(all_p)} | momentum: {len(all_m)}")

    indices = {
        "turnovers": (all_t, {"match_id":"keyword","tournament":"keyword","team":"keyword","opponent":"keyword","minute":"integer","loss_type":"keyword","loss_zone":"keyword","loss_x":"float","resulted_in_shot":"boolean","resulted_in_goal":"boolean","danger_level":"keyword"}),
        "player_impact": (all_p, {"match_id":"keyword","tournament":"keyword","team":"keyword","player":"keyword","position":"keyword","passes_completed":"integer","passes_total":"integer","pass_pct":"float","shots":"integer","goals":"integer","xg":"float","pressures":"integer","interceptions":"integer","tackles":"integer","blocks":"integer","recoveries":"integer","dribbles_success":"integer","dispossessed":"integer","miscontrols":"integer","impact_score":"float"}),
        "match_momentum": (all_m, {"match_id":"keyword","tournament":"keyword","team":"keyword","opponent":"keyword","period_start":"integer","period_end":"integer","period_label":"keyword","possession_pct":"float","shots":"integer","shots_against":"integer","xg":"float","pressures":"integer","recoveries":"integer","interceptions":"integer","dominance_score":"float"}),
    }
    for name, (data, props) in indices.items():
        if es.indices.exists(index=name): es.indices.delete(index=name)
        es.indices.create(index=name, body={"mappings": {"properties": {k: {"type": v} for k, v in props.items()}}})
        if data: helpers.bulk(es, [{"_index": name, "_source": d} for d in data], raise_on_error=False)
        es.indices.refresh(index=name)
        print(f"  ✓ {name}: {es.count(index=name)['count']} docs")
