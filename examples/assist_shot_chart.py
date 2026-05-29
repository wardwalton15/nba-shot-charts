"""
Nikola Jokic assist shot chart — 2025-26 Regular Season.
Shows where shots assisted by Jokic came from.

WARNING: First run fetches data for every game in the season (~3 min).
Subsequent runs load from cache and complete in seconds.

Run from the repo root:
    python examples/assist_shot_chart.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from nba_shot_charts import assist_shot_chart

assist_shot_chart(
    assisting_player_name="Nikola Jokic",
    season="2025-26",
    season_type="Regular Season",
    chart_type="scatter",
    color_by="made",
    save_path="jokic_assists_scatter.png",
)
print("Saved jokic_assists_scatter.png")

assist_shot_chart(
    assisting_player_name="Nikola Jokic",
    season="2025-26",
    season_type="Regular Season",
    chart_type="hexbin",
    save_path="jokic_assists_hexbin.png",
)
print("Saved jokic_assists_hexbin.png")
