"""Optional Firebase Admin SDK bootstrap.

The current application data layer is SQLAlchemy (PostgreSQL/SQLite). This
module initializes Firebase Admin/Firestore for optional Firebase features;
it does NOT silently migrate relational models into Firestore.
"""
import json
import os
from functools import lru_cache


@lru_cache(maxsize=1)
def get_firebase_app():
    raw = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    project_id = os.getenv("FIREBASE_PROJECT_ID")
    if not raw:
        return None
    import firebase_admin
    from firebase_admin import credentials
    try:
        existing = firebase_admin.get_app()
        return existing
    except ValueError:
        info = json.loads(raw)
        cred = credentials.Certificate(info)
        options = {"projectId": project_id or info.get("project_id")}
        return firebase_admin.initialize_app(cred, options)


def get_firestore_client():
    app = get_firebase_app()
    if app is None:
        return None
    from firebase_admin import firestore
    return firestore.client(app=app)
