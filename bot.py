"""Telegram polling worker using the same Cloud Firestore database as app.py."""
import logging
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from config import WEBAPP_URL, ADMIN_IDS
from models import create_user, get_user, create_transaction, db

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("efona-bingo")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg = update.effective_user
    create_user(tg.id, tg.username or "unknown")
    if context.args and context.args[0].isdigit():
        referrer = context.args[0]
        if referrer != str(tg.id):
            db.collection("users").document(str(tg.id)).set({"referred_by": referrer}, merge=True)
    keyboard = [[InlineKeyboardButton("🎮 Play Bingo", web_app=WebAppInfo(url=WEBAPP_URL))],
                [InlineKeyboardButton("💰 Balance", callback_data="balance")]]
    await update.message.reply_text(
        "እንኳን ወደ Efona Bingo በደህና መጡ!\nWelcome to Efona Bingo!",
        reply_markup=InlineKeyboardMarkup(keyboard))


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    amount = float((user or {}).get("balance", 0))
    await update.message.reply_text(f"💰 Your balance: {amount:.2f} ETB")


async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["pending_action"] = "deposit"
    await update.message.reply_text("Send deposit amount and transaction reference separated by a comma. Example: 100, ABC12345")


async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["pending_action"] = "withdraw"
    await update.message.reply_text("Send withdrawal amount and phone number separated by a comma. Example: 100, 09XXXXXXXX")


async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Language setting will be available soon. /start to open the game.")


async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    url = f"{WEBAPP_URL}?tgWebAppStartParam={user_id}"
    await update.message.reply_text("Open the Bingo game:", reply_markup=InlineKeyboardMarkup(
        [[InlineKeyboardButton("🎮 Open Bingo", web_app=WebAppInfo(url=url))]]))


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = context.user_data.get("pending_action")
    if not action:
        await update.message.reply_text("Use /start, /balance, /deposit, /withdraw or /play.")
        return
    parts = [p.strip() for p in update.message.text.split(",", 1)]
    try:
        amount = float(parts[0])
        if amount <= 0:
            raise ValueError
    except (ValueError, IndexError):
        await update.message.reply_text("Invalid amount. Try again, e.g. 100, reference/phone.")
        return
    user_id = str(update.effective_user.id)
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("Please use /start first.")
        return
    if action == "withdraw" and float(user.get("balance", 0)) < amount:
        await update.message.reply_text("Insufficient balance.")
        return
    extra = {"reference": parts[1][:100]} if action == "deposit" and len(parts) > 1 else {}
    if action == "withdraw":
        extra = {"withdrawal_phone": parts[1][:30]} if len(parts) > 1 else {}
    if action == "deposit" and amount < 30:
        await update.message.reply_text("Minimum deposit is 30 ETB.")
        return
    create_transaction(user_id, action, amount, **extra)
    context.user_data.pop("pending_action", None)
    await update.message.reply_text("Request submitted. It will remain pending until an administrator reviews it.")


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("Not authorized.")
        return
    users = list(db.collection("users").stream())
    games = list(db.collection("games").stream())
    total = sum(float(x.to_dict().get("balance", 0)) for x in users)
    await update.message.reply_text(f"Users: {len(users)}\nGames: {len(games)}\nTotal balance: {total:.2f} ETB")


def main():
    token = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("Set BOT_TOKEN in Render environment variables.")
    if not WEBAPP_URL.startswith("https://"):
        raise RuntimeError("WEBAPP_URL must be the public HTTPS URL of the deployed web app.")
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("deposit", deposit))
    application.add_handler(CommandHandler("withdraw", withdraw))
    application.add_handler(CommandHandler("play", play))
    application.add_handler(CommandHandler("language", language))
    application.add_handler(CommandHandler("adminstats", admin_stats))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    log.info("Starting Telegram polling worker")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
