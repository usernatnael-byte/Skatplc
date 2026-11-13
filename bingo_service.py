"""Server-authoritative, Firestore-backed real-player Bingo rooms for Efona."""
import random
from datetime import datetime, timezone
from google.cloud.firestore_v1.transaction import transactional
from database import db


MIN_PLAYERS = 2
MAX_PLAYERS = 100
DEFAULT_DRAW_INTERVAL = 5


def now():
    return datetime.now(timezone.utc)


def make_board():
    columns = [random.sample(range(start, end + 1), 5) for start, end in
               ((1, 15), (16, 30), (31, 45), (46, 60), (61, 75))]
    board = [columns[col][row] for row in range(5) for col in range(5)]
    board[12] = 0
    return board


def _ref(game_id):
    return db.collection("games").document(str(game_id))


def create_game(entry_price=10, created_by=None, room_name=None):
    try:
        price = int(entry_price)
    except (TypeError, ValueError):
        raise ValueError("Choose a valid ticket price.")
    if price not in (10, 20, 50, 100):
        raise ValueError("Entry price must be 10, 20, 50 or 100 ETB.")

    name = " ".join(str(room_name or "").split())[:36] or "Efona Live Room"
    ref = db.collection("games").document()
    created = now()
    data = {
        "id": ref.id,
        "room_name": name,
        "entry_price": price,
        "status": "waiting",
        "player_count": 0,
        "min_players": MIN_PLAYERS,
        "max_players": MAX_PLAYERS,
        "draw_interval_seconds": DEFAULT_DRAW_INTERVAL,
        "pool": 0.0,
        "called_numbers": [],
        "current_number": None,
        "last_call_at": None,
        "winner_id": None,
        "created_by": str(created_by or ""),
        "created_at": created,
        "updated_at": created,
    }
    ref.set(data)
    return data


def list_games(limit=50):
    docs = db.collection("games").order_by(
        "created_at", direction="DESCENDING"
    ).limit(limit).stream()
    result = []
    for snap in docs:
        data = snap.to_dict() or {}
        if data.get("status") not in ("waiting", "active"):
            continue
        result.append({
            "id": snap.id,
            "room_name": data.get("room_name", "Efona Live Room"),
            "entry_price": data.get("entry_price", 10),
            "status": data.get("status"),
            "players": int(data.get("player_count", 0)),
            "min_players": int(data.get("min_players", MIN_PLAYERS)),
            "max_players": int(data.get("max_players", MAX_PLAYERS)),
            "pool": float(data.get("pool", 0)),
            "current_number": data.get("current_number"),
            "called_count": len(data.get("called_numbers", [])),
        })
    return result


def join_game(game_id, telegram_id, username="Player"):
    game_ref = _ref(game_id)
    player_ref = game_ref.collection("players").document(str(telegram_id))
    user_ref = db.collection("users").document(str(telegram_id))
    transaction = db.transaction()

    @transactional
    def apply(tx):
        game_snap = game_ref.get(transaction=tx)
        user_snap = user_ref.get(transaction=tx)
        player_snap = player_ref.get(transaction=tx)
        if not game_snap.exists:
            raise LookupError("Room not found.")
        if not user_snap.exists:
            raise LookupError("Start the Efona Telegram bot first.")
        if player_snap.exists:
            return player_snap.to_dict()

        game = game_snap.to_dict() or {}
        if game.get("status") != "waiting":
            raise ValueError("This room has already started. Join a waiting room.")
        player_count = int(game.get("player_count", 0))
        if player_count >= int(game.get("max_players", MAX_PLAYERS)):
            raise ValueError("This room is full.")

        user = user_snap.to_dict() or {}
        price = float(game.get("entry_price", 10))
        balance = float(user.get("balance", 0))
        if balance < price:
            raise ValueError("Insufficient balance. Deposit and wait for approval.")

        player = {
            "telegram_id": str(telegram_id),
            "username": str(username or "Player")[:40],
            "board": make_board(),
            "joined_at": now(),
            "claimed": False,
        }
        new_count = player_count + 1
        updates = {
            "balance": balance - price,
            "games_played": int(user.get("games_played", 0)) + 1,
            "updated_at": now(),
        }
        tx.update(user_ref, updates)
        tx.set(player_ref, player)
        game_updates = {
            "player_count": new_count,
            "pool": float(game.get("pool", 0)) + price,
            "updated_at": now(),
        }
        if new_count >= int(game.get("min_players", MIN_PLAYERS)):
            game_updates.update({"status": "active", "started_at": now()})
        tx.update(game_ref, game_updates)
        return player

    return apply(transaction)


