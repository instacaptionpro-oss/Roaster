"""
core/battle_card.py
===================
Overlays dynamic text on battle_template.png.
Fixes: no bar/text overlap, single match time, Roasts Landed (same total both sides).
"""

import os, random, tempfile
from PIL import Image, ImageDraw, ImageFont

TEMPLATE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "battle_template.png")
LOGO      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
W, H      = 1024, 1024
LOGO_BAR  = 90    # black bar height added above the template for logo

W_GOLD  = (255, 200,  35)
W_GOLD2 = (200, 145,  10)
W_BLUE  = ( 70, 145, 255)
W_WHITE = (225, 235, 255)
L_RED   = (220,  55,  15)
L_FIRE  = (255, 125,  20)
L_WHITE = (255, 210, 185)
WHITE   = (255, 255, 255)
GREY    = (170, 165, 180)

# Full interior of each panel — wipe these completely
LP = (36,  646, 484, 990)     # left  panel interior
RP = (542, 646, 990, 990)     # right panel interior

# Wipe the baked-in match time from template + our row
MT_WIPE = (150, 540, 875, 598)   # wide enough to kill template text


def _f(s, reg=False):
    try:    return ImageFont.truetype(FONT_REG if reg else FONT_BOLD, s)
    except: return ImageFont.load_default()

def _tw(d, t, f): return d.textlength(t, font=f)

