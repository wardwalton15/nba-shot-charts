# Top assister -> scorer duos: most assists from one player to one teammate.
#
# Run from repo root after exporting the data:
#   .venv/bin/python examples/export_r_table_data.py
#   Rscript r/assist_duos_table.R            # defaults: 2026-27, top 5
#   Rscript r/assist_duos_table.R 2026-27 10

source("r/gt_helpers.R")

args <- commandArgs(trailingOnly = TRUE)
season <- if (length(args) >= 1) args[1] else "2026-27"
top_n <- if (length(args) >= 2) as.integer(args[2]) else 5L

path <- sprintf("r/data/assist_pairs_%s.csv", season)
duos <- read.csv(path) |>
  arrange(desc(AST), desc(PTS)) |>  # ties broken by points created
  slice_head(n = top_n) |>
  mutate(
    rank = row_number(),
    assister = player_cell(ASSISTER_ID, ASSISTER_NAME),
    arrow = "&#8594;",
    scorer = player_cell(SCORER_ID, SCORER_NAME),
    team = logo_cell(TEAM_ID),
    SHARE = AST / ASSISTER_TOTAL_AST
  ) |>
  select(rank, assister, arrow, scorer, team, AST, PTS, AST_3PM, SHARE)

duo_tbl <- duos |>
  gt() |>
  html_cols(c(assister, arrow, scorer, team)) |>
  cols_label(rank = "", assister = "Passer", arrow = "", scorer = "Scorer", team = "Team",
             PTS = "Pts Created", AST_3PM = "3PM", SHARE = "% of Passer's AST") |>
  fmt_percent(SHARE, decimals = 0) |>
  data_color(AST, palette = c("#F1F5F9", "#C05621")) |>
  tab_style(cell_text(weight = "bold", size = px(18)), cells_body(AST)) |>
  tab_style(cell_text(color = "#94A3B8", size = px(20)), cells_body(arrow)) |>
  tab_style(cell_text(color = "#94A3B8"), cells_body(rank)) |>
  theme_nba_table(
    "Top Passer-to-Scorer Duos",
    sprintf("Most assists from one player to a specific teammate · %s regular season", season),
    paste0("Data: NBA.com play-by-play, as of ", data_as_of(path), ". Ties broken by points created.")
  )

save_table(duo_tbl, sprintf("assist_duos_%s", season))
