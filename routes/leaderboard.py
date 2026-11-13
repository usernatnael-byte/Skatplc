from flask import Blueprint, render_template
from database import db
from models import User, Transaction
from sqlalchemy import func

leaderboard_bp = Blueprint("leaderboard", __name__)

@leaderboard_bp.route("/leaderboard")
def leaderboard():
    winners = db.session.query(
        User.username,
        func.sum(Transaction.amount).label("total")
    ).join(Transaction).filter(Transaction.type=="jackpot_win")\
     .group_by(User.username).order_by(func.sum(Transaction.amount).desc()).limit(10).all()

    return render_template("leaderboard.html", winners=winners)
