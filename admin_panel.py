from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
from datetime import datetime
import logging
import os
from config import (
    ADMIN_USERNAME, ADMIN_PASSWORD, SECRET_KEY,
    FLASK_HOST, FLASK_PORT
)
from models import db, User, Game, Transaction

from telegram import Bot
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)

app = Flask(__name__)
app.secret_key = SECRET_KEY

# 🔐 Admin login protection
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('dashboard'))
        flash('Invalid credentials')
    return render_template('admin/login.html')

@app.route('/admin/dashboard')
@admin_required
def dashboard():
    players = User.query.all()
    games = Game.query.all()
    active_game = Game.query.filter_by(status="active").first()
    pending_withdrawals = Transaction.query.filter_by(type="withdrawal", status="pending").all()
    pending_deposits = Transaction.query.filter_by(type="deposit", status="pending").all()
    return render_template(
        'admin/dashboard.html',
        players=players,
        games=games,
        active_game=active_game,
        pending_withdrawals=pending_withdrawals,
        pending_deposits=pending_deposits,
        active_games=Game.query.filter_by(status="active").count(),
        total_players=User.query.count()
    )

@app.route('/admin/game/start', methods=['POST'])
@admin_required
def start_game():
    game_id = request.form.get('game_id')
    game = Game.query.get(game_id)
    if game and game.status == "waiting":
        game.status = "active"
        game.called_numbers = []
        game.created_at = datetime.utcnow()
        db.session.commit()
        flash('Game started successfully')
    else:
        flash('Could not start game')
    return redirect(url_for('dashboard'))

@app.route('/admin/game/finish', methods=['POST'])
@admin_required
def finish_game():
    game_id = request.form.get('game_id')
    game = Game.query.get(game_id)
    if game and game.status == "active":
        game.status = "finished"
        game.finished_at = datetime.utcnow()
        db.session.commit()
        flash('Game marked as finished')
    else:
        flash('Game not active or not found')
    return redirect(url_for('dashboard'))

@app.route('/admin/leaderboard')
@admin_required
def leaderboard():
    top_players = User.query.order_by(User.games_won.desc()).limit(10).all()
    return render_template('admin/leaderboard.html', players=top_players)

@app.route('/admin/call_number', methods=['POST'])
@admin_required
def call_number():
    game_id = int(request.form.get('game_id'))
    number = int(request.form.get('number'))
    game = Game.query.get(game_id)
    if not game or game.status != "active":
        flash("Game not active or not found")
        return redirect(url_for("dashboard"))

    if number in game.called_numbers:
        flash(f"Number {number} already called")
        return redirect(url_for("dashboard"))

    game.called_numbers.append(number)
    db.session.commit()

    logging.info(f"📢 Called number {number} in game {game_id}")
    flash(f"📢 Called number {number}")

    return redirect(url_for("dashboard"))

@app.route('/admin/withdrawal/approve', methods=['POST'])
@admin_required
def approve_withdrawal():
    user_id = request.form.get('user_id')
    tx_id = request.form.get('tx_id')
    amount = float(request.form.get('amount'))
    user = User.query.get(user_id)
    tx = Transaction.query.get(tx_id)
    if not user or not tx:
        flash('User or transaction not found')
        return redirect(url_for('dashboard'))
    if user.balance >= amount:
        user.balance -= amount
        tx.status = "approved"
        tx.completed_at = datetime.utcnow()
        db.session.commit()
        logging.info(f"✅ Admin approved withdrawal TX {tx_id} for user {user_id}")
        bot.send_message(chat_id=user.telegram_id, text=f"✅ Your withdrawal of {amount} birr was approved.")
        flash('Withdrawal approved')
    else:
        flash('Insufficient balance')
    return redirect(url_for('dashboard'))

@app.route('/admin/withdrawal/reject', methods=['POST'])
@admin_required
def reject_withdrawal():
    tx_id = request.form.get('tx_id')
    reason = request.form.get('reason', 'No reason provided')
    tx = Transaction.query.get(tx_id)
    if not tx:
        flash('Transaction not found')
        return redirect(url_for('dashboard'))
    tx.status = "rejected"
    tx.admin_note = reason
    tx.completed_at = datetime.utcnow()
    db.session.commit()
    logging.info(f"❌ Admin rejected withdrawal TX {tx_id} with reason: {reason}")
    bot.send_message(chat_id=tx.user.telegram_id, text=f"❌ Your withdrawal request was rejected.\nReason: {reason}")
    flash('Withdrawal rejected')
    return redirect(url_for('dashboard'))

@app.route('/admin/deposit/approve', methods=['POST'])
@admin_required
def approve_deposit():
    tx_id = request.form.get('tx_id')
    tx = Transaction.query.get(tx_id)
    if not tx or tx.status != "pending":
        flash('Invalid transaction')
        return redirect(url_for('dashboard'))
    user = tx.user
    user.balance += tx.amount
    tx.status = "approved"
    tx.completed_at = datetime.utcnow()
    db.session.commit()
    logging.info(f"✅ Admin approved deposit TX {tx_id} for user {user.id}")
    bot.send_message(chat_id=user.telegram_id, text=f"✅ Your deposit of {tx.amount} birr was approved.")
    flash('Deposit approved')
    return redirect(url_for('dashboard'))

@app.route('/admin/deposit/reject', methods=['POST'])
@admin_required
def reject_deposit():
    tx_id = request.form.get('tx_id')
    reason = request.form.get('reason', 'No reason provided')
    tx = Transaction.query.get(tx_id)
    if not tx:
        flash('Transaction not found')
        return redirect(url_for('dashboard'))
    tx.status = "rejected"
    tx.admin_note = reason
    tx.completed_at = datetime.utcnow()
    db.session.commit()
    logging.info(f"❌ Admin rejected deposit TX {tx_id} with reason: {reason}")
    bot.send_message(chat_id=tx.user.telegram_id, text=f"❌ Your deposit was rejected.\nReason: {reason}")
    flash('Deposit rejected')
    return redirect(url_for('dashboard'))

@app.route('/admin/user/<int:user_id>')
@admin_required
def user_profile(user_id):
    user = User.query.get(user_id)
    if not user:
        flash("User not found")
        return redirect(url_for("dashboard"))
    return render_template("admin/user.html", user=user)

@app.route('/admin/update_balance/<int:user_id>', methods=["POST"])
@admin_required
def update_balance(user_id):
    amount = float(request.form.get("amount", 0))
    user = User.query.get(user_id)
    if user:
        user.balance += amount
        db.session.commit()
        flash(f"💰 Updated balance for {user.username}")
    return redirect(url_for("user_profile", user_id=user_id))

@app.route('/admin/cartela/<int:game_id>/<int:user_id>/<int:cartela_number>')
@admin_required
def view_cartela(game_id, user_id, cartela_number):
    from models import GameParticipant, Game
    participant = GameParticipant.query.filter_by(
        game_id=game_id,
        user_id=user_id,
        cartela_number=cartela_number
    ).first()
    game = Game.query.get(game_id)
    if not participant or not game:
        flash("Cartela not found")
        return redirect(url_for("dashboard"))
    return render_template("admin/cartela_viewer.html", participant=participant, game=game)

@app.route('/admin/logout')
@admin_required
def logout():
    session.pop('admin_logged_in', None)
    flash('Logged out successfully')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=True)
