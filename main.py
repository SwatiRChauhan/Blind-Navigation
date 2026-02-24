from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout

from yolo_detector import YoloDetector

KV = '''
#:kivy 2.2.0
<RootView>:
    orientation: "vertical"
    padding: "18dp"
    spacing: "14dp"
    canvas.before:
        Color:
            rgba: 0.04, 0.05, 0.08, 1
        Rectangle:
            pos: self.pos
            size: self.size

    Label:
        text: "Vision Companion"
        font_size: "30sp"
        bold: True
        color: 0.75, 0.93, 1, 1
        size_hint_y: None
        height: "56dp"

    Label:
        text: root.command_hint
        font_size: "18sp"
        color: 0.9, 0.95, 1, 1
        text_size: self.width, None
        halign: "center"
        valign: "middle"
        size_hint_y: None
        height: "72dp"

    Label:
        text: root.status_text
        font_size: "24sp"
        bold: True
        color: 0.4, 0.95, 0.55, 1
        text_size: self.width, None
        halign: "center"
        valign: "middle"
        size_hint_y: None
        height: "72dp"

    Label:
        text: root.scene_text
        font_size: "20sp"
        color: 1, 1, 1, 1
        text_size: self.width, None
        halign: "center"
        valign: "middle"

    Label:
        text: "Voice help: say Help for command list"
        font_size: "16sp"
        color: 0.8, 0.85, 0.95, 1
        size_hint_y: None
        height: "36dp"
'''


@dataclass
class VoiceCommandState:
    active: bool = False


class RootView(BoxLayout):
    status_text = StringProperty("Stopped")
    scene_text = StringProperty("Say start safe navigation")
    command_hint = StringProperty("Commands: Start safe navigation, Stop safe navigation, What is ahead, Describe surroundings, Help, Repeat")


class OfflineSpeaker:
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
            # Keep app resilient even without a local TTS backend.
            pass


class VisionCompanionMobile(App):
    title = "Vision Companion Offline"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.state = VoiceCommandState()
        self.detector = YoloDetector()
        self.speaker = OfflineSpeaker()
        self._last_instruction = ""
        self._scan_event = None
        self.root_view: RootView | None = None

    def build(self) -> RootView:
        Builder.load_string(KV)
        self.root_view = RootView()
        Clock.schedule_once(lambda *_: self._announce("Voice control ready. Say start safe navigation."), 0.2)
        return self.root_view

    def handle_voice_command(self, text: str) -> None:
        command = self._normalize(text)

        if self._phrase_in_command(command, "start safe navigation"):
            self._start_navigation()
            return

        if self._phrase_in_command(command, "stop safe navigation"):
            self._stop_navigation()
            return

        if "help" in command or "what can you do" in command:
            self._announce(self._help_text())
            return

        if not self.state.active:
            return

        if "what is ahead" in command or "describe surroundings" in command or "describe scene" in command:
            self._scan_once(user_requested=True)
            return

        if "repeat" in command:
            self._announce(self._last_instruction or "No instruction available")

    def _help_text(self) -> str:
        return (
            "Available voice commands: Start safe navigation, Stop safe navigation, "
            "What is ahead, Describe surroundings, Help, and Repeat."
        )

    def _start_navigation(self) -> None:
        if self.state.active:
            return
        self.state.active = True
        if self.root_view:
            self.root_view.status_text = "Active"
            self.root_view.scene_text = "Safe navigation running"
        self._announce("Safe navigation started")
        self._scan_event = Clock.schedule_interval(lambda *_: self._scan_once(user_requested=False), 1.0)

    def _stop_navigation(self) -> None:
        if not self.state.active:
            return
        self.state.active = False
        if self._scan_event is not None:
            self._scan_event.cancel()
            self._scan_event = None
        if self.root_view:
            self.root_view.status_text = "Stopped"
            self.root_view.scene_text = "Safe navigation stopped"
        self._announce("Safe navigation stopped")

    def _scan_once(self, user_requested: bool) -> None:
        result = self.detector.detect(image_path=None)
        detections = result.get("detections", [])
        spoken = self._compose_scene_text(detections)

        if self.root_view:
            self.root_view.scene_text = spoken

        if user_requested:
            self._announce(spoken)
            return

        if "very close" in spoken or "vehicle" in spoken or "dropoff" in spoken or "stairs down" in spoken:
            self._announce(f"Stop. {spoken}")

    def _compose_scene_text(self, detections: list[dict[str, Any]]) -> str:
        if not detections:
            return "Unclear environment. Move slowly"

        parts = []
        for item in detections[:3]:
            label = str(item.get("label", "object")).lower()
            direction = str(item.get("direction", "ahead")).lower()
            proximity = str(item.get("proximity", "near")).lower()
            if label == "person":
                parts.append(f"person {direction} {proximity}")
            else:
                parts.append(f"{label} {direction} {proximity}")
        return ". ".join(parts)

    def _announce(self, text: str) -> None:
        self._last_instruction = text
        if self.root_view:
            self.root_view.scene_text = text
        self.speaker.speak(text)

    @staticmethod
    def _normalize(text: str) -> str:
        normalized = "".join(ch if (ch.isalpha() or ch.isspace()) else " " for ch in text.lower())
        return " ".join(normalized.split())

    @staticmethod
    def _phrase_in_command(command: str, phrase: str) -> bool:
        return command == phrase or command.startswith(f"{phrase} ") or command.endswith(f" {phrase}") or f" {phrase} " in command


if __name__ == "__main__":
    VisionCompanionMobile().run()
