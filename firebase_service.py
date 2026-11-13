"""Compatibility helpers for the single shared Firestore database."""
from database import get_firestore


def get_firebase_app():
    import firebase_admin
    from database import get_firestore as _get
    _get()
    return firebase_admin.get_app()


def get_firestore_client():
    return get_firestore()
