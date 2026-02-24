from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import BooleanProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout

from voice_engine import VoiceCommandEngine
from yolo_detector import YoloDetector


@dataclass
class RuntimeState:
    active: bool = False
    last_instruction: str = ""
    last_hazard_level: int = 0
    last_critical_condition: str = ""


class LocalSpeaker:
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
            pass


class VisionRoot(BoxLayout):
    status_text = StringProperty("Stopped")
    permission_text = StringProperty("Permissions: waiting")
    vision_state = StringProperty("Off")
    scene_text = StringProperty("Say start safe navigation")
    listen_state = StringProperty("Idle")
    listening = BooleanProperty(False)


class VisionCompanionMobile(App):
    title = "Vision Companion Offline"

    START_PHRASE = "start safe navigation"
    STOP_PHRASE = "stop safe navigation"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.state = RuntimeState()
        self.root_view: VisionRoot | None = None
        self.detector = YoloDetector()
        self.speaker = LocalSpeaker()
        self.voice = VoiceCommandEngine()
        self.scan_event = None
        self.permissions_granted = False

    def build(self) -> VisionRoot:
        Builder.load_file("vision_companion.kv")
        self.root_view = VisionRoot()
        Clock.schedule_once(lambda *_: self.bootstrap(), 0.2)
        return self.root_view

    def bootstrap(self) -> None:
        self.request_runtime_permissions()

    # -------- Permission flow --------
    def request_runtime_permissions(self) -> None:
        try:
            from kivy.utils import platform
        except Exception:
            platform = "unknown"

        if platform != "android":
            self.permissions_granted = True
            if self.root_view:
                self.root_view.permission_text = "Permissions: desktop mode"
            self.start_voice_engine()
            self.announce("Voice control ready. Say start safe navigation.")
            return

        try:
            from android.permissions import Permission, check_permission, request_permissions

            wanted = [Permission.RECORD_AUDIO, Permission.CAMERA, Permission.ACCESS_FINE_LOCATION]
            if all(check_permission(p) for p in wanted):
                self.on_permissions_result(wanted, [True] * len(wanted))
                return

            if self.root_view:
                self.root_view.permission_text = "Permissions: requesting microphone, camera, location"
            request_permissions(wanted, self.on_permissions_result)
        except Exception:
            self.permissions_granted = False
            if self.root_view:
                self.root_view.permission_text = "Permissions: request failed"
            self.announce("Permission request failed. Enable microphone, camera, and location in app settings.")

    def on_permissions_result(self, permissions: list[str], grants: list[bool]) -> None:
        self.permissions_granted = bool(grants) and all(grants)
        if self.permissions_granted:
            if self.root_view:
                self.root_view.permission_text = "Permissions granted"
            self.start_voice_engine()
            self.announce("Permissions granted. Say start safe navigation.")
            return

        denied = [p for p, g in zip(permissions, grants) if not g]
        missing = ", ".join(denied) if denied else "required permissions"
        if self.root_view:
            self.root_view.permission_text = f"Permissions denied: {missing}"
        self.announce("Permissions denied. Enable microphone, camera, and location to run safe navigation.")

    # -------- Voice flow --------
    def start_voice_engine(self) -> None:
        self.voice.start(self._on_voice_text, self._on_voice_status, self._on_voice_error)
        if self.root_view:
            self.root_view.listening = True

    def stop_voice_engine(self) -> None:
        self.voice.stop()
        if self.root_view:
            self.root_view.listening = False
            self.root_view.listen_state = "Idle"

    def _on_voice_status(self, text: str) -> None:
        Clock.schedule_once(lambda *_: self._set_listen_state(text), 0)

    def _on_voice_error(self, text: str) -> None:
        Clock.schedule_once(lambda *_: self._set_listen_state(text), 0)

    def _on_voice_text(self, text: str) -> None:
        Clock.schedule_once(lambda *_: self.handle_command(text), 0)

    def _set_listen_state(self, text: str) -> None:
        if self.root_view:
            self.root_view.listen_state = text

    # -------- Command mapping --------
    def handle_command(self, raw_command: str) -> None:
        command = self.normalize_command(raw_command)

        if self.matches_any_phrase(command, [self.START_PHRASE, "start navigation"]):
            self.start_navigation()
            return

        if self.matches_any_phrase(command, [self.STOP_PHRASE]):
            self.stop_navigation()
            return

        if self.matches_any_phrase(command, ["help", "what can you do"]):
            self.speak_help()
            return

        if not self.state.active:
            return

        if self.matches_any_phrase(command, ["what is ahead", "whats ahead", "tell me what is in front of me"]):
            self.analyze_once(user_requested=True)
            return

        if self.matches_any_phrase(command, ["describe surroundings", "describe my surroundings", "describe scene"]):
            self.analyze_once(user_requested=True)
            return

        if self.matches_any_phrase(command, ["repeat", "repeat last instruction"]):
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

    def matches_any_phrase(self, command: str, phrases: list[str]) -> bool:
        return any(self.matches_phrase(command, p) for p in phrases)

    # -------- Navigation runtime --------
    def start_navigation(self) -> None:
        if self.state.active:
            return
        if not self.permissions_granted:
            self.request_runtime_permissions()
            self.announce("Cannot start. Please grant microphone, camera, and location permissions.")
            return

        self.state.active = True
        self.state.last_hazard_level = 0
        self.state.last_critical_condition = ""

        if self.root_view:
            self.root_view.status_text = "Active"
            self.root_view.vision_state = self.detector.engine

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
                    self.announce("Low visibility. Move slowly.")
                return

            self.state.last_critical_condition = ""
            summary = self.compose_environmental_description(detections)
            hazard = self.hazard_level(summary)

            if user_requested:
                self.state.last_hazard_level = hazard
                self.process_safety_summary(summary)
                return

            if hazard > self.state.last_hazard_level:
                self.state.last_hazard_level = hazard
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
            proximity = str(item.get("proximity", "near")).lower()
            movement = str(item.get("movement", "unknown")).lower()
            moving = f" moving {movement}" if movement and movement != "unknown" else ""
            lines.append(f"{label} {direction} {proximity}{moving}")
        return ". ".join(lines)

    def process_safety_summary(self, text: str) -> None:
        lower = text.lower()
        if "vehicle" in lower or "very close" in lower or "dropoff" in lower or "stairs down" in lower:
            self.announce(f"Stop. {text}")
            return
        self.announce(text)

    def announce(self, text: str) -> None:
        self.state.last_instruction = text
        if self.root_view:
            self.root_view.scene_text = text
        self.speaker.speak(text)

    def on_stop(self) -> None:
        self.stop_scan_loop()
        self.stop_voice_engine()


if __name__ == "__main__":
    VisionCompanionMobile().run()
