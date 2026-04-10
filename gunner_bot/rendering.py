import logging
import os
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from .config import THEME

log = logging.getLogger(__name__)


# --- Font Loading ---

def get_font(size):
    paths = [
        "font.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/seguiemj.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    try:
        url = "https://github.com/google/fonts/raw/main/apache/roboto/static/Roboto-Bold.ttf"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            with open("font.ttf", "wb") as f:
                f.write(r.content)
            return ImageFont.truetype("font.ttf", size)
    except Exception:
        pass
    return ImageFont.load_default()


# --- Drawing Primitives ---

def add_white_outline(img, thickness=5):
    r, g, b, a = img.split()
    silhouette = Image.merge("RGBA", (a, a, a, a))
    silhouette = Image.eval(silhouette, lambda x: 255 if x > 0 else 0)
    silhouette.putalpha(a)
    mask = silhouette.getchannel('A')
    expanded_mask = mask.filter(ImageFilter.MaxFilter(thickness * 2 + 1))
    outline_layer = Image.new('RGBA', img.size, (255, 255, 255, 255))
    outline_layer.putalpha(expanded_mask)
    result = Image.new('RGBA', img.size, (0, 0, 0, 0))
    result.paste(outline_layer, (0, 0), outline_layer)
    result.paste(img, (0, 0), img)
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

    grad = Image.new('RGB', (width, height))
    grad_d = ImageDraw.Draw(grad)
    for col in range(width):
        t = col / max(width - 1, 1)
        grad_d.line([(col, 0), (col, height - 1)],
                    fill=(int(lr + t*(rr-lr)), int(lg + t*(rg-lg)), int(lb + t*(rb-lb))))

    mask = Image.new('L', (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, width - 1, height - 1],
                                            radius=height // 2, fill=255)
    img.paste(grad, (x, y), mask)


def paste_logo_centered(bg_img, logo_img, center_x, center_y, target_height):
    if not logo_img:
        return
    aspect = logo_img.width / logo_img.height
    new_w = int(target_height * aspect)
    logo_resized = logo_img.resize((new_w, target_height), Image.Resampling.LANCZOS)
    logo_outlined = add_white_outline(logo_resized, thickness=4)
    paste_x = int(center_x - (logo_outlined.width / 2))
    paste_y = int(center_y - (logo_outlined.height / 2))
    bg_img.paste(logo_outlined, (paste_x, paste_y), logo_outlined)


# --- Main Image Generator ---

def create_match_image(data):
    log.info("Creating graphic: Arsenal vs %s", data['opponent'])
    width, height = 1080, 1500
    img = Image.new('RGB', (width, height), THEME["BG"])
    draw = ImageDraw.Draw(img)

    # Font scale
    f_xl = get_font(140)
    f_h = get_font(40)
    f_sm = get_font(28)
    f_num = get_font(36)
    f_ctx = get_font(22)
    f_wm = get_font(20)

    cx = width / 2

    # =========================================================
    # SCORE CONTAINER  [40, 40] → [1040, 590]
    # =========================================================
    score_box = (40, 40, 1040, 590)
    draw_shadow_rect(img, *score_box, radius=40)
    draw.rounded_rectangle(score_box, radius=40, fill=THEME["CONTAINER"])

    # "FULL TIME" label
    draw.text((80, 80), "FULL TIME", font=f_sm, fill=THEME["GOLD"])

    # Competition name (right-aligned)
    if data.get('competition'):
        comp_txt = data['competition'].upper()
        comp_bbox = draw.textbbox((0, 0), comp_txt, font=f_sm)
        draw.text((1040 - 40 - (comp_bbox[2] - comp_bbox[0]), 80),
                  comp_txt, font=f_sm, fill=THEME["TEXT_DIM"])

    # Score
    cy_score = 310
    score_txt = f"{data['ars_score']} - {data['opp_score']}"
    bbox = draw.textbbox((0, 0), score_txt, font=f_xl)
    sw = bbox[2] - bbox[0]
    sh = bbox[3] - bbox[1]
    draw.text((cx - sw / 2, cy_score - sh / 1.5), score_txt, font=f_xl, fill=THEME["TEXT"])

    # Badges
    badge_y = cy_score
    if data.get('ars_logo_img'):
        paste_logo_centered(img, data['ars_logo_img'], cx - sw / 2 - 120, badge_y, 180)
    if data.get('opp_logo_img'):
        paste_logo_centered(img, data['opp_logo_img'], cx + sw / 2 + 120, badge_y, 180)

    # Goalscorers (centered under badges)
    for goals, side_sign in [(data['ars_goals'], -1), (data['opp_goals'], 1)]:
        y_goals = badge_y + 110
        badge_cx = cx + side_sign * (sw / 2 + 120)
        for i, g in enumerate(goals):
            if i > 3:
                break
            bg = draw.textbbox((0, 0), g, font=f_sm)
            draw.text((badge_cx - (bg[2] - bg[0]) / 2, y_goals + (i * 35)),
                      g, font=f_sm, fill=THEME["TEXT_DIM"])

    # Venue / Attendance context line
    context_parts = []
    if data.get('venue'):
        context_parts.append(data['venue'])
    if data.get('attendance'):
        context_parts.append(f"Att: {data['attendance']:,}")
    if context_parts:
        ctx_txt = "  |  ".join(context_parts)
        ctx_bbox = draw.textbbox((0, 0), ctx_txt, font=f_ctx)
        draw.text((cx - (ctx_bbox[2] - ctx_bbox[0]) / 2, 555),
                  ctx_txt, font=f_ctx, fill=THEME["TEXT_DIM"])

    # =========================================================
    # DIVIDER LINE
    # =========================================================
    draw.line([(80, 605), (1000, 605)], fill="#333333", width=1)

    # =========================================================
    # STATS CONTAINER  [40, 620] → [1040, 1380]
    # =========================================================
    stats_box = (40, 620, 1040, 1380)
    draw_shadow_rect(img, *stats_box, radius=40)
    draw.rounded_rectangle(stats_box, radius=40, fill=THEME["CONTAINER"])

    # Header
    header_txt = "MATCH STATS"
    bbox_h = draw.textbbox((0, 0), header_txt, font=f_h)
    draw.text((cx - (bbox_h[2] - bbox_h[0]) / 2, 655), header_txt, font=f_h, fill=THEME["TEXT"])

    # ── Possession normalization ──
    p_a = data['ars_poss']
    p_o = data['opp_poss']
    if p_a + p_o != 100 and p_a + p_o > 0:
        diff = 100 - (p_a + p_o)
        if p_a >= p_o:
            p_a += diff
        else:
            p_o += diff

    # ── Build stat rows ──
    # Fixed order: POSSESSION → xG (conditional) → SHOTS → ON TARGET → PASS ACCURACY
    stats_data = [
        ("POSSESSION", f"{p_a}%", f"{p_o}%", True),
    ]

    # xG — only include when available
    if data.get('ars_xg') is not None and data.get('opp_xg') is not None:
        stats_data.append(("EXPECTED GOALS (xG)", f"{data['ars_xg']:.2f}", f"{data['opp_xg']:.2f}", False))

    stats_data.append(("SHOTS", data['ars_shots'], data['opp_shots'], False))
    stats_data.append(("ON TARGET", data['ars_sot'], data['opp_sot'], False))

    # Pass accuracy — always include when available
    if data.get('ars_pass_pct') is not None and data.get('opp_pass_pct') is not None:
        stats_data.append(("PASS ACCURACY", f"{data['ars_pass_pct']}%", f"{data['opp_pass_pct']}%", True))

    # ── Draw stat rows ──
    num_stats = len(stats_data)
    # Dynamically space rows within the available area (y 730 → 1340)
    stat_area_top = 730
    stat_area_bot = 1340
    row_step = min(110, (stat_area_bot - stat_area_top) // max(num_stats, 1))

    # Center the block vertically
    block_height = row_step * (num_stats - 1)
    y_start = stat_area_top + ((stat_area_bot - stat_area_top) - block_height) // 2

    bar_w = 320
    bar_h = 24

    for idx, (label, v_a, v_o, is_pct) in enumerate(stats_data):
        y_stat = y_start + idx * row_step

        # Label (centered)
        lb = draw.textbbox((0, 0), label, font=f_sm)
        draw.text((cx - (lb[2] - lb[0]) / 2, y_stat - 38), label, font=f_sm, fill=THEME["TEXT_DIM"])

        # Parse values
        safe_va = float(str(v_a).replace('%', '')) if v_a else 0
        safe_vo = float(str(v_o).replace('%', '')) if v_o else 0

        if "xG" in label:
            max_val = max(safe_va + safe_vo, 3.0)
        elif is_pct:
            max_val = 100
        else:
            max_val = max(safe_va + safe_vo, 15)

        len_a = min((safe_va / max_val) * 100, 100)
        len_o = min((safe_vo / max_val) * 100, 100)
        ars_winning = safe_va > safe_vo

        # Arsenal value + bar (right-anchored to center)
        draw.text((cx - 20 - bar_w - 90, y_stat - 10), str(v_a), font=f_num, fill=THEME["RED"])
        draw.rounded_rectangle(
            [cx - 20 - bar_w, y_stat, cx - 20, y_stat + bar_h],
            radius=bar_h // 2, fill=THEME["BAR_TRACK"])
        act_w = max(bar_h, int((len_a / 100) * bar_w))
        left_col = THEME["RED"] if ars_winning else THEME["RED_DIM"]
        right_col = THEME["RED_HI"] if ars_winning else THEME["RED"]
        draw_gradient_pill(img, int(cx - 20 - act_w), y_stat, act_w, bar_h, left_col, right_col)

        # Opponent value + bar (left-anchored from center)
        draw.text((cx + 20 + bar_w + 20, y_stat - 10), str(v_o), font=f_num, fill=THEME["TEXT"])
        draw.rounded_rectangle(
            [cx + 20, y_stat, cx + 20 + bar_w, y_stat + bar_h],
            radius=bar_h // 2, fill=THEME["BAR_TRACK"])
        opp_act_w = max(bar_h, int((len_o / 100) * bar_w))
        draw_gradient_pill(img, int(cx + 20), y_stat, opp_act_w, bar_h, THEME["BAR_TRACK"], THEME["BAR_OPP"])

    # =========================================================
    # FOOTER — watermark inside stats container, bottom-right
    # =========================================================
    footer_text = "GUNNER BOT"
    bbox_f = draw.textbbox((0, 0), footer_text, font=f_wm)
    draw.text((cx - (bbox_f[2] - bbox_f[0]) / 2, height - 70),
              footer_text, font=f_wm, fill=THEME["GOLD"])

    return img
