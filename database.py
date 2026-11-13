"""Shared Firestore connection for Efona Bingo.

Set EFONA_FIREBASE_CREDENTIALS_JSON to the service-account JSON on Render.
For local development, EFONA_GOOGLE_APPLICATION_CREDENTIALS may point to a
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
        raw = (os.getenv("EFONA_FIREBASE_CREDENTIALS_JSON")
               or os.getenv("EFONA_FIREBASE_SERVICE_ACCOUNT_JSON"))
        if raw:
            info = json.loads(raw)
            firebase_admin.initialize_app(credentials.Certificate(info))
        elif os.getenv("EFONA_GOOGLE_APPLICATION_CREDENTIALS"):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.environ["EFONA_GOOGLE_APPLICATION_CREDENTIALS"]
            firebase_admin.initialize_app()
        else:
            raise RuntimeError(
                "Efona Firebase credentials missing. Set EFONA_FIREBASE_CREDENTIALS_JSON "
                "or EFONA_GOOGLE_APPLICATION_CREDENTIALS."
            )
    return firestore.client()


class _LazyFirestore:
    """Resolve the client only when an operation is requested."""
    def __getattr__(self, name):
        return getattr(get_firestore(), name)


db = _LazyFirestore()
