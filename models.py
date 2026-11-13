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
    """Create a pending transaction; reserve withdrawal funds atomically."""
    amount = float(amount)
    if amount <= 0:
        raise ValueError("Transaction amount must be positive")
    tx_id = uuid4().hex
    tx_ref = db.collection("transactions").document(tx_id)
    data = {
        "user_id": str(telegram_id), "type": tx_type,
        "amount": amount, "status": "pending",
        "created_at": utc_now(), **fields,
    }
    if tx_type != "withdraw":
        tx_ref.set(data)
        return {"id": tx_id, **data}

    user_ref = db.collection("users").document(str(telegram_id))
    transaction = db.transaction()

    @transactional
    def reserve(tx):
        user_snap = user_ref.get(transaction=tx)
        if not user_snap.exists:
            raise LookupError("User not found")
        user = user_snap.to_dict()
        balance = float(user.get("balance", 0))
        if balance < amount:
            raise ValueError("Insufficient balance")
        tx.update(user_ref, {"balance": balance - amount, "updated_at": utc_now()})
        tx.set(tx_ref, {**data, "funds_reserved": True})
        return {"id": tx_id, **data, "funds_reserved": True}

    return reserve(transaction)


def process_transaction(tx_id, approve):
    """Approve/reject exactly once; withdrawals are reserved when requested."""
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
        amount = float(data.get("amount", 0))
        balance = float(user.get("balance", 0))
        tx_type = data.get("type")
        updates = {"updated_at": utc_now()}
        if approve:
            if tx_type == "deposit":
                updates["balance"] = balance + amount
            elif tx_type == "withdraw" and not data.get("funds_reserved"):
                # Backward compatibility for requests created before reservation was added.
                if balance < amount:
                    raise ValueError("Insufficient balance")
                updates["balance"] = balance - amount
            status = "approved"
        else:
            if tx_type == "withdraw" and data.get("funds_reserved"):
                updates["balance"] = balance + amount
            status = "rejected"
        if len(updates) > 1:
            tx.update(user_ref, updates)
        tx.update(ref, {"status": status, "completed_at": utc_now()})
        return status

    return apply(transaction)
