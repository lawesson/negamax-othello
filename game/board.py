from typing import List, Optional

from game.api import Board, Tile, Move, Score


class BoardRow(List[Tile]):
    def __init__(self, tiles=None):
        super().__init__()
        if tiles:
            for tile in tiles:
                self.append(tile)
        else:
            for _ in range(8):
                self.append(Tile.EMPTY)

    def __repr__(self) -> str:
        return ''.join([tile.ascii for tile in self])


class ListImplementedBoard(Board):
    def __init__(self, tiles=None):
        super().__init__()
        if tiles is None:
            self._tiles: List[BoardRow] = []
            for _ in range(8):
                self._tiles.append(BoardRow())
        else:
            self._tiles = tiles
        self._score = None
        self._empty_count = 64

    def clear(self):
        self._tiles[3][3] = Tile.WHITE
        self._tiles[4][4] = Tile.WHITE
        self._tiles[3][4] = Tile.BLACK
        self._tiles[4][3] = Tile.BLACK
        self._empty_count = 60

    def __getitem__(self, row_number: int) -> List[Tile]:
        return self._tiles[row_number]

    def get_tile(self, x, y) -> Optional[Tile]:
        if x < 0 or x > 7 or y < 0 or y > 7:
            return None
        return self[x][y]

    @property
    def score(self) -> Score:
        if self._score is not None:
            return self._score
        counts = {tile: 0 for tile in Tile}
        for row in self._tiles:
            for tile in row:
                counts[tile] += 1

        self._score = Score(counts[Tile.BLACK], counts[Tile.WHITE], self._next_to_move)
        return self._score

    def _clone(self) -> 'ListImplementedBoard':
        tiles = [BoardRow(row) for row in self._tiles]
        board = ListImplementedBoard(tiles)
        board._next_to_move = self._next_to_move
        board._empty_count = self._empty_count
        return board

    def _apply_destructive(self, move: Move) -> Board:
        self._next_to_move = move.color.other

        if move.is_skip:
            return self

        tile = Tile.for_color(move.color)
        other = tile.other
        self[move.x][move.y] = tile
        self._empty_count -= 1

        for other_x, other_y in self._find_neighbour_tiles(move.x, move.y, other):
            dx, dy = other_x - move.x, other_y - move.y
            x, y = other_x + dx, other_y + dy
            path = [(other_x, other_y)]
            while (ending_tile := self.get_tile(x, y)) == other:
                path.append((x, y))
                x += dx
                y += dy
            if tile == ending_tile:
                for item in path:
                    self[item[0]][item[1]] = tile

        if not self.valid_moves():
            self._next_to_move = None

        self._score = None
        return self

    def apply(self, move: Move) -> Board:
        clone = self._clone()
        return clone._apply_destructive(move)

    def _find_tiles(self, tile: Tile):
        for x, row in enumerate(self._tiles):
            for y, cell_tile in enumerate(row):
                if cell_tile == tile:
                    yield x, y

    def _find_neighbour_tiles(self, x: int, y: int, tile: Tile):
        for dx in (-1, 0, 1):
            other_x = x + dx
            if 0 <= other_x <= 7:
                row = self._tiles[other_x]
                other_ys = (-1, 0, 1) if dx != 0 else (-1, 1)
                for dy in other_ys:
                    other_y = y + dy
                    if 0 <= other_y <= 7 and row[other_y] == tile:
                        yield other_x, other_y

    def _valid_moves_for(self, tile: Tile):
        moves = []
        other_tile = tile.other

        if self._empty_count < 50:
            start = Tile.EMPTY
            stop = tile
            add_start = True
        else:
            start = tile
            stop = Tile.EMPTY
            add_start = False

        for origin_x, origin_y in self._find_tiles(start):
            for other_x, other_y in self._find_neighbour_tiles(origin_x, origin_y, other_tile):
                dx, dy = other_x - origin_x, other_y - origin_y
                x, y = other_x + dx, other_y + dy
                while (stepping_tile := self.get_tile(x, y)) == other_tile:
                    x += dx
                    y += dy
                if stepping_tile == stop:
                    if add_start:
                        moves.append(Move(tile.color, origin_x, origin_y))
                        break
                    else:
                        moves.append(Move(tile.color, x, y))

        return moves

    def valid_moves(self) -> List[Move]:
        tile = Tile.for_color(self._next_to_move)
        moves = self._valid_moves_for(tile)

        if not moves:
            moves = [Move.create_skip(tile.color)] if self._valid_moves_for(tile.other) else []
        return moves
