# Top clutch scorers: points in the last 5 minutes of games within 5 points (NBA clutch definition).
#
# Run from repo root after exporting the data:
#   .venv/bin/python examples/export_r_table_data.py
#   Rscript r/clutch_scoring_table.R              # defaults: 2026-27, min 10 clutch FGA + FTA, top 10
#   Rscript r/clutch_scoring_table.R 2026-27 15 15

source("r/gt_helpers.R")

args <- commandArgs(trailingOnly = TRUE)
season <- if (length(args) >= 1) args[1] else "2026-27"
min_att <- if (length(args) >= 2) as.integer(args[2]) else 10L
top_n <- if (length(args) >= 3) as.integer(args[3]) else 10L

path <- sprintf("r/data/clutch_%s.csv", season)
clutch <- read.csv(path) |>
  filter(FGA + FTA >= min_att) |>
  mutate(TS = PTS / (2 * (FGA + 0.44 * FTA)))
league_ts <- with(clutch, sum(PTS) / (2 * (sum(FGA) + 0.44 * sum(FTA))))

top <- clutch |>
  arrange(desc(PTS), desc(TS)) |>
  slice_head(n = top_n) |>
  mutate(
    rank = row_number(),
    player = player_cell(PLAYER_ID, PLAYER_NAME),
    team = logo_cell(TEAM_ID),
    fg = sprintf("%d-%d", FGM, FGA),
    fg3 = sprintf("%d-%d", FG3M, FG3A),
    ft = sprintf("%d-%d", FTM, FTA),
    TS = 100 * TS
  ) |>
  select(rank, player, team, GP, MIN, fg, fg3, ft, TS, PTS)

signed <- function(x) sprintf("%s%d", ifelse(x > 0, "+", ""), x)

clutch_tbl <- top |>
  gt() |>
  html_cols(c(player, team)) |>
  cols_label(rank = "", player = "Player", team = "Team", MIN = "Clutch Min",
             fg = "FGM-FGA", fg3 = "3PM-3PA", ft = "FTM-FTA", TS = "TS%", PTS = "Clutch Pts") |>
  fmt_number(MIN, decimals = 0) |>
  fmt_number(TS, decimals = 1) |>
  data_color(PTS, palette = c("#F1F5F9", "#C05621"), domain = range(top$PTS)) |>
  tab_style(cell_text(weight = "bold", size = px(18)), cells_body(PTS)) |>
  tab_style(cell_text(color = SLATE), cells_body(c(MIN, fg, fg3, ft))) |>
  tab_style(cell_text(color = "#94A3B8"), cells_body(rank)) |>
  tab_footnote(sprintf("True shooting: PTS ÷ (2 × (FGA + 0.44 × FTA)). All qualified players combined: %.1f.",
                       100 * league_ts),
               cells_column_labels(TS)) |>
  theme_nba_table(
    "Who's Closing Games?",
    sprintf("Points in clutch time · %s regular season · min. %d clutch FGA + FTA (%d players qualify)",
            season, min_att, nrow(clutch)),
    paste0("Data: NBA.com, as of ", data_as_of(path), ". ",
           "Clutch = last 5 minutes of the 4th quarter or overtime with the score within 5 points. ",
           "GP counts games with clutch minutes.")
  )

save_table(clutch_tbl, sprintf("clutch_scoring_%s", season))
