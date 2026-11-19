# Most points scored per touch (NBA player tracking).
#
# Run from repo root after exporting the data:
#   .venv/bin/python examples/export_r_table_data.py
#   Rscript r/points_per_touch_table.R              # defaults: 2026-27, min 8 GP, min 400 touches, top 15
#   Rscript r/points_per_touch_table.R 2026-27 10 600 20

source("r/gt_helpers.R")

args <- commandArgs(trailingOnly = TRUE)
season <- if (length(args) >= 1) args[1] else "2026-27"
min_gp <- if (length(args) >= 2) as.integer(args[2]) else 8L
min_touches <- if (length(args) >= 3) as.integer(args[3]) else 400L
top_n <- if (length(args) >= 4) as.integer(args[4]) else 15L

path <- sprintf("r/data/possessions_%s.csv", season)
# PTS_PER_TOUCH from the API is rounded to 2 decimals, so recompute it from totals
poss <- read.csv(path) |>
  filter(GP >= min_gp, TOUCHES >= min_touches) |>
  mutate(PPT = POINTS / TOUCHES)
league_ppt <- with(poss, sum(POINTS) / sum(TOUCHES))

top <- poss |>
  arrange(desc(PPT), desc(TOUCHES)) |>
  slice_head(n = top_n) |>
  mutate(
    rank = row_number(),
    player = player_cell(PLAYER_ID, PLAYER_NAME),
    team = logo_cell(TEAM_ID),
    MPG = MIN / GP,
    TPG = TOUCHES / GP,
    PPG = POINTS / GP
  ) |>
  select(rank, player, team, GP, MPG, PPG, TPG, AVG_DRIB_PER_TOUCH, PPT)

ppt_tbl <- top |>
  gt() |>
  html_cols(c(player, team)) |>
  cols_label(rank = "", player = "Player", team = "Team", MPG = "MPG", PPG = "PPG",
             TPG = "Touches/G", AVG_DRIB_PER_TOUCH = "Drib/Touch", PPT = "Pts/Touch") |>
  fmt_number(c(MPG, PPG, TPG), decimals = 1) |>
  fmt_number(AVG_DRIB_PER_TOUCH, decimals = 2) |>
  fmt_number(PPT, decimals = 3) |>
  data_color(PPT, palette = c("#F1F5F9", "#2F855A"),
             domain = c(league_ppt, max(top$PPT))) |>
  tab_style(cell_text(weight = "bold", size = px(18)), cells_body(PPT)) |>
  tab_style(cell_text(color = SLATE), cells_body(c(MPG, TPG, AVG_DRIB_PER_TOUCH))) |>
  tab_style(cell_text(color = "#94A3B8"), cells_body(rank)) |>
  tab_footnote(sprintf("Total points / total touches. All qualified players combined: %.3f.", league_ppt),
               cells_column_labels(PPT)) |>
  theme_nba_table(
    "Most Points Per Touch",
    sprintf("%s regular season · min. %d GP and %d touches (%d players qualify)",
            season, min_gp, min_touches, nrow(poss)),
    paste0("Data: NBA.com player tracking, as of ", data_as_of(path), ". ",
           "Early-season samples are small and noisy.")
  )

save_table(ppt_tbl, sprintf("points_per_touch_%s", season))
