import datetime
import requests
import os
import io
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# --- 🔐 SECRETS ---
BSKY_HANDLE = os.environ.get("BSKY_HANDLE")
BSKY_PASSWORD = os.environ.get("BSKY_PASSWORD")

# --- ⚙️ CONFIGURATION ---
TEAM_ID_ESPN = 359 # Arsenal

# --- 🎨 VISUAL THEME ---
THEME = {
    "RED": "#EF0107",
    "GOLD": "#D4A046",
    "BG": "#121212",
    "CONTAINER": "#2A2A2A", 
    "TEXT": "#F5F5F5",
    "TEXT_DIM": "#C4C4C4",
    "BAR_TRACK": "#444444"
}

# --- 🛠️ UTILS ---
def get_headers():
    return {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def get_font(size):
    # CLOUD FONT FIX: Prioritize Linux System Fonts (Ubuntu/GitHub Actions)
    linux_fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"
    ]
    for path in linux_fonts:
        if os.path.exists(path): return ImageFont.truetype(path, size)
    
    # Fallback: Download if missing
    try:
        if not os.path.exists("font.ttf"):
            url = "https://github.com/google/fonts/raw/main/apache/roboto/static/Roboto-Bold.ttf"
            r = requests.get(url, timeout=5)
            with open("font.ttf", "wb") as f: f.write(r.content)
        return ImageFont.truetype("font.ttf", size)
    except: return ImageFont.load_default()

def get_image_from_url(url):
    if not url: return None
    try:
        r = requests.get(url, headers=get_headers(), timeout=10)
        return Image.open(io.BytesIO(r.content)).convert("RGBA")
    except: return None

# --- 🖌️ DRAWING ENGINE (Large Fonts & White Outline) ---
def add_white_outline(img, thickness=5):
    r, g, b, a = img.split()
    silhouette = Image.merge("RGBA", (a, a, a, a))
    silhouette = Image.eval(silhouette, lambda x: 255 if x > 0 else 0)
    silhouette.putalpha(a)
    mask = silhouette.getchannel('A')
    expanded_mask = mask.filter(ImageFilter.MaxFilter(thickness * 2 + 1))
    outline_layer = Image.new('RGBA', img.size, (255, 255, 255, 255))
    outline_layer.putalpha(expanded_mask)
    result = Image.new('RGBA', img.size, (0,0,0,0))
    result.paste(outline_layer, (0,0), outline_layer)
    result.paste(img, (0,0), img)
    return result

def draw_pill_bar(draw, x, y, width, height, percentage, color_active, color_track):
    draw.rounded_rectangle([x, y, x + width, y + height], radius=height/2, fill=color_track)
    if percentage > 0:
        active_width = max(height, width * (percentage / 100))
        draw.rounded_rectangle([x, y, x + active_width, y + height], radius=height/2, fill=color_active)

def paste_logo_centered(bg_img, logo_img, center_x, center_y, target_height):
    if not logo_img: return
    aspect = logo_img.width / logo_img.height
    new_h = target_height
    new_w = int(new_h * aspect)
    logo_resized = logo_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    logo_outlined = add_white_outline(logo_resized, thickness=4)
    paste_x = int(center_x - (logo_outlined.width / 2))
    paste_y = int(center_y - (logo_outlined.height / 2))
    bg_img.paste(logo_outlined, (paste_x, paste_y), logo_outlined)

