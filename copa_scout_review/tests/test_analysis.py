import ast
import pickle
import tempfile
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def load_analysis(filename):
    tree = ast.parse((ROOT / filename).read_text(encoding="utf-8"))
    tree.body = [
        node for node in tree.body
        if not isinstance(node, ast.If)
        and not (isinstance(node, ast.ImportFrom) and node.module in {"config", "statsbombpy", "elasticsearch"})
    ]
    namespace = {"CACHE_DIR": str(ROOT.parent / "copa_scout_original" / "cache")}
    exec(compile(tree, str(ROOT / filename), "exec"), namespace)
    return namespace


def events(rows):
    defaults = {
        "index": 1, "period": 1, "minute": 0, "second": 0,
        "team": "Brazil", "type": "Pass", "player": "Player",
        "position": "Forward", "location": [60, 40], "possession": 1,
        "shot_outcome": None, "shot_statsbomb_xg": 0.0,
        "pass_outcome": None, "duel_type": None, "dribble_outcome": None,
    }
    return pd.DataFrame([defaults | row for row in rows])


class AnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.transform = load_analysis("2_transform.py")
        cls.goals = load_analysis("5_goal_chains.py")
        cls.advanced = load_analysis("6_advanced_analysis.py")
        cls.counterfactual = load_analysis("7_contrafactual.py")

    def test_shootouts_excluded_but_in_match_penalties_retained(self):
        frame = events([
            {"type": "Shot", "shot_outcome": "Goal", "shot_statsbomb_xg": 0.76, "shot_type": "Penalty"},
            {"type": "Shot", "period": 4, "shot_outcome": "Saved", "shot_statsbomb_xg": 0.2},
            {"type": "Shot", "period": 5, "shot_outcome": "Goal", "shot_statsbomb_xg": 0.76},
            {"type": "Shot", "team": "Croatia", "shot_outcome": "Goal", "shot_statsbomb_xg": 0.1},
        ])
        self.assertEqual(self.transform["count_threat"](frame, "Brazil"),
                         {"shots": 2, "shots_on_target": 2, "goals": 1, "xg": 0.96})

    def test_threat_without_period_column(self):
        frame = events([{"type": "Shot", "shot_outcome": "Goal", "shot_statsbomb_xg": 0.3}]).drop(columns="period")
        self.assertEqual(self.transform["count_threat"](frame, "Brazil")["goals"], 1)

    def test_shootouts_do_not_extend_playing_time(self):
        frame = events([{"minute": 120, "period": 4}, {"minute": 130, "period": 5}])
        result = self.transform["process_team_in_match"](frame, "Brazil", "Croatia")
        self.assertEqual(result["minutes_played"], 120)

    def test_turnover_uses_next_events_in_match_order(self):
        frame = events([
            {"index": 1, "type": "Dispossessed"},
            {"index": 2, "type": "Shot", "team": "Croatia", "shot_outcome": "Goal"},
            *[{"index": i, "second": i} for i in range(3, 20)],
        ]).sort_values("type")
        result = self.advanced["analyze_turnovers"](frame, 1, "Cup", "Brazil", "Croatia")
        self.assertTrue(result[0]["resulted_in_goal"])

    def test_turnover_does_not_cross_period_boundary(self):
        frame = events([
            {"index": 1, "type": "Dispossessed", "minute": 45},
            {"index": 2, "type": "Shot", "team": "Croatia", "period": 2, "minute": 45, "second": 1, "shot_outcome": "Goal"},
        ])
        result = self.advanced["analyze_turnovers"](frame, 1, "Cup", "Brazil", "Croatia")
        self.assertFalse(result[0]["resulted_in_shot"])

    def test_momentum_includes_event_at_last_interval_boundary(self):
        frame = events([{"type": "Shot", "minute": 90, "shot_statsbomb_xg": 0.3},
                        {"type": "Shot", "period": 5, "minute": 125, "shot_statsbomb_xg": 0.76}])
        result = self.advanced["analyze_momentum"](frame, 1, "Cup", "Brazil", "Croatia")
        self.assertEqual(sum(row["shots"] for row in result), 1)
        self.assertEqual(max(row["period_end"] for row in result), 91)

    def test_player_impact_excludes_shootouts(self):
        frame = events([*[{} for _ in range(5)],
                        {"type": "Shot", "shot_outcome": "Goal", "shot_statsbomb_xg": 0.2},
                        {"type": "Shot", "period": 5, "shot_outcome": "Goal", "shot_statsbomb_xg": 0.76}])
        result = self.advanced["analyze_players"](frame, 1, "Cup", "Brazil", "Croatia")
        self.assertEqual((result[0]["goals"], result[0]["shots"], result[0]["xg"]), (1, 1, 0.2))

    def test_counterfactual_window_respects_sequence_period_and_30_seconds(self):
        for shot, expected in [
            ({"index": 2, "second": 0}, True),
            ({"index": 0, "second": 0}, False),
            ({"index": 2, "period": 2, "second": 1}, False),
            ({"index": 2, "second": 30}, True),
            ({"index": 2, "second": 31}, False),
        ]:
            with self.subTest(shot=shot), tempfile.TemporaryDirectory() as directory:
                frame = events([{"type": "Dispossessed"},
                                {"type": "Shot", "team": "Croatia", "shot_outcome": "Goal"} | shot])
                frame.to_pickle(Path(directory) / "1.pkl")
                previous = self.counterfactual["CACHE_DIR"]
                try:
                    self.counterfactual["CACHE_DIR"] = directory
                    result = self.counterfactual["analyze_match"](1, "Cup", "Brazil", "Croatia")
                finally:
                    self.counterfactual["CACHE_DIR"] = previous
                self.assertEqual(result[0]["resulted_in_goal"], expected)

    def test_saved_narratives_use_final_survival_scale(self):
        frame = pd.read_csv(ROOT / "match_stats.csv")
        for record in frame.to_dict("records"):
            self.assertEqual(record["narrative"], self.transform["build_match_narrative"](record))

    def test_brazil_croatia_cached_match(self):
        cache = ROOT.parent / "copa_scout_original" / "cache"
        with (cache / "3869420.pkl").open("rb") as source:
            frame = pickle.load(source)
        for team in ["Brazil", "Croatia"]:
            self.assertEqual(self.transform["count_threat"](frame, team)["goals"], 1)
        self.assertEqual(len(self.goals["process_match_goals"](3869420, "FIFA World Cup 2022")), 2)


if __name__ == "__main__":
    unittest.main()
