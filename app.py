# app.py
from flask import Flask, request, jsonify, render_template
from database import db, init_db
from models import User, Game, GameParticipant, Transaction
from game_logic import BingoGame
from datetime import datetime
import os
import random

# 🔧 Flask App Setup
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET") or os.getenv("SECRET_KEY") or "local-development-only-change-me"

# Initialize the one shared SQLAlchemy extension.
init_db(app)


# Lightweight cartela preview store. Persisting and binding these boards to
# authenticated Telegram WebApp users is a required next production step.
_cartelas = {}

@app.route("/", methods=["GET"])
def health():
    return jsonify({"service": "Efona Bingo", "status": "online"}), 200

@app.route("/cartela", methods=["GET"])
def cartela_page():
    return render_template("cartela.html", game_id="—", entry_price=10,
                           player_count=0, pool=0, sound_enabled=True,
                           play_mode="manual")

@app.route("/api/cartela", methods=["GET", "POST"])
def cartela_api():
    telegram_id = request.args.get("id", "")
    if not telegram_id:
        return jsonify({"error": "Telegram user id is required"}), 400
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        numbers = data.get("cartela")
        if not isinstance(numbers, list) or len(numbers) != 25:
            return jsonify({"error": "Cartela must contain 25 numbers"}), 400
        if any(not isinstance(n, int) or n < 1 or n > 75 for n in numbers):
            return jsonify({"error": "Cartela numbers must be integers from 1 to 75"}), 400
        _cartelas[telegram_id] = numbers
    if telegram_id not in _cartelas:
        columns = [random.sample(range(1, 16), 5), random.sample(range(16, 31), 5),
                   random.sample(range(31, 46), 5), random.sample(range(46, 61), 5),
                   random.sample(range(61, 76), 5)]
        _cartelas[telegram_id] = [columns[c][r] for r in range(5) for c in range(5)]
    return jsonify({"cartela": _cartelas[telegram_id], "bonus": [], "winner": None})

# 🎮 In-memory game store
active_games = {}

# -------------------- API SECURITY --------------------
def require_api_token():
    """Protect administrative API routes with a server-side bearer token."""
    expected = os.getenv("ADMIN_API_TOKEN")
    supplied = request.headers.get("X-Admin-Token")
    return bool(expected and supplied and supplied == expected)

# -------------------- GAME ROUTES --------------------

@app.route("/game/create", methods=["POST"])
def create_game():
    data = request.json
    entry_price = data.get("entry_price", 10)
    game = BingoGame(game_id=len(active_games) + 1, entry_price=entry_price)
    active_games[game.game_id] = game
    return jsonify({"game_id": game.game_id})

@app.route("/game/join", methods=["POST"])
def join_game():
    data = request.json
    game_id = data.get("game_id")
    user_id = data.get("user_id")
    cartela_number = data.get("cartela_number")

    game = active_games.get(game_id)
    if not game:
        return jsonify({"error": "Game not found"}), 404

    board = game.add_player(user_id, cartela_number)
    return jsonify({"cartela": board})

@app.route("/game/call/<int:game_id>", methods=["POST"])
def call_number(game_id):
    game = active_games.get(game_id)
    if not game:
        return jsonify({"error": "Game not found"}), 404

    result = game.call_number()
    return jsonify(result)

@app.route("/game/mark", methods=["POST"])
def mark_number():
    data = request.json
    game_id = data.get("game_id")
    user_id = data.get("user_id")
    number = data.get("number")

    game = active_games.get(game_id)
    if not game:
        return jsonify({"error": "Game not found"}), 404

    updated = game.mark_number(user_id, number)
    win, message = game.check_winner(user_id)

    if win:
        game.end_game(user_id)

    return jsonify({
        "marked": updated,
        "win": win,
        "message": message
    })

# -------------------- DEPOSIT & WITHDRAW --------------------

