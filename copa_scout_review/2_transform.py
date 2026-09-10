"""
2_transform.py — Processamento e cálculo de métricas

Lê os eventos cacheados pelo 1_extract.py e gera:
  1. match_stats.csv    — uma linha por time por partida (2 linhas por jogo)
  2. team_profiles.csv  — stats agregados por time por torneio
  
Ambos os CSVs servem de fallback pro frontend e são indexados no Elastic.
"""

import os
import pickle
import pandas as pd
from statsbombpy import sb

CACHE_DIR = "cache"

TOURNAMENTS = [
    (43, 106, "FIFA World Cup 2022"),
    (43, 3, "FIFA World Cup 2018"),
]

# ============================================================
# FUNÇÕES DE CÁLCULO
# ============================================================

def count_defensive_actions(events_df: pd.DataFrame, team: str) -> dict:
    
    #evitar a contagem errada de gols (partida normal + penaltis nao vai mais ocorrer)
    if "period" in events_df.columns:
        events_df = events_df[events_df["period"] != 5]
    t = events_df[events_df["team"] == team]
    """Conta ações defensivas de um time numa partida."""
    t = events_df[events_df["team"] == team]

    pressures     = len(t[t["type"] == "Pressure"])
    interceptions = len(t[t["type"] == "Interception"])
    blocks        = len(t[t["type"] == "Block"])
    clearances    = len(t[t["type"] == "Clearance"])
    ball_recoveries = len(t[t["type"] == "Ball Recovery"])
    fouls_won     = len(t[t["type"] == "Foul Won"])

    # Tackles são Duel com duel_type == 'Tackle'
    duels = t[t["type"] == "Duel"]
    tackles = len(duels[duels["duel_type"] == "Tackle"])

    return {
        "pressures": pressures,
        "interceptions": interceptions,
        "tackles": tackles,
        "blocks": blocks,
        "clearances": clearances,
        "ball_recoveries": ball_recoveries,
        "fouls_won": fouls_won,
        "total_defensive_actions": pressures + interceptions + tackles + blocks + clearances + ball_recoveries,
    }


def count_threat(events_df: pd.DataFrame, team: str) -> dict:
    # Exclui penalty shootout (period == 5) importante pra evitar dizer que o brasil sofreu 5 gols da croacia
    events_filtered = events_df[events_df["period"] != 5] if "period" in events_df.columns else events_df
    shots = events_filtered[(events_filtered["type"] == "Shot") & (events_filtered["team"] == team)]
    
    """Mede a ameaça ofensiva de um time (chutes, gols, xG)."""

    total_shots = len(shots)
    goals = len(shots[shots["shot_outcome"] == "Goal"])

    on_target_outcomes = ["Goal", "Saved", "Saved to Post"]
    shots_on_target = len(shots[shots["shot_outcome"].isin(on_target_outcomes)])

    xg = shots["shot_statsbomb_xg"].fillna(0).sum()

    return {
        "shots": total_shots,
        "shots_on_target": shots_on_target,
        "goals": goals,
        "xg": round(xg, 3),
    }


def calculate_zone_distribution(events_df: pd.DataFrame, team: str) -> dict:
    """Calcula % de ações defensivas por zona do campo."""
    defensive_types = ["Pressure", "Block", "Interception", "Clearance", "Duel", "Ball Recovery"]

    t = events_df[(events_df["team"] == team) & (events_df["type"].isin(defensive_types))]
    t = t.dropna(subset=["location"])

    if len(t) == 0:
        return {
            "def_own_third_pct": 0.0,
            "def_mid_third_pct": 0.0,
            "def_final_third_pct": 0.0,
        }

    x_coords = t["location"].apply(lambda loc: loc[0])
    total = len(x_coords)

    own_third   = len(x_coords[x_coords < 40])
    mid_third   = len(x_coords[(x_coords >= 40) & (x_coords < 80)])
    final_third = len(x_coords[x_coords >= 80])

    return {
        "def_own_third_pct": round(own_third / total * 100, 1),
        "def_mid_third_pct": round(mid_third / total * 100, 1),
        "def_final_third_pct": round(final_third / total * 100, 1),
    }


