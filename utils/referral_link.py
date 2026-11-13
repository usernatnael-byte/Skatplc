def referral_link(bot_username, user_id):
    """
    Generates a Telegram referral link for the given user.
    """
    return f"https://t.me/{bot_username}?start={user_id}"
