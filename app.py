"""Flask web application backed exclusively by Cloud Firestore."""
import hashlib
import hmac
import json
import os
import random
import time
from urllib.parse import parse_qsl

from flask import Flask, jsonify, render_template, request

from database import db
from models import create_user, get_user, create_transaction, process_transaction

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET") or os.getenv("SECRET_KEY")
if not app.secret_key:
    app.secret_key = "development-only-change-this"


def _telegram_user():
    """Validate Telegram WebApp initData; never trust a query-string user id."""
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    token = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    if not init_data or not token:
        return None
    values = dict(parse_qsl(init_data, keep_blank_values=True))
    supplied_hash = values.pop("hash", None)
    if not supplied_hash:
        return None
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(values.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, supplied_hash):
        return None
    try:
        auth_date = int(values.get("auth_date", "0"))
        if abs(time.time() - auth_date) > 86400:
            return None
        user = json.loads(values["user"])
        return str(user["id"])
    except (KeyError, ValueError, TypeError, json.JSONDecodeError):
        return None


def _admin_authorized():
    expected = os.getenv("ADMIN_API_TOKEN")
    supplied = request.headers.get("X-Admin-Token", "")
    return bool(expected and hmac.compare_digest(expected, supplied))


def _new_cartela():
    columns = [random.sample(range(1, 16), 5), random.sample(range(16, 31), 5),
               random.sample(range(31, 46), 5), random.sample(range(46, 61), 5),
               random.sample(range(61, 76), 5)]
    return [columns[col][row] for row in range(5) for col in range(5)]


@app.get("/")
def health():
    return jsonify({"service": "Efona Bingo", "status": "online", "database": "cloud_firestore"}), 200


@app.get("/cartela")
def cartela_page():
    return render_template("cartela.html", game_id="—", entry_price=10,
                           player_count=0, pool=0, sound_enabled=True,
                           play_mode="manual")


@app.route("/api/cartela", methods=["GET", "POST"])
def cartela_api():
    telegram_id = _telegram_user()
    if not telegram_id:
        return jsonify({"error": "Valid Telegram WebApp authentication is required"}), 401
    user = get_user(telegram_id)
    if not user:
        create_user(telegram_id)
    ref = db.collection("cartelas").document(telegram_id)
    snap = ref.get()
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        numbers = data.get("cartela")
        if (not isinstance(numbers, list) or len(numbers) != 25 or
                any(type(n) is not int or n < 1 or n > 75 for n in numbers) or
                len(set(numbers)) != 25):
            return jsonify({"error": "Cartela must contain 25 unique integers from 1 to 75"}), 400
        for col, limits in enumerate(((1,15),(16,30),(31,45),(46,60),(61,75))):
            if any(not limits[0] <= numbers[row * 5 + col] <= limits[1] for row in range(5)):
                return jsonify({"error": "Cartela numbers must follow B-I-N-G-O column ranges"}), 400
        ref.set({"numbers": numbers, "updated_at": time.time()}, merge=True)
        return jsonify({"cartela": numbers, "bonus": [], "winner": None}), 200
    if snap.exists:
        numbers = snap.to_dict().get("numbers", [])
    else:
        numbers = _new_cartela()
        ref.set({"numbers": numbers, "created_at": time.time()})
    return jsonify({"cartela": numbers, "bonus": [], "winner": None})


@app.post("/deposit")
def deposit():
    telegram_id = _telegram_user()
    if not telegram_id:
        return jsonify({"error": "Valid Telegram WebApp authentication is required"}), 401
    data = request.get_json(silent=True) or {}
    try:
        amount = float(data.get("amount"))
    except (TypeError, ValueError):
        return jsonify({"error": "A valid amount is required"}), 400
    if not 30 <= amount <= 100000:
        return jsonify({"error": "Deposit must be between 30 and 100000 ETB"}), 400
    if not get_user(telegram_id):
        return jsonify({"error": "User not found. Start the bot first."}), 404
    tx = create_transaction(telegram_id, "deposit", amount,
                            method=str(data.get("method", ""))[:40],
                            deposit_phone=str(data.get("phone", ""))[:30],
                            reference=str(data.get("code", ""))[:100])
    return jsonify({"message": "Deposit submitted for admin verification", "status": "pending", "transaction_id": tx["id"]}), 202


@app.post("/withdraw")
def withdraw():
    telegram_id = _telegram_user()
    if not telegram_id:
        return jsonify({"error": "Valid Telegram WebApp authentication is required"}), 401
    data = request.get_json(silent=True) or {}
    try:
        amount = float(data.get("amount"))
    except (TypeError, ValueError):
        return jsonify({"error": "A valid amount is required"}), 400
    if not 1 <= amount <= 100000:
        return jsonify({"error": "Invalid withdrawal amount"}), 400
    user = get_user(telegram_id)
    if not user or float(user.get("balance", 0)) < amount:
        return jsonify({"error": "Insufficient balance"}), 400
    tx = create_transaction(telegram_id, "withdraw", amount,
                            withdrawal_phone=str(data.get("phone", ""))[:30])
    return jsonify({"message": "Withdrawal request submitted", "status": "pending", "transaction_id": tx["id"]}), 202


@app.get("/admin/transactions")
def admin_transactions():
    if not _admin_authorized():
        return jsonify({"error": "Unauthorized"}), 401
    docs = db.collection("transactions").order_by("created_at", direction="DESCENDING").limit(50).stream()
    result = []
    for doc in docs:
        item = doc.to_dict()
        user = get_user(item.get("user_id"))
        result.append({"id": doc.id, "user": (user or {}).get("username", "unknown"),
                       "type": item.get("type"), "amount": item.get("amount"),
                       "method": item.get("method"), "reference": item.get("reference"),
                       "status": item.get("status")})
    return jsonify(result)


@app.post("/admin/approve/<tx_id>")
def approve_transaction(tx_id):
    if not _admin_authorized():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        status = process_transaction(tx_id, True)
        return jsonify({"message": "Transaction approved", "status": status})
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 409


@app.post("/admin/reject/<tx_id>")
def reject_transaction(tx_id):
    if not _admin_authorized():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        status = process_transaction(tx_id, False)
        return jsonify({"message": "Transaction rejected", "status": status})
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 409


@app.get("/leaderboard")
def leaderboard():
    docs = db.collection("users").order_by("games_won", direction="DESCENDING").limit(10).stream()
    return jsonify([{"username": d.to_dict().get("username", "unknown"),
                     "wins": d.to_dict().get("games_won", 0),
                     "balance": d.to_dict().get("balance", 0)} for d in docs])


# Render's free web instance cannot host a separate free Background Worker.
# Run the Telegram polling loop in a single daemon thread in this same service.
if os.getenv("RUN_TELEGRAM_BOT", "").lower() == "true":
    import threading

    def _run_bot():
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        from bot import main as run_telegram_bot
        run_telegram_bot()

    threading.Thread(target=_run_bot, name="telegram-polling", daemon=True).start()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", os.getenv("FLASK_PORT", 5000))))
