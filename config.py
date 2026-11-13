# config.py
import os
from dotenv import load_dotenv

# 📦 Load environment variables from .env file (for local development)
load_dotenv()

# 🔐 Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_IDS = [
    int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip().isdigit()
]

# 🎮 Game Settings
CARTELA_SIZE = int(os.getenv("CARTELA_SIZE", 100))  # Total numbers in Bingo
MIN_PLAYERS = int(os.getenv("MIN_PLAYERS", 2))
GAME_PRICES = [10, 20, 30, 50, 100]  # ETB options
MIN_GAMES_FOR_WITHDRAWAL = int(os.getenv("MIN_GAMES_FOR_WITHDRAWAL", 5))
MIN_WINS_FOR_WITHDRAWAL = int(os.getenv("MIN_WINS_FOR_WITHDRAWAL", 1))
REFERRAL_BONUS = int(os.getenv("REFERRAL_BONUS", 20))  # ETB bonus

# 🛡️ Admin Panel Credentials
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
SECRET_KEY = os.getenv("SECRET_KEY") or os.getenv("FLASK_SECRET") or "local-development-only-change-me"

# 🧠 Database Configuration
SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
SQLALCHEMY_TRACK_MODIFICATIONS = False

# 🌐 Flask Server Configuration
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))

# 🌍 URLs for Web App & Telegram Webhook
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://YOUR-WEB-SERVICE.onrender.com/cartela")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

# 🔑 Flask Secret (used for sessions)
FLASK_SECRET = os.getenv("FLASK_SECRET", "super-secret-key-change-this")