def get_game(game_id, telegram_id=None):
    ref = _ref(game_id)
    snap = ref.get()
    if not snap.exists:
        return None
    data = snap.to_dict() or {}
    data["id"] = snap.id
    data["called_numbers"] = data.get("called_numbers", [])

    players = []
    for player_snap in ref.collection("players").stream():
        player = player_snap.to_dict() or {}
        players.append({
            "username": player.get("username", "Player"),
            "is_you": str(player.get("telegram_id", player_snap.id)) == str(telegram_id),
        })
    data["players"] = players

    if telegram_id is not None:
        player_snap = ref.collection("players").document(str(telegram_id)).get()
        data["player"] = player_snap.to_dict() if player_snap.exists else None
    return data


def call_next_number(game_id, force=False):
    ref = _ref(game_id)
    transaction = db.transaction()

    @transactional
    def apply(tx):
        snap = ref.get(transaction=tx)
        if not snap.exists:
            raise LookupError("Room not found.")
        game = snap.to_dict() or {}
        if game.get("status") != "active":
            raise ValueError("Room is not active yet.")
        called = list(game.get("called_numbers", []))
        interval = max(3, int(game.get("draw_interval_seconds", DEFAULT_DRAW_INTERVAL)))
        last_call = game.get("last_call_at")
        if not force and last_call:
            elapsed = (now() - last_call).total_seconds()
            if elapsed < interval:
                return None
        available = [number for number in range(1, 76) if number not in called]
        if not available:
            tx.update(ref, {"status": "finished", "updated_at": now()})
            return None
        number = random.choice(available)
        called.append(number)
        updates = {
            "called_numbers": called,
            "current_number": number,
            "last_call_at": now(),
            "updated_at": now(),
        }
        if len(called) == 75:
            updates["all_numbers_called"] = True
        tx.update(ref, updates)
        return number

    return apply(transaction)


def _has_bingo(board, called):
    if not isinstance(board, list) or len(board) != 25:
        return False
    marked = set(called) | {0}
    lines = [[row * 5 + col for col in range(5)] for row in range(5)]
    lines += [[row * 5 + col for row in range(5)] for col in range(5)]
    lines += [[i * 5 + i for i in range(5)],
              [i * 5 + (4 - i) for i in range(5)],
              [0, 4, 20, 24]]
    return any(all(board[index] in marked for index in line) for line in lines)


def claim_bingo(game_id, telegram_id):
    ref = _ref(game_id)
    player_ref = ref.collection("players").document(str(telegram_id))
    user_ref = db.collection("users").document(str(telegram_id))
    transaction = db.transaction()

    @transactional
    def apply(tx):
        game_snap = ref.get(transaction=tx)
        player_snap = player_ref.get(transaction=tx)
        user_snap = user_ref.get(transaction=tx)
        if not game_snap.exists or not player_snap.exists or not user_snap.exists:
            raise LookupError("Room or player not found.")
        game = game_snap.to_dict() or {}
        player = player_snap.to_dict() or {}
        user = user_snap.to_dict() or {}
        if game.get("status") != "active":
            raise ValueError("This game is not active.")
        if game.get("winner_id"):
            raise ValueError("A winner has already been confirmed.")
        if not _has_bingo(player.get("board", []), game.get("called_numbers", [])):
            raise ValueError("Your Bingo pattern is not complete yet.")

        pool = float(game.get("pool", 0))
        commission = round(pool * 0.20, 2)
        prize = round(pool - commission, 2)
        tx.update(ref, {
            "status": "finished",
            "winner_id": str(telegram_id),
            "winner_name": player.get("username", "Player"),
            "prize": prize,
            "commission": commission,
            "finished_at": now(),
            "updated_at": now(),
        })
        tx.update(user_ref, {
            "balance": float(user.get("balance", 0)) + prize,
            "games_won": int(user.get("games_won", 0)) + 1,
            "updated_at": now(),
        })
        tx.update(player_ref, {"claimed": True})
        return {
            "winner": str(telegram_id),
            "winner_name": player.get("username", "Player"),
            "prize": prize,
            "commission": commission,
        }

    return apply(transaction)
