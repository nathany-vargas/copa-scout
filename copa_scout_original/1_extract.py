import os
import pickle
import pandas as pd
from statsbombpy import sb

# Torneios: Copa de 2022 e Copa de 2018
TOURNAMENTS = [
    (43, 106, "FIFA World Cup 2022"),
    (43, 3, "FIFA World Cup 2018"),
]
CACHE_DIR = "cache"

def extract_match_events(match_id: int):
    cache_path = os.path.join(CACHE_DIR, f"{match_id}.pkl")
    if os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            return pickle.load(f)
    events_df = sb.events(match_id=match_id)
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(cache_path, "wb") as f:
        pickle.dump(events_df, f)
    return events_df

def extract_tournaments():
    os.makedirs(CACHE_DIR, exist_ok=True)
    brazil_matches = []
    other_matches = []

    # 1. Puxa os metadados das partidas
    print("Mapeando partidas das Copas 2018 e 2022...")
    for comp_id, season_id, name in TOURNAMENTS:
        matches_df = sb.matches(competition_id=comp_id, season_id=season_id)
        
        # Separa jogos do Brasil para prioridade
        for _, row in matches_df.iterrows():
            match_data = {
                "match_id": row["match_id"],
                "match_date": row["match_date"],
                "home": row["home_team"],
                "away": row["away_team"],
                "tournament": name
            }
            if row["home_team"] == "Brazil" or row["away_team"] == "Brazil":
                brazil_matches.append(match_data)
            else:
                other_matches.append(match_data)

    all_matches = brazil_matches + other_matches
    total = len(all_matches)

    print(f"Total de {total} partidas. Priorizando Brasil...")
    
    # 2. Extrai os eventos
    for i, m in enumerate(all_matches, 1):
        print(f"[{i}/{total}] Extraindo: {m['home']} vs {m['away']} ({m['tournament']})", end="")
        
        cache_path = os.path.join(CACHE_DIR, f"{m['match_id']}.pkl")
        if os.path.exists(cache_path):
            print(" -> (Cache)")
        else:
            try:
                extract_match_events(m["match_id"])
                print(" -> (Download OK)")
            except Exception as e:
                print(f" -> (Erro: {e})")

if __name__ == "__main__":
    extract_tournaments()
    print("\nExtração finalizada! Pode rodar o 2_transform.py")