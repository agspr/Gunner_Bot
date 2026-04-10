import io
import logging
import requests
from PIL import Image

from .config import TEAM_ID_ESPN, LEAGUES

log = logging.getLogger(__name__)


def get_headers():
    return {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}


def get_image_from_url(url):
    if not url:
        return None
    try:
        r = requests.get(url, headers=get_headers(), timeout=10)
        if r.status_code == 200:
            return Image.open(io.BytesIO(r.content)).convert("RGBA")
    except Exception:
        return None


def get_last_fixture_espn():
    """Return the match ID of the most recently completed Arsenal fixture.

    Queries every league in LEAGUES individually because the ESPN ``/all/``
    schedule endpoint no longer returns data.  Results are merged and
    deduplicated by match ID, then the most recent completed match is returned.
    """
    all_completed = {}  # id -> event, avoids duplicates

    for league in LEAGUES:
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/teams/{TEAM_ID_ESPN}/schedule"
        try:
            r = requests.get(url, headers=get_headers(), timeout=10)
            if r.status_code != 200:
                log.warning("ESPN schedule %s returned HTTP %d", league, r.status_code)
                continue
            data = r.json()
            events = data.get('events', [])
            completed = [e for e in events if e['competitions'][0]['status']['type']['state'] == 'post']
            log.info("  %s: %d completed matches", league, len(completed))
            for e in completed:
                all_completed[e['id']] = e
        except Exception:
            log.exception("Failed to fetch %s schedule", league)

    if not all_completed:
        log.warning("No completed matches found across any league")
        return None

    # Sort by date and return the most recent
    sorted_matches = sorted(all_completed.values(), key=lambda x: x['date'])
    last = sorted_matches[-1]
    log.info("Most recent match: %s (%s)", last['name'], last['date'])
    return last['id']


def get_match_stats_espn(match_id):
    """Fetch full match statistics for a given ESPN match ID."""
    # The /all/ summary endpoint still works, but we fall back to league-specific if it fails
    urls_to_try = [
        f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/summary?event={match_id}",
    ] + [
        f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/summary?event={match_id}"
        for league in LEAGUES
    ]

    r_data = None
    for url in urls_to_try:
        try:
            resp = requests.get(url, headers=get_headers(), timeout=10)
            if resp.status_code == 200:
                candidate = resp.json()
                if candidate.get('header', {}).get('competitions'):
                    r_data = candidate
                    break
        except Exception:
            continue

    if r_data is None:
        log.error("Could not fetch summary for match %s from any endpoint", match_id)
        return None

    try:
        header = r_data['header']
        status = header['competitions'][0]['status']['type']['state']

        if status != 'post':
            return None

        competitors = header['competitions'][0]['competitors']
        if competitors[0]['id'] == str(TEAM_ID_ESPN):
            ars, opp = competitors[0], competitors[1]
        else:
            ars, opp = competitors[1], competitors[0]

        # Extract match context from gameInfo and header
        game_info = r_data.get('gameInfo', {})
        venue_info = game_info.get('venue', {})
        officials = game_info.get('officials', [])
        league_info = header.get('league', {})

        data = {
            "opponent": opp['team']['displayName'],
            "ars_score": ars['score'], "opp_score": opp['score'],
            "ars_logo_img": get_image_from_url(ars['team']['logos'][0]['href']),
            "opp_logo_img": get_image_from_url(opp['team']['logos'][0]['href']),
            "ars_goals": [], "opp_goals": [],
            "ars_poss": 0, "ars_shots": 0, "ars_sot": 0, "ars_corners": 0,
            "opp_poss": 0, "opp_shots": 0, "opp_sot": 0, "opp_corners": 0,
            "ars_xg": None, "opp_xg": None,
            "ars_pass_pct": None, "opp_pass_pct": None,
            "match_date": header['competitions'][0]['date'],
            "venue": venue_info.get('fullName', ''),
            "attendance": game_info.get('attendance'),
            "referee": officials[0].get('displayName', '') if officials else '',
            "competition": league_info.get('name', ''),
        }

        # Parse boxscore statistics
        boxscore = r_data.get('boxscore', {})
        for team in boxscore.get('teams', []):
            prefix = "ars" if team['team']['id'] == str(TEAM_ID_ESPN) else "opp"
            for s in team.get('statistics', []):
                try:
                    val = float(s['displayValue']) if '.' in s['displayValue'] else int(s['displayValue'])
                except (ValueError, KeyError):
                    val = 0

                if s['name'] == "possessionPct":   data[f"{prefix}_poss"] = int(val)
                elif s['name'] == "totalShots":    data[f"{prefix}_shots"] = int(val)
                elif s['name'] == "shotsOnTarget": data[f"{prefix}_sot"] = int(val)
                elif s['name'] == "wonCorners":    data[f"{prefix}_corners"] = int(val)
                elif s['name'] == "passPct":       data[f"{prefix}_pass_pct"] = int(round(val * 100))
                elif s['name'] == "expectedGoals": data[f"{prefix}_xg"] = val

        # Parse and aggregate goalscorers
        timeline = header.get('competitions', [{}])[0].get('details', [])
        if timeline:
            ars_goals_dict = {}
            opp_goals_dict = {}

            for e in timeline:
                if e.get('scoringPlay', False):
                    scorer_full = e.get('participants', [{}])[0].get('athlete', {}).get('displayName', 'Unknown')
                    scorer_last = scorer_full.split()[-1].upper()

                    if e.get('ownGoal', False):
                        scorer_last += " (OG)"

                    time_str = e.get('clock', {}).get('displayValue', '')
                    if ":" in time_str:
                        time_str = time_str.split(":")[0]
                    if not time_str.endswith("'"):
                        time_str += "'"

                    team_id = e.get('team', {}).get('id')
                    target_dict = ars_goals_dict if team_id == str(TEAM_ID_ESPN) else opp_goals_dict

                    if scorer_last in target_dict:
                        target_dict[scorer_last].append(time_str)
                    else:
                        target_dict[scorer_last] = [time_str]

            data['ars_goals'] = [f"{name}   {', '.join(times)}" for name, times in ars_goals_dict.items()]
            data['opp_goals'] = [f"{name}   {', '.join(times)}" for name, times in opp_goals_dict.items()]

        return data
    except Exception as e:
        log.exception("Error parsing stats for match %s", match_id)
        return None
