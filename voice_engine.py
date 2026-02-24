from __future__ import annotations

import threading
from typing import Callable


class VoiceCommandEngine:
    """Cross-platform voice engine.

    - Android: uses native SpeechRecognizer via PyJNIus.
    - Non-Android: uses SpeechRecognition package as fallback.
    """

    def __init__(self) -> None:
        self._running = False
        self._on_command: Callable[[str], None] | None = None
        self._on_status: Callable[[str], None] | None = None
        self._on_error: Callable[[str], None] | None = None
        self._platform = self._detect_platform()

        self._thread: threading.Thread | None = None
        self._stop_evt = threading.Event()

        self._android_ready = False
        self._android_recognizer = None
        self._android_listener = None

    @staticmethod
    def _detect_platform() -> str:
        try:
            from kivy.utils import platform

            return platform
        except Exception:
            return "unknown"

    def start(
        self,
        on_command: Callable[[str], None],
        on_status: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        if self._running:
            return

        self._on_command = on_command
        self._on_status = on_status
        self._on_error = on_error
        self._running = True

        if self._platform == "android":
            self._start_android()
            return

        self._start_desktop()

    def stop(self) -> None:
        if not self._running:
            return

        self._running = False
        self._stop_evt.set()

        if self._android_recognizer is not None:
            try:
                self._android_recognizer.stopListening()
                self._android_recognizer.cancel()
                self._android_recognizer.destroy()
            except Exception:
                pass
            self._android_recognizer = None

    # ---------- Android implementation ----------
    def _start_android(self) -> None:
        try:
            from jnius import PythonJavaClass, autoclass, java_method

            SpeechRecognizer = autoclass("android.speech.SpeechRecognizer")
            Intent = autoclass("android.content.Intent")
            RecognizerIntent = autoclass("android.speech.RecognizerIntent")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")

            class Listener(PythonJavaClass):
                __javainterfaces__ = ["android/speech/RecognitionListener"]
                __javacontext__ = "app"

                def __init__(self, outer: VoiceCommandEngine):
                    super().__init__()
                    self.outer = outer

                @java_method("(Landroid/os/Bundle;)V")
                def onResults(self, results):
                    try:
                        matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                        if matches and len(matches) > 0:
                            text = str(matches.get(0))
                            if self.outer._on_command:
                                self.outer._on_command(text)
                    except Exception:
                        if self.outer._on_error:
                            self.outer._on_error("Voice parse error")
                    finally:
                        self.outer._restart_android_listen()

                @java_method("(I)V")
                def onError(self, _error_code):
                    if self.outer._on_error:
                        self.outer._on_error("Listening error. Restarting.")
                    self.outer._restart_android_listen()

                @java_method("()V")
                def onReadyForSpeech(self):
                    if self.outer._on_status:
                        self.outer._on_status("Listening...")

                @java_method("()V")
                def onBeginningOfSpeech(self):
                    if self.outer._on_status:
                        self.outer._on_status("Processing...")

                @java_method("()V")
                def onEndOfSpeech(self):
                    pass

                @java_method("([B)V")
                def onBufferReceived(self, _buffer):
                    pass

                @java_method("(F)V")
                def onRmsChanged(self, _rmsdB):
                    pass

                @java_method("()V")
                def onPartialResults(self):
                    pass

                @java_method("()V")
                def onEvent(self):
                    pass

            activity = PythonActivity.mActivity
            self._android_recognizer = SpeechRecognizer.createSpeechRecognizer(activity)
            self._android_listener = Listener(self)
            self._android_recognizer.setRecognitionListener(self._android_listener)

            self._intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            self._intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            self._intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, False)
            self._intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
            self._intent.putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, True)

            self._android_ready = True
            self._restart_android_listen()
        except Exception:
            self._android_ready = False
            if self._on_error:
                self._on_error("Android speech recognizer unavailable")

    def _restart_android_listen(self) -> None:
        if not self._running or not self._android_ready or self._android_recognizer is None:
            return
        try:
            self._android_recognizer.cancel()
            self._android_recognizer.startListening(self._intent)
        except Exception:
            if self._on_error:
                self._on_error("Unable to restart listening")

    # ---------- Desktop implementation ----------
    def _start_desktop(self) -> None:
        self._stop_evt.clear()
        self._thread = threading.Thread(target=self._desktop_loop, daemon=True)
        self._thread.start()

    def _desktop_loop(self) -> None:
        try:
            import speech_recognition as sr
        except Exception:
            if self._on_error:
                self._on_error("speech_recognition package missing")
            self._running = False
            return

        recognizer = sr.Recognizer()

        try:
            mic = sr.Microphone()
        except Exception:
            if self._on_error:
                self._on_error("Microphone unavailable")
            self._running = False
            return

        while self._running and not self._stop_evt.is_set():
            try:
                if self._on_status:
                    self._on_status("Listening...")
                with mic as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.2)
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=4)

                if self._on_status:
                    self._on_status("Processing...")
                text = recognizer.recognize_google(audio)
                if self._on_command:
                    self._on_command(text)
            except Exception:
                if self._on_error:
                    self._on_error("Voice not understood")
