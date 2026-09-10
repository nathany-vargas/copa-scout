"""
3_load.py — Indexação no Elasticsearch

Lê os CSVs gerados pelo 2_transform.py e indexa no Elastic Cloud.
Cria 2 índices:
  1. match_stats    — uma linha por time por partida
  2. team_profiles  — stats agregados por time por torneio
"""

import pandas as pd
from elasticsearch import Elasticsearch, helpers

# ============================================================
# CONEXÃO
# ============================================================

es = Elasticsearch(
    cloud_id="chavinha_expirada",
    api_key="chavinha_expirada"
)

# ============================================================
# MAPPINGS
# ============================================================

MATCH_STATS_MAPPING = {
    "mappings": {
        "properties": {
            # Identificação
            "match_id": {"type": "keyword"},
            "match_date": {"type": "date"},
            "tournament": {"type": "keyword"},
            "stage": {"type": "keyword"},
            "team": {"type": "keyword"},
            "opponent": {"type": "keyword"},
            "home_team": {"type": "keyword"},
            "away_team": {"type": "keyword"},
            "score_home": {"type": "integer"},
            "score_away": {"type": "integer"},
            "result": {"type": "keyword"},
            "minutes_played": {"type": "integer"},

            # Defesa
            "pressures": {"type": "integer"},
            "interceptions": {"type": "integer"},
            "tackles": {"type": "integer"},
            "blocks": {"type": "integer"},
            "clearances": {"type": "integer"},
            "ball_recoveries": {"type": "integer"},
            "fouls_won": {"type": "integer"},
            "total_defensive_actions": {"type": "integer"},

            # Ataque
            "goals_scored": {"type": "integer"},
            "shots_for": {"type": "integer"},
            "shots_on_target_for": {"type": "integer"},
            "xg_for": {"type": "float"},

            # Ameaça sofrida
            "goals_conceded": {"type": "integer"},
            "shots_against": {"type": "integer"},
            "shots_on_target_against": {"type": "integer"},
            "xg_against": {"type": "float"},
            "xg_diff": {"type": "float"},

            # Posse e passe
            "possession_pct": {"type": "float"},
            "pass_completion_pct": {"type": "float"},

            # Zonas defensivas
            "def_own_third_pct": {"type": "float"},
            "def_mid_third_pct": {"type": "float"},
            "def_final_third_pct": {"type": "float"},

            # Índice de Sobrevivência
            "survival_index": {"type": "float"},
            "survival_index_norm": {"type": "float"},
            "survival_class": {"type": "keyword"},

            # Narrativa
            "narrative": {"type": "text"},
        }
    }
}

TEAM_PROFILES_MAPPING = {
    "mappings": {
        "properties": {
            "team": {"type": "keyword"},
            "tournament": {"type": "keyword"},
            "matches": {"type": "integer"},
            "avg_possession": {"type": "float"},
            "avg_pass_pct": {"type": "float"},
            "total_goals": {"type": "integer"},
            "total_goals_conceded": {"type": "integer"},
            "avg_xg": {"type": "float"},
            "avg_xg_against": {"type": "float"},
            "avg_shots": {"type": "float"},
            "avg_shots_against": {"type": "float"},
            "avg_pressures": {"type": "float"},
            "avg_interceptions": {"type": "float"},
            "avg_tackles": {"type": "float"},
            "avg_blocks": {"type": "float"},
            "avg_survival_index": {"type": "float"},
            "avg_def_own_third": {"type": "float"},
            "avg_def_mid_third": {"type": "float"},
        }
    }
}

# ============================================================
# FUNÇÕES
# ============================================================

def create_index(index_name: str, mapping: dict):
    """Cria índice. Se já existir, deleta e recria."""
    if es.indices.exists(index=index_name):
        print(f"  Deletando índice existente: {index_name}")
        es.indices.delete(index=index_name)

    es.indices.create(index=index_name, body=mapping)
    print(f"  ✓ Índice criado: {index_name}")


def bulk_index(index_name: str, df: pd.DataFrame):
    """Indexa DataFrame no Elastic via bulk."""
    # Converte NaN pra None (Elastic não aceita NaN)
    df = df.where(pd.notna(df), None)

    actions = [
        {"_index": index_name, "_source": row.to_dict()}
        for _, row in df.iterrows()
    ]

    success, errors = helpers.bulk(es, actions, raise_on_error=False)
    print(f"  ✓ {success} documentos indexados em '{index_name}'")
    if errors:
        print(f"  ⚠ {len(errors)} erros:")
        for e in errors[:3]:
            print(f"    {e}")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("FASE 3: INDEXAÇÃO NO ELASTICSEARCH")
    print("=" * 60)

    # Testa conexão
    print("\nTestando conexão...")
    info = es.info()
    print(f"  ✓ Conectado ao cluster: {info['cluster_name']}")
    print(f"  ✓ Versão: {info['version']['number']}")

    # Carrega CSVs
    print("\nCarregando CSVs...")
    try:
        match_stats = pd.read_csv("match_stats.csv")
        print(f"  ✓ match_stats.csv: {len(match_stats)} linhas")
    except FileNotFoundError:
        print("  ✗ match_stats.csv não encontrado! Rode 2_transform.py primeiro.")
        exit(1)

    try:
        team_profiles = pd.read_csv("team_profiles.csv")
        print(f"  ✓ team_profiles.csv: {len(team_profiles)} linhas")
    except FileNotFoundError:
        print("  ⚠ team_profiles.csv não encontrado, pulando...")
        team_profiles = None

    # Cria e popula índices
    print("\nCriando índices...")
    create_index("match_stats", MATCH_STATS_MAPPING)
    if team_profiles is not None:
        create_index("team_profiles", TEAM_PROFILES_MAPPING)

    print("\nIndexando dados...")
    bulk_index("match_stats", match_stats)
    if team_profiles is not None:
        bulk_index("team_profiles", team_profiles)

    # Validação
    print("\nValidação:")
    es.indices.refresh(index="match_stats")
    count = es.count(index="match_stats")
    print(f"  match_stats: {count['count']} documentos")

    if team_profiles is not None:
        es.indices.refresh(index="team_profiles")
        count = es.count(index="team_profiles")
        print(f"  team_profiles: {count['count']} documentos")

    print("\nIndexação concluída! Agora configure o Agent Builder no Kibana.")
    print(f"KIBANA_URL: acesse pelo cloud.elastic.co → Open Kibana")