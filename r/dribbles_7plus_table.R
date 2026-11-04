# Players with the highest share of their field goal attempts coming after 7+
# dribbles (NBA player tracking).
#
# Run from repo root after exporting the data:
#   .venv/bin/python examples/export_r_table_data.py
#   Rscript r/dribbles_7plus_table.R              # defaults: 2026-27, min 75 FGA, top 10
#   Rscript r/dribbles_7plus_table.R 2026-27 150 15

source("r/gt_helpers.R")

args <- commandArgs(trailingOnly = TRUE)
season <- if (length(args) >= 1) args[1] else "2026-27"
min_fga <- if (length(args) >= 2) as.integer(args[2]) else 75L
top_n <- if (length(args) >= 3) as.integer(args[3]) else 10L

path <- sprintf("r/data/dribbles_7plus_%s.csv", season)
dribbles <- read.csv(path) |>
  mutate(DRIB_SHARE = 100 * FGA / TOTAL_FGA)
league_efg <- 100 * with(dribbles, sum(FGM + 0.5 * FG3M) / sum(FGA))
dribbles <- filter(dribbles, TOTAL_FGA >= min_fga)

top <- dribbles |>
  arrange(desc(DRIB_SHARE), desc(FGA)) |>
  slice_head(n = top_n) |>
  mutate(
    rank = row_number(),
    player = player_cell(PLAYER_ID, PLAYER_NAME),
    team = logo_cell(TEAM_ID),
    EFG = 100 * EFG_PCT
  ) |>
  select(rank, player, team, GP, TOTAL_FGA, FGA, EFG, DRIB_SHARE)

dribbles_tbl <- top |>
  gt() |>
  html_cols(c(player, team)) |>
  cols_label(rank = "", player = "Player", team = "Team", TOTAL_FGA = "FGA",
             FGA = "7+ Drib FGA", EFG = "7+ Drib eFG%", DRIB_SHARE = "% of FGA") |>
  fmt_number(c(TOTAL_FGA, FGA), decimals = 0) |>
  fmt_number(c(EFG, DRIB_SHARE), decimals = 1) |>
  data_color(DRIB_SHARE, palette = c("#F1F5F9", "#2B6CB0"),
             domain = c(0, max(top$DRIB_SHARE))) |>
  tab_style(cell_text(weight = "bold", size = px(18)), cells_body(DRIB_SHARE)) |>
  tab_style(cell_text(color = "#2F855A"), cells_body(EFG, rows = EFG > league_efg)) |>
  tab_style(cell_text(color = "#C53030"), cells_body(EFG, rows = EFG < league_efg)) |>
  tab_style(cell_text(color = "#94A3B8"), cells_body(rank)) |>
  tab_footnote("Share of the player's field goal attempts taken after 7 or more dribbles.",
               cells_column_labels(DRIB_SHARE)) |>
  tab_footnote(sprintf("Green/red = above/below the league-wide eFG%% on 7+ dribble shots (%.1f%%).",
                       league_efg),
               cells_column_labels(EFG)) |>
  theme_nba_table(
    "Most Shots Off 7+ Dribbles",
    sprintf("Share of FGA after 7+ dribbles · %s regular season · min. %d FGA (%d players qualify)",
            season, min_fga, nrow(dribbles)),
    paste0("Data: NBA.com player tracking, as of ", data_as_of(path), ". ",
           "Early-season samples are small and noisy.")
  )

save_table(dribbles_tbl, sprintf("dribbles_7plus_%s", season))
