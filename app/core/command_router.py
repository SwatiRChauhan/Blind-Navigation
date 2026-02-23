from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CommandConfig:
    start_phrase: str = "assistant start navigation"
    stop_phrase: str = "assistant stop"


class CommandRouter:
    def __init__(self, config: CommandConfig | None = None) -> None:
        self.config = config or CommandConfig()

    def route(self, raw_text: str) -> str:
        text = " ".join(raw_text.lower().strip().split())
        if text == self.config.start_phrase:
            return "START"
        if text in {self.config.stop_phrase, "stop assistant", "stop"}:
            return "STOP"
        if "what" in text and "ahead" in text:
            return "WHAT_AHEAD"
        if "describe" in text and "scene" in text:
            return "DESCRIBE_SCENE"
        if "safe" in text and "move" in text:
            return "SAFE_TO_MOVE"
        if "obstacle" in text:
            return "OBSTACLE_QUERY"
        if "pause" in text and "alert" in text:
            return "PAUSE_ALERTS"
        if "resume" in text and "alert" in text:
            return "RESUME_ALERTS"
        if "repeat" in text:
            return "REPEAT"
        return "UNKNOWN"
