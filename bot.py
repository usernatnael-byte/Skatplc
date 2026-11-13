import os
import asyncio
import logging
import threading
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    InputFile, WebAppInfo
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from models import db, User, Game, GameParticipant, Transaction, ScheduledGame
from utils import get_lang, referral_link, is_valid_tx_id
from sqlalchemy import func
from config import WEBAPP_URL, ADMIN_IDS, TELEGRAM_BOT_TOKEN
import game

# The web application and bot share one SQLAlchemy instance and schema.
from app import app as flask_app

# ------------------------------------------------------
# Logging setup
# ------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------------------------------------
# Telegram bot setup
# ------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN") or TELEGRAM_BOT_TOKEN
if not BOT_TOKEN:
    raise RuntimeError("Set BOT_TOKEN (or TELEGRAM_BOT_TOKEN) in the environment")

telegram_app = Application.builder().token(BOT_TOKEN).build()

# ------------------------------------------------------
# COMMAND HANDLERS
# ------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "unknown"
    with flask_app.app_context():
        user = User.query.filter_by(telegram_id=telegram_id).first()
        if not user:
            user = User(telegram_id=telegram_id, username=username, balance=0)
            db.session.add(user)
            db.session.commit()
    lang = get_lang(context)
    await update.message.reply_text(lang["welcome"])

async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    context.chat_data["deposit_method"] = "cbe_birr"
    await update.message.reply_text(lang["deposit"])

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    await update.message.reply_text(lang["withdraw"])

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.effective_user.id)
    user = User.query.filter_by(telegram_id=telegram_id).first()
    if user:
        lang = get_lang(context)
        await update.message.reply_text(f"{lang['balance']}: {user.balance} birr")
    else:
        await update.message.reply_text("❌ You must start the bot first using /start.")

async def referral_contest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    telegram_id = str(update.effective_user.id)
    link = referral_link(telegram_id)
    await update.message.reply_text(f"{lang['referral_contest']}:\n{link}")

async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.effective_user.id)
    lang = get_lang(context)
    link = referral_link(telegram_id)
    await update.message.reply_text(f"{lang['invite']}: {link}")

async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌐 Choose your language:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🇬🇧 English", callback_data="toggle_lang:en")],
            [InlineKeyboardButton("🇪🇹 አማርኛ", callback_data="toggle_lang:am")]
        ])
    )

async def play_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    lang = get_lang(context)
    await update.message.reply_text(
        f"{lang['play']}...",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🧩 Open Game WebApp", web_app=WebAppInfo(url=f"{WEBAPP_URL}?id={telegram_id}"))]
        ])
    )
    game.start_game(chat_id=update.effective_chat.id, context=context)

async def call_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = game.call_number(chat_id=update.effective_chat.id, context=context)
    if result:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"🎱 {result['formatted']}")
        try:
            await context.bot.send_voice(chat_id=update.effective_chat.id, voice=InputFile("audio/number_call_am.ogg"))
        except Exception:
            pass
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="✅ Game finished!")

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    lb = game.get_leaderboard()
    if not lb:
        await update.message.reply_text(f"{lang['leaderboard']}: No winners yet.")
        return
    lines = [lang["leaderboard"]]
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, wins, earnings) in enumerate(lb):
        user = User.query.get(uid)
        medal = medals[i] if i < 3 else "🔹"
        lines.append(f"{medal} @{user.username} – {wins} wins, {earnings} birr")
    await update.message.reply_text("\n".join(lines))

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    s = game.summary(update.effective_chat.id)
    lines = [
        f"{lang['summary']}:",
        f"Game #{s['game_id']}",
        f"Status: {s['status']}",
        f"Players: {s['players']}",
        f"Pool: {s['pool']} birr",
        f"Called Numbers: {s['called']}",
        f"Winner: @{User.query.get(s['winner']).username}" if s['winner'] else "Winner: —",
        f"Admin Earnings: {s['admin_earnings']} birr"
    ]
    await update.message.reply_text("\n".join(lines))

async def mycartela(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.effective_user.id)
    user = User.query.filter_by(telegram_id=telegram_id).first()
    summary = game.get_player_summary(user.id)
    if not summary:
        await update.message.reply_text("🧩 You have no active cartelas.")
        return
    lines = ["🧩 Your Cartelas:"]
    for c in summary:
        lines.append(f"Cartela #{c['cartela_number']}: marked {len(c['marked'])} numbers")
        lines.append(f"🔢 {sorted(c['marked'])}")
    await update.message.reply_text("\n".join(lines))

async def mygames(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.effective_user.id)
    user = User.query.filter_by(telegram_id=telegram_id).first()
    games = GameParticipant.query.filter_by(user_id=user.id).order_by(GameParticipant.id.desc()).limit(5).all()
    lines = ["📜 Your Recent Games:"]
    for g in games:
        lines.append(f"Game #{g.game_id} – Cartela #{g.cartela_number} – Marked: {len(g.marked_numbers)}")
    await update.message.reply_text("\n".join(lines))

async def referrals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.effective_user.id)
    user = User.query.filter_by(telegram_id=telegram_id).first()
    active_refs = [u for u in user.referred_users if u.games_played > 0]
    link = referral_link(telegram_id)
    lang = get_lang(context)
    await update.message.reply_text(f"{lang['referrals']}: {len(active_refs)} active\nLink: {link}")

