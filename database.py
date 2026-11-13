"""Single SQLAlchemy extension shared by every application module."""
import os
from models import db


def _database_url():
    url = os.getenv("DATABASE_URL")
    if not url:
        # Local development only. Render production must set DATABASE_URL.
        return "sqlite:///efona_local.db"
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


def init_db(app):
    app.config.setdefault("SQLALCHEMY_DATABASE_URI", _database_url())
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)
    app.config.setdefault("SQLALCHEMY_ENGINE_OPTIONS", {"pool_pre_ping": True, "pool_recycle": 300})
    db.init_app(app)
    with app.app_context():
        db.create_all()
    return db

__all__ = ["db", "init_db"]
