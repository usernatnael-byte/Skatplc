from flask import Blueprint, render_template, request, redirect, url_for, session
from models import db, Transaction, User, Game
from telegram import Bot
from utils.notify_user import notify_user
import os
import asyncio

admin_bp = Blueprint("admin", __name__)
bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))

# -------------------- DASHBOARD --------------------

@admin_bp.route("/admin/dashboard")
def admin_dashboard():
    pending_withdrawals = Transaction.query.filter_by(type="withdraw", status="pending").all()
    pending_deposits = Transaction.query.filter_by(type="deposit", status="pending").all()
    games = Game.query.order_by(Game.created_at.desc()).limit(10).all()
    players = User.query.order_by(User.created_at.desc()).limit(10).all()
    return render_template(
        "admin_dashboard.html",
        pending_withdrawals=pending_withdrawals,
        pending_deposits=pending_deposits,
        games=games,
        players=players
    )

# -------------------- APPROVE WITHDRAWAL --------------------

@admin_bp.route("/approve_withdrawal", methods=["POST"])
def approve_withdrawal():
    tx_id = request.form.get("tx_id")
    user_id = request.form.get("user_id")
    amount = float(request.form.get("amount"))
    note = request.form.get("note", "")
    admin_id = session.get("admin_id")

    tx = Transaction.query.get(tx_id)
    user = User.query.get(user_id)
    admin = User.query.get(admin_id)

    if tx and tx.status == "pending":
        tx.status = "approved"
        tx.completed_at = db.func.now()
        tx.approved_by = admin.telegram_id if admin else "unknown"
        tx.approval_note = note
        user.balance -= amount
        db.session.commit()
        asyncio.run(notify_user(bot, user.telegram_id, f"✅ Your withdrawal of {amount} birr has been approved."))

    return redirect(url_for("admin.admin_dashboard"))

# -------------------- APPROVE DEPOSIT --------------------

@admin_bp.route("/approve_deposit", methods=["POST"])
def approve_deposit():
    tx_id = request.form.get("tx_id")
    user_id = request.form.get("user_id")
    amount = float(request.form.get("amount"))

    tx = Transaction.query.get(tx_id)
    user = User.query.get(user_id)

    if tx and tx.status == "pending":
        tx.status = "approved"
        tx.completed_at = db.func.now()
        user.balance += amount
        db.session.commit()

        message = (
            f"💰 Deposit confirmed!\n"
            f"Your balance is now {user.balance} birr.\n\n"
            f"እባኮትን የተሰጠውን ቀሪ ገንዘብ በተጫወት ለመጠቀም ዝግጁ ይሁኑ።"
        )
        asyncio.run(notify_user(bot, user.telegram_id, message))

    return redirect(url_for("admin.admin_dashboard"))

# -------------------- START GAME --------------------

@admin_bp.route("/start_game", methods=["POST"])
def start_game():
    game_id = request.form.get("game_id")
    game = Game.query.get(game_id)
    if game and game.status == "waiting":
        game.status = "active"
        db.session.commit()
    return redirect(url_for("admin.admin_dashboard"))

# -------------------- LOGOUT --------------------

@admin_bp.route("/logout")
def logout():
    session.clear()
    return "✅ Logged out"

# -------------------- LOGIN VIA TELEGRAM --------------------

@admin_bp.route("/admin/login/364344971")
def login_via_telegram():
    user = User.query.filter_by(telegram_id="364344971").first()
    if user and user.is_admin:
        session["admin_id"] = user.id
        return redirect(url_for("admin.admin_dashboard"))
    return "❌ Access denied", 403

# -------------------- ACCESS CONTROL --------------------

@admin_bp.before_request
def require_admin_login():
    protected_paths = [
        "/admin/dashboard",
        "/approve_withdrawal",
        "/approve_deposit",
        "/start_game",
        "/admin/leaderboard",
        "/admin/referrals",
        "/admin/audit"
    ]
    if request.path.startswith(tuple(protected_paths)):
        if "admin_id" not in session:
            return "🔒 You must be logged in as admin", 403

# -------------------- GAME LEADERBOARD --------------------

@admin_bp.route("/admin/leaderboard")
def leaderboard():
    top_winners = User.query.order_by(User.games_won.desc()).limit(10).all()
    most_active = User.query.order_by(User.games_played.desc()).limit(10).all()
    richest = User.query.order_by(User.balance.desc()).limit(10).all()
    return render_template("leaderboard.html", top_winners=top_winners, most_active=most_active, richest=richest)

# -------------------- REFERRAL LEADERBOARD --------------------

@admin_bp.route("/admin/referrals")
def referral_leaderboard():
    top_referrers = (
        User.query
        .filter(User.referred_users.any())
        .order_by(db.func.count(User.referred_users).desc())
        .limit(10)
        .all()
    )

    referral_data = []
    for user in top_referrers:
        invited = [u.username for u in user.referred_users]
        referral_data.append({
            "username": user.username,
            "count": len(invited),
            "bonus": len(invited) * 5,
            "invited": invited
        })

    return render_template("referral_leaderboard.html", referral_data=referral_data)

# -------------------- AUDIT TRAIL --------------------

@admin_bp.route("/admin/audit")
def audit_trail():
    approved_tx = Transaction.query.filter_by(type="withdraw", status="approved").order_by(Transaction.completed_at.desc()).limit(50).all()
    return render_template("audit_trail.html", approved_tx=approved_tx)

# -------------------- ONE-TIME ADMIN SETUP --------------------

@admin_bp.route("/make_me_admin")
def make_me_admin():
    user = User.query.filter_by(telegram_id="364344971").first()
    if user:
        user.is_admin = True
        db.session.commit()
        return "✅ You are now marked as admin."
    return "❌ User not found."