async def toggle_sound(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.effective_user.id)
    user = User.query.filter_by(telegram_id=telegram_id).first()
    user.sound_enabled = not user.sound_enabled
    db.session.commit()
    lang = get_lang(context)
    status = lang["toggle_sound"] + (" ✅ ON" if user.sound_enabled else " ❌ OFF")
    await update.message.reply_text(status)

async def report_bug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    await update.message.reply_text(lang["report_bug"])

async def schedule_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Only admins can schedule games.")
        return
    sg = ScheduledGame(entry_price=10.0, status="pending")
    db.session.add(sg)
    db.session.commit()
    lang = get_lang(context)
    await update.message.reply_text(f"{lang['schedule_game']}: Game #{sg.id} created.")

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Only admins can broadcast.")
        return
    message = " ".join(context.args)
    users = User.query.all()
    for u in users:
        try:
            await context.bot.send_message(chat_id=int(u.telegram_id), text=message)
        except Exception:
            continue
    lang = get_lang(context)
    await update.message.reply_text(f"{lang['broadcast']}: Sent.")

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_users = User.query.count()
    total_games = Game.query.count()
    total_balance = db.session.query(func.sum(User.balance)).scalar() or 0
    lang = get_lang(context)
    await update.message.reply_text(
        f"{lang['adminstats']}:\nUsers: {total_users}\nGames: {total_games}\nTotal Balance: {total_balance} birr"
    )

async def cartela_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    await update.message.reply_text(f"{lang['cartela_preview']}: Coming soon.")

# ------------------------------------------------------
# Message input + error handling
# ------------------------------------------------------
async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return
    telegram_id = str(update.effective_user.id)
    text = update.message.text.strip()

    with flask_app.app_context():
        user = User.query.filter_by(telegram_id=telegram_id).first()
        if not user:
            await update.message.reply_text("❌ You must start the bot first using /start.")
            return

        if text.startswith("edit:"):
            user.cartela = text.replace("edit:", "").strip()
            db.session.commit()
            await update.message.reply_text("✅ Cartela updated.")
            return

        if "deposit_method" in context.chat_data:
            method = context.chat_data["deposit_method"]
            if not is_valid_tx_id(text):
                await update.message.reply_text("❌ Invalid transaction ID. Please try again.")
                return
            tx = Transaction(user_id=user.id, type="deposit", amount=0,
                             method=method, status="pending", reference=text)
            db.session.add(tx)
            db.session.commit()
            await update.message.reply_text("✅ Transaction received. Awaiting admin approval.")
            return

        try:
            amount = int(text)
            if amount <= 0 or amount > user.balance:
                await update.message.reply_text("❌ Invalid amount or insufficient balance.")
                return
            tx = Transaction(user_id=user.id, type="withdraw", amount=amount, status="pending")
            db.session.add(tx)
            db.session.commit()
            await update.message.reply_text(f"✅ Withdrawal request for {amount} birr submitted.")
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid number.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception while handling an update:", exc_info=context.error)
    if isinstance(update, Update) and update.message:
        await update.message.reply_text("⚠️ Something went wrong. Please try again.")

# ------------------------------------------------------
# Startup: run as a dedicated Render Background Worker (polling mode).
# ------------------------------------------------------
def register_handlers():
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("deposit", deposit))
    telegram_app.add_handler(CommandHandler("withdraw", withdraw))
    telegram_app.add_handler(CommandHandler("balance", balance))
    telegram_app.add_handler(CommandHandler("referral_contest", referral_contest))
    telegram_app.add_handler(CommandHandler("invite", invite))
    telegram_app.add_handler(CommandHandler("language", language))
    telegram_app.add_handler(CommandHandler("play", play_game))
    telegram_app.add_handler(CommandHandler("call", call_number))
    telegram_app.add_handler(CommandHandler("leaderboard", leaderboard))
    telegram_app.add_handler(CommandHandler("summary", summary))
    telegram_app.add_handler(CommandHandler("mycartela", mycartela))
    telegram_app.add_handler(CommandHandler("mygames", mygames))
    telegram_app.add_handler(CommandHandler("referrals", referrals))
    telegram_app.add_handler(CommandHandler("toggle_sound", toggle_sound))
    telegram_app.add_handler(CommandHandler("report_bug", report_bug))
    telegram_app.add_handler(CommandHandler("schedule_game", schedule_game))
    telegram_app.add_handler(CommandHandler("broadcast", admin_broadcast))
    telegram_app.add_handler(CommandHandler("adminstats", admin_stats))
    telegram_app.add_handler(CommandHandler("cartela_preview", cartela_preview))
    telegram_app.add_handler(CallbackQueryHandler(language, pattern="toggle_lang"))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input))
    telegram_app.add_error_handler(error_handler)


if __name__ == "__main__":
    logging.info("Starting Efona Bingo Telegram polling worker")
    register_handlers()
    # Keep the Flask application context active for SQLAlchemy in handlers.
    with flask_app.app_context():
        telegram_app.run_polling(drop_pending_updates=True)
