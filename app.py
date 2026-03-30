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
CHECK_INTERVAL = 120 # Check every 2 mins when game is finishing

# --- 🎨 VISUAL THEME ---
THEME = {
    "RED": "#EF0107",
    "GOLD": "#D4A046",
    "BG": "#121212",
    "CONTAINER": "#2A2A2A",
    "TEXT": "#F5F5F5",
    "TEXT_DIM": "#C4C4C4",
    "BAR_TRACK": "#444444",
    "BAR_OPP": "#555555",      # Opponent bar color (improved contrast)
    "RED_DIM": "#B80003",      # Darker red for gradient (losing stat)
    "RED_HI": "#FF2222",       # Brighter red for gradient (winning stat)
}

# --- 🛠️ UTILS: FONTS & IMAGES ---
def get_headers():
    return {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def get_font(size):
    paths = ["font.ttf", "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/seguiemj.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    for p in paths:
        if os.path.exists(p): return ImageFont.truetype(p, size)
    try:
        url = "https://github.com/google/fonts/raw/main/apache/roboto/static/Roboto-Bold.ttf"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            with open("font.ttf", "wb") as f: f.write(r.content)
            return ImageFont.truetype("font.ttf", size)
    except: pass
    return ImageFont.load_default()

def get_image_from_url(url):
    if not url: return None
    try:
        r = requests.get(url, headers=get_headers(), timeout=10)
        if r.status_code == 200:
            return Image.open(io.BytesIO(r.content)).convert("RGBA")
    except: return None

# --- 🖌️ DRAWING ENGINE ---
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

def draw_shadow_rect(img, x1, y1, x2, y2, radius, blur=20, offset_x=5, offset_y=7, opacity=130):
    """Draw a soft drop shadow behind a rounded rectangle."""
    shadow_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow_layer)
    sd.rounded_rectangle(
        [x1 + offset_x, y1 + offset_y, x2 + offset_x, y2 + offset_y],
        radius=radius, fill=(0, 0, 0, opacity)
    )
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=blur))
    img.paste(shadow_layer.convert('RGB'), (0, 0), shadow_layer.split()[3])

