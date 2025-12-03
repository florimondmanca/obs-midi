import enum
from dataclasses import dataclass


class CommandActionEnum(enum.Enum):
    SWITCH_SCENE = "SwitchScene"
    SHOW_FILTER = "ShowFilter"


@dataclass(frozen=True, kw_only=True)
class SwitchSceneCommand:
    scene: str


@dataclass(frozen=True, kw_only=True)
class ShowFilterCommand:
    source: str
    filter: str


Command = SwitchSceneCommand | ShowFilterCommand