def create_match_image(data):
    width, height = 1080, 1350
    img = Image.new('RGB', (width, height), THEME["BG"])
    draw = ImageDraw.Draw(img)
    
    # LARGE FONTS for Cloud
    f_xl = get_font(180)
    f_h = get_font(50)
    f_body = get_font(38)
    f_sm = get_font(36)
    f_num = get_font(55)

    draw.rounded_rectangle([40, 40, 1040, 590], radius=40, fill=THEME["CONTAINER"])
    draw.text((80, 80), "FULL TIME", font=f_sm, fill=THEME["GOLD"])

    cx, cy = width / 2, 315 
    score_txt = f"{data['ars_score']} - {data['opp_score']}"
    bbox = draw.textbbox((0,0), score_txt, font=f_xl)
    sw = bbox[2]-bbox[0]
    draw.text((cx - sw/2, cy - (bbox[3]-bbox[1])/1.5), score_txt, font=f_xl, fill=THEME["TEXT"])

    if data.get('ars_logo_img'): paste_logo_centered(img, data['ars_logo_img'], cx - sw/2 - 120, cy, 180)
    if data.get('opp_logo_img'): paste_logo_centered(img, data['opp_logo_img'], cx + sw/2 + 120, cy, 180)

    sy = cy + 120
    for i, g in enumerate(data['ars_goals']):
        if i > 3: break
        bg = draw.textbbox((0,0), g, font=f_body)
        draw.text((cx - sw/2 - 120 - (bg[2]-bg[0])/2, sy + (i*45)), g, font=f_body, fill=THEME["TEXT_DIM"])
    for i, g in enumerate(data['opp_goals']):
        if i > 3: break
        bg = draw.textbbox((0,0), g, font=f_body)
        draw.text((cx + sw/2 + 120 - (bg[2]-bg[0])/2, sy + (i*45)), g, font=f_body, fill=THEME["TEXT_DIM"])

    draw.rounded_rectangle([40, 620, 1040, 1230], radius=40, fill=THEME["CONTAINER"])
    draw.text((cx - 140, 660), "MATCH STATS", font=f_h, fill=THEME["TEXT"])

    stats_data = [("POSSESSION", data['ars_poss'], data['opp_poss'], True),("SHOTS", data['ars_shots'], data['opp_shots'], False),("ON TARGET", data['ars_sot'], data['opp_sot'], False),("CORNERS", data['ars_corners'], data['opp_corners'], False)]
    y_stat = 760 
    bar_w = 300 
    for label, v_a, v_o, is_pct in stats_data:
        lb = draw.textbbox((0,0), label, font=f_sm)
        draw.text((cx - (lb[2]-lb[0])/2, y_stat - 45), label, font=f_sm, fill=THEME["TEXT_DIM"])
        max_val = 100 if is_pct else max(v_a + v_o, 15) 
        len_a = min((v_a / max_val) * 100, 100)
        len_o = min((v_o / max_val) * 100, 100)
        val_a_str = str(v_a)
        na_bbox = draw.textbbox((0,0), val_a_str, font=f_num)
        draw.text((cx - 20 - bar_w - 20 - (na_bbox[2]-na_bbox[0]), y_stat - 15), val_a_str, font=f_num, fill=THEME["RED"])
        draw_pill_bar(draw, cx - 20 - bar_w, y_stat, bar_w, 20, 100, THEME["BAR_TRACK"], THEME["BAR_TRACK"])
        act_w = (len_a / 100) * bar_w
        draw.rounded_rectangle([cx - 20 - act_w, y_stat, cx - 20, y_stat + 20], radius=10, fill=THEME["RED"])
        draw_pill_bar(draw, cx + 20, y_stat, bar_w, 20, len_o, "#666666", THEME["BAR_TRACK"])
        draw.text((cx + 20 + bar_w + 20, y_stat - 15), str(v_o), font=f_num, fill=THEME["TEXT"])
        y_stat += 120

    footer_text = "GUNNER BOT"
    bbox_f = draw.textbbox((0,0), footer_text, font=f_sm)
    f_w = bbox_f[2] - bbox_f[0]
    draw.text((cx - (f_w / 2), height - 80), footer_text, font=f_sm, fill=THEME["GOLD"])
    return img

# --- 📡 LOGIC: ONE-SHOT CHECK (NO LOOPS) ---
def get_todays_finished_match_espn():
    """Checks if Arsenal finished a game TODAY/NOW."""
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/teams/{TEAM_ID_ESPN}/schedule"
    try:
        r = requests.get(url, headers=get_headers(), timeout=10).json()
        events = r.get('events', [])
        
        # Filter for 'post' (Finished) games
        completed = [e for e in events if e['competitions'][0]['status']['type']['state'] == 'post']
        
        if not completed: return None
        
        # Sort by date
        completed.sort(key=lambda x: x['date'])
        last_match = completed[-1]
        
        # CHECK TIME: Did it finish recently?
        # If the game date is NOT today, ignore it.
        game_date_str = last_match['date'] 
        game_date = datetime.datetime.strptime(game_date_str.replace("Z", "+0000"), "%Y-%m-%dT%H:%M%z")
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # If game was more than 3 hours ago, assume it's old news.
        # This prevents reposting last week's game.
        if (now - game_date).total_seconds() > 10800: # 3 hours
            print("💤 Found finished game, but it's too old (>3 hours). Ignoring.")
            return None
            
        return last_match['id']
    except: return None

