from __future__ import annotations

from app.audio.priority_manager import AudioEvent, AudioPriorityManager, Priority
from app.vision.label_filter import Detection, filter_allowed_detections, is_person_presence_only
from app.vision.spatial_reasoner import build_spatial_cue


class SafetyEngine:
    def __init__(self) -> None:
        self.audio = AudioPriorityManager()

    def detections_to_alert(self, detections: list[Detection]) -> AudioEvent:
        filtered = filter_allowed_detections(detections)
        if not filtered:
            return AudioEvent("Unclear environment. Move slowly.", Priority.IMMEDIATE_DANGER)

        strongest = sorted(filtered, key=lambda d: d.confidence, reverse=True)[0]
        cue = build_spatial_cue(strongest.x_center, strongest.width)

        if strongest.label in {"car", "truck", "bus", "motorcycle"} and cue.proximity in {"very close", "near"}:
            return AudioEvent("Vehicle approaching", Priority.IMMEDIATE_DANGER)

        if strongest.label in {"dropoff", "stairs", "curb"} and cue.proximity in {"very close", "near"}:
            return AudioEvent("Stop", Priority.IMMEDIATE_DANGER)

        if is_person_presence_only(strongest.label):
            if cue.direction == "center":
                return AudioEvent("Person ahead", Priority.ENV_AWARENESS)
            return AudioEvent(f"Person on your {cue.direction}", Priority.ENV_AWARENESS)

        if cue.proximity == "very close":
            return AudioEvent("Obstacle very close", Priority.IMMEDIATE_DANGER)

        if cue.direction == "left":
            return AudioEvent("Step right", Priority.DIRECTIONAL_GUIDANCE)
        if cue.direction == "right":
            return AudioEvent("Step left", Priority.DIRECTIONAL_GUIDANCE)

        return AudioEvent("Clear ahead", Priority.DIRECTIONAL_GUIDANCE)
