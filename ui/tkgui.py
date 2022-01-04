from bisect import bisect
from threading import Thread, Condition
from time import time, sleep
from typing import Optional, Callable, Type, Tuple

from game2dboard import Board as TkBoard

from game.ai import NegaMaxPlayer
from game.api import Board, Game, Player, Color, Move, Tile, AI
from ui.api import UI

BOARD_MARGIN = 20
CELL_SIZE = 50
BANNER_WIDTH = 48

HELP_KEY = 'F1'
SWITCH_SIDE_KEY = 's'
RESTART_KEY = 'r'
HINT_KEY = 'x'


class Banner:
    def __init__(self, width: int, stop_time: Optional[int] = None, ttl: Optional[int] = None):
        self._message = ''
        self._deadline = time() + ttl if ttl else None
        self._time_to_move = time() + stop_time if stop_time else None
        self._scrollpos: Optional[int] = None
        self._width = width

    @property
    def message(self):
        return self._message[:-self._width]

    @message.setter
    def message(self, txt: str):
        if txt != self.message:
            self._message = txt + ' ' * self._width
            self._scrollpos = 0 if len(txt) > self._width else None

    def step(self):
        if self._scrollpos is None:
            return self.message
        if self._time_to_move is None or time() > self._time_to_move:
            self._scrollpos += 1
            if self._scrollpos > len(self._message) - self._width:
                self._scrollpos = 0
                if self._message[0] != ' ':
                    self._message = ' ' * self._width + self._message
        msg = f'{self._message[self._scrollpos: self._scrollpos + self._width]}'
        return msg

    def valid(self):
        return self._deadline is None or self._deadline >= time()


class TkPlayer(Player):
    def __init__(self, gui: 'TkGui', color: Color):
        super().__init__(color)
        self.gui = gui
        self.my_move: Optional[Move] = None
        self.clicked = Condition()
        self.quit_requested = False
        self.board_for_my_turn: Optional[Board] = None

    def next_move(self, board: Board) -> Move:
        if board.valid_moves()[0].is_skip:
            self.gui.set_banner('No valid moves, click to acknowledge')
        with self.clicked:
            self.board_for_my_turn = board
            try:
                while True:
                    self.clicked.wait()
                    if self.quit_requested:
                        raise InterruptedError()
                    if self.my_move is not None:
                        return self.my_move
            finally:
                self.board_for_my_turn = None

    def last_click(self, x: int, y: int):
        with self.clicked:
            if self.board_for_my_turn is not None:
                move = Move(self.color, x, y)
                valid_moves = self.board_for_my_turn.valid_moves()
                if valid_moves[0].is_skip:
                    move = valid_moves[0]
                if move in valid_moves:
                    self.my_move = move
                    self.clicked.notify()
                else:
                    self.gui.push_banner('Invalid move - indicating valid moves!', ttl=3)
                    for move in valid_moves:
                        self.gui.tkboard[move.x][move.y] = Tile.TIP.image_name
            else:
                pass  # TODO - indicate it is not our turn?

    def stop(self):
        with self.clicked:
            self.quit_requested = True
            self.clicked.notify()


class TkGame(Game):
    def __init__(self, board_type: Type[Board], players: Tuple[Player, Player], on_change: Callable[[Move], None]):
        super().__init__(board_type, players)
        self._thread = Thread(target=self.run)
        self._on_change = on_change
        self._running = True

    def step(self):
        if self._running:
            stepping = super().step()
            self._on_change(self._last_move)
            return stepping
        else:
            raise InterruptedError()

    def start(self):
        self._thread.start()

    def stop(self):
        self._running = False


class Taunter:
    THRESHOLDS = [20, 50, 900]

    def __init__(self):
        self._pos = 0

    def get_taunt(self, last_pos, new_pos):
        if new_pos > last_pos:
            # Getting better
            if new_pos < 0:
                return 'Looks better now. Scared yet?'
            if new_pos == 0:
                return 'You thought you were ahead, hu?'
            if new_pos == 1:
                return 'I am very pleased with this development.'
            if new_pos == 2:
                return 'No way you can turn this into a victory!'
            if new_pos == 3:
                return 'HAHA! I think it is time for you to resign this game. I WIN!!!'
        else:
            # Getting worse
            if new_pos == 1:
                return 'No matter, I am still winning this!'
            if new_pos == 0:
                return 'I may have lost some of the edge, but I am still better than you.'
            if new_pos == -1:
                return 'Well, that may seem like you made a good move, but looks can be deceiving.'
            if new_pos == -2:
                return 'ok, ok, ok... Stop looking so happy about it.'
            if new_pos == -3:
                return 'I have actually started to think about our next game. Somehow I have lost interest in ' \
                       'what happens in this game.'

        return 'I do not understand. How did this happen?'

    def taunt(self, new_score: int) -> Optional[str]:
        if neg := new_score < 0:
            new_score = -new_score
        i = bisect(Taunter.THRESHOLDS, new_score)
        pos = -i if neg else i

        taunt = None
        if pos != self._pos:
            taunt = self.get_taunt(self._pos, pos)
            self._pos = pos
        return taunt


