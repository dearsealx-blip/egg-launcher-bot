"""
EGG LAUNCHER BOT
Handles: /launch, /token, /dashboard, /follow, /portfolio
Integrates with egg's existing bot.py character
"""

import os, json, asyncio, logging, httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, ContextTypes
)
from dashboard_image import generate_dashboard, generate_token_card

log = logging.getLogger("egg.launcher")

API_URL     = os.getenv("LAUNCHER_API_URL", "http://localhost:3000")
BOT_TOKEN   = os.getenv("TELEGRAM_TOKEN")
EGG_CHANNEL = int(os.getenv("CHAT_ID", "0"))
PINATA_JWT  = os.getenv("PINATA_JWT")

# ── Conversation states ───────────────────────────────────────────────────────
NAME, TICKER, DESCRIPTION, IMAGE, DEX_CHOICE, CONFIRM = range(6)

# ── /launch ───────────────────────────────────────────────────────────────────

async def cmd_launch(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username or ""

    await update.message.reply_text(
        "🥚 *egg launcher* — deploy your token on TON\n\n"
        "Fee: *1 TON* to launch\n"
        "You earn: *0.2% of every trade* forever\n"
        "Graduation: *500 TON* → real DEX pool\n\n"
        "Let's start. What's your token name?",
        parse_mode="Markdown"
    )
    ctx.user_data["tg_id"]       = user.id
    ctx.user_data["tg_username"] = username
    return NAME


async def got_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if len(name) > 32:
        await update.message.reply_text("Too long. Max 32 chars.")
        return NAME
    ctx.user_data["name"] = name
    await update.message.reply_text(f"Token ticker? (e.g. MOON, max 8 chars)")
    return TICKER


async def got_ticker(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ticker = update.message.text.strip().upper().replace("$", "")
    username = ctx.user_data.get("tg_username", "")

    if len(ticker) > 8:
        await update.message.reply_text("Max 8 characters.")
        return TICKER

    # Username verification
    if username:
        # Ticker must match username (first word, case insensitive)
        base = username.split("_")[0].upper()
        if ticker != base and ticker != username.upper():
            await update.message.reply_text(
                f"⚠️ @{username} can only launch ${base} or ${username.upper()}\n\n"
                f"Your username is your token. No squatting.",
            )
            return TICKER

    # Check not already taken
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_URL}/api/tokens/{ticker}")
        if r.status_code == 200:
            await update.message.reply_text(f"${ticker} already exists. Choose another.")
            return TICKER

    ctx.user_data["ticker"] = ticker
    await update.message.reply_text("Short description (max 100 chars):")
    return DESCRIPTION


async def got_description(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    desc = update.message.text.strip()[:100]
    ctx.user_data["description"] = desc
    await update.message.reply_text("Send your token image (jpg/png):")
    return IMAGE


async def got_image(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("Please send an image.")
        return IMAGE

    # Get largest photo
    photo = update.message.photo[-1]
    file = await ctx.bot.get_file(photo.file_id)

    # Upload to IPFS via Pinata
    import io
    file_bytes = await file.download_as_bytearray()

    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.pinata.cloud/pinning/pinFileToIPFS",
            headers={"Authorization": f"Bearer {PINATA_JWT}"},
            files={"file": (f"{ctx.user_data['ticker'].lower()}.jpg", bytes(file_bytes), "image/jpeg")},
        )
        if r.status_code != 200:
            await update.message.reply_text("Image upload failed. Try again.")
            return IMAGE
        ipfs_hash = r.json()["IpfsHash"]
        image_url = f"https://gateway.pinata.cloud/ipfs/{ipfs_hash}"

    ctx.user_data["image_url"] = image_url
    await update.message.reply_text(
        "Choose graduation DEX:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("DeDust", callback_data="dex_dedust"),
            InlineKeyboardButton("STON.fi", callback_data="dex_stonfi"),
        ]])
    )
    return DEX_CHOICE


async def got_dex(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    dex = "dedust" if query.data == "dex_dedust" else "stonfi"
    ctx.user_data["dex_choice"] = dex

    d = ctx.user_data
    await query.edit_message_text(
        f"🥚 *Review your token:*\n\n"
        f"Name: *{d['name']}*\n"
        f"Ticker: *${d['ticker']}*\n"
        f"Description: {d['description']}\n"
        f"Graduation DEX: *{dex.upper()}*\n\n"
        f"Fee: *1 TON* to egg wallet\n"
        f"Send 1.2 TON to:\n`UQCPMM8-ORuo7XVypJdcKQe5Cg_rLTjD09SyxKvyYSKoeRuc`\n"
        f"With comment: `LAUNCH_{d['ticker']}`\n\n"
        f"egg will deploy your token automatically.",
        parse_mode="Markdown"
    )
    return CONFIRM


async def cancel_launch(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("launch cancelled.")
    ctx.user_data.clear()
    return ConversationHandler.END


# ── /token $TICKER ────────────────────────────────────────────────────────────

async def cmd_token(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if not args:
        await update.message.reply_text("Usage: /token TICKER")
        return

    ticker = args[0].upper().replace("$", "")
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_URL}/api/tokens/{ticker}")
        if r.status_code != 200:
            await update.message.reply_text(f"${ticker} not found.")
            return
        token = r.json()

    # Generate token card image
    img = await generate_token_card(token)
    await update.message.reply_photo(
        photo=img,
        caption=f"${ticker} — {token['real_ton']:.1f}/500 TON",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📊 Chart", url=f"https://dexscreener.com/ton/{token.get('jetton_address','')}"),
            InlineKeyboardButton("🔔 Follow", callback_data=f"follow_{ticker}"),
            InlineKeyboardButton("🌐 Mini App", url=f"https://t.me/EggLauncherBot/app?startapp={ticker}"),
        ]])
    )


