from __future__ import annotations


class SafetyWatchdog:
    def __init__(self, confidence_floor: float = 0.40) -> None:
        self.confidence_floor = confidence_floor

    def camera_state_alert(self, camera_ok: bool, low_light: bool, angle_ok: bool) -> str | None:
        if not camera_ok:
            return "Camera failure. Stop and check phone position."
        if low_light:
            return "Low light. Move slowly."
        if not angle_ok:
            return "Phone angle unsafe. Reposition device."
        return None

    def confidence_alert(self, confidence: float) -> str | None:
        if confidence < self.confidence_floor:
            return "Unclear environment. Move slowly."
        return None
