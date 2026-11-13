"""Legacy import path kept compatible with the Firestore Flask application.

Admin transaction operations are exposed through the token-protected /admin API
routes in app.py. Configure ADMIN_API_TOKEN in the hosting environment.
"""
from app import app

__all__ = ["app"]

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(__import__("os").getenv("PORT", "5000")))
