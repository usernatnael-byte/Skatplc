"""Efona-only environment configuration shared by the Flask app and Telegram bot.

All configurable names use the EFONA_ prefix so this service cannot collide
with another Render service's application-specific variables.
"""
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("EFONA_BOT_TOKEN")
ADMIN_IDS = [int(value.strip()) for value in os.getenv("EFONA_ADMIN_IDS", "").split(",")
             if value.strip().isdigit()]
WEBAPP_URL = os.getenv("EFONA_WEBAPP_URL", "https://example.onrender.com/cartela")
FLASK_HOST = "0.0.0.0"
FLASK_PORT = int(os.getenv("PORT", os.getenv("EFONA_FLASK_PORT", "5000")))
SECRET_KEY = os.getenv("EFONA_FLASK_SECRET") or os.getenv("EFONA_SECRET_KEY")
ADMIN_USERNAME = os.getenv("EFONA_ADMIN_USERNAME", "")
ADMIN_PASSWORD = os.getenv("EFONA_ADMIN_PASSWORD", "")
