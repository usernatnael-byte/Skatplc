"""Compatibility facade for the Telegram bot's in-memory Bingo sessions.

Game sessions are process-local in this legacy codebase. For multi-instance
production deployments, move live game state to Redis or the SQL database.
"""
from game_logic import BingoGame

_sessions = {}


def _session(chat_id):
    if chat_id not in _sessions:
        _sessions[chat_id] = BingoGame(game_id=int(chat_id) if str(chat_id).lstrip('-').isdigit() else 1)
    return _sessions[chat_id]


def start_game(chat_id, context=None):
    session = _session(chat_id)
    if session.status == "waiting" and session.total_players() == 0:
        # A game can be opened before the first player joins.
        return True
    return session.start_game(chat_id, context)


def call_number(chat_id, context=None):
    return _session(chat_id).call_number(chat_id, context)


def get_leaderboard(top_n=10):
    rows = []
    for session in _sessions.values():
        rows.extend(session.get_leaderboard(top_n))
    return sorted(rows, key=lambda row: (row[1], row[2]), reverse=True)[:top_n]


def summary(chat_id=None):
    if chat_id is not None:
        return _session(chat_id).summary()
    if not _sessions:
        return {"game_id": 0, "status": "waiting", "players": 0, "pool": 0,
                "called": 0, "winner": None, "admin_earnings": 0}
    return list(_sessions.values())[-1].summary()


def get_player_summary(user_id, chat_id=None):
    if chat_id is not None:
        return _session(chat_id).get_player_summary(user_id)
    for session in _sessions.values():
        result = session.get_player_summary(user_id)
        if result:
            return result
    return []
