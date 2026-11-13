import requests
import os

# Load bot token and webhook URL from environment variables
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBAPP_URL", "https://efona-bingo-oxct.onrender.com/webhook")

# Set the webhook
response = requests.post(
    f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
    data={"url": WEBHOOK_URL}
)

# Print the result
print("Webhook setup response:")
print(response.json())