def _glow(d, text, font, x, y, fill, gc, p=3, sp=7, a='lt'):
    if a == 'ct': x = int(x - _tw(d, text, font) / 2)
    if a == 'rt': x = int(x - _tw(d, text, font))
    r, g, b = gc
    for i in range(p, 0, -1):
        s = sp * i // p
        al = min(255, int(145 / i))
        for dx in range(-s, s+1, max(1, s//2)):
            for dy in range(-s, s+1, max(1, s//2)):
                d.text((x+dx, y+dy), text, font=font, fill=(r, g, b, al))
    d.text((x, y), text, font=font, fill=fill)

def _shadow(d, text, font, x, y, fill, a='lt', off=2):
    if a == 'ct': x = int(x - _tw(d, text, font) / 2)
    if a == 'rt': x = int(x - _tw(d, text, font))
    d.text((x+off, y+off), text, font=font, fill=(0, 0, 0, 180))
    d.text((x, y),          text, font=font, fill=fill)

def _bar(d, x, y, w, h, pct, col):
    """Progress bar with guaranteed spacing — caller must give correct y."""
    d.rectangle([x, y, x+w, y+h], fill=(10, 8, 20), outline=(50, 48, 65), width=1)
    fw = max(4, int(w * min(pct, 100) / 100))
    r, g, b = col
    for i in range(fw):
        br = 0.45 + 0.55 * (i / max(fw, 1))
        d.line([(x+i, y+1),(x+i, y+h-1)], fill=(int(r*br), int(g*br), int(b*br)))
    if fw > 3:
        d.line([(x+fw-1, y),(x+fw-1, y+h)], fill=col, width=2)

def _divider(d, x1, x2, y, col=(55, 52, 70)):
    d.line([(x1, y),(x2, y)], fill=col, width=1)

def _wrap(d, text, font, mw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if _tw(d, t, font) <= mw: cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def _shame(reason, dh, lr, wr):
    ratio = wr / max(lr, 1)
    pool = (["Tapped out. Couldn't take it.",
             "Waved the white flag. Pathetic.",
             "Quit mid-battle. Zero spine.",
             "Surrendered. This is your legacy."]
            if reason == "surrendered" else
            [f"Went silent for {dh}h. Classic.",
             "Clock finished what they couldn't.",
             "Timed out. Ran out of words.",
             "Ghosted the battle. Very brave."])
    if ratio >= 3: pool.append(f"Outroasted {ratio:.0f}x. Not even close.")
    return random.choice(pool)

def _quote(topic):
    return random.choice([
        f"Destroyed {topic} without breaking a sweat.",
        "Left them with absolutely no comeback.",
        "The roast heard around the world.",
        f"{topic} never recovered from this.",
        "Savage. Clean. Untouchable.",
    ])


def generate_battle_card(battle_data: dict) -> str:
    bid    = battle_data.get("battle_id",    "RB-00000")
    winner = battle_data.get("winner_name",  "WINNER").upper()
    loser  = battle_data.get("loser_name",   "LOSER").upper()
    wr     = int(battle_data.get("winner_roasts", 0))
    lr     = int(battle_data.get("loser_roasts",  0))
    dh     = int(battle_data.get("duration_hrs",  0))
    dm     = int(battle_data.get("duration_mins", 0))
    reason = battle_data.get("loss_reason", "timeout").lower()
    total  = int(battle_data.get("total_rounds", max(wr+lr, 1)))
    topic  = battle_data.get("topic", "Unknown")

    # Both fought same total rounds — difference is roasts LANDED
    w_dom   = min(99, wr * 100 // max(total, 1))
    l_dom   = max(4,  min(25, lr * 100 // max(total, 1)))
    dur     = f"{dh}:{dm:02d}"
    shame   = _shame(reason, dh, lr, wr)
    quote   = _quote(topic)
    r_lbl   = "Knockout" if reason == "timeout" else "Surrender"
    d_time  = f"Round {total}  ·  {dh:02d}:{dm:02d}"

    # ── Load template — paste below logo bar ─────────────────
    template_img = Image.open(TEMPLATE).convert("RGBA")
    template_img = template_img.resize((W, H), Image.LANCZOS)

    # New canvas = logo bar on top + template below
    img  = Image.new("RGBA", (W, H + LOGO_BAR), (0, 0, 0, 255))
    img.paste(template_img, (0, LOGO_BAR))
    draw = ImageDraw.Draw(img, 'RGBA')

    # ── LOGO BAR — black bg, logo centered ───────────────────
    if os.path.exists(LOGO):
        logo     = Image.open(LOGO).convert("RGBA")
        logo_h   = LOGO_BAR - 10           # slight padding top/bottom
        logo_w   = logo_h                   # square logo
        logo     = logo.resize((logo_w, logo_h), Image.LANCZOS)
        logo_x   = (W - logo_w) // 2
        logo_y   = 5
        img.alpha_composite(logo, dest=(logo_x, logo_y))

    # Thin fire-red separator line under logo bar
    draw.rectangle([0, LOGO_BAR - 2, W, LOGO_BAR], fill=(200, 40, 10))

    # All subsequent y positions are offset by LOGO_BAR
    Y = LOGO_BAR   # use this offset for everything below

    # ── WIPE panels + match time completely ───────────────────
    draw.rectangle([LP[0], LP[1]+Y, LP[2], LP[3]+Y], fill=(14, 11, 24, 252))
    draw.rectangle([RP[0], RP[1]+Y, RP[2], RP[3]+Y], fill=(22,  8,  5, 252))
    draw.rectangle([MT_WIPE[0], MT_WIPE[1]+Y, MT_WIPE[2], MT_WIPE[3]+Y], fill=(6, 4, 14, 245))

    # ─────────────────────────────────────────────────────────
    # MATCH TIME — single, centered, clean
    # ─────────────────────────────────────────────────────────
    _shadow(draw, f"Match Time:  {dur}", _f(25), 512, 553+Y, WHITE, a='ct')

    # ─────────────────────────────────────────────────────────
    # LEFT PANEL — Winner stats
    # ─────────────────────────────────────────────────────────
    LX  = LP[0] + 18
    LXR = LP[2] - 18
    LBW = LP[2] - LP[0] - 36
    lf2 = _f(21, reg=True)
    vf  = _f(28)
    smf = _f(18, reg=True)
    BAR_H = 15

    y = LP[1] + 16 + Y

    # Roasts Landed
    draw.text((LX, y), "Roasts Landed:", font=lf2, fill=GREY)
    _glow(draw, f"{wr}/{total}", vf, LXR, y-2, W_WHITE, W_BLUE, p=2, sp=5, a='rt')
    y += 32
    _bar(draw, LX, y, LBW, BAR_H, w_dom, (55, 135, 255))
    y += BAR_H + 20

    # Dominance Score
    draw.text((LX, y), "Dominance Score:", font=lf2, fill=GREY)
    _glow(draw, f"{w_dom}%", vf, LXR, y-2, W_GOLD, W_GOLD2, p=2, sp=5, a='rt')
    y += 32
    _bar(draw, LX, y, LBW, BAR_H, w_dom, (195, 95, 8))
    y += BAR_H + 20

    # Divider
    _divider(draw, LX, LXR, y)
    y += 14

    # Best Roast
    _glow(draw, "Best Roast:", _f(21), LX, y, W_GOLD, W_GOLD2, p=1, sp=3)
    y += 30
    for ql in _wrap(draw, f'"{quote}"', smf, LBW)[:3]:
        _shadow(draw, ql, smf, LX, y, WHITE)
        y += 25

    # Winner name pinned to panel bottom
    _divider(draw, LX, LXR, LP[3]+Y-46, col=(60, 58, 80))
    _glow(draw, winner, _f(30), LX, LP[3]+Y-40, W_GOLD, W_GOLD2, p=3, sp=7)

    # ─────────────────────────────────────────────────────────
    # RIGHT PANEL — Loser stats
    # ─────────────────────────────────────────────────────────
    RX  = RP[0] + 18
    RXR = RP[2] - 18
    RBW = RP[2] - RP[0] - 36

    y = RP[1] + 16 + Y

    # Roasts Landed
    draw.text((RX, y), "Roasts Landed:", font=lf2, fill=GREY)
    _glow(draw, f"{lr}/{total}", vf, RXR, y-2, L_WHITE, L_RED, p=2, sp=5, a='rt')
    y += 32
    _bar(draw, RX, y, RBW, BAR_H, l_dom, (195, 35, 8))
    y += BAR_H + 20

    # Dominance Score
    draw.text((RX, y), "Dominance Score:", font=lf2, fill=GREY)
    _glow(draw, f"{l_dom}%", vf, RXR, y-2, L_FIRE, L_RED, p=2, sp=5, a='rt')
    y += 32
    _bar(draw, RX, y, RBW, BAR_H, l_dom, (170, 55, 4))
    y += BAR_H + 20

    # Divider
    _divider(draw, RX, RXR, y, col=(70, 35, 25))
    y += 14

    # Reason for Loss
    draw.text((RX, y), "Reason for Loss:", font=lf2, fill=GREY)
    _glow(draw, r_lbl, vf, RXR, y-2, WHITE, L_RED, p=2, sp=5, a='rt')
    y += 40

    # Time of Defeat
    draw.text((RX, y), "Time of Defeat:", font=lf2, fill=GREY)
    _shadow(draw, d_time, _f(21), RXR, y+3, WHITE, a='rt')
    y += 40

    # Shame line
    _divider(draw, RX, RXR, y, col=(70, 35, 25))
    y += 12
    for sl in _wrap(draw, shame, _f(17, reg=True), RBW)[:2]:
        draw.text((RX, y), sl, font=_f(17, reg=True), fill=(210, 100, 80))
        y += 23

    # Loser name pinned to panel bottom
    _divider(draw, RX, RXR, RP[3]+Y-46, col=(70, 30, 20))
    _glow(draw, loser, _f(30), RXR, RP[3]+Y-40, L_RED, L_FIRE, p=3, sp=7, a='rt')

    # ─────────────────────────────────────────────────────────
    # WATERMARK — bottom center
    # ─────────────────────────────────────────────────────────
    wm  = f"roasterai.com  ·  #{bid}"
    wmf = _f(14, reg=True)
    draw.text(((W - int(_tw(draw, wm, wmf))) // 2, H + Y - 16),
              wm, font=wmf, fill=(85, 82, 95, 185))

    # ── Save ─────────────────────────────────────────────────
    out = img.convert("RGB")
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", prefix=f"battle_{bid}_", delete=False)
    out.save(tmp.name, "JPEG", quality=96)
    tmp.close()
    return tmp.name


if __name__ == "__main__":
    path = generate_battle_card({
        "battle_id":     "RB-00421",
        "winner_name":   "Arjun",
        "loser_name":    "Rahul",
        "winner_roasts": 7,
        "loser_roasts":  2,
        "duration_hrs":  18,
        "duration_mins": 42,
        "loss_reason":   "timeout",
        "total_rounds":  9,
        "topic":         "My Ex",
    })
    print(f"Saved: {path}")
