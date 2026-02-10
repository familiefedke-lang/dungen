from __future__ import annotations

import random
from typing import Iterator, List, Tuple, TYPE_CHECKING

try:
    import tcod
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    tcod = None

from game_map import GameMap
import tile_types


if TYPE_CHECKING:
    from entity import Entity


class RectangularRoom:
    def __init__(self, x: int, y: int, width: int, height: int):
        self.x1 = x
        self.y1 = y
        self.x2 = x + width
        self.y2 = y + height

    @property
    def center(self) -> Tuple[int, int]:
        center_x = int((self.x1 + self.x2) / 2)
        center_y = int((self.y1 + self.y2) / 2)

        return center_x, center_y

    @property
    def inner(self) -> Tuple[slice, slice]:
        """Return the inner area of this room as a 2D array index."""
        return slice(self.x1 + 1, self.x2), slice(self.y1 + 1, self.y2)

    def intersects(self, other: RectangularRoom) -> bool:
        """Return True if this room overlaps with another RectangularRoom."""
        return (
            self.x1 <= other.x2
            and self.x2 >= other.x1
            and self.y1 <= other.y2
            and self.y2 >= other.y1
        )


def tunnel_between(
    start: Tuple[int, int], end: Tuple[int, int], rng: random.Random
) -> Iterator[Tuple[int, int]]:
    """Return an L-shaped tunnel between these two points."""
    x1, y1 = start
    x2, y2 = end
    if rng.uniform(0.0, 1.0) < 0.5:  # 50% chance.
        # Move horizontally, then vertically.
        corner_x, corner_y = x2, y1
    else:
        # Move vertically, then horizontally.
        corner_x, corner_y = x1, y2

    # Generate the coordinates for this tunnel.
    for x, y in _bresenham_line((x1, y1), (corner_x, corner_y)):
        yield x, y
    for x, y in _bresenham_line((corner_x, corner_y), (x2, y2)):
        yield x, y


def _bresenham_line(
    start: Tuple[int, int], end: Tuple[int, int]
) -> Iterator[Tuple[int, int]]:
    if tcod is not None:
        for x, y in tcod.los.bresenham(start, end).tolist():
            yield x, y
        return
    x1, y1 = start
    x2, y2 = end
    dx = abs(x2 - x1)
    dy = -abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx + dy
    while True:
        yield x1, y1
        if x1 == x2 and y1 == y2:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x1 += sx
        if e2 <= dx:
            err += dx
            y1 += sy


def _create_rng(seed: int | None) -> random.Random:
    if tcod is not None:
        return tcod.random.Random(seed)
    return random.Random(seed)


def generate_seed() -> int:
    if tcod is not None:
        return tcod.random.Random().randint(0, 2**31 - 1)
    return random.SystemRandom().randrange(0, 2**31 - 1)


def generate_dungeon(
    max_rooms: int,
    room_min_size: int,
    room_max_size: int,
    map_width: int,
    map_height: int,
    player: Entity,
    seed: int | None = None,
) -> Tuple[GameMap, int]:
    """Generate a new dungeon map."""
    if seed is None:
        seed = generate_seed()
    rng = _create_rng(seed)
    dungeon = GameMap(map_width, map_height)

    rooms: List[RectangularRoom] = []

    for r in range(max_rooms):
        room_width = rng.randint(room_min_size, room_max_size)
        room_height = rng.randint(room_min_size, room_max_size)

        x = rng.randint(0, dungeon.width - room_width - 1)
        y = rng.randint(0, dungeon.height - room_height - 1)

        # "RectangularRoom" class makes rectangles easier to work with
        new_room = RectangularRoom(x, y, room_width, room_height)

        # Run through the other rooms and see if they intersect with this one.
        if any(new_room.intersects(other_room) for other_room in rooms):
            continue  # This room intersects, so go to the next attempt.
        # If there are no intersections then the room is valid.

        # Dig out this rooms inner area.
        dungeon.tiles[new_room.inner] = tile_types.floor

        if len(rooms) == 0:
            # The first room, where the player starts.
            player.x, player.y = new_room.center
        else:  # All rooms after the first.
            # Dig out a tunnel between this room and the previous one.
            for x, y in tunnel_between(rooms[-1].center, new_room.center, rng):
                dungeon.tiles[x, y] = tile_types.floor

        # Finally, append the new room to the list.
        rooms.append(new_room)

    if rooms:
        dungeon.entrance = rooms[0].center
        dungeon.exit = rooms[-1].center
        player.x, player.y = dungeon.entrance
    return dungeon, seed
