from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, List, Type, Tuple


class Color(Enum):
    BLACK = 1
    WHITE = 2

    @property
    def other(self) -> 'Color':
        return Color.BLACK if self == Color.WHITE else Color.WHITE


class Tile(Enum):
    EMPTY = 'empty', None, '-'
    BLACK = 'black', Color.BLACK, 'X'
    WHITE = 'white', Color.WHITE, 'O'
    TIP = 'tip', None, '.'

    @property
    def image_name(self) -> str:
        return self.value[0]

    @property
    def color(self) -> Optional[Color]:
        return self.value[1]

    @property
    def ascii(self):
        return self.value[2]

    @staticmethod
    def for_color(color: Color):
        return Tile.BLACK if color == Color.BLACK else Tile.WHITE

    @property
    def other(self) -> 'Tile':
        if self.color is None:
            return self
        return Tile.BLACK if self == Tile.WHITE else Tile.WHITE


@dataclass
class Score:
    black_stones: int
    white_stones: int
    next_to_move: Optional[Color]

    @property
    def winning_color(self) -> Optional[Color]:
        if self.black_stones == self.white_stones:
            return None
        return Color.BLACK if self.black_stones > self.white_stones else Color.WHITE

    def __repr__(self):
        if self.next_to_move is None:
            if self.black_stones > self.white_stones:
                winner = 'Black wins'
            elif self.white_stones > self.black_stones:
                winner = 'White wins'
            else:
                winner = 'Draw'
            winner_tag = f', {winner}!'
        else:
            winner_tag = ''
        return f'B-W:{self.black_stones}-{self.white_stones}' + winner_tag


@dataclass(frozen=True)
class Move:
    color: Color
    x: int
    y: int

    @property
    def is_skip(self):
        return self.x < 0

    @staticmethod
    def create_skip(color: Color):
        return Move(color, -1, -1)

    def __repr__(self):
        color = self.color.name.lower()
        if self.is_skip:
            return f'{color} skipped'
        return f'{color} {self.x}, {self.y}'


class Board(ABC):
    def __init__(self):
        self._next_to_move: Optional[Color] = Color.BLACK

    @abstractmethod
    def clear(self):
        """Sets up the board to the initial position"""

    @abstractmethod
    def __getitem__(self, row_number: int) -> List[Tile]:
        """Get a specific row of the board"""

    @property
    def finished(self) -> bool:
        return self._next_to_move is None

    @property
    def next_to_move(self) -> Color:
        return self._next_to_move

    @property
    @abstractmethod
    def score(self) -> Score:
        """Compute the current score"""

    @abstractmethod
    def apply(self, move: Move) -> 'Board':
        """Apply a move and return the resulting board"""

    @abstractmethod
    def valid_moves(self) -> List[Move]:
        """Compute the sequence of all valid moves"""

    @staticmethod
    def get_default_type():
        from game.board import ListImplementedBoard
        return ListImplementedBoard


class Player(ABC):
    def __init__(self, color: Color):
        self.color = color

    @abstractmethod
    def next_move(self, board: Board) -> Move:
        """Get the next move from the player"""


class AI(Player):
    def __init__(self, color: Color):
        super().__init__(color)
        self._last_score = None

    @property
    def last_score(self) -> Optional[int]:
        return self._last_score

    def next_move(self, board: Board) -> Move:
        return board.valid_moves()[0]


class Game:
    def __init__(self, board_type: Type[Board], players: Tuple[Player, Player]):
        self._board_type = board_type
        self._board = board_type()
        self._board.clear()
        self._players: Dict[Color, Player] = {}
        self._last_move: Move = None
        for player in players:
            self._players[player.color] = player

    @property
    def board(self):
        return self._board

    def step(self) -> bool:
        board = self._board
        self._last_move = self._players[board.next_to_move].next_move(board)
        self._board = board.apply(self._last_move)
        return not self._board.finished

    def done(self):
        pass

    def run(self):
        try:
            while self.step():
                pass
        except InterruptedError:
            pass
        finally:
            self.done()
