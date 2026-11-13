# utils/notify_user.py
import logging

async def notify_user(bot, telegram_id, message):
    try:
        await bot.send_message(chat_id=telegram_id, text=message)
    except Exception as e:
        logging.error(f"Failed to notify user {telegram_id}: {e}")
