"""
"Guess the player" season shot charts for TikTok: 1080x1920, no name, headshot,
team or dates on the image.

Files are numbered rather than named so the filename doesn't give the answer away:
  mystery_1_2026-27.png ... mystery_4_2026-27.png
The key is printed to the terminal.

Run from the repo root:
    .venv/bin/python examples/mystery_player_charts.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from nba_shot_charts import mystery_player_shot_chart

PLAYERS = ["Joel Embiid", "Luka Doncic", "Deni Avdija", "Rudy Gobert"]

for i, name in enumerate(PLAYERS, 1):
    path = f"mystery_{i}_2026-27.png"
    mystery_player_shot_chart(name, season="2026-27", credit="WARD WALTON",
                              refresh=True, save_path=path)
    print(f"Saved {path}  ({name})")