def calculate_possession_proxy(events_df: pd.DataFrame, team: str) -> float:
    """
    Proxy de posse: passes do time / total de passes × 100.
    Não é perfeito mas é o que dá pra fazer sem dados de tracking.
    """
    all_passes = events_df[events_df["type"] == "Pass"]
    if len(all_passes) == 0:
        return 50.0

    team_passes = len(all_passes[all_passes["team"] == team])
    return round(team_passes / len(all_passes) * 100, 1)


def calculate_pass_completion(events_df: pd.DataFrame, team: str) -> float:
    """% de passes completos (sem outcome = completo no StatsBomb)."""
    passes = events_df[(events_df["type"] == "Pass") & (events_df["team"] == team)]
    if len(passes) == 0:
        return 0.0

    completed = len(passes[passes["pass_outcome"].isna()])
    return round(completed / len(passes) * 100, 1)


def calculate_survival_index(defensive: dict, opponent_threat: dict) -> float:
    """
    IS = (pressures×1) + (interceptions×2) + (tackles×2) +
         (blocks×2.5) + (clearances×1) + (recoveries×1.5) -
         (goals_conceded×10) - (shots_on_target_against×3)
    """
    is_score = (
        defensive["pressures"] * 1.0
        + defensive["interceptions"] * 2.0
        + defensive["tackles"] * 2.0
        + defensive["blocks"] * 2.5
        + defensive["clearances"] * 1.0
        + defensive["ball_recoveries"] * 1.5
        - opponent_threat["goals"] * 10
        - opponent_threat["shots_on_target"] * 3
    )
    return round(is_score, 1)


def classify_survival(is_normalized: float) -> str:
    if is_normalized > 120:
        return "Fortaleza Impenetrável"
    elif is_normalized > 80:
        return "Muro Sólido"
    elif is_normalized > 50:
        return "Resistência Competitiva"
    elif is_normalized > 20:
        return "Sobrevivência Precária"
    else:
        return "Defesa Colapsada"


# ============================================================
# PROCESSAMENTO POR PARTIDA
# ============================================================

def process_team_in_match(events_df: pd.DataFrame, team: str, opponent: str) -> dict:
    """
    Calcula TODAS as métricas de um time numa partida.
    Retorna um dict plano com todos os campos.
    """
    if "period" in events_df.columns:
        events_df = events_df[events_df["period"] != 5]
    defensive = count_defensive_actions(events_df, team)
    own_threat = count_threat(events_df, team)
    opp_threat = count_threat(events_df, opponent)
    zones = calculate_zone_distribution(events_df, team)
    possession = calculate_possession_proxy(events_df, team)
    pass_pct = calculate_pass_completion(events_df, team)

    # Survival Index (defesa do time vs ataque do adversário)
    survival = calculate_survival_index(defensive, opp_threat)

    # Minutos jogados
    max_minute = events_df["minute"].max()
    minutes_played = max(max_minute, 90)

    # Normaliza por 90 min
    survival_norm = round(survival * (90 / minutes_played), 1)
    classification = classify_survival(survival_norm)

    # xG diferença
    xg_diff = round(own_threat["xg"] - opp_threat["xg"], 3)

    record = {
        # Identificação
        "team": team,
        "opponent": opponent,
        "minutes_played": minutes_played,

        # Defesa
        **defensive,

        # Ataque próprio
        "goals_scored": own_threat["goals"],
        "shots_for": own_threat["shots"],
        "shots_on_target_for": own_threat["shots_on_target"],
        "xg_for": own_threat["xg"],

        # Ameaça sofrida
        "goals_conceded": opp_threat["goals"],
        "shots_against": opp_threat["shots"],
        "shots_on_target_against": opp_threat["shots_on_target"],
        "xg_against": opp_threat["xg"],
        "xg_diff": xg_diff,

        # Posse e passe
        "possession_pct": possession,
        "pass_completion_pct": pass_pct,

        # Zonas
        **zones,

        # Índice de Sobrevivência
        "survival_index": survival,
        "survival_index_norm": survival_norm,
        "survival_class": classification,
    }

    # Breakdown do IS: o que ajudou e o que prejudicou
    contributions = {
        "Pressões": defensive["pressures"] * 1.0,
        "Interceptações": defensive["interceptions"] * 2.0,
        "Desarmes": defensive["tackles"] * 2.0,
        "Bloqueios": defensive["blocks"] * 2.5,
        "Cortes": defensive["clearances"] * 1.0,
        "Recuperações": defensive["ball_recoveries"] * 1.5,
        "Gols sofridos": opp_threat["goals"] * -10,
        "Chutes no gol sofridos": opp_threat["shots_on_target"] * -3,
    }

    sorted_pos = sorted([(k, v) for k, v in contributions.items() if v > 0], key=lambda x: -x[1])
    sorted_neg = sorted([(k, v) for k, v in contributions.items() if v < 0], key=lambda x: x[1])

    record["is_top_strength"] = f"{sorted_pos[0][0]} (+{sorted_pos[0][1]:.0f}pts)" if sorted_pos else "Nenhum"
    record["is_second_strength"] = f"{sorted_pos[1][0]} (+{sorted_pos[1][1]:.0f}pts)" if len(sorted_pos) > 1 else "Nenhum"
    record["is_top_weakness"] = f"{sorted_neg[0][0]} ({sorted_neg[0][1]:.0f}pts)" if sorted_neg else "Nenhum"
    record["is_second_weakness"] = f"{sorted_neg[1][0]} ({sorted_neg[1][1]:.0f}pts)" if len(sorted_neg) > 1 else "Nenhum"

    return record


