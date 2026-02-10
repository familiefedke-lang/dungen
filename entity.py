from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Entity:
    x: int
    y: int


@dataclass
class Player(Entity):
    direction: str = "down"
