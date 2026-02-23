from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class Priority(IntEnum):
    IMMEDIATE_DANGER = 1
    DIRECTIONAL_GUIDANCE = 2
    ENV_AWARENESS = 3
    ON_DEMAND_DESCRIPTION = 4


@dataclass
class AudioEvent:
    text: str
    priority: Priority


class AudioPriorityManager:
    def __init__(self) -> None:
        self._current: AudioEvent | None = None

    def can_interrupt(self, candidate: AudioEvent) -> bool:
        if self._current is None:
            return True
        return candidate.priority <= self._current.priority

    def submit(self, candidate: AudioEvent) -> AudioEvent | None:
        if self.can_interrupt(candidate):
            self._current = candidate
            return candidate
        return None

    def clear(self) -> None:
        self._current = None
