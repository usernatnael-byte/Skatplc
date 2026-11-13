import unittest

from bingo_service import make_board, _has_bingo


class BingoRulesTests(unittest.TestCase):
    def test_generated_board_has_valid_bingo_columns_and_free_center(self):
        board = make_board()
        self.assertEqual(len(board), 25)
        self.assertEqual(board[12], 0)
        ranges = ((1, 15), (16, 30), (31, 45), (46, 60), (61, 75))
        for row in range(5):
            for col, (low, high) in enumerate(ranges):
                value = board[row * 5 + col]
                if row == 2 and col == 2:
                    continue
                self.assertGreaterEqual(value, low)
                self.assertLessEqual(value, high)
        self.assertEqual(len([n for n in board if n]), 24)

    def test_bingo_requires_a_complete_line(self):
        board = make_board()
        row_numbers = [board[i] for i in range(5) if board[i] != 0]
        self.assertFalse(_has_bingo(board, row_numbers[:-1]))
        self.assertTrue(_has_bingo(board, row_numbers))

    def test_called_numbers_can_complete_diagonal(self):
        board = make_board()
        diagonal = [board[i * 5 + i] for i in range(5) if board[i * 5 + i] != 0]
        self.assertTrue(_has_bingo(board, diagonal))


if __name__ == "__main__":
    unittest.main()
