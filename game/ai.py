from dataclasses import dataclass
from typing import List, Optional

from game.api import Board, Move, Color, Tile, AI

SCORE_MATRIX = [[20,  5,  5,  5],
                [ 5, -2, -1, -1],
                [ 5, -1,  0,  0],
                [ 5, -1,  0,  0]]


def neg(i: Optional[int]) -> Optional[int]:
    return None if i is None else -i


@dataclass
class NegamaxResult:
    score: int
    move: Optional[Move] = None


class NegaMaxPlayer(AI):
    def __init__(self, color: Color, depth: int, score_matrix: List[List[int]] = None):
        super().__init__(color)
        self.depth = int(depth)
        corner = score_matrix or SCORE_MATRIX
        top_half_matrix = [row + list(reversed(row)) for row in corner]
        self._matrix = top_half_matrix + list(reversed(top_half_matrix))

    def _evaluate(self, board, color) -> int:
        """compute a score with respect to the player in turn to move"""
        if board.finished:
            winner = board.score.winning_color
            if winner is None:
                return 0
            return 999 if color == winner else -999
        else:
            return self._evaluate_heuristic(board, color)

    def _evaluate_heuristic(self, board, color) -> int:
        my_tile = Tile.for_color(color)
        other_tile = my_tile.other
        score = 0
        for row, score_row in zip(board, self._matrix):
            for tile, tile_score in zip(row, score_row):
                if tile == my_tile:
                    score += tile_score
                elif tile == other_tile:
                    score -= tile_score
        return score

    def _negamax(self, board: Board, depth: int, alpha: Optional[int], beta: Optional[int], color) -> NegamaxResult:
        if depth == 0 or board.finished:
            return NegamaxResult(self._evaluate(board, color))

        valid_moves = board.valid_moves()
        if not valid_moves:
            return NegamaxResult(self._evaluate(board, color))

        moves_with_preference = [(self._matrix[move.x][move.y], move) for move in valid_moves]
        moves_with_preference.sort(key=lambda t: t[0], reverse=True)

        value = None
        best_move = None
        for item in moves_with_preference:
            move = item[1]
            item_score = -self._negamax(board.apply(move), depth - 1, neg(beta), neg(alpha), color.other).score
            if value is None or item_score > value:
                value = item_score
                best_move = move
            if alpha is None or value > alpha:
                alpha = value
            if beta is not None and alpha >= beta:
                break
        return NegamaxResult(value, best_move)

    def score_moves(self, board) -> List[NegamaxResult]:
        result = []
        for move in board.valid_moves():
            score = -self._negamax(board.apply(move), self.depth, None, None, board.next_to_move.other).score
            result.append(NegamaxResult(score, move))
        return result

    def next_move(self, board: Board) -> Move:
        negamax = self._negamax(board, self.depth, None, None, board.next_to_move)
        self._last_score = negamax.score
        return negamax.move

