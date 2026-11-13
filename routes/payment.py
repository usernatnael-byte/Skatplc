from flask import Blueprint, request, jsonify
from models import User, Transaction
from database import db

payment_bp = Blueprint("payment", __name__)

@payment_bp.route("/chapa/webhook", methods=["POST"])
def chapa_webhook():
    data = request.json
    tx_ref = data.get("tx_ref")
    telegram_id = data.get("custom_data", {}).get("telegram_id")
    amount = float(data.get("amount"))

    user = User.query.filter_by(telegram_id=telegram_id).first()
    if user:
        user.balance += amount
        db.session.add(Transaction(
            user_id=user.id,
            type="deposit",
            amount=amount,
            status="approved",
            reference=tx_ref,
            method="chapa"
        ))
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"status": "user_not_found"})
