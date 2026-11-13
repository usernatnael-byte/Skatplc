"""Environment configuration shared by the Flask app and Telegram bot."""
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_IDS = [int(value.strip()) for value in os.getenv("ADMIN_IDS", "").split(",")
             if value.strip().isdigit()]
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://example.onrender.com/cartela")
FLASK_HOST = "0.0.0.0"
FLASK_PORT = int(os.getenv("PORT", os.getenv("FLASK_PORT", "5000")))
SECRET_KEY = os.getenv("FLASK_SECRET") or os.getenv("SECRET_KEY")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
