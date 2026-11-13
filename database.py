"""Shared Firestore connection for the website and Telegram worker.

Set FIREBASE_CREDENTIALS_JSON to the service-account JSON on Render.
For local development, GOOGLE_APPLICATION_CREDENTIALS may point to a
service-account file. No SQL database is used.
"""
import json
import os
from functools import lru_cache

import firebase_admin
from firebase_admin import credentials, firestore


@lru_cache(maxsize=1)
def get_firestore():
    if not firebase_admin._apps:
        raw = os.getenv("FIREBASE_CREDENTIALS_JSON") or os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        if raw:
            info = json.loads(raw)
            firebase_admin.initialize_app(credentials.Certificate(info))
        elif os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            firebase_admin.initialize_app()
        else:
            raise RuntimeError(
                "Firebase credentials missing. Set FIREBASE_CREDENTIALS_JSON "
                "or GOOGLE_APPLICATION_CREDENTIALS."
            )
    return firestore.client()


class _LazyFirestore:
    """Resolve the client only when an operation is requested."""
    def __getattr__(self, name):
        return getattr(get_firestore(), name)


db = _LazyFirestore()
