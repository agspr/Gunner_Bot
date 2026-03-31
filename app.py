import datetime
import logging
import sys

from gunner_bot.data import get_last_fixture_espn, get_match_stats_espn
from gunner_bot.rendering import create_match_image
from gunner_bot.publishing import get_bluesky_session, check_if_already_posted, post_to_bluesky

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("gunner_bot")


def main():
    log.info("GUNNER BOT: Checking for recent results...")

    # 1. Authenticate with Bluesky (needed for history check)
    session = get_bluesky_session()
    if not session:
        log.warning("Could not authenticate with Bluesky. Will run in DRY RUN mode.")

    # 2. Get latest match data
    espn_id = get_last_fixture_espn()
    if not espn_id:
        log.info("No completed games found.")
        sys.exit(2)

    stats = get_match_stats_espn(espn_id)
    if not stats:
        log.error("Could not fetch match stats.")
        sys.exit(1)

    # 3. Check time window (only post within 24 hours of match end)
    try:
        date_str = stats['match_date'].replace('Z', '+00:00')
        match_date = datetime.datetime.fromisoformat(date_str)
        match_end_approx = match_date + datetime.timedelta(minutes=115)
        now = datetime.datetime.now(datetime.timezone.utc)
        time_since_end = (now - match_end_approx).total_seconds() / 60

        log.info("Match: %s | Approx end: %s | %.0f min ago", match_date, match_end_approx, time_since_end)

        if not (0 <= time_since_end <= 1440):
            log.info("Match result is outside 24-hour window. Skipping.")
            sys.exit(2)

        # 4. Check for duplicate posts
        if session and check_if_already_posted(session, stats['opponent']):
            log.info("Already posted this result. Skipping.")
            sys.exit(2)

        log.info("Generating report for Arsenal vs %s", stats['opponent'])

        img = create_match_image(stats)
        filename = f"result_{stats['opponent']}.png"
        img.save(filename)

        caption = f"Full Time: Arsenal {stats['ars_score']} - {stats['opp_score']} {stats['opponent']}. #COYG #Arsenal"

        if session:
            post_to_bluesky(session, filename, caption)
            sys.exit(0)
        else:
            log.info("[DRY RUN] Would post: %s", caption)
            sys.exit(2)

    except Exception as e:
        log.exception("Error in main execution: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