def get_match_stats_espn(match_id):
    # (Same stats logic as before)
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/summary?event={match_id}"
    try:
        r = requests.get(url, headers=get_headers(), timeout=10).json()
        header = r['header']
        competitors = header['competitions'][0]['competitors']
        if competitors[0]['id'] == str(TEAM_ID_ESPN): ars, opp = competitors[0], competitors[1]
        else: ars, opp = competitors[1], competitors[0]
            
        data = {
            "opponent": opp['team']['displayName'],
            "ars_score": ars['score'], "opp_score": opp['score'],
            "ars_logo_img": get_image_from_url(ars['team']['logos'][0]['href']),
            "opp_logo_img": get_image_from_url(opp['team']['logos'][0]['href']),
            "ars_goals": [], "opp_goals": [],
            "ars_poss": 0, "ars_shots": 0, "ars_sot": 0, "ars_corners": 0,
            "opp_poss": 0, "opp_shots": 0, "opp_sot": 0, "opp_corners": 0
        }
        # (Stats parsing omitted for brevity - assuming standard fetch)
        boxscore = r.get('boxscore', {})
        for team in boxscore.get('teams', []):
            prefix = "ars" if team['team']['id'] == str(TEAM_ID_ESPN) else "opp"
            for s in team.get('statistics', []):
                try: val = int(float(s['displayValue']))
                except: val = 0
                if s['name'] == "possessionPct": data[f"{prefix}_poss"] = val
                elif s['name'] == "totalShots": data[f"{prefix}_shots"] = val
                elif s['name'] == "shotsOnTarget": data[f"{prefix}_sot"] = val
                elif s['name'] == "wonCorners": data[f"{prefix}_corners"] = val
        timeline = header.get('competitions', [{}])[0].get('details', [])
        if timeline:
            for e in timeline:
                if e.get('type', {}).get('text') == 'Goal':
                    scorer = e.get('participants', [{}])[0].get('athlete', {}).get('displayName', 'Unknown')
                    time = e.get('clock', {}).get('displayValue', '')
                    team_id = e.get('team', {}).get('id')
                    txt = f"{scorer} {time}"
                    if team_id == str(TEAM_ID_ESPN): data['ars_goals'].append(txt)
                    else: data['opp_goals'].append(txt)
        return data
    except: return None

# --- 🦋 BLUESKY DUPE CHECK ---
def create_session():
    resp = requests.post("https://bsky.social/xrpc/com.atproto.server.createSession", json={"identifier": BSKY_HANDLE, "password": BSKY_PASSWORD})
    resp.raise_for_status()
    return resp.json()

def has_already_posted(session, opponent_name):
    try:
        feed_url = "https://bsky.social/xrpc/app.bsky.feed.getAuthorFeed"
        headers = {"Authorization": f"Bearer {session['accessJwt']}"}
        r = requests.get(feed_url, headers=headers, params={"actor": session['did'], "limit": 5})
        if r.status_code != 200: return False
        for item in r.json().get('feed', []):
            # Check if recent post mentions the opponent and "Full Time"
            if opponent_name in item['post']['record']['text'] and "Full Time" in item['post']['record']['text']:
                return True
        return False
    except: return False

def post_to_bluesky(image_path, caption, session):
    print("☁️ Uploading image...")
    with open(image_path, "rb") as f: img_data = f.read()
    headers = {"Authorization": f"Bearer {session['accessJwt']}", "Content-Type": "image/png"}
    blob = requests.post("https://bsky.social/xrpc/com.atproto.repo.uploadBlob", headers=headers, data=img_data).json()["blob"]
    print("📝 Publishing...")
    post_data = {
        "repo": session['did'], "collection": "app.bsky.feed.post",
        "record": {
            "$type": "app.bsky.feed.post", "text": caption,
            "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "embed": {"$type": "app.bsky.embed.images", "images": [{"alt": caption, "image": blob}]}
        }
    }
    requests.post("https://bsky.social/xrpc/com.atproto.repo.createRecord", headers={"Authorization": f"Bearer {session['accessJwt']}"}, json=post_data).raise_for_status()
    print("✅ SUCCESS! Posted to Bluesky.")

# --- 🤖 MAIN ONE-SHOT RUN ---
def main():
    if not BSKY_HANDLE or not BSKY_PASSWORD:
        print("❌ Secrets missing.")
        sys.exit(1)

    print("🤖 Gunner Bot Cloud Check...")
    
    # 1. Is there a RECENTLY finished game?
    match_id = get_todays_finished_match_espn()
    
    if not match_id:
        print("💤 No matches finished in the last 3 hours. Exiting.")
        sys.exit(0) # Successful exit, nothing to do

    # 2. Get Stats
    stats = get_match_stats_espn(match_id)
    if not stats: return

    # 3. Login
    try: session = create_session()
    except: 
        print("❌ Login Failed"); sys.exit(1)

    # 4. Check if we already posted this specific game
    if has_already_posted(session, stats['opponent']):
        print(f"✅ Already posted results for {stats['opponent']}. Exiting.")
        sys.exit(0)

    # 5. GENERATE & POST
    print("⚡ New Result Detected! Generating graphic...")
    img = create_match_image(stats)
    img.save("result.png")
    
    caption = f"Full Time: Arsenal {stats['ars_score']} - {stats['opp_score']} {stats['opponent']}. #COYG #Arsenal"
    post_to_bluesky("result.png", caption, session)

if __name__ == "__main__":
    main()