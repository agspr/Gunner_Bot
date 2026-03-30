# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Gunner Bot** is an automated Arsenal FC match statistics dashboard that fetches recent match data from ESPN, generates visual graphics, and posts results to Bluesky.

## Architecture

```
app.py                          # Entry point (logging setup + main orchestration)
gunner_bot/
  config.py                     # All configuration: secrets, team ID, THEME colors
  data.py                       # ESPN API: fixture lookup, stat parsing, goal aggregation
  rendering.py                  # PIL image generation: layout, gradients, shadows
  publishing.py                 # Bluesky API: auth, duplicate check, post
.github/workflows/bot.yml       # GitHub Actions cron (every 30 min)
```

### Data Flow

1. `data.get_last_fixture_espn()` — finds most recent completed Arsenal match via ESPN schedule API
2. `data.get_match_stats_espn(match_id)` — fetches boxscore stats, goalscorers (aggregated by player), venue/attendance/competition context
3. `rendering.create_match_image(data)` — generates 1080x1350 PNG with score, badges, stat bars, and context
4. `publishing.post_to_bluesky(session, image_path, caption)` — uploads to Bluesky with duplicate checking

### Key Constants

- `TEAM_ID_ESPN = 359` (Arsenal)
- ESPN stat field names: `possessionPct`, `totalShots`, `shotsOnTarget`, `wonCorners`, `passPct` (decimal, multiply by 100), `expectedGoals`
- Time window: posts only within 24 hours of match completion (estimated as kickoff + 115 min)

## Running

```bash
pip install -r requirements.txt
python app.py                    # Dry run if no BSKY credentials set
```

For live posting:
```bash
export BSKY_HANDLE="your.handle"
export BSKY_PASSWORD="your_password"
python app.py
```

Test data + image without posting:
```python
from gunner_bot.data import get_last_fixture_espn, get_match_stats_espn
from gunner_bot.rendering import create_match_image
stats = get_match_stats_espn(get_last_fixture_espn())
create_match_image(stats).save("test.png")
```

## Rendering Details

- Canvas: 1080x1350px, dark theme (#121212 background)
- Score container: `[40, 40, 1040, 590]` with drop shadow
- Stats container: `[40, 620, 1040, 1230]` with drop shadow
- Bar charts: gradient-filled pills (column-by-column RGB interpolation clipped to pill mask)
- Stat rows: y starts at 770, step 110px — **max 5 rows** before overflow (container bottom at 1230)
- Stats shown: POSSESSION, (xG if available), SHOTS, ON TARGET, PASS COMPLETION (falls back to CORNERS)
- Winning stat highlight: brighter red gradient when Arsenal value > opponent
- Goalscorers: aggregated by player name (e.g., "SAKA 12', 45'"), max 4 per side
- Font fallback chain: local font.ttf → Windows fonts → Linux DejaVu → Google Fonts download → PIL default

## ESPN API

- Schedule: `site.api.espn.com/apis/site/v2/sports/soccer/all/teams/{id}/schedule`
- Summary: `site.api.espn.com/apis/site/v2/sports/soccer/all/summary?event={match_id}`
- `gameInfo.venue.fullName` for venue, `gameInfo.attendance` for attendance, `gameInfo.officials[0]` for referee
- `header.league.name` for competition name
- Goal timeline is in `header.competitions[0].details` — filter by `scoringPlay: true`
- `passPct` returns as decimal (0.80 = 80%), must multiply by 100