def draw_gradient_pill(img, x, y, width, height, color_left, color_right):
    """Draw a horizontal gradient-filled pill shape."""
    def hex_to_rgb(h):
        return tuple(int(h.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

    lr, lg, lb = hex_to_rgb(color_left)
    rr, rg, rb = hex_to_rgb(color_right)

    # Create gradient rectangle
    grad = Image.new('RGB', (width, height))
    grad_d = ImageDraw.Draw(grad)
    for col in range(width):
        t = col / max(width - 1, 1)
        grad_d.line([(col, 0), (col, height - 1)],
                    fill=(int(lr + t*(rr-lr)), int(lg + t*(rg-lg)), int(lb + t*(rb-lb))))

    # Create pill-shaped mask
    mask = Image.new('L', (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, width - 1, height - 1],
                                            radius=height // 2, fill=255)
    img.paste(grad, (x, y), mask)

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
    print(f"Creating graphic: Arsenal vs {data['opponent']}")
    width, height = 1080, 1350
    img = Image.new('RGB', (width, height), THEME["BG"])
    draw = ImageDraw.Draw(img)
    
    f_xl = get_font(160)
    f_h = get_font(40)
    f_body = get_font(32)
    f_sm = get_font(28)
    f_num = get_font(36)

    # Draw drop shadow for score container
    draw_shadow_rect(img, 40, 40, 1040, 590, radius=40)
    draw.rounded_rectangle([40, 40, 1040, 590], radius=40, fill=THEME["CONTAINER"])
    draw.text((80, 80), "FULL TIME", font=f_sm, fill=THEME["GOLD"])

    # Competition name (right-aligned in score header)
    if data.get('competition'):
        comp_txt = data['competition'].upper()
        comp_bbox = draw.textbbox((0, 0), comp_txt, font=f_sm)
        draw.text((1040 - 40 - (comp_bbox[2] - comp_bbox[0]), 80), comp_txt, font=f_sm, fill=THEME["TEXT_DIM"])

    cx, cy = width / 2, 315 
    score_txt = f"{data['ars_score']} - {data['opp_score']}"
    bbox = draw.textbbox((0,0), score_txt, font=f_xl)
    sw = bbox[2]-bbox[0]
    draw.text((cx - sw/2, cy - (bbox[3]-bbox[1])/1.5), score_txt, font=f_xl, fill=THEME["TEXT"])

    # Badges
    if data.get('ars_logo_img'):
        paste_logo_centered(img, data['ars_logo_img'], cx - sw/2 - 120, cy, 180)
    if data.get('opp_logo_img'):
        paste_logo_centered(img, data['opp_logo_img'], cx + sw/2 + 120, cy, 180)

    # Goalscorers (Moved under badges)
    # Arsenal Scorers
    y_ars = cy + 110
    for i, g in enumerate(data['ars_goals']):
        if i > 3: break
        bg = draw.textbbox((0,0), g, font=f_sm) # Using f_sm as requested
        # Center under Arsenal badge (cx - sw/2 - 120)
        badge_center_x = cx - sw/2 - 120
        draw.text((badge_center_x - (bg[2]-bg[0])/2, y_ars + (i*35)), g, font=f_sm, fill=THEME["TEXT_DIM"])

    # Opponent Scorers
    y_opp = cy + 110
    for i, g in enumerate(data['opp_goals']):
        if i > 3: break
        bg = draw.textbbox((0,0), g, font=f_sm) # Using f_sm as requested
        # Center under Opponent badge (cx + sw/2 + 120)
        badge_center_x = cx + sw/2 + 120
        draw.text((badge_center_x - (bg[2]-bg[0])/2, y_opp + (i*35)), g, font=f_sm, fill=THEME["TEXT_DIM"])

    # Venue and attendance line at bottom of score container
    context_parts = []
    if data.get('venue'):
        context_parts.append(data['venue'])
    if data.get('attendance'):
        context_parts.append(f"Att: {data['attendance']:,}")
    if context_parts:
        f_ctx = get_font(22)
        ctx_txt = "  |  ".join(context_parts)
        ctx_bbox = draw.textbbox((0, 0), ctx_txt, font=f_ctx)
        draw.text((cx - (ctx_bbox[2] - ctx_bbox[0]) / 2, 560), ctx_txt, font=f_ctx, fill=THEME["TEXT_DIM"])

    # Draw drop shadow for stats container
    draw_shadow_rect(img, 40, 620, 1040, 1230, radius=40)
    draw.rounded_rectangle([40, 620, 1040, 1230], radius=40, fill=THEME["CONTAINER"])

    # Centered Header
    header_txt = "MATCH STATS"
    bbox_h = draw.textbbox((0,0), header_txt, font=f_h)
    draw.text((cx - (bbox_h[2]-bbox_h[0])/2, 660), header_txt, font=f_h, fill=THEME["TEXT"])

    # Possession Logic (Sum to 100%)
    p_a = data['ars_poss']
    p_o = data['opp_poss']
    if p_a + p_o != 100 and p_a + p_o > 0:
        # Simple adjustment: if sum != 100, adjust the larger one to make it fit
        diff = 100 - (p_a + p_o)
        if p_a >= p_o: p_a += diff
        else: p_o += diff
    
    # Format with %
    p_a_str = f"{p_a}%"
    p_o_str = f"{p_o}%"

    stats_data = [
        ("POSSESSION", p_a_str, p_o_str, True),
        ("SHOTS", data['ars_shots'], data['opp_shots'], False),
        ("ON TARGET", data['ars_sot'], data['opp_sot'], False),
    ]

    # Add xG if available (insert at position 1, after POSSESSION)
    if data.get('ars_xg') is not None and data.get('opp_xg') is not None:
        stats_data.insert(1, ("EXPECTED GOALS (xG)", data['ars_xg'], data['opp_xg'], False))

    # Add PASS COMPLETION if available, otherwise CORNERS
    if data.get('ars_pass_pct') is not None and data.get('opp_pass_pct') is not None:
        stats_data.append(("PASS COMPLETION", f"{data['ars_pass_pct']}%", f"{data['opp_pass_pct']}%", True))
    else:
        stats_data.append(("CORNERS", data['ars_corners'], data['opp_corners'], False))

    y_stat = 770 # Increased spacing (was 750)
    bar_w = 320
    for label, v_a, v_o, is_pct in stats_data:
        lb = draw.textbbox((0,0), label, font=f_sm)
        draw.text((cx - (lb[2]-lb[0])/2, y_stat - 35), label, font=f_sm, fill=THEME["TEXT_DIM"])
        
        # Parse values for bars
        safe_va = float(str(v_a).replace('%','')) if v_a else 0
        safe_vo = float(str(v_o).replace('%','')) if v_o else 0
        
        # For xG, max value is usually small (e.g. 2.5), so we need a different scale or just max(sum, 1)
        if "xG" in label:
            max_val = max(safe_va + safe_vo, 3.0) # Assume 3.0 is a decent baseline for xG bars
        elif is_pct:
            max_val = 100
        else:
            max_val = max(safe_va + safe_vo, 15) 

        len_a = min((safe_va / max_val) * 100, 100)
        len_o = min((safe_vo / max_val) * 100, 100)

        # Determine if Arsenal wins this stat (higher value is better for all stats)
        ars_winning = safe_va > safe_vo

        # Arsenal bar (right-anchored, grows leftward)
        draw.text((cx - 20 - bar_w - 90, y_stat - 8), str(v_a), font=f_num, fill=THEME["RED"])
        draw.rounded_rectangle([cx - 20 - bar_w, y_stat, cx - 20, y_stat + 20],
                               radius=10, fill=THEME["BAR_TRACK"])
        act_w = max(20, int((len_a / 100) * bar_w))
        if act_w > 0:
            left_col = THEME["RED"] if ars_winning else THEME["RED_DIM"]
            right_col = THEME["RED_HI"] if ars_winning else THEME["RED"]
            draw_gradient_pill(img, int(cx - 20 - act_w), y_stat, act_w, 20, left_col, right_col)

        # Opponent bar (left-anchored, grows rightward)
        draw.text((cx + 20 + bar_w + 20, y_stat - 8), str(v_o), font=f_num, fill=THEME["TEXT"])
        draw.rounded_rectangle([cx + 20, y_stat, cx + 20 + bar_w, y_stat + 20],
                               radius=10, fill=THEME["BAR_TRACK"])
        opp_act_w = max(20, int((len_o / 100) * bar_w))
        if opp_act_w > 0:
            draw_gradient_pill(img, int(cx + 20), y_stat, opp_act_w, 20, THEME["BAR_TRACK"], THEME["BAR_OPP"])

        y_stat += 110

    # Updated Footer
    footer_text = "GUNNER BOT"
    bbox_f = draw.textbbox((0,0), footer_text, font=f_sm)
    draw.text((cx - (bbox_f[2]-bbox_f[0])/2, height - 80), footer_text, font=f_sm, fill=THEME["GOLD"])
    return img

# --- 📊 DATA FETCHING ---
def get_last_fixture_espn():
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/teams/{TEAM_ID_ESPN}/schedule"
    try:
        r = requests.get(url, headers=get_headers(), timeout=10).json()
        events = r.get('events', [])
        completed = [e for e in events if e['competitions'][0]['status']['type']['state'] == 'post']
        if not completed: return None
        completed.sort(key=lambda x: x['date'])
        return completed[-1]['id']
    except: return None

def get_match_stats_espn(match_id):
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/summary?event={match_id}"
    try:
        r = requests.get(url, headers=get_headers(), timeout=10).json()
        header = r['header']
        status = header['competitions'][0]['status']['type']['state']
        
        if status != 'post': return None
            
        competitors = header['competitions'][0]['competitors']
        if competitors[0]['id'] == str(TEAM_ID_ESPN):
            ars, opp = competitors[0], competitors[1]
        else:
            ars, opp = competitors[1], competitors[0]
            
        # Extract match context from gameInfo and header
        game_info = r.get('gameInfo', {})
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
            "ars_xg": None, "opp_xg": None,             # Init xG
            "ars_pass_pct": None, "opp_pass_pct": None,  # Init pass completion %
            "match_date": header['competitions'][0]['date'], # Added date for freshness check
            # Match context
            "venue": venue_info.get('fullName', ''),
            "attendance": game_info.get('attendance'),
            "referee": officials[0].get('displayName', '') if officials else '',
            "competition": league_info.get('name', ''),
        }

        boxscore = r.get('boxscore', {})
        for team in boxscore.get('teams', []):
            prefix = "ars" if team['team']['id'] == str(TEAM_ID_ESPN) else "opp"
            for s in team.get('statistics', []):
                try: val = float(s['displayValue']) if '.' in s['displayValue'] else int(s['displayValue'])
                except: val = 0
                
                if s['name'] == "possessionPct": data[f"{prefix}_poss"] = int(val)
                elif s['name'] == "totalShots": data[f"{prefix}_shots"] = int(val)
                elif s['name'] == "shotsOnTarget": data[f"{prefix}_sot"] = int(val)
                elif s['name'] == "wonCorners": data[f"{prefix}_corners"] = int(val)
                elif s['name'] == "passPct": data[f"{prefix}_pass_pct"] = int(round(val * 100))  # Convert decimal to percentage
                elif s['name'] == "expectedGoals": data[f"{prefix}_xg"] = val # Capture xG

        timeline = header.get('competitions', [{}])[0].get('details', [])
        if timeline:
            # Aggregate goals by scorer to handle multiple goals per player
            ars_goals_dict = {}
            opp_goals_dict = {}

            for e in timeline:
                if e.get('scoringPlay', False):
                    scorer_full = e.get('participants', [{}])[0].get('athlete', {}).get('displayName', 'Unknown')
                    # Last name only, ALL CAPS
                    scorer_last = scorer_full.split()[-1].upper()

                    # Handle own goals
                    if e.get('ownGoal', False):
                        scorer_last += " (OG)"

                    time_str = e.get('clock', {}).get('displayValue', '')

                    # Format time: "45:00" -> "45'"
                    if ":" in time_str:
                        time_str = time_str.split(":")[0]

                    if not time_str.endswith("'"):
                        time_str += "'"

                    team_id = e.get('team', {}).get('id')
                    target_dict = ars_goals_dict if team_id == str(TEAM_ID_ESPN) else opp_goals_dict

                    # Aggregate times for each scorer
                    if scorer_last in target_dict:
                        target_dict[scorer_last].append(time_str)
                    else:
                        target_dict[scorer_last] = [time_str]

            # Format goals as "SCORER   time1, time2, time3"
            data['ars_goals'] = [f"{name}   {', '.join(times)}" for name, times in ars_goals_dict.items()]
            data['opp_goals'] = [f"{name}   {', '.join(times)}" for name, times in opp_goals_dict.items()]
        return data
    except Exception as e:
        print(f"Error fetching stats: {e}")
        return None

# --- 🚀 PUBLISHING ---
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
        print(f"Session Error: {e}")
        return None

def check_if_already_posted(session, opponent_name):
    print(f"Checking history for: {opponent_name}")
    if not session: return False
    
    try:
        # Fetch author feed
        params = {"actor": session["did"], "limit": 10}
        headers = {"Authorization": f"Bearer {session['accessJwt']}"}
        resp = requests.get(
            "https://bsky.social/xrpc/app.bsky.feed.getAuthorFeed",
            headers=headers, params=params
        )
        resp.raise_for_status()
        data = resp.json()
        
        for item in data.get("feed", []):
            post = item.get("post", {})
            record = post.get("record", {})
            text = record.get("text", "")
            # Check if opponent name is in the post text
            if opponent_name.lower() in text.lower() and "Full Time" in text:
                print(f"Found existing post: {text}")
                return True
        return False
    except Exception as e:
        print(f"History Check Error: {e}")
        return False

def post_to_bluesky(session, image_path, caption):
    print("Connecting to Bluesky...")
    if not session:
        print("Secrets not configured. Skipping post.")
        return

    try:
        access_jwt = session["accessJwt"]
        did = session["did"]

        print("Uploading image...")
        with open(image_path, "rb") as f:
            img_data = f.read()
            
        blob_resp = requests.post(
            "https://bsky.social/xrpc/com.atproto.repo.uploadBlob",
            headers={"Authorization": f"Bearer {access_jwt}", "Content-Type": "image/png"},
            data=img_data
        )
        blob_resp.raise_for_status()
        blob = blob_resp.json()["blob"]

        print("Publishing Post...")
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
        print("SUCCESS! Posted to Bluesky.")
    except Exception as e:
        print(f"Bluesky Error: {e}")

# --- 🤖 MAIN EXECUTION ---
def main():
    print("GUNNER BOT: Checking for recent results...")
    
    # 1. Get Secrets Session First (needed for history check)
    session = get_bluesky_session()
    if not session:
        print("Could not authenticate with Bluesky. Will run in DRY RUN mode (no posting).")

    # 2. Get Data
    espn_id = get_last_fixture_espn()
    if not espn_id:
        print("No completed games found.")
        return

    stats = get_match_stats_espn(espn_id)
    if not stats:
        print("Could not fetch match stats.")
        return

    # 3. Check Time Window
    try:
        # Robust ISO parsing (handles 'Z' or offsets)
        date_str = stats['match_date'].replace('Z', '+00:00')
        match_date = datetime.datetime.fromisoformat(date_str)
        
        match_end_approx = match_date + datetime.timedelta(minutes=115)
        now = datetime.datetime.now(datetime.timezone.utc)
        time_since_end = (now - match_end_approx).total_seconds() / 60
        
        print(f"Match Date: {match_date}")
        print(f"Approx End: {match_end_approx}")
        print(f"Time since approx end: {time_since_end:.1f} minutes")

        # WIDENED WINDOW: 0 to 1440 minutes (24 hours)
        if 0 <= time_since_end <= 1440:
            print("Match is within the 24-hour window.")
            
            # 4. Check Duplicates
            if session and check_if_already_posted(session, stats['opponent']):
                print("Already posted this result. Skipping.")
                return

            print(f"Match just finished & not posted yet! Generating report for Arsenal vs {stats['opponent']}")
            
            img = create_match_image(stats)
            filename = f"result_{stats['opponent']}.png"
            img.save(filename)
            
            caption = f"Full Time: Arsenal {stats['ars_score']} - {stats['opp_score']} {stats['opponent']}. #COYG #Arsenal"
            
            if session:
                post_to_bluesky(session, filename, caption)
            else:
                print(f"[DRY RUN] Would post: {caption}")
                
        else:
            print("Match result is too old (> 24 hours) or in future. Skipping.")

    except Exception as e:
        print(f"Error parsing date or checking time: {e}")

if __name__ == "__main__":
    main()