def build_match_narrative(record) -> str:
    if record["team"] == record["home_team"]:
        my_goals, their_goals = record["score_home"], record["score_away"]
    else:
        my_goals, their_goals = record["score_away"], record["score_home"]
    return (
        f"{record['team']} enfrentou {record['opponent']} na {record['stage']} do {record['tournament']}. "
        f"Resultado: {my_goals}-{their_goals}. "
        f"{record['team']} teve {record['possession_pct']:.0f}% de posse, "
        f"{record['shots_for']} chutes ({record['xg_for']} xG) "
        f"e sofreu {record['shots_against']} chutes ({record['xg_against']} xG contra). "
        f"Índice de Sobrevivência: {record['survival_index_norm']} ({record['survival_class']})."
    )


def process_match(match_id: int, match_meta: dict) -> list:
    """
    Processa uma partida completa.
    Retorna lista com 2 dicts (um por time).
    """
    cache_path = os.path.join(CACHE_DIR, f"{match_id}.pkl")
    if not os.path.exists(cache_path):
        print(f"  ⚠ Cache não encontrado: {match_id}")
        return []

    with open(cache_path, "rb") as f:
        events_df = pickle.load(f)

    home = match_meta["home_team"]
    away = match_meta["away_team"]

    results = []
    for team, opponent in [(home, away), (away, home)]:
        record = process_team_in_match(events_df, team, opponent)

        # Adiciona metadata da partida
        record["match_id"] = match_id
        record["match_date"] = str(match_meta["match_date"])
        record["tournament"] = match_meta["tournament"]
        record["stage"] = match_meta["competition_stage"]
        record["home_team"] = home
        record["away_team"] = away
        record["score_home"] = match_meta["home_score"]
        record["score_away"] = match_meta["away_score"]

        # Resultado do ponto de vista desse time
        if team == home:
            my_goals, their_goals = match_meta["home_score"], match_meta["away_score"]
        else:
            my_goals, their_goals = match_meta["away_score"], match_meta["home_score"]

        if my_goals > their_goals:
            record["result"] = "Vitória"
        elif my_goals < their_goals:
            record["result"] = "Derrota"
        else:
            record["result"] = "Empate"

        # Narrativa simples
        record["narrative"] = build_match_narrative(record)

        results.append(record)

    return results


# ============================================================
# AGREGAÇÃO POR TIME (TEAM PROFILES)
# ============================================================

