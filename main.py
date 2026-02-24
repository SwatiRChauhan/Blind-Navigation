from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import BooleanProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout

from yolo_detector import YoloDetector


# -----------------------------
# Core runtime logic structures
# -----------------------------
@dataclass
class RuntimeState:
    active: bool = False
    last_instruction: str = ""
    last_auto_summary: str = ""
    last_hazard_level: int = 0
    last_critical_condition: str = ""


class LocalSpeaker:
    """Offline TTS wrapper for Android/Desktop.

    Tries `plyer.tts` (best for mobile), then `pyttsx3` as a desktop fallback.
    """

    def speak(self, text: str) -> None:
        try:
            from plyer import tts

            tts.speak(text)
            return
        except Exception:
            pass

        try:
            import pyttsx3

            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        except Exception:
            # Fail safely: app remains usable even if TTS backend is unavailable.
            pass


class VisionRoot(BoxLayout):
    status_text = StringProperty("Stopped")
    permission_text = StringProperty("Permissions: microphone/camera/location unavailable check pending")
    vision_state = StringProperty("Off")
    gps_state = StringProperty("Off")
    command_input = StringProperty("")
    scene_text = StringProperty("Say start safe navigation")
    listening = BooleanProperty(False)


class VisionCompanionMobile(App):
    """Offline, voice-first Kivy mobile app.

    Notes:
    - Keeps the same command workflows as the web runtime.
    - Uses local detector directly (no cloud dependency).
    - Includes a typed command fallback field for environments where offline ASR
      cannot be provisioned yet.
    """

    title = "Vision Companion Offline"

    START_PHRASE = "start safe navigation"
    STOP_PHRASE = "stop safe navigation"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.state = RuntimeState()
        self.root_view: VisionRoot | None = None
        self.detector = YoloDetector()
        self.speaker = LocalSpeaker()
        self.scan_event = None

    def build(self) -> VisionRoot:
        Builder.load_file("vision_companion.kv")
        self.root_view = VisionRoot()
        Clock.schedule_once(lambda *_: self.bootstrap(), 0.2)
        return self.root_view

    # -----------------------------
    # Lifecycle / permission checks
    # -----------------------------
    def bootstrap(self) -> None:
        # In Kivy Android builds, permissions are requested by manifest + runtime APIs.
        # For now we keep an explicit status text and fail-loud guidance.
        if self.root_view:
            self.root_view.permission_text = "Permissions: request microphone, camera, and location on first run"
        self.announce("Voice control ready. Say start safe navigation.")

    # -----------------------------
    # Command processing
    # -----------------------------
    def on_submit_command(self) -> None:
        if not self.root_view:
            return
        raw = self.root_view.command_input.strip()
        self.root_view.command_input = ""
        if raw:
            self.handle_command(raw)

    def handle_command(self, raw_command: str) -> None:
        command = self.normalize_command(raw_command)

        if self.matches_phrase(command, self.START_PHRASE):
            self.start_navigation()
            return

        if self.matches_phrase(command, self.STOP_PHRASE):
            self.stop_navigation()
            return

        if "help" in command or "what can you do" in command:
            self.speak_help()
            return

        if not self.state.active:
            return

        if "what is ahead" in command or "describe surroundings" in command or "describe scene" in command:
            self.analyze_once(user_requested=True)
            return

        if "repeat" in command:
            self.announce(self.state.last_instruction or "No instruction available")

    def speak_help(self) -> None:
        self.announce(
            "Available voice commands: Start safe navigation, Stop safe navigation, "
            "What is ahead, Describe surroundings, Help, and Repeat."
        )

    @staticmethod
    def normalize_command(command: str) -> str:
        cleaned = "".join(ch if (ch.isalpha() or ch.isspace()) else " " for ch in command.lower())
        return " ".join(cleaned.split())

    @staticmethod
    def matches_phrase(command: str, phrase: str) -> bool:
        return command == phrase or command.startswith(f"{phrase} ") or command.endswith(f" {phrase}") or f" {phrase} " in command

    # -----------------------------
    # Navigation runtime
    # -----------------------------
    def start_navigation(self) -> None:
        if self.state.active:
            return
        self.state.active = True
        self.state.last_hazard_level = 0
        self.state.last_auto_summary = ""
        self.state.last_critical_condition = ""

        if self.root_view:
            self.root_view.status_text = "Active"
            self.root_view.vision_state = self.detector.engine
            self.root_view.gps_state = "Locked"

        self.announce("Safe navigation started")
        self.start_scan_loop()

    def stop_navigation(self) -> None:
        if not self.state.active:
            return
        self.state.active = False
        self.stop_scan_loop()

        if self.root_view:
            self.root_view.status_text = "Stopped"
            self.root_view.vision_state = "Off"
            self.root_view.gps_state = "Off"

        self.announce("Safe navigation stopped")

    def start_scan_loop(self) -> None:
        if self.scan_event is None:
            self.scan_event = Clock.schedule_interval(lambda *_: self.analyze_once(user_requested=False), 1.0)

    def stop_scan_loop(self) -> None:
        if self.scan_event is not None:
            self.scan_event.cancel()
            self.scan_event = None

    def analyze_once(self, user_requested: bool) -> None:
        if not self.state.active:
            return

        try:
            result = self.detector.detect(image_path=None)
            detections = result.get("detections", [])

            if self.root_view:
                self.root_view.vision_state = result.get("engine", "On")

            condition = self.assess_system_conditions(detections)
            if condition != "ok":
                if condition != self.state.last_critical_condition:
                    self.state.last_critical_condition = condition
                    if condition == "camera blocked":
                        self.announce("Camera blocked. Stop and reposition phone.")
                    else:
                        self.announce("Low visibility. Move slowly.")
                return

            self.state.last_critical_condition = ""

            summary = self.compose_environmental_description(detections)
            hazard = self.hazard_level(summary)

            if user_requested:
                self.state.last_hazard_level = hazard
                self.state.last_auto_summary = summary
                self.process_safety_summary(summary)
                return

            # Controlled feedback rules: only speak automatically if danger increases.
            if hazard > self.state.last_hazard_level:
                self.state.last_hazard_level = hazard
                self.state.last_auto_summary = summary
                self.process_safety_summary(summary)
            elif hazard < self.state.last_hazard_level:
                self.state.last_hazard_level = hazard

        except Exception:
            if self.root_view:
                self.root_view.vision_state = "Error"
            if self.state.last_critical_condition != "vision-failure":
                self.state.last_critical_condition = "vision-failure"
                self.announce("Unclear environment. Move slowly.")

    @staticmethod
    def assess_system_conditions(detections: list[dict[str, Any]]) -> str:
        if not detections:
            return "low visibility"
        return "ok"

    @staticmethod
    def hazard_level(text: str) -> int:
        lower = text.lower()
        if "vehicle" in lower or "dropoff" in lower or "very close" in lower or "stairs down" in lower:
            return 3
        if "near" in lower or "obstacle" in lower:
            return 2
        if "person" in lower or "medium" in lower:
            return 1
        return 0

    def compose_environmental_description(self, detections: list[dict[str, Any]]) -> str:
        if not detections:
            return "Path unclear. Move slowly."

        lines: list[str] = []
        for item in detections[:3]:
            label = str(item.get("label", "object")).lower()
            direction = str(item.get("direction", "ahead")).lower()
            proximity = str(item.get("proximity", self.proximity_from_distance(item.get("distance_hint_m")))).lower()
            movement = str(item.get("movement", "unknown")).lower()
            moving = f" moving {movement}" if movement and movement != "unknown" else ""

            if label == "person":
                lines.append(f"person {direction} {proximity}{moving}")
            else:
                lines.append(f"{label} {direction} {proximity}{moving}")

        return ". ".join(lines)

    @staticmethod
    def proximity_from_distance(distance_hint: Any) -> str:
        try:
            d = float(distance_hint)
        except Exception:
            return "near"

        if d <= 0.8:
            return "very close"
        if d <= 1.6:
            return "near"
        if d <= 3:
            return "medium"
        return "far"

    def process_safety_summary(self, text: str) -> None:
        lower = text.lower()
        if "vehicle" in lower or "very close" in lower or "dropoff" in lower or "stairs down" in lower:
            self.announce(f"Stop. {text}")
            return
        self.announce(text)

    # -----------------------------
    # Output helpers
    # -----------------------------
    def announce(self, text: str) -> None:
        self.state.last_instruction = text
        if self.root_view:
            self.root_view.scene_text = text
        self.speaker.speak(text)


if __name__ == "__main__":
    VisionCompanionMobile().run()
