from telegram import Bot
import os

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)

def notify_user(telegram_id: int, message: str):
    try:
        bot.send_message(chat_id=telegram_id, text=message)
    except Exception as e:
        print(f"Failed to notify user {telegram_id}: {e}")
