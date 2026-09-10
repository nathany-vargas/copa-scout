"""3_load.py — Indexação no Elasticsearch"""
import pandas as pd
from elasticsearch import helpers
from config import es

MATCH_STATS_MAPPING = {
    "mappings": {"properties": {
        "match_id": {"type": "keyword"}, "match_date": {"type": "date"},
        "tournament": {"type": "keyword"}, "stage": {"type": "keyword"},
        "team": {"type": "keyword"}, "opponent": {"type": "keyword"},
        "home_team": {"type": "keyword"}, "away_team": {"type": "keyword"},
        "score_home": {"type": "integer"}, "score_away": {"type": "integer"},
        "result": {"type": "keyword"}, "minutes_played": {"type": "integer"},
        "pressures": {"type": "integer"}, "interceptions": {"type": "integer"},
        "tackles": {"type": "integer"}, "blocks": {"type": "integer"},
        "clearances": {"type": "integer"}, "ball_recoveries": {"type": "integer"},
        "fouls_won": {"type": "integer"}, "total_defensive_actions": {"type": "integer"},
        "goals_scored": {"type": "integer"}, "shots_for": {"type": "integer"},
        "shots_on_target_for": {"type": "integer"}, "xg_for": {"type": "float"},
        "goals_conceded": {"type": "integer"}, "shots_against": {"type": "integer"},
        "shots_on_target_against": {"type": "integer"}, "xg_against": {"type": "float"},
        "xg_diff": {"type": "float"}, "possession_pct": {"type": "float"},
        "pass_completion_pct": {"type": "float"},
        "def_own_third_pct": {"type": "float"}, "def_mid_third_pct": {"type": "float"},
        "def_final_third_pct": {"type": "float"},
        "survival_index": {"type": "float"}, "survival_index_norm": {"type": "float"},
        "survival_class": {"type": "keyword"}, "narrative": {"type": "text"},
    }}
}

TEAM_PROFILES_MAPPING = {
    "mappings": {"properties": {
        "team": {"type": "keyword"}, "tournament": {"type": "keyword"},
        "matches": {"type": "integer"}, "avg_possession": {"type": "float"},
        "avg_pass_pct": {"type": "float"}, "total_goals": {"type": "integer"},
        "total_goals_conceded": {"type": "integer"}, "avg_xg": {"type": "float"},
        "avg_xg_against": {"type": "float"}, "avg_shots": {"type": "float"},
        "avg_shots_against": {"type": "float"}, "avg_pressures": {"type": "float"},
        "avg_interceptions": {"type": "float"}, "avg_tackles": {"type": "float"},
        "avg_blocks": {"type": "float"}, "avg_survival_index": {"type": "float"},
        "avg_def_own_third": {"type": "float"}, "avg_def_mid_third": {"type": "float"},
    }}
}

def create_index(index_name, mapping):
    if es.indices.exists(index=index_name):
        es.indices.delete(index=index_name)
    es.indices.create(index=index_name, body=mapping)
    print(f"  ✓ Índice criado: {index_name}")

def bulk_index(index_name, df):
    df = df.where(pd.notna(df), None)
    actions = [{"_index": index_name, "_source": row.to_dict()} for _, row in df.iterrows()]
    success, errors = helpers.bulk(es, actions, raise_on_error=False)
    print(f"  ✓ {success} documentos em '{index_name}'")
    if errors:
        for e in errors[:3]: print(f"    ⚠ {e}")

if __name__ == "__main__":
    print("FASE 3: INDEXAÇÃO")
    print(f"  Conexão: {es.info()['cluster_name']}")

    match_stats = pd.read_csv("match_stats.csv")
    team_profiles = pd.read_csv("team_profiles.csv")
    print(f"  match_stats: {len(match_stats)} linhas | team_profiles: {len(team_profiles)} linhas")

    create_index("match_stats", MATCH_STATS_MAPPING)
    create_index("team_profiles", TEAM_PROFILES_MAPPING)
    bulk_index("match_stats", match_stats)
    bulk_index("team_profiles", team_profiles)

    es.indices.refresh(index="match_stats,team_profiles")
    print(f"  Validação: {es.count(index='match_stats')['count']} + {es.count(index='team_profiles')['count']} docs")