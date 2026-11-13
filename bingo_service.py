"""Transactional Bingo game engine backed by Cloud Firestore."""
import random
from datetime import datetime, timezone
from google.cloud.firestore_v1.transaction import transactional
from database import db

def now():
    return datetime.now(timezone.utc)

def make_board():
    cols = [random.sample(range(a, b + 1), 5) for a, b in
            ((1,15),(16,30),(31,45),(46,60),(61,75))]
    board = [cols[c][r] for r in range(5) for c in range(5)]
    board[12] = 0
    return board

def _ref(game_id):
    return db.collection("games").document(str(game_id))

def create_game(entry_price=10, created_by=None):
    price = int(entry_price)
    if price not in (10, 20, 50, 100):
        raise ValueError("Entry price must be 10, 20, 50 or 100 ETB")
    ref = db.collection("games").document()
    data = {"id": ref.id, "entry_price": price, "status": "waiting",
            "player_count": 0, "pool": 0.0, "called_numbers": [],
            "current_number": None, "winner_id": None, "created_by": str(created_by or ""),
            "created_at": now(), "updated_at": now()}
    ref.set(data)
    return data

def list_games(limit=30):
    docs = db.collection("games").order_by("created_at", direction="DESCENDING").limit(limit).stream()
    result = []
    for snap in docs:
        d = snap.to_dict()
        if d.get("status") in ("waiting", "active"):
            result.append({"id": snap.id, "entry_price": d.get("entry_price", 10),
                           "status": d.get("status"), "players": d.get("player_count", 0),
                           "pool": d.get("pool", 0)})
    return result

def join_game(game_id, telegram_id, username="unknown"):
    game_ref = _ref(game_id)
    player_ref = game_ref.collection("players").document(str(telegram_id))
    user_ref = db.collection("users").document(str(telegram_id))
    tx = db.transaction()
    @transactional
    def apply(t):
        gs, us, ps = game_ref.get(transaction=t), user_ref.get(transaction=t), player_ref.get(transaction=t)
        if not gs.exists: raise LookupError("Game not found")
        if not us.exists: raise LookupError("Start the Telegram bot first.")
        game = gs.to_dict()
        if game.get("status") not in ("waiting", "active"): raise ValueError("This game is already finished.")
        if ps.exists: return ps.to_dict()
        user = us.to_dict()
        price, balance = float(game.get("entry_price", 10)), float(user.get("balance", 0))
        if balance < price: raise ValueError("Insufficient balance. Deposit and wait for approval.")
        player = {"telegram_id": str(telegram_id), "username": username or "unknown",
                  "board": make_board(), "joined_at": now(), "claimed": False}
        t.update(user_ref, {"balance": balance-price, "games_played": int(user.get("games_played", 0))+1, "updated_at": now()})
        t.set(player_ref, player)
        t.update(game_ref, {"player_count": int(game.get("player_count", 0))+1,
                            "pool": float(game.get("pool", 0))+price, "status": "active", "updated_at": now()})
        return player
    return apply(tx)

def get_game(game_id, telegram_id=None):
    ref = _ref(game_id)
    snap = ref.get()
    if not snap.exists: return None
    data = snap.to_dict()
    data["id"] = snap.id
    data["called_numbers"] = data.get("called_numbers", [])
    if telegram_id is not None:
        p = ref.collection("players").document(str(telegram_id)).get()
        data["player"] = p.to_dict() if p.exists else None
    return data

def call_next_number(game_id):
    ref, tx = _ref(game_id), db.transaction()
    @transactional
    def apply(t):
        snap = ref.get(transaction=t)
        if not snap.exists: raise LookupError("Game not found")
        game = snap.to_dict()
        if game.get("status") != "active": raise ValueError("Game is not active.")
        called = list(game.get("called_numbers", []))
        available = [n for n in range(1, 76) if n not in called]
        if not available:
            t.update(ref, {"status": "finished", "updated_at": now()})
            return None
        number = random.choice(available)
        called.append(number)
        t.update(ref, {"called_numbers": called, "current_number": number, "updated_at": now()})
        return number
    return apply(tx)

def _has_bingo(board, called):
    marked = set(called) | {0}
    lines = [[r*5+c for c in range(5)] for r in range(5)]
    lines += [[r*5+c for r in range(5)] for c in range(5)]
    lines += [[i*5+i for i in range(5)], [i*5+(4-i) for i in range(5)], [0,4,20,24]]
    return any(all(board[i] in marked for i in line) for line in lines)

def claim_bingo(game_id, telegram_id):
    ref = _ref(game_id)
    player_ref = ref.collection("players").document(str(telegram_id))
    user_ref = db.collection("users").document(str(telegram_id))
    tx = db.transaction()
    @transactional
    def apply(t):
        gs, ps, us = ref.get(transaction=t), player_ref.get(transaction=t), user_ref.get(transaction=t)
        if not gs.exists or not ps.exists or not us.exists: raise LookupError("Game or player not found.")
        game, player, user = gs.to_dict(), ps.to_dict(), us.to_dict()
        if game.get("status") != "active": raise ValueError("This game is not active.")
        if game.get("winner_id"): raise ValueError("A winner has already been confirmed.")
        if not _has_bingo(player.get("board", []), game.get("called_numbers", [])):
            raise ValueError("Bingo pattern is not complete yet.")
        pool = float(game.get("pool", 0))
        commission, prize = round(pool*0.20, 2), round(pool*0.80, 2)
        t.update(ref, {"status": "finished", "winner_id": str(telegram_id), "prize": prize,
                       "commission": commission, "finished_at": now(), "updated_at": now()})
        t.update(user_ref, {"balance": float(user.get("balance", 0))+prize,
                            "games_won": int(user.get("games_won", 0))+1, "updated_at": now()})
        t.update(player_ref, {"claimed": True})
        return {"winner": str(telegram_id), "prize": prize, "commission": commission}
    return apply(tx)
