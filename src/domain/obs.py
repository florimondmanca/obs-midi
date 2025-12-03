from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True, kw_only=True)
class Scene:
    name: str


@dataclass(frozen=True, kw_only=True)
class SceneListReceivedEvent:
    scenes: list[Scene]


@dataclass(frozen=True, kw_only=True)
class Filter:
    name: str


@dataclass(frozen=True, kw_only=True)
class FilterListReceivedEvent:
    filters: list[Filter]


Event = SceneListReceivedEvent | FilterListReceivedEvent

EventHandler = Callable[[Event], None]
