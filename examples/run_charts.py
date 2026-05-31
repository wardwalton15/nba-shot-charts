"""
Generate:
  1. Knicks 2025-26 hexbin differential charts (gridsize=20)
  2. Karl-Anthony Towns assist shot chart — 2025-26 Playoffs

Run from repo root:
    .venv/bin/python examples/run_charts.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from nba_shot_charts import assist_shot_chart, team_comparison_charts

print("--- Knicks differential charts ---")
team_comparison_charts(
    team_name="Knicks",
    season="2025-26",
    chart_style="hexbin",
    gridsize=20,
    freq_save_path="knicks_freq_diff.png",
    efficiency_save_path="knicks_eff_diff.png",
)
print("Saved knicks_freq_diff.png and knicks_eff_diff.png")

print("\n--- KAT assist shot chart (2025-26 Playoffs) ---")
assist_shot_chart(
    assisting_player_name="Karl-Anthony Towns",
    season="2025-26",
    season_type="Playoffs",
    chart_type="hexbin",
    save_path="kat_assists_playoffs_hexbin.png",
)
print("Saved kat_assists_playoffs_hexbin.png")
