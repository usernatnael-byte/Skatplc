from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# -------------------- USER MODEL --------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.BigInteger, unique=True, nullable=False, index=True)
    username = db.Column(db.String(64))
    phone = db.Column(db.String(20))
    balance = db.Column(db.Float, default=0.0)
    games_played = db.Column(db.Integer, default=0)
    games_won = db.Column(db.Integer, default=0)
    sound_enabled = db.Column(db.Boolean, default=True)
    play_mode = db.Column(db.String(10), default="auto")
    language = db.Column(db.String(10), default="en")
    is_admin = db.Column(db.Boolean, default=False)

    referrer_id = db.Column(db.BigInteger, db.ForeignKey('user.id'), nullable=True)
    referred_users = db.relationship('User', backref=db.backref('referrer', remote_side=[id]), lazy=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    game_entries = db.relationship('GameParticipant', backref='user', lazy=True)
    won_games = db.relationship('Game', backref='winner', lazy=True)
    scheduled_games = db.relationship('ScheduledGame', backref='creator', lazy=True)

# -------------------- GAME MODEL --------------------

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), default='waiting', index=True)
    entry_price = db.Column(db.Float, nullable=False)
    pool = db.Column(db.Float, default=0.0)
    payout = db.Column(db.Float, default=0.0)
    commission = db.Column(db.Float, default=0.0)
    called_numbers = db.Column(db.PickleType)

    winner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    finished_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    participants = db.relationship('GameParticipant', backref='game', lazy=True)

# -------------------- GAME PARTICIPANT MODEL --------------------

class GameParticipant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    cartela_number = db.Column(db.Integer, nullable=False)
    cartela_count = db.Column(db.Integer, default=1)
    marked_numbers = db.Column(db.PickleType)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('game_id', 'cartela_number', name='unique_cartela_per_game'),
    )

# -------------------- TRANSACTION MODEL --------------------

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    type = db.Column(db.String(20), index=True)  # deposit, withdraw, referral_bonus, jackpot_win
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending', index=True)

    method = db.Column(db.String(20))            # cbe_birr, telebirr, etc.
    reference = db.Column(db.String(100))        # user input
    reason = db.Column(db.String(200))           # optional admin note

    deposit_phone = db.Column(db.String(20))
    transaction_id = db.Column(db.String(100))
    sms_text = db.Column(db.Text)

    withdrawal_phone = db.Column(db.String(20))
    withdrawal_status = db.Column(db.String(20))
    admin_note = db.Column(db.Text)

    approved_by = db.Column(db.String(64))        # Telegram ID or username of admin
    approval_note = db.Column(db.String(200))     # Optional comment

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# -------------------- SCHEDULED GAME MODEL --------------------

class ScheduledGame(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    start_time = db.Column(db.DateTime)
    entry_price = db.Column(db.Float, default=10.0)
    status = db.Column(db.String(20), default="pending", index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# -------------------- JACKPOT LOBBY MODEL --------------------

lobby_players = db.Table("lobby_players",
    db.Column("lobby_id", db.Integer, db.ForeignKey("lobby.id")),
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"))
)

class Lobby(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), default="waiting")  # waiting, active, completed
    jackpot = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    players = db.relationship("User", secondary=lobby_players, backref="lobbies")

# -------------------- INDEXES --------------------

db.Index('ix_game_created_at', Game.created_at)
db.Index('ix_transaction_created_at', Transaction.created_at)
