from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True, kw_only=True)
class Scene:
    name: str


@dataclass(frozen=True, kw_only=True)
class SceneListChangedEvent:
    scenes: list[Scene]


Event = SceneListChangedEvent

EventHandler = Callable[[Event], None]