# ── /dashboard ────────────────────────────────────────────────────────────────

async def cmd_dashboard(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_URL}/api/dashboard")
        if r.status_code != 200:
            await update.message.reply_text("dashboard unavailable")
            return
        data = r.json()

    img = await generate_dashboard(data)
    await update.message.reply_photo(
        photo=img,
        caption="🥚 egg launcher — live stats",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🚀 Launch Token", callback_data="start_launch"),
            InlineKeyboardButton("📱 Mini App", url="https://t.me/EggLauncherBot/app"),
        ]])
    )


# ── /follow TICKER ────────────────────────────────────────────────────────────

async def cmd_follow(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if not args:
        await update.message.reply_text("Usage: /follow TICKER")
        return

    ticker = args[0].upper().replace("$", "")
    tg_id  = update.effective_user.id

    async with httpx.AsyncClient() as client:
        r = await client.post(f"{API_URL}/api/tokens/{ticker}/follow", json={"tg_id": tg_id})
        if r.status_code == 200:
            await update.message.reply_text(
                f"🔔 following ${ticker}\n"
                f"egg will notify you on big moves and graduation."
            )
        else:
            await update.message.reply_text(f"${ticker} not found.")


# ── Callback handler ──────────────────────────────────────────────────────────

async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("follow_"):
        ticker = data[7:]
        tg_id  = update.effective_user.id
        async with httpx.AsyncClient() as client:
            await client.post(f"{API_URL}/api/tokens/{ticker}/follow", json={"tg_id": tg_id})
        await query.edit_message_caption(
            caption=f"🔔 following ${ticker}. egg will alert you.",
            reply_markup=query.message.reply_markup
        )

    elif data == "start_launch":
        await query.message.reply_text("use /launch to deploy your token.")


# ── Egg verdict (called from watcher) ────────────────────────────────────────

async def post_egg_verdict(bot, token: dict, event: str):
    """Post egg's character verdict for a token event."""
    from anthropic import Anthropic
    ai = Anthropic(api_key=os.getenv("ANTHROPIC_KEY"))

    prompts = {
        "launch": f"egg has observed a new token: ${token['ticker']} by @{token.get('creator_username','unknown')}. description: {token.get('description','')}. write egg's cryptic verdict. 2 sentences max. lowercase. no hashtags.",
        "graduation": f"${token['ticker']} has reached 500 TON and graduated. write egg's reaction in character. triumphant but cryptic. 2 sentences.",
        "death": f"${token['ticker']} has been abandoned on the bonding curve. write egg's eulogy. dry humor. 1-2 sentences.",
    }

    r = ai.messages.create(
        model="claude-haiku-4-5",
        max_tokens=150,
        messages=[{"role": "user", "content": prompts.get(event, prompts["launch"])}]
    )
    verdict = r.content[0].text.strip()

    await bot.send_message(
        chat_id=EGG_CHANNEL,
        text=f"🥚 {verdict}\n\n"
             f"${token['ticker']} — /token {token['ticker']}",
    )


# ── App setup ─────────────────────────────────────────────────────────────────

def setup_launcher_handlers(app: Application):
    """Add launcher handlers to existing egg bot app."""

    launch_conv = ConversationHandler(
        entry_points=[CommandHandler("launch", cmd_launch)],
        states={
            NAME:        [MessageHandler(filters.TEXT & ~filters.COMMAND, got_name)],
            TICKER:      [MessageHandler(filters.TEXT & ~filters.COMMAND, got_ticker)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_description)],
            IMAGE:       [MessageHandler(filters.PHOTO, got_image)],
            DEX_CHOICE:  [CallbackQueryHandler(got_dex, pattern="^dex_")],
            CONFIRM:     [MessageHandler(filters.TEXT & ~filters.COMMAND, cancel_launch)],
        },
        fallbacks=[CommandHandler("cancel", cancel_launch)],
    )

    app.add_handler(launch_conv)
    app.add_handler(CommandHandler("token",     cmd_token))
    app.add_handler(CommandHandler("dashboard", cmd_dashboard))
    app.add_handler(CommandHandler("follow",    cmd_follow))
    app.add_handler(CallbackQueryHandler(on_callback))

    log.info("launcher handlers registered")
