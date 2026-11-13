# Efona Bingo — deployment preparation bundle


## Architecture

- **Render Web Service:** Flask app (`gunicorn app:app`).
- **Render Background Worker:** Telegram bot in polling mode (`python bot.py`).
- **Database:** PostgreSQL on Render is the system of record for the existing SQLAlchemy models.
- **Firebase:** Optional Firebase Admin/Firestore bootstrap is included in `firebase_service.py`. Existing User/Game/Transaction models still use SQLAlchemy; Firestore is NOT a drop-in replacement and is not yet the source of truth. Do not enter Firestore-only credentials and assume game/payment data is being stored there.

## Local run

Use Python 3.11. From the repository root:

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `BOT_TOKEN` and a strong `FLASK_SECRET`, then run the web service and bot in separate terminals:

```bash
gunicorn app:app
python bot.py
```

For local development only, the app falls back to `sqlite:///efona_local.db` when `DATABASE_URL` is not set. Hosted deployments must use PostgreSQL.

## GitHub upload

1. Create a **private** GitHub repository.
2. Extract this ZIP locally and upload the contents (not the enclosing folder) to the repository root.
3. Confirm `.env`, service-account JSON files, database files and tokens are not committed. `.gitignore` is provided.
4. Commit and push the code. Never put bot tokens, Firebase private keys or passwords in source files or GitHub Actions logs.

CLI alternative:

```bash
git init
git add .
git commit -m "Prepare Efona Bingo deployment"
git branch -M main
git remote add origin https://github.com/YOUR_ACCOUNT/efona-bingo.git
git push -u origin main
```

## Render deployment

The included `render.yaml` describes a Web Service, a Background Worker and a PostgreSQL database. In Render:

1. Choose **New → Blueprint** and connect the GitHub repository.
2. Review the Blueprint and create the resources. The database plan in the YAML may incur charges; choose an available plan that meets your expected traffic and backup requirements.
3. Set `BOT_TOKEN` on the worker and `ADMIN_IDS` (comma-separated Telegram numeric IDs).
4. Set `ADMIN_USERNAME` and `ADMIN_PASSWORD` on the web service to unique strong values.
5. Set `WEBAPP_URL` to the actual public HTTPS URL of the web service plus the intended page path.
6. Confirm both services use the same PostgreSQL database URL.
7. Deploy and inspect both service logs. Test `/` on the web URL; it should return a JSON health response.

If you create services manually instead of using the Blueprint:

**Web Service**
- Build: `pip install -r requirements.txt`
- Start: `gunicorn app:app --workers 1 --threads 4 --timeout 120`

**Background Worker**
- Build: `pip install -r requirements.txt`
- Start: `python bot.py`

**Required environment values**

| Variable | Where | Value |
|---|---|---|
| `DATABASE_URL` | Web + Worker | Same Render PostgreSQL Internal URL |
| `BOT_TOKEN` | Worker | Token from BotFather; keep private |
| `ADMIN_IDS` | Worker | Telegram numeric admin IDs, comma-separated |
| `WEBAPP_URL` | Worker + Web if needed | Actual public HTTPS URL for the Mini App |
| `FLASK_SECRET` | Web + Worker | Long random secret; same value if sessions are shared |
| `SECRET_KEY` | Web | Different long random secret |
| `ADMIN_API_TOKEN` | Web | Long random token for protected admin API endpoints |
| `ADMIN_USERNAME` | Web | Unique admin login name |
| `ADMIN_PASSWORD` | Web | Strong unique password |
| `FIREBASE_PROJECT_ID` | Optional | Firebase project ID |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | Optional | Entire service-account JSON as a one-line secret value |

Do not paste real secret values into ChatGPT, GitHub issues, screenshots or public files. If a token has been exposed, rotate it with its provider.

## Firebase setup (optional)

1. Create a Firebase project in the Firebase Console.
2. Enable Firestore only if a feature specifically needs it; create a database in the correct region.
3. Create a service account in Project Settings → Service Accounts and generate a private key. Store the JSON securely; never commit it.
4. Add `FIREBASE_PROJECT_ID` and the complete service-account JSON to Render Environment as secret values.
5. Redeploy. `firebase_service.get_firestore_client()` initializes Firestore when called.

**Important:** Current user, game, participant and transaction tables are SQLAlchemy models. They continue to use PostgreSQL. A real migration to Firestore requires redesigning all queries, transactions, indexes, security rules and concurrency handling. Do not delete PostgreSQL or assume Firestore contains these records.




3. In the Gradle properties for the build, set `WEB_APP_URL=https://YOUR-WEB-SERVICE.onrender.com/cartela` (replace with the real URL).
5. Use **Build → Build Bundle(s) / APK(s) → Build APK(s)**.
6. Test on a physical device. The WebView must load only the HTTPS production URL.

## Current limitations — must be addressed before public launch

The uploaded source is a partially implemented prototype, not a finished commercial bingo platform. In particular:

- Live game sessions and cartela preview data are currently held in process memory; they are lost on restart and are not shared across multiple Render instances.
- Telegram WebApp `initData` signature validation and full user authorization are not yet implemented on all API routes. A client-supplied Telegram/user ID must never be trusted as authentication.
- Deposit proof must be checked against the actual bank/payment provider before balance credit. The `/deposit` API was changed to create a pending record instead of instantly crediting a client-supplied amount, but payment-provider verification is not integrated.
- Withdrawals, game entry fees, winner selection, prize pool accounting, referral bonuses and admin actions need transactional rules, audit logging and independent security testing before real money is used.
- The included cartela endpoint is a preview scaffold, not the complete multiplayer game state implementation.
- Firebase initialization is optional scaffolding; the existing relational business logic is not migrated to Firestore.

Do not use this prototype to accept real money until the above items have been completed and independently tested. For an ETB cash-prize Bingo product, also obtain local legal/compliance advice before public operation.

## Basic checks

```bash
python -m compileall .
```