@app.route("/deposit", methods=["POST"])
def deposit():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    amount = data.get("amount")
    method = data.get("method")
    phone = data.get("phone")
    code = data.get("code")

    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return jsonify({"error": "A valid amount is required"}), 400
    if amount < 30:
        return jsonify({"error": "Minimum deposit is 30 ETB"}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    tx = Transaction(
        user_id=user.id,
        type="deposit",
        amount=amount,
        method=method,
        deposit_phone=phone,
        transaction_id=code,
        status="pending",
        created_at=datetime.utcnow()
    )
    db.session.add(tx)
    db.session.commit()

    return jsonify({"message": "Deposit proof submitted for administrator verification. Balance is unchanged until approval.", "status": "pending"}), 202

@app.route("/withdraw", methods=["POST"])
def withdraw():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    amount = data.get("amount")
    phone = data.get("phone")
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return jsonify({"error": "A valid amount is required"}), 400
    if amount <= 0:
        return jsonify({"error": "Amount must be positive"}), 400

    user = User.query.get(user_id)
    if not user or user.balance < amount:
        return jsonify({"error": "Insufficient balance"}), 400

    tx = Transaction(
        user_id=user.id,
        type="withdraw",
        amount=amount,
        withdrawal_phone=phone,
        withdrawal_status="pending",
        status="pending",
        created_at=datetime.utcnow()
    )
    db.session.add(tx)
    db.session.commit()

    return jsonify({"message": "Withdrawal request submitted."})

# -------------------- ADMIN ROUTES --------------------

@app.route("/admin/transactions", methods=["GET"])
def admin_transactions():
    if not require_api_token():
        return jsonify({"error": "Unauthorized"}), 401
    txs = Transaction.query.order_by(Transaction.created_at.desc()).limit(50).all()
    data = []
    for tx in txs:
        user = User.query.get(tx.user_id)
        data.append({
            "id": tx.id,
            "user": user.username if user else "unknown",
            "type": tx.type,
            "amount": tx.amount,
            "method": tx.method,
            "reference": tx.reference,
            "status": tx.status,
            "created_at": tx.created_at.isoformat()
        })
    return jsonify(data)

@app.route("/admin/approve/<int:tx_id>", methods=["POST"])
def approve_transaction(tx_id):
    if not require_api_token():
        return jsonify({"error": "Unauthorized"}), 401
    tx = Transaction.query.get(tx_id)
    if not tx or tx.status != "pending":
        return jsonify({"error": "Transaction not found or already processed"}), 400

    tx.status = "approved"
    tx.completed_at = datetime.utcnow()

    user = User.query.get(tx.user_id)
    if tx.type == "deposit":
        user.balance += tx.amount
    elif tx.type == "withdraw":
        if user.balance < tx.amount:
            db.session.rollback()
            return jsonify({"error": "Insufficient balance at approval time"}), 409
        user.balance -= tx.amount

    db.session.commit()
    return jsonify({"message": "Transaction approved."})

@app.route("/admin/reject/<int:tx_id>", methods=["POST"])
def reject_transaction(tx_id):
    if not require_api_token():
        return jsonify({"error": "Unauthorized"}), 401
    tx = Transaction.query.get(tx_id)
    if not tx or tx.status != "pending":
        return jsonify({"error": "Transaction not found or already processed"}), 400

    tx.status = "rejected"
    db.session.commit()
    return jsonify({"message": "Transaction rejected."})

# -------------------- LEADERBOARD --------------------

@app.route("/leaderboard", methods=["GET"])
def leaderboard():
    top_users = User.query.order_by(User.games_won.desc(), User.balance.desc()).limit(10).all()
    data = [
        {
            "username": user.username,
            "wins": user.games_won,
            "balance": user.balance
        }
        for user in top_users
    ]
    return jsonify(data)

# -------------------- START SERVER --------------------

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=int(os.getenv("FLASK_PORT", 5000)), debug=True)
