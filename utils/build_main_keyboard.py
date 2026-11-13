from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

def build_main_keyboard(lang, webapp_url):
    """
    Builds the main menu keyboard based on language and WebApp URL.
    """
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Play", web_app=WebAppInfo(url=webapp_url))],
        [InlineKeyboardButton("💰 Deposit", callback_data="deposit_menu")],
        [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("📊 Stats", callback_data="stats")],
        [InlineKeyboardButton("🎁 Invite", callback_data="invite")],
        [InlineKeyboardButton("🌐 Language", callback_data="toggle_lang")]
    ])
