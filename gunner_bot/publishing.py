import datetime
import logging
import requests

from .config import BSKY_HANDLE, BSKY_PASSWORD

log = logging.getLogger(__name__)


def get_bluesky_session():
    if not BSKY_HANDLE or not BSKY_PASSWORD:
        return None
    try:
        resp = requests.post(
            "https://bsky.social/xrpc/com.atproto.server.createSession",
            json={"identifier": BSKY_HANDLE, "password": BSKY_PASSWORD}
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        log.error("Session Error: %s", e)
        return None


def check_if_already_posted(session, opponent_name):
    log.info("Checking history for: %s", opponent_name)
    if not session:
        return False
    try:
        params = {"actor": session["did"], "limit": 10}
        headers = {"Authorization": f"Bearer {session['accessJwt']}"}
        resp = requests.get(
            "https://bsky.social/xrpc/app.bsky.feed.getAuthorFeed",
            headers=headers, params=params
        )
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("feed", []):
            text = item.get("post", {}).get("record", {}).get("text", "")
            if opponent_name.lower() in text.lower() and "Full Time" in text:
                log.info("Found existing post: %s", text)
                return True
        return False
    except Exception as e:
        log.error("History Check Error: %s", e)
        return False


def post_to_bluesky(session, image_path, caption):
    log.info("Connecting to Bluesky...")
    if not session:
        log.warning("Secrets not configured. Skipping post.")
        return

    try:
        access_jwt = session["accessJwt"]
        did = session["did"]

        log.info("Uploading image...")
        with open(image_path, "rb") as f:
            img_data = f.read()

        blob_resp = requests.post(
            "https://bsky.social/xrpc/com.atproto.repo.uploadBlob",
            headers={"Authorization": f"Bearer {access_jwt}", "Content-Type": "image/png"},
            data=img_data
        )
        blob_resp.raise_for_status()
        blob = blob_resp.json()["blob"]

        log.info("Publishing Post...")
        post_data = {
            "repo": did,
            "collection": "app.bsky.feed.post",
            "record": {
                "$type": "app.bsky.feed.post",
                "text": caption,
                "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "embed": {
                    "$type": "app.bsky.embed.images",
                    "images": [{"alt": caption, "image": blob}]
                }
            }
        }
        requests.post(
            "https://bsky.social/xrpc/com.atproto.repo.createRecord",
            headers={"Authorization": f"Bearer {access_jwt}"},
            json=post_data
        ).raise_for_status()
        log.info("SUCCESS! Posted to Bluesky.")
    except Exception as e:
        log.error("Bluesky Error: %s", e)
