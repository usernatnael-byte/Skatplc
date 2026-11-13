import random
import threading
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
from telegram import InputFile
import os

def play_bingo_audio(chat_id: int, number: int, context: Any):
    filename = BingoGame.format_number(number).lower().replace("-", "") + ".ogg"
    path = os.path.join("audio", "bingo", filename)
    try:
        context.bot.send_voice(chat_id=chat_id, voice=InputFile(path))
    except Exception as e:
        context.bot.send_message(chat_id=chat_id, text=f"🎙️ Audio for {number} not found.")

class BingoGame:
    def __init__(self, game_id: int, entry_price: int = 10):
        self.game_id = game_id
        self.entry_price = entry_price
        self.pool = 0
        self.players: Dict[int, List[dict]] = {}
        self.called_numbers: List[int] = []
        self.status = "waiting"
        self.winner_id = None
        self.created_at = datetime.utcnow()
        self.finished_at = None

        self.min_players = 1
        self.max_players = 100
        self.call_interval = 3.5
        self.last_call_time = None
        self.auto_call_timer = None

        self.player_modes: Dict[int, str] = {}
        self.sound_enabled: Dict[int, bool] = {}
        self.leaderboard: Dict[int, Dict[str, int]] = {}
        self.admin_earnings = 0

    def generate_board(self, cartela_number: int) -> List[int]:
        random.seed(cartela_number)
        b = random.sample(range(1, 16), 5)
        i = random.sample(range(16, 31), 5)
        n = random.sample(range(31, 46), 5)
        g = random.sample(range(46, 61), 5)
        o = random.sample(range(61, 76), 5)
        random.seed()

        board = []
        for row in range(5):
            board.extend([b[row], i[row], n[row], g[row], o[row]])
        return board

    def add_player(self, user_id: int, cartela_number: Optional[int] = None, mode: str = "auto") -> List[int]:
        if user_id not in self.players:
            self.players[user_id] = []

        if len(self.players[user_id]) >= 5:
            return []

        used_cartelas = {b['cartela_number'] for boards in self.players.values() for b in boards}
        available = [n for n in range(1, 101) if n not in used_cartelas]
        cartela_number = cartela_number or (random.choice(available) if available else 0)

        board = self.generate_board(cartela_number)
        self.players[user_id].append({
            'board': board,
            'marked': [board[12]],
            'cartela_number': cartela_number
        })

        self.pool += self.entry_price
        self.player_modes[user_id] = mode
        self.sound_enabled[user_id] = True

        if self.status == "waiting" and self.total_players() >= self.min_players:
            self.start_game()

        return board

    def total_players(self) -> int:
        return sum(len(boards) for boards in self.players.values())

    def toggle_sound(self, user_id: int, enabled: bool):
        self.sound_enabled[user_id] = enabled

    def toggle_mode(self, user_id: int, mode: str):
        self.player_modes[user_id] = mode

    def start_game(self, chat_id: Optional[int] = None, context: Optional[Any] = None) -> bool:
        if self.status != "waiting":
            return False
        self.status = "active"
        self.call_number(chat_id=chat_id, context=context)
        self.schedule_next_call(chat_id, context)
        return True

    def schedule_next_call(self, chat_id: Optional[int], context: Optional[Any]):
        if self.status == "active" and "auto" in self.player_modes.values():
            self.auto_call_timer = threading.Timer(
                self.call_interval,
                lambda: self.auto_call(chat_id, context)
            )
            self.auto_call_timer.start()

    def auto_call(self, chat_id: Optional[int], context: Optional[Any]):
        if self.status != "active":
            return

        result = self.call_number(chat_id=chat_id, context=context)
        if not result:
            return

        number = int(result["formatted"].split("-")[1])
        for user_id in self.players:
            self.mark_number(user_id, number)
            won, message = self.check_winner(user_id)
            if won:
                self.end_game(user_id)
                if context:
                    context.bot.send_message(chat_id=user_id, text=f"🎉 {message}")
                return

        self.schedule_next_call(chat_id, context)

    def call_number(self, chat_id: Optional[int] = None, context: Optional[Any] = None) -> Optional[Dict[str, Optional[str]]]:
        available = [n for n in range(1, 76) if n not in self.called_numbers]
        if not available:
            self.status = "finished"
            self.finished_at = datetime.utcnow()
            return None

        number = random.choice(available)
        self.called_numbers.append(number)
        self.last_call_time = datetime.utcnow()

        if chat_id and context and self.sound_enabled.get(chat_id, True):
            play_bingo_audio(chat_id, number, context)

        return {
            "formatted": self.format_number(number),
            "audio": self.audio_filename(number)
        }

    def manual_call(self, number: int) -> bool:
        if number in self.called_numbers or not (1 <= number <= 75):
            return False
        self.called_numbers.append(number)
        self.last_call_time = datetime.utcnow()
        return True

    def mark_number(self, user_id: int, number: int) -> bool:
        if user_id not in self.players:
            return False
        updated = False
        for board in self.players[user_id]:
            if number in board['board'] and number in self.called_numbers:
                if number not in board['marked']:
                    board['marked'].append(number)
                    board['marked'].sort()
                    updated = True
        return updated

    def check_winner(self, user_id: int) -> Tuple[bool, str]:
        if user_id not in self.players:
            return False, "Player not in game"

        for board in self.players[user_id]:
            marked = set(board['marked'])
            b = board['board']

            for i in range(0, 25, 5):
                if all(b[i + j] in marked for j in range(5)):
                    return True, "Winner - Row complete!"

            for i in range(5):
                if all(b[i + j*5] in marked for j in range(5)):
                    return True, "Winner - Column complete!"

            if all(b[i] in marked for i in [0, 6, 12, 18, 24]):
                return True, "Winner - Diagonal complete!"
            if all(b[i] in marked for i in [4, 8, 12, 16, 20]):
                return True, "Winner - Diagonal complete!"

            if all(b[i] in marked for i in [0, 4, 20, 24]):
                return True, "Winner - Corner complete!"

        return False, "Keep playing"

    def end_game(self, winner_id: int):
        self.winner_id = winner_id
        self.status = "finished"
        self.finished_at = datetime.utcnow()
        if self.auto_call_timer:
            self.auto_call_timer.cancel()

        commission = int(self.pool * 0.20)
        payout = self.pool - commission
        self.admin_earnings = commission

        if winner_id not in self.leaderboard:
            self.leaderboard[winner_id] = {"wins": 0, "earnings": 0}
        self.leaderboard[winner_id]["wins"] += 1
        self.leaderboard[winner_id]["earnings"] += payout

    @staticmethod
    def format_number(number: int) -> str:
        if 1 <= number <= 15: return f"B-{number}"
        elif 16 <= number <= 30: return f"I-{number}"
        elif 31 <= number <= 45: return f"N-{number}"
        elif 46 <= number <= 60: return f"G-{number}"
        else: return f"O-{number}"

    @staticmethod
    def audio_filename(number: int) -> str:
        return f"{BingoGame.format_number(number).lower().replace('-', '')}.ogg"

    def get_leaderboard(self, top_n: int = 10) -> List[Tuple[int, int, int]]:
        sorted_lb = sorted(
            self.leaderboard.items(),
            key=lambda item: (item[1]["earnings"], item[1]["wins"]),
            reverse=True
        )
        return [(uid, data["wins"], data["earnings"]) for uid, data in sorted_lb[:top_n]]
   
    def get_player_summary(self, user_id: int) -> List[Dict[str, Any]]:
        return [
            {
                "cartela_number": b["cartela_number"],
                "marked": b["marked"],
                "mode": self.player_modes.get(user_id, "auto"),
                "sound": self.sound_enabled.get(user_id, True)
            }
            for b in self.players.get(user_id, [])
        ]

    def get_called_history(self) -> List[str]:
        return [self.format_number(n) for n in self.called_numbers]

    def get_winner_board(self) -> Optional[List[int]]:
        if self.winner_id and self.winner_id in self.players:
            return self.players[self.winner_id][0]["board"]
        return None

    def is_ready(self) -> bool:
        return self.status == "waiting" and self.total_players() >= self.min_players

    def reset_game(self):
        self.status = "waiting"
        self.called_numbers.clear()
        self.winner_id = None
        self.finished_at = None
        self.last_call_time = None
        self.admin_earnings = 0
        if self.auto_call_timer:
            self.auto_call_timer.cancel()
            self.auto_call_timer = None
        logging.info(f"🔄 Game {self.game_id} has been reset.")

    def summary(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "status": self.status,
            "players": self.total_players(),
            "pool": self.pool,
            "called": len(self.called_numbers),
            "winner": self.winner_id,
            "created_at": self.created_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "admin_earnings": self.admin_earnings
        }
