import os

from .helpers import is_valid_tx_id, referral_link, toggle_language, format_cartela, build_main_keyboard


def get_lang(context):
    """Return language strings based on user's selected language."""
    default = {
        "en": {
            "deposit": "Please send your deposit transaction ID.",
            "withdraw": "Enter amount to withdraw.",
            "balance": "Your balance",
            "referral_contest": "Referral Contest",
            "invite": "Invite your friends using this link",
            "leaderboard": "Leaderboard",
            "summary": "Game Summary",
            "referrals": "Referrals",
            "toggle_sound": "Sound",
            "report_bug": "Report a bug",
            "schedule_game": "Schedule a new game",
            "broadcast": "Broadcast message",
            "adminstats": "Admin Stats",
            "cartela_preview": "Cartela Preview",
            "play": "Let’s play Bingo!"
        },
        "am": {
            "deposit": "የተቀበልክዎትን የግብይት መለያ ያስገቡ።",
            "withdraw": "የሚወጡትን መጠን ያስገቡ።",
            "balance": "የእርስዎ ቀሪ ገንዘብ",
            "referral_contest": "የመጋቢ ውድድር",
            "invite": "ጓደኞችዎን ይጋብዙ።",
            "leaderboard": "የአሸናፊዎች ዝርዝር",
            "summary": "የጨዋታ ማጠቃለያ",
            "referrals": "የተጠቃሚ ማመንጫዎች",
            "toggle_sound": "ድምጽ",
            "report_bug": "ችግኝ ያመልክቱ።",
            "schedule_game": "ጨዋታ ያቅዱ።",
            "broadcast": "መልዕክት ይላኩ።",
            "adminstats": "የአስተዳዳሪ ቁጥሮች",
            "cartela_preview": "የካርቴላ ቅድመ እይታ",
            "play": "ቢንጎ እንጫወታ!"
        }
    }

    lang_code = context.user_data.get("lang", "en")
    return default.get(lang_code, default["en"])


def referral_link(telegram_id: str) -> str:
    """Simplified referral link for the bot."""
    bot_username = os.getenv("BOT_USERNAME", "EfonaBingoBot").lstrip("@")
    return f"https://t.me/{bot_username}?start={telegram_id}"
