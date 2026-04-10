import os

# --- Secrets ---
BSKY_HANDLE = os.environ.get("BSKY_HANDLE")
BSKY_PASSWORD = os.environ.get("BSKY_PASSWORD")

# --- Configuration ---
TEAM_ID_ESPN = 359  # Arsenal

# All competitions Arsenal can appear in.
# The ESPN `/all/` schedule endpoint is unreliable, so we query each league individually.
LEAGUES = [
    "eng.1",              # Premier League
    "uefa.champions",     # Champions League
    "eng.fa",             # FA Cup
    "eng.league_cup",     # League Cup (Carabao)
    "eng.charity",        # Community Shield
]

# --- Visual Theme ---
THEME = {
    "RED": "#EF0107",
    "GOLD": "#D4A046",
    "BG": "#121212",
    "CONTAINER": "#2A2A2A",
    "TEXT": "#F5F5F5",
    "TEXT_DIM": "#C4C4C4",
    "BAR_TRACK": "#444444",
    "BAR_OPP": "#555555",
    "RED_DIM": "#B80003",
    "RED_HI": "#FF2222",
}