def build_team_profiles(match_stats_df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega stats por time por torneio.
    Uma linha por seleção por torneio.
    """
    grouped = match_stats_df.groupby(["team", "tournament"]).agg(
        matches=("match_id", "count"),
        avg_possession=("possession_pct", "mean"),
        avg_pass_pct=("pass_completion_pct", "mean"),
        total_goals=("goals_scored", "sum"),
        total_goals_conceded=("goals_conceded", "sum"),
        avg_xg=("xg_for", "mean"),
        avg_xg_against=("xg_against", "mean"),
        avg_shots=("shots_for", "mean"),
        avg_shots_against=("shots_against", "mean"),
        avg_pressures=("pressures", "mean"),
        avg_interceptions=("interceptions", "mean"),
        avg_tackles=("tackles", "mean"),
        avg_blocks=("blocks", "mean"),
        avg_survival_index=("survival_index_norm", "mean"),
        avg_def_own_third=("def_own_third_pct", "mean"),
        avg_def_mid_third=("def_mid_third_pct", "mean"),
    ).reset_index()

    # Arredonda tudo
    numeric_cols = grouped.select_dtypes(include=["float64"]).columns
    grouped[numeric_cols] = grouped[numeric_cols].round(2)

    return grouped


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("FASE 2: TRANSFORMAÇÃO E CÁLCULO DE MÉTRICAS")
    print("=" * 60)

    all_records = []

    for comp_id, season_id, tournament_name in TOURNAMENTS:
        print(f"\nProcessando: {tournament_name}")

        matches_df = sb.matches(competition_id=comp_id, season_id=season_id)
        total = len(matches_df)

        for i, (_, row) in enumerate(matches_df.iterrows(), 1):
            mid = row["match_id"]
            home = row["home_team"]
            away = row["away_team"]
            print(f"  [{i}/{total}] {home} vs {away}", end="")

            match_meta = {
                "home_team": home,
                "away_team": away,
                "home_score": row["home_score"],
                "away_score": row["away_score"],
                "match_date": row["match_date"],
                "competition_stage": row["competition_stage"],
                "tournament": tournament_name,
            }

            records = process_match(mid, match_meta)
            if records:
                all_records.extend(records)
                print(f" ✓ (IS: {records[0]['survival_index_norm']} / {records[1]['survival_index_norm']})")
            else:
                print(" ✗ (sem cache)")

    # Monta DataFrame principal
    match_stats_df = pd.DataFrame(all_records)
    
    # Normaliza IS pra 0-100 (min-max)
    is_col = match_stats_df["survival_index_norm"]
    is_min = is_col.min()
    is_max = is_col.max()
    match_stats_df["survival_index_norm"] = ((is_col - is_min) / (is_max - is_min) * 100).round(1)

    # Reclassifica
    match_stats_df["survival_class"] = match_stats_df["survival_index_norm"].apply(
        lambda x: "Fortaleza Impenetrável" if x > 85
        else "Muro Sólido" if x > 65
        else "Resistência Competitiva" if x > 40
        else "Sobrevivência Precária" if x > 20
        else "Defesa Colapsada"
    )

    match_stats_df["narrative"] = match_stats_df.apply(build_match_narrative, axis=1)

    # Salva CSV (fallback pro frontend)
    match_stats_df.to_csv("match_stats.csv", index=False)
    print(f"\n✓ match_stats.csv salvo: {len(match_stats_df)} linhas")

    # Agrega por time
    team_profiles_df = build_team_profiles(match_stats_df)
    team_profiles_df.to_csv("team_profiles.csv", index=False)
    print(f"✓ team_profiles.csv salvo: {len(team_profiles_df)} linhas")

    # Mostra prévia do Brasil
    print("\n" + "=" * 60)
    print("PRÉVIA: BRASIL NA COPA 2022")
    print("=" * 60)
    brazil = match_stats_df[
        (match_stats_df["team"] == "Brazil")
        & (match_stats_df["tournament"] == "FIFA World Cup 2022")
    ][["opponent", "result", "goals_scored", "goals_conceded", "xg_for", "xg_against", "possession_pct", "survival_index_norm", "survival_class"]]
    print(brazil.to_string(index=False))

    print("\nTransformação concluída! Rode 3_load.py em seguida.")
