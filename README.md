# Efona Bingo — Firestore migration branch

This branch is being migrated from mixed SQLAlchemy/Firebase code to a single Cloud Firestore data store. The production entry point is Flask (app.py); the Telegram polling bot is bot.py.

## Current implementation

- database.py provides a lazy shared Firebase Admin / Firestore client.
- models.py provides Firestore user, transaction, and atomic transaction-approval helpers.
- app.py provides Telegram WebApp-authenticated game APIs, admin login/dashboard, deposit and withdrawal APIs, and protected transaction actions.
- bingo_service.py stores games and player boards in Firestore; joining charges the entry fee once, number calls are persisted, and Bingo claims are checked server-side before prize payout.
- templates/cartela.html provides the Telegram Mini App game lobby, board, called-number display, and Bingo claim flow.
- templates/admin_dashboard.html provides a token-protected Firestore admin dashboard for games, transactions, and users.
- bot.py uses the same Firestore collections for registration, balance, deposit and withdrawal requests, and opens the Telegram Mini App.
- templates/cartela.html uses Telegram WebApp initData; the API validates its HMAC signature instead of trusting a URL user ID.
- requirements.txt and pyproject.toml no longer install SQLAlchemy/PostgreSQL dependencies.
- .github/workflows/ci.yml adds Python compile and Flask smoke checks.

## Firestore collections

- users/{telegram_id}
- transactions/{transaction_id}
- cartelas/{telegram_id}
- games/{game_id} with a nested players/{telegram_id} subcollection

The Firebase service-account key must never be committed. Set FIREBASE_CREDENTIALS_JSON to the full service-account JSON in the hosting provider's secret environment settings.

## Render setup

The included render.yaml creates one Free Web Service. It starts Flask with Gunicorn and starts the Telegram polling bot in a background thread in that same process to avoid creating a paid Background Worker.

Set these environment variables in Render:

| Variable | Required value |
|---|---|
| FIREBASE_CREDENTIALS_JSON | Full Firebase service-account JSON (secret) |
| BOT_TOKEN | Telegram bot token from BotFather (secret) |
| WEBAPP_URL | The deployed HTTPS URL ending in /cartela |
| ADMIN_IDS | Comma-separated Telegram numeric admin IDs |
| ADMIN_API_TOKEN | Generate a long random token (secret; Render YAML generates one) |
| FLASK_SECRET | Render-generated secret (Render YAML generates one) |
| RUN_TELEGRAM_BOT | true (Render YAML sets this) |

Build command: pip install -r requirements.txt

Start command: gunicorn app:app --workers 1 --threads 4 --timeout 120

**Free-tier limitation:** Render Free Web Services sleep after inactivity. Because the bot polling loop shares this free web process, the bot also stops responding while the service is asleep and resumes only after the service wakes. Always-on bot polling on Render requires a paid always-on worker or a different always-on host. Do not assume the free Render plan provides 24/7 bot availability.

## API notes

- GET / — health check; does not require Firebase credentials.
- GET /api/games — list waiting/active games; requires Telegram WebApp initData.
- POST /api/games — create a game (entry fee 10/20/50/100 ETB); requires Telegram WebApp initData.
- POST /api/games/{id}/join — atomically deduct entry fee and create the player's board.
- GET /api/games/{id} — return game state and the authenticated player's board.
- POST /api/games/{id}/claim — server-side Bingo validation and one-time prize credit.
- POST /api/games/{id}/call — admin-only number call.
- /admin — browser dashboard; sign in using ADMIN_API_TOKEN.
- GET/POST /api/cartela — legacy single-cartela endpoint; requires Telegram WebApp initData.
- POST /deposit and POST /withdraw — require valid Telegram WebApp authentication. Requests are stored as pending.
- GET /admin/transactions, POST /admin/approve/{id}, POST /admin/reject/{id} — require X-Admin-Token: ADMIN_API_TOKEN.

## Important: not ready for real-money/public launch

This commit is a foundation migration, not a finished bingo/payment platform. The current work does not yet complete:
- persistent multiplayer game creation, joining, number calling, marking, winner validation, and prize accounting;
- a full browser-based admin dashboard and Telegram notifications for approval/rejection;
- payment-provider verification (deposit references are user-submitted and must not be treated as verified payments);
- withdrawal reservation/anti-double-spend policy while requests are pending;
- full migration of legacy admin/route modules and end-to-end tests against a real Firestore project.

Do not credit real balances, pay prizes, or launch public cash games until these remaining features and security/legal checks are completed. The API keeps deposits pending until an administrator approves them, but a submitted reference is not proof of payment.

## Local checks

    python -m pip install -r requirements.txt
    python -m compileall -q app.py bot.py database.py firebase_service.py models.py config.py bingo_service.py\n    python -m unittest discover -s tests -v

For local use, set FIREBASE_CREDENTIALS_JSON, BOT_TOKEN, WEBAPP_URL, and ADMIN_API_TOKEN in environment variables. Do not paste secrets into source code or commit them to GitHub.
