"""
Generates visual dashboard cards using Pillow.
Dark amber/gold theme matching egg's identity.
"""

import io, httpx, asyncio
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Colors
BG       = "#0D0D0D"
AMBER    = "#F5A623"
GOLD     = "#FFD700"
WHITE    = "#FFFFFF"
GRAY     = "#888888"
GREEN    = "#4CAF50"
RED      = "#F44336"
CARD_BG  = "#1A1A1A"


def _font(size: int, bold=False):
    try:
        name = "arialbd.ttf" if bold else "arial.ttf"
        return ImageFont.truetype(name, size)
    except:
        return ImageFont.load_default()


def _progress_bar(draw, x, y, w, h, pct, color=AMBER, bg="#2A2A2A"):
    draw.rounded_rectangle([x, y, x+w, y+h], radius=h//2, fill=bg)
    if pct > 0:
        fill_w = max(h, int(w * min(pct, 100) / 100))
        draw.rounded_rectangle([x, y, x+fill_w, y+h], radius=h//2, fill=color)


async def generate_dashboard(data: dict) -> io.BytesIO:
    W, H = 800, 600
    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Header
    draw.rectangle([0, 0, W, 80], fill=CARD_BG)
    draw.text((20, 20), "🥚 EGG LAUNCHER", font=_font(28, bold=True), fill=GOLD)
    draw.text((20, 55), "the living launchpad", font=_font(14), fill=GRAY)

    # Stats row
    stats = [
        ("🚀 LAUNCHES", str(data.get("total", 0))),
        ("🎓 GRADUATED", str(data.get("graduated", 0))),
        ("💰 TREASURY", f"{data.get('treasury_ton', 0):.1f} TON"),
    ]
    sx = 20
    for label, val in stats:
        draw.rounded_rectangle([sx, 100, sx+230, 180], radius=8, fill=CARD_BG)
        draw.text((sx+12, 112), label, font=_font(11), fill=GRAY)
        draw.text((sx+12, 135), val, font=_font(22, bold=True), fill=AMBER)
        sx += 250

    # Trending tokens
    draw.text((20, 200), "🔥 TRENDING", font=_font(16, bold=True), fill=WHITE)
    tokens = data.get("trending", [])
    ty = 230
    for i, t in enumerate(tokens[:5]):
        pct = t.get("progress", 0)
        color = GOLD if pct >= 80 else AMBER
        draw.text((20, ty), f"${t['ticker']}", font=_font(15, bold=True), fill=color)
        draw.text((160, ty+2), f"by @{t.get('creator_username','?')}", font=_font(12), fill=GRAY)
        draw.text((500, ty+2), f"{t.get('real_ton', 0):.0f}/500 TON", font=_font(12), fill=GRAY)
        _progress_bar(draw, 20, ty+22, W-40, 8, pct, color=color)
        ty += 50

    # Hall of fame
    graduated = data.get("graduated_tokens", [])
    if graduated:
        draw.text((20, ty+10), "🏆 HALL OF FAME", font=_font(14, bold=True), fill=GOLD)
        gx = 20
        for t in graduated[:4]:
            draw.rounded_rectangle([gx, ty+35, gx+175, ty+65], radius=6, fill="#1F1F00")
            draw.text((gx+8, ty+43), f"${t['ticker']}", font=_font(13, bold=True), fill=GOLD)
            gx += 185

    # Footer
    draw.rectangle([0, H-40, W, H], fill=CARD_BG)
    draw.text((20, H-28), "/launch to deploy your token", font=_font(13), fill=GRAY)
    draw.text((W-200, H-28), "t.me/EggonTon", font=_font(13), fill=AMBER)

    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf


async def generate_token_card(token: dict) -> io.BytesIO:
    W, H = 800, 420
    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    pct   = token.get("progress", 0)
    color = GOLD if pct >= 80 else AMBER

    # Header bar
    draw.rectangle([0, 0, W, 70], fill=CARD_BG)
    draw.text((20, 12), f"${token['ticker']}", font=_font(32, bold=True), fill=color)
    draw.text((20, 48), token.get("name", ""), font=_font(16), fill=GRAY)
    draw.text((W-180, 22), "🥚 egg-certified" if token.get("certified") else "", font=_font(13), fill=AMBER)

    # Token image (if available)
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(token.get("image_url", ""), timeout=5)
            if r.status_code == 200:
                tok_img = Image.open(io.BytesIO(r.content)).convert("RGB")
                tok_img = tok_img.resize((120, 120))
                img.paste(tok_img, (W-140, 80))
    except:
        pass

    # Bonding curve progress
    draw.text((20, 90), "BONDING CURVE", font=_font(11), fill=GRAY)
    draw.text((20, 110), f"{token.get('real_ton', 0):.1f} / 500 TON", font=_font(22, bold=True), fill=WHITE)
    _progress_bar(draw, 20, 145, W-180, 18, pct, color=color)
    draw.text((W-170, 148), f"{pct:.0f}%", font=_font(14, bold=True), fill=color)

    # Stats
    stats = [
        ("PRICE",   f"{token.get('price', 0) / 1e9:.8f} TON"),
        ("TRADES",  str(token.get("trade_count", 0))),
        ("CREATOR", f"@{token.get('creator_username', '?')}"),
        ("DEX",     token.get("dex_choice", "dedust").upper()),
    ]
    sx = 20
    for label, val in stats:
        draw.text((sx, 185), label, font=_font(10), fill=GRAY)
        draw.text((sx, 202), val,   font=_font(14, bold=True), fill=WHITE)
        sx += 185

    # Description
    desc = token.get("description", "")[:80]
    draw.text((20, 250), desc, font=_font(13), fill=GRAY)

    # Graduation status
    if token.get("graduated"):
        draw.rounded_rectangle([20, 280, W-20, 330], radius=8, fill="#1F2D00")
        draw.text((40, 295), "🎓 GRADUATED — trading on DEX", font=_font(16, bold=True), fill=GOLD)
    else:
        remaining = 500 - token.get("real_ton", 0)
        draw.rounded_rectangle([20, 280, W-20, 330], radius=8, fill=CARD_BG)
        draw.text((40, 292), f"🎯 {remaining:.0f} TON until graduation", font=_font(14), fill=AMBER)

    # Footer
    draw.rectangle([0, H-45, W, H], fill=CARD_BG)
    draw.text((20, H-32), "buy via mini app or /buy command", font=_font(12), fill=GRAY)
    draw.text((W-200, H-32), "🥚 egg launcher", font=_font(12), fill=AMBER)

    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf
