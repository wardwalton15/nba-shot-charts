# Stingiest defenders by the shooting of the players they were guarding
# (NBA player tracking matchup data), for all field goals or 3s only.
#
# Run from repo root after exporting the data:
#   .venv/bin/python examples/export_r_table_data.py
#   Rscript r/matchup_defense_table.R fg3          # 3s: defaults 2026-27, min 50 3PA defended, top 10
#   Rscript r/matchup_defense_table.R fg           # all FGs: defaults 2026-27, min 100 FGA defended, top 10
#   Rscript r/matchup_defense_table.R fg 2026-27 150 15

source("r/gt_helpers.R")

args <- commandArgs(trailingOnly = TRUE)
shot <- if (length(args) >= 1) args[1] else "fg3"
stopifnot(shot %in% c("fg", "fg3"))
season <- if (length(args) >= 2) args[2] else "2026-27"

cfg <- if (shot == "fg3") {
  list(made = "MATCHUP_FG3M", att = "MATCHUP_FG3A", min = 50L, short = "3P", att_label = "3PA",
       shots_label = "3PM-3PA", shots_note = "3s", title = "Toughest 3-Point Defenders",
       stem = "three_defense")
} else {
  list(made = "MATCHUP_FGM", att = "MATCHUP_FGA", min = 100L, short = "FG", att_label = "FGA",
       shots_label = "FGM-FGA", shots_note = "Shots", title = "Toughest Matchup Defenders",
       stem = "fg_defense")
}
min_att <- if (length(args) >= 3) as.integer(args[3]) else cfg$min
top_n <- if (length(args) >= 4) as.integer(args[4]) else 10L

path <- sprintf("r/data/matchup_defense_%s.csv", season)
all_def <- read.csv(path) |>
  mutate(MADE = .data[[cfg$made]], ATT = .data[[cfg$att]])
league_pct <- 100 * sum(all_def$MADE) / sum(all_def$ATT)

qual <- all_def |>
  filter(ATT >= min_att, !is.na(TEAM_ID))

top <- qual |>
  mutate(PCT = 100 * MADE / ATT) |>
  arrange(PCT, desc(ATT)) |>
  slice_head(n = top_n) |>
  mutate(
    rank = row_number(),
    player = player_cell(PLAYER_ID, PLAYER_NAME),
    team = logo_cell(TEAM_ID),
    poss = PARTIAL_POSS,
    shots = sprintf("%d-%d", MADE, ATT),
    DIFF = PCT - league_pct
  ) |>
  select(rank, player, team, GP, poss, shots, PCT, DIFF)

signed <- function(x) sprintf("%s%.1f", ifelse(x > 0, "+", ""), x)

tbl <- top |>
  gt() |>
  html_cols(c(player, team)) |>
  cols_label(rank = "", player = "Player", team = "Team", poss = "Matchup Poss",
             shots = cfg$shots_label, PCT = paste0("Opp ", cfg$short, "%"), DIFF = "vs Lg Avg") |>
  fmt_number(poss, decimals = 0) |>
  fmt_number(PCT, decimals = 1) |>
  fmt(DIFF, fns = signed) |>
  data_color(PCT, palette = c("#2F855A", "#F1F5F9"),
             domain = range(top$PCT)) |>
  tab_style(cell_text(weight = "bold", size = px(18)), cells_body(PCT)) |>
  tab_style(cell_text(color = "#2F855A", weight = "bold"), cells_body(DIFF)) |>
  tab_style(cell_text(color = SLATE), cells_body(poss)) |>
  tab_style(cell_text(color = "#94A3B8"), cells_body(rank)) |>
  tab_footnote("Partial possessions spent guarding an opponent, per NBA tracking.",
               cells_column_labels(poss)) |>
  tab_footnote(paste(cfg$shots_note, "taken by the opponent the defender was guarding at the time of the shot."),
               cells_column_labels(shots)) |>
  tab_footnote(sprintf("League-wide %s%% in tracked matchups: %.1f%%.", cfg$short, league_pct),
               cells_column_labels(DIFF)) |>
  theme_nba_table(
    cfg$title,
    sprintf("Lowest opponent %s%% in matchups · %s regular season · min. %d %s defended (%d players qualify)",
            cfg$short, season, min_att, cfg$att_label, nrow(qual)),
    paste0("Data: NBA.com matchup tracking, as of ", data_as_of(path), ". ",
           "Opponent shooting allowed is noisy in small samples.")
  )

save_table(tbl, sprintf("%s_%s", cfg$stem, season))
