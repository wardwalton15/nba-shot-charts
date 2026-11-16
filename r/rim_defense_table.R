# Stingiest rim protectors: lowest opponent FG% on shots within 6 ft where the
# player was the closest defender (NBA player tracking).
#
# Run from repo root after exporting the data:
#   .venv/bin/python examples/export_r_table_data.py
#   Rscript r/rim_defense_table.R              # defaults: 2026-27, min 45 shots defended, top 10
#   Rscript r/rim_defense_table.R 2026-27 60 15

source("r/gt_helpers.R")

args <- commandArgs(trailingOnly = TRUE)
season <- if (length(args) >= 1) args[1] else "2026-27"
min_dfga <- if (length(args) >= 2) as.integer(args[2]) else 45L
top_n <- if (length(args) >= 3) as.integer(args[3]) else 10L

path <- sprintf("r/data/rim_defense_%s.csv", season)
rim <- read.csv(path) |>
  filter(D_FGA >= min_dfga)

top <- rim |>
  arrange(D_FG_PCT, desc(D_FGA)) |>
  slice_head(n = top_n) |>
  mutate(
    rank = row_number(),
    player = player_cell(PLAYER_ID, PLAYER_NAME),
    team = logo_cell(TEAM_ID),
    shots = sprintf("%d-%d", D_FGM, D_FGA),
    DFG = 100 * D_FG_PCT,
    NORMAL = 100 * NORMAL_FG_PCT,
    DIFF = 100 * PCT_DIFF
  ) |>
  select(rank, player, team, GP, shots, NORMAL, DFG, DIFF)

signed <- function(x) sprintf("%s%.1f", ifelse(x > 0, "+", ""), x)

rim_tbl <- top |>
  gt() |>
  html_cols(c(player, team)) |>
  cols_label(rank = "", player = "Player", team = "Team", shots = "FGM-FGA",
             NORMAL = "Expected FG%", DFG = "Defended FG%", DIFF = "Diff") |>
  fmt_number(c(NORMAL, DFG), decimals = 1) |>
  fmt(DIFF, fns = signed) |>
  data_color(DFG, palette = c("#2F855A", "#F1F5F9"),
             domain = range(top$DFG)) |>
  tab_style(cell_text(weight = "bold", size = px(18)), cells_body(DFG)) |>
  tab_style(cell_text(color = "#2F855A", weight = "bold"), cells_body(DIFF)) |>
  tab_style(cell_text(color = SLATE), cells_body(NORMAL)) |>
  tab_style(cell_text(color = "#94A3B8"), cells_body(rank)) |>
  tab_footnote("Shots within 6 ft where the player was the closest defender.",
               cells_column_labels(shots)) |>
  tab_footnote("What those shooters normally make from within 6 ft.",
               cells_column_labels(NORMAL)) |>
  theme_nba_table(
    "Best Rim Protectors",
    sprintf("Opponent FG%% within 6 ft · %s regular season · min. %d shots defended (%d players qualify)",
            season, min_dfga, nrow(rim)),
    paste0("Data: NBA.com player tracking, as of ", data_as_of(path), ". ",
           "Early-season samples are small and noisy.")
  )

save_table(rim_tbl, sprintf("rim_defense_%s", season))
