from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

try:
    import pygame
except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
    raise ModuleNotFoundError(
        "pygame is required to run this game. Install with `pip install pygame`."
    ) from exc

from entity import Player
from procgen import generate_dungeon, generate_seed
import tile_types


TILE_SIZE = 64
MAP_WIDTH = 20
MAP_HEIGHT = 15
MAX_ROOMS = 8
ROOM_MIN_SIZE = 4
ROOM_MAX_SIZE = 8
SAVE_FILE = Path(__file__).with_name("savegame.txt")
ASSET_DIR = Path(__file__).with_name("data")
TILESET_PATH = ASSET_DIR / "tileset.png"
PLAYER_PATH = ASSET_DIR / "player.png"


class GameState(Enum):
    MENU = auto()
    PLAYING = auto()


@dataclass
class SaveData:
    seed: int
    player_position: tuple[int, int]
    entrance: tuple[int, int]
    exit: tuple[int, int]


@dataclass
class Assets:
    floor: pygame.Surface
    wall: pygame.Surface
    player_frames: dict[str, pygame.Surface]


def _maybe_convert(surface: pygame.Surface) -> pygame.Surface:
    if pygame.display.get_surface() is None:
        return surface
    return surface.convert_alpha()


def load_assets() -> Assets:
    tileset = _maybe_convert(pygame.image.load(TILESET_PATH))
    floor = tileset.subsurface(pygame.Rect(0, 0, TILE_SIZE, TILE_SIZE))
    wall = tileset.subsurface(pygame.Rect(TILE_SIZE, 0, TILE_SIZE, TILE_SIZE))

    player_sheet = _maybe_convert(pygame.image.load(PLAYER_PATH))
    direction_rows = {"up": 0, "left": 1, "down": 2, "right": 3}
    player_frames = {
        direction: player_sheet.subsurface(
            pygame.Rect(0, row * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        )
        for direction, row in direction_rows.items()
    }
    return Assets(floor=floor, wall=wall, player_frames=player_frames)


def save_game(save_data: SaveData) -> None:
    lines = [
        f"seed:{save_data.seed}",
        f"player:{save_data.player_position[0]},{save_data.player_position[1]}",
        f"entrance:{save_data.entrance[0]},{save_data.entrance[1]}",
        f"exit:{save_data.exit[0]},{save_data.exit[1]}",
    ]
    SAVE_FILE.write_text("\n".join(lines), encoding="utf-8")


def load_game_file() -> SaveData | None:
    if not SAVE_FILE.exists():
        return None
    raw_lines = SAVE_FILE.read_text(encoding="utf-8").splitlines()
    values: dict[str, str] = {}
    for line in raw_lines:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    def parse_pair(key: str) -> tuple[int, int] | None:
        if key not in values:
            return None
        parts = values[key].split(",")
        if len(parts) != 2:
            return None
        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            return None

    try:
        seed = int(values["seed"])
    except (KeyError, ValueError):
        return None

    player_position = parse_pair("player")
    entrance = parse_pair("entrance")
    exit_location = parse_pair("exit")
    if player_position is None or entrance is None or exit_location is None:
        return None
    return SaveData(
        seed=seed,
        player_position=player_position,
        entrance=entrance,
        exit=exit_location,
    )


class Game:
    def __init__(self, assets: Assets) -> None:
        self.assets = assets
        self.state = GameState.MENU
        self.menu_index = 0
        self.menu_message = ""
        self.player: Player | None = None
        self.game_map: GameMap | None = None
        self.seed: int | None = None

    @property
    def window_size(self) -> tuple[int, int]:
        return MAP_WIDTH * TILE_SIZE, MAP_HEIGHT * TILE_SIZE

    @property
    def menu_options(self) -> list[str]:
        return ["Start Game", "Load Game", "Save Game"]

    def start_new_game(self) -> None:
        self.seed = generate_seed()
        self.player = Player(0, 0)
        self.game_map, _ = generate_dungeon(
            MAX_ROOMS,
            ROOM_MIN_SIZE,
            ROOM_MAX_SIZE,
            MAP_WIDTH,
            MAP_HEIGHT,
            self.player,
            seed=self.seed,
        )
        self.state = GameState.PLAYING
        self.menu_message = ""

    def load_game(self) -> bool:
        save_data = load_game_file()
        if save_data is None:
            self.menu_message = "No save file found."
            return False
        self.seed = save_data.seed
        self.player = Player(0, 0)
        self.game_map, _ = generate_dungeon(
            MAX_ROOMS,
            ROOM_MIN_SIZE,
            ROOM_MAX_SIZE,
            MAP_WIDTH,
            MAP_HEIGHT,
            self.player,
            seed=self.seed,
        )
        if self.game_map is None or self.player is None:
            return False
        self.game_map.entrance = save_data.entrance
        self.game_map.exit = save_data.exit
        self.player.x, self.player.y = save_data.player_position
        if not self.game_map.is_walkable(self.player.x, self.player.y):
            self.player.x, self.player.y = self.game_map.entrance
        self.state = GameState.PLAYING
        self.menu_message = "Game loaded."
        return True

    def save_game(self) -> bool:
        if self.game_map is None or self.player is None or self.seed is None:
            self.menu_message = "No active game to save."
            return False
        save_game(
            SaveData(
                seed=self.seed,
                player_position=(self.player.x, self.player.y),
                entrance=self.game_map.entrance,
                exit=self.game_map.exit,
            )
        )
        self.menu_message = "Game saved."
        return True

    def handle_menu_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_UP, pygame.K_w):
            self.menu_index = (self.menu_index - 1) % len(self.menu_options)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.menu_index = (self.menu_index + 1) % len(self.menu_options)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            option = self.menu_options[self.menu_index]
            if option == "Start Game":
                self.start_new_game()
            elif option == "Load Game":
                self.load_game()
            elif option == "Save Game":
                self.save_game()

    def handle_game_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN or self.player is None or self.game_map is None:
            return
        if event.key == pygame.K_ESCAPE:
            self.state = GameState.MENU
            return
        direction_map = {
            pygame.K_UP: (0, -1, "up"),
            pygame.K_w: (0, -1, "up"),
            pygame.K_DOWN: (0, 1, "down"),
            pygame.K_s: (0, 1, "down"),
            pygame.K_LEFT: (-1, 0, "left"),
            pygame.K_a: (-1, 0, "left"),
            pygame.K_RIGHT: (1, 0, "right"),
            pygame.K_d: (1, 0, "right"),
        }
        if event.key in direction_map:
            dx, dy, direction = direction_map[event.key]
            new_x = self.player.x + dx
            new_y = self.player.y + dy
            if self.game_map.is_walkable(new_x, new_y):
                self.player.x = new_x
                self.player.y = new_y
            self.player.direction = direction

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.state == GameState.MENU:
            self.handle_menu_event(event)
        else:
            self.handle_game_event(event)

    def render_menu(self, screen: pygame.Surface) -> None:
        screen.fill((10, 10, 10))
        font = pygame.font.Font(None, 56)
        title = font.render("Dungeon Prototype", True, (230, 230, 230))
        screen.blit(
            title,
            (self.window_size[0] // 2 - title.get_width() // 2, 40),
        )
        option_font = pygame.font.Font(None, 40)
        start_y = 140
        for index, option in enumerate(self.menu_options):
            color = (255, 215, 0) if index == self.menu_index else (200, 200, 200)
            text = option_font.render(option, True, color)
            screen.blit(
                text,
                (self.window_size[0] // 2 - text.get_width() // 2, start_y + 50 * index),
            )
        if self.menu_message:
            message_font = pygame.font.Font(None, 32)
            message = message_font.render(self.menu_message, True, (180, 180, 255))
            screen.blit(
                message,
                (self.window_size[0] // 2 - message.get_width() // 2, start_y + 180),
            )

    def render_game(self, screen: pygame.Surface) -> None:
        if self.game_map is None or self.player is None:
            screen.fill((0, 0, 0))
            return
        for x in range(self.game_map.width):
            for y in range(self.game_map.height):
                tile = self.game_map.tiles[x, y]
                image = (
                    self.assets.floor
                    if tile == tile_types.floor
                    else self.assets.wall
                )
                screen.blit(image, (x * TILE_SIZE, y * TILE_SIZE))

        entrance_rect = pygame.Rect(
            self.game_map.entrance[0] * TILE_SIZE,
            self.game_map.entrance[1] * TILE_SIZE,
            TILE_SIZE,
            TILE_SIZE,
        )
        exit_rect = pygame.Rect(
            self.game_map.exit[0] * TILE_SIZE,
            self.game_map.exit[1] * TILE_SIZE,
            TILE_SIZE,
            TILE_SIZE,
        )
        pygame.draw.rect(screen, (50, 200, 255), entrance_rect, 3)
        pygame.draw.rect(screen, (50, 255, 120), exit_rect, 3)

        sprite = self.assets.player_frames.get(self.player.direction, self.assets.player_frames["down"])
        screen.blit(sprite, (self.player.x * TILE_SIZE, self.player.y * TILE_SIZE))

    def render(self, screen: pygame.Surface) -> None:
        if self.state == GameState.MENU:
            self.render_menu(screen)
        else:
            self.render_game(screen)


def main() -> None:
    pygame.init()
    pygame.display.set_caption("Dungeon Prototype")
    screen = pygame.display.set_mode((MAP_WIDTH * TILE_SIZE, MAP_HEIGHT * TILE_SIZE))
    assets = load_assets()
    game = Game(assets)
    clock = pygame.time.Clock()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                game.handle_event(event)
        game.render(screen)
        pygame.display.flip()
        clock.tick(30)
    pygame.quit()


if __name__ == "__main__":
    main()
