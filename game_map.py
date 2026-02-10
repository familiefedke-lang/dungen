from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple

import tile_types


class TileGrid:
    def __init__(self, width: int, height: int, fill: int) -> None:
        self.width = width
        self.height = height
        self._tiles = [[fill for _ in range(height)] for _ in range(width)]

    def __getitem__(self, index: Tuple[int | slice, int | slice]):
        x_index, y_index = index
        if isinstance(x_index, slice) or isinstance(y_index, slice):
            x_values = self._expand_index(x_index, self.width)
            y_values = self._expand_index(y_index, self.height)
            return [
                [self._tiles[x][y] for y in y_values]
                for x in x_values
            ]
        return self._tiles[x_index][y_index]

    def __setitem__(self, index: Tuple[int | slice, int | slice], value: int) -> None:
        x_index, y_index = index
        x_values = self._expand_index(x_index, self.width)
        y_values = self._expand_index(y_index, self.height)
        for x in x_values:
            for y in y_values:
                self._tiles[x][y] = value

    @staticmethod
    def _expand_index(index: int | slice, maximum: int) -> Iterable[int]:
        if isinstance(index, slice):
            return range(*index.indices(maximum))
        return [index]


@dataclass
class GameMap:
    width: int
    height: int

    def __post_init__(self) -> None:
        self.tiles = TileGrid(self.width, self.height, tile_types.wall)
        self.entrance = (0, 0)
        self.exit = (self.width - 1, self.height - 1)

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def is_walkable(self, x: int, y: int) -> bool:
        return self.in_bounds(x, y) and self.tiles[x, y] == tile_types.floor
