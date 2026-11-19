# Players who dribble the most each time they touch the ball (NBA player
# tracking, average dribbles per touch).
#
# Run from repo root after exporting the data:
#   .venv/bin/python examples/export_r_table_data.py
#   Rscript r/dribbles_per_touch_table.R              # defaults: 2026-27, min 8 GP, min 400 touches, top 15
#   Rscript r/dribbles_per_touch_table.R 2026-27 10 600 20

source("r/gt_helpers.R")

args <- commandArgs(trailingOnly = TRUE)
season <- if (length(args) >= 1) args[1] else "2026-27"
min_gp <- if (length(args) >= 2) as.integer(args[2]) else 8L
min_touches <- if (length(args) >= 3) as.integer(args[3]) else 400L
top_n <- if (length(args) >= 4) as.integer(args[4]) else 15L

path <- sprintf("r/data/possessions_%s.csv", season)
poss <- read.csv(path) |>
  filter(GP >= min_gp, TOUCHES >= min_touches)
league_drib <- with(poss, weighted.mean(AVG_DRIB_PER_TOUCH, TOUCHES))

top <- poss |>
  arrange(desc(AVG_DRIB_PER_TOUCH), desc(TOUCHES)) |>
  slice_head(n = top_n) |>
  mutate(
    rank = row_number(),
    player = player_cell(PLAYER_ID, PLAYER_NAME),
    team = logo_cell(TEAM_ID),
    MPG = MIN / GP,
    TPG = TOUCHES / GP
  ) |>
  select(rank, player, team, GP, MPG, TPG, AVG_SEC_PER_TOUCH, PTS_PER_TOUCH, AVG_DRIB_PER_TOUCH)

drib_tbl <- top |>
  gt() |>
  html_cols(c(player, team)) |>
  cols_label(rank = "", player = "Player", team = "Team", MPG = "MPG", TPG = "Touches/G",
             AVG_SEC_PER_TOUCH = "Sec/Touch", PTS_PER_TOUCH = "Pts/Touch",
             AVG_DRIB_PER_TOUCH = "Drib/Touch") |>
  fmt_number(c(MPG, TPG, AVG_SEC_PER_TOUCH), decimals = 1) |>
  fmt_number(c(PTS_PER_TOUCH, AVG_DRIB_PER_TOUCH), decimals = 2) |>
  data_color(AVG_DRIB_PER_TOUCH, palette = c("#F1F5F9", "#2B6CB0"),
             domain = c(league_drib, max(top$AVG_DRIB_PER_TOUCH))) |>
  tab_style(cell_text(weight = "bold", size = px(18)), cells_body(AVG_DRIB_PER_TOUCH)) |>
  tab_style(cell_text(color = SLATE), cells_body(c(MPG, TPG, AVG_SEC_PER_TOUCH, PTS_PER_TOUCH))) |>
  tab_style(cell_text(color = "#94A3B8"), cells_body(rank)) |>
  tab_footnote(sprintf("Average dribbles per touch. Touch-weighted average of qualified players: %.2f.",
                       league_drib),
               cells_column_labels(AVG_DRIB_PER_TOUCH)) |>
  theme_nba_table(
    "Most Dribbles Per Touch",
    sprintf("%s regular season · min. %d GP and %d touches (%d players qualify)",
            season, min_gp, min_touches, nrow(poss)),
    paste0("Data: NBA.com player tracking, as of ", data_as_of(path), ". ",
           "Early-season samples are small and noisy.")
  )

save_table(drib_tbl, sprintf("dribbles_per_touch_%s", season))
