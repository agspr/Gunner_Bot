# Gunner Bot

An automated match report bot that generates visual post-match graphics and publishes them to Bluesky. It pulls live data from ESPN, creates a styled infographic with scores, goalscorers, and key stats, and posts it shortly after full time.

Built for Arsenal FC, but easily adaptable to any team covered by ESPN.

## What It Does

After every match, the bot:

1. Detects the most recent completed fixture via the ESPN API
2. Fetches boxscore stats (possession, shots, xG, pass completion, etc.)
3. Generates a 1080x1350 PNG with score, club badges, goalscorers, and stat bars
4. Posts the image to Bluesky with a caption

## How It Runs

The bot uses a two-phase GitHub Actions workflow:

- **Scheduler** (`scheduler.yml`) — runs once daily at 06:00 UTC, checks the ESPN fixture list for a match today, and dispatches the poller with the exact wait time based on kick-off
- **Poller** (`poller.yml`) — sleeps until the match is expected to end, then polls every 5 minutes until the result is posted. For long waits (>5h), it chain-dispatches itself to stay under GitHub's 6-hour job limit

On non-match days, only the lightweight scheduler runs (no Python, no dependencies).

## Setup

### 1. Fork the repository

### 2. Set repository secrets

In your fork, go to **Settings > Secrets and variables > Actions** and add:

| Secret | Description |
|---|---|
| `BSKY_HANDLE` | Your Bluesky handle (e.g. `yourbot.bsky.social`) |
| `BSKY_PASSWORD` | An [app password](https://bsky.app/settings/app-passwords) for the account |

### 3. Enable GitHub Actions

Go to the **Actions** tab in your fork and enable workflows if prompted.

### 4. Test manually

Trigger the poller directly to test without waiting for a match day:

```
gh workflow run poller.yml -f wait_seconds=0
```

Or run locally:

```bash
pip install -r requirements.txt
python app.py
```

Without Bluesky credentials set, it runs in dry-run mode (generates the image but doesn't post).

## Adapting for a Different Team

All team-specific configuration lives in `gunner_bot/config.py`.

### 1. Change the ESPN team ID

```python
TEAM_ID_ESPN = 359  # Arsenal
```

Replace `359` with your team's ESPN ID. To find it, search for your team on [espn.com/soccer](https://www.espn.com/soccer/) and look at the URL:

```
espn.com/soccer/team/_/id/360/tottenham-hotspur
                            ^^^
                          Team ID
```

### 2. Update the color theme

The `THEME` dictionary controls the entire visual style:

```python
THEME = {
    "RED": "#EF0107",      # Primary team color (stat bars, numbers)
    "GOLD": "#D4A046",     # Accent color (headers, footer)
    "BG": "#121212",       # Background
    "CONTAINER": "#2A2A2A",# Card backgrounds
    "TEXT": "#F5F5F5",     # Primary text
    "TEXT_DIM": "#C4C4C4", # Secondary text (labels, goalscorers)
    "BAR_TRACK": "#444444",# Empty stat bar track
    "BAR_OPP": "#555555",  # Opponent stat bar fill
    "RED_DIM": "#B80003",  # Losing stat bar (darker primary)
    "RED_HI": "#FF2222",   # Winning stat bar (brighter primary)
}
```

Replace `RED`, `RED_DIM`, `RED_HI`, and `GOLD` with your team's colors. The other values work well as-is for any dark theme.

### 3. Update the post caption (optional)

In `app.py`, the caption template includes `#COYG #Arsenal`:

```python
caption = f"Full Time: Arsenal {stats['ars_score']} - {stats['opp_score']} {stats['opponent']}. #COYG #Arsenal"
```

Change this to your team's name and hashtags.

## Project Structure

```
app.py                              # Entry point and orchestration
gunner_bot/
  config.py                         # Team ID, secrets, color theme
  data.py                           # ESPN API: fixtures, stats, goalscorers
  rendering.py                      # PIL image generation
  publishing.py                     # Bluesky API: auth, posting
.github/workflows/
  scheduler.yml                     # Daily fixture check (bash + curl)
  poller.yml                        # Match result polling (Python)
```

## Requirements

- Python 3.11+
- `requests`
- `Pillow`

## License

MIT
