"""Firestore-backed data helpers shared by the web app and Telegram bot."""
from datetime import datetime, timezone
from uuid import uuid4

from google.cloud.firestore_v1.transaction import transactional
from database import db


def utc_now():
    return datetime.now(timezone.utc)


def get_user(telegram_id):
    if telegram_id is None:
        return None
    ref = db.collection("users").document(str(telegram_id))
    snap = ref.get()
    if not snap.exists:
        return None
    data = snap.to_dict()
    data["id"] = str(telegram_id)
    return data


def create_user(telegram_id, username="unknown"):
    ref = db.collection("users").document(str(telegram_id))
    snap = ref.get()
    if snap.exists:
        ref.set({"username": username or "unknown", "updated_at": utc_now()}, merge=True)
        return {**snap.to_dict(), "id": str(telegram_id)}
    data = {
        "telegram_id": str(telegram_id), "username": username or "unknown",
        "balance": 0.0, "games_played": 0, "games_won": 0,
        "sound_enabled": True, "language": "en",
        "created_at": utc_now(), "updated_at": utc_now(),
    }
    ref.set(data)
    return {**data, "id": str(telegram_id)}


def create_transaction(telegram_id, tx_type, amount, **fields):
    tx_id = uuid4().hex
    data = {
        "user_id": str(telegram_id), "type": tx_type,
        "amount": float(amount), "status": "pending",
        "created_at": utc_now(), **fields,
    }
    db.collection("transactions").document(tx_id).set(data)
    return {"id": tx_id, **data}


def process_transaction(tx_id, approve):
    """Approve/reject exactly once and update the balance atomically."""
    ref = db.collection("transactions").document(str(tx_id))
    transaction = db.transaction()

    @transactional
    def apply(tx):
        snap = ref.get(transaction=tx)
        if not snap.exists:
            raise LookupError("Transaction not found")
        data = snap.to_dict()
        if data.get("status") != "pending":
            raise ValueError("Transaction already processed")
        user_ref = db.collection("users").document(str(data["user_id"]))
        user_snap = user_ref.get(transaction=tx)
        if not user_snap.exists:
            raise LookupError("User not found")
        user = user_snap.to_dict()
        if approve:
            amount = float(data.get("amount", 0))
            if data.get("type") == "withdraw" and float(user.get("balance", 0)) < amount:
                raise ValueError("Insufficient balance")
            delta = amount if data.get("type") == "deposit" else -amount
            tx.update(user_ref, {"balance": float(user.get("balance", 0)) + delta,
                                 "updated_at": utc_now()})
            status = "approved"
        else:
            status = "rejected"
        tx.update(ref, {"status": status, "completed_at": utc_now()})
        return status

    return apply(transaction)