class TkGui(UI):
    def __init__(self):
        self.banners = []
        self.tkboard: Optional[TkBoard] = None
        self._player: Optional[TkPlayer] = None
        self._ai: Optional[AI] = None
        self._game: Optional[TkGame] = None
        self._ai_color = Color.WHITE
        self._ai_depth = 3
        self._taunter = Taunter()

    def _reset(self):
        self._taunter = Taunter()
        self.banners = []
        self.push_banner(f'Welcome to Othello. Press {SWITCH_SIDE_KEY} to switch sides.', ttl=None)
        if self._game is not None:
            self._game.stop()
        human = self._ai_color.other
        self.tkboard.title = f"Othello (you are playing {human.name.lower()})"
        self._player = TkPlayer(self, human)
        self._ai = NegaMaxPlayer(self._ai_color, self._ai_depth)
        self._game = TkGame(Board.get_default_type(), (self._player, self._ai), self._update_view)
        self._update_view(None)
        self._game.start()

    def _move_on_board(self, move: Move):
        info = 'skipped' if move.is_skip else f'{move.x + 1}{"ABCDEFGH"[move.y]}'
        return f'{move.color.name.lower()} {info}'

    def _update_view(self, last_move: Optional[Move]):
        tk = self.tkboard
        b = self._game.board
        if b.finished:
            self.set_banner(f'{b.score}, press {RESTART_KEY} to restart')
        else:
            if last_move is not None:
                self.set_banner(f'Last: {self._move_on_board(last_move)}, '
                                f'Score {b.score} AI:{self._ai.last_score or 0}')
                if last_move.color == self._ai.color:

                    if (taunt := self._taunter.taunt(self._ai.last_score)) is not None:
                        self.push_banner(taunt, ttl=5)
                if not last_move.is_skip:
                    tk[last_move.x][last_move.y] = Tile.for_color(last_move.color).image_name
                    sleep(0.3)

        for x in range(8):
            tk_row, game_row = tk[x], b[x]
            for y, game_cell in enumerate(game_row):
                tk_row[y] = game_cell.image_name

        if not b.finished:
            color_to_move = b.next_to_move
            player_to_move = 'you' if self._player.color == color_to_move else 'AI'
            self.tkboard.title = f"Othello - {color_to_move.name.lower()} ({player_to_move}) to move."

    def set_banner(self, txt='', stop_time: int = 1, tag: str = None):
        banner = Banner(BANNER_WIDTH, stop_time, ttl=None)
        banner.message = txt
        banner.tag = tag
        self.banners = [banner]

    def push_banner(self, txt='', stop_time: int = 1, ttl: Optional[int] = 5, tag: str = None):
        banner = Banner(BANNER_WIDTH, stop_time, ttl)
        banner.message = txt
        banner.tag = tag
        self.banners.append(banner)

    def init(self):
        board = self.tkboard = TkBoard(8, 8)
        board.background_image = 'board'
        board.cell_size = CELL_SIZE
        board.margin = BOARD_MARGIN
        board.cell_spacing = 0
        board.title = "Othello"
        board.on_mouse_click = self._on_mouse
        board.on_timer = self._on_timer
        board.on_key_press = self._on_key
        board.create_output(background_color='#427F5F', font_size=11)
        self._reset()

    def run(self):
        self.tkboard.start_timer(300)
        self.tkboard.show()

    def _on_mouse(self, _btn, row: int, col: int):
        self._player.last_click(row, col)

    def _on_timer(self):
        self._update_banner()

    def _update_banner(self):
        if self.banners:
            banner = self.banners.pop()
            if banner.valid():
                self.tkboard.print(banner.step())
                self.banners.append(banner)
            else:
                self._update_banner()

    def _on_key(self, key: str):
        if key == SWITCH_SIDE_KEY:
            self._ai_color = self._ai_color.other
            self._game.stop()
            self._reset()
            self.set_banner(f'You are playing {self._ai_color.other.name.lower()}.')
        elif key == RESTART_KEY:
            self._reset()
            self.set_banner(f'Game restarted. You are playing {self._ai_color.other.name.lower()}.')
        elif key == HELP_KEY:
            if self.banners and self.banners[-1].tag == 'help':
                self.banners.pop()
            else:
                self.push_banner(f'Keys: {SWITCH_SIDE_KEY} - switch side, {RESTART_KEY} - restart game, '
                                 f'{HINT_KEY} - get hints. '
                                 f'Press {HELP_KEY} again to close. ',
                                 2, None, 'help')
        elif key == HINT_KEY:
            board = self._game.board
            if color := board.next_to_move is not None:
                ai = NegaMaxPlayer(color, 3)
                for negamax in ai.score_moves(board):
                    self.tkboard[negamax.move.x][negamax.move.y] = negamax.score
        elif key == 'y':
            board = self._game.board
            if color := board.next_to_move is not None:
                ai = NegaMaxPlayer(color, self._ai_depth - 1)
                for negamax in ai.score_moves(board):
                    self.tkboard[negamax.move.x][negamax.move.y] = negamax.score
        else:
            self.push_banner(f'Thank you for pressing the {key} key. Press {HELP_KEY} for help.')

    def cleanup(self):
        if self._game is not None:
            self._game.stop()
        if self._player is not None:
            self._player.stop()
        self.tkboard.close()

