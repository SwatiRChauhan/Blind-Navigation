# AEGIS Offline Mobile Safety Navigation App — Phase 0 (Architecture Seed)

## 1) Architecture Overview (Safety-First, Fully Offline)

### 1.1 Mission profile
AEGIS is an **audio-only, offline, safety companion** for blind and severely visually impaired users.

- Inactive by default.
- Activates only by start phrase: **"Assistant start navigation"**.
- Stops immediately by stop phrase: **"Assistant stop"**.
- Runs all perception and speech pipelines **on-device**.
- No cloud, no uploads, no identity analysis, no persistent recording.

### 1.2 Runtime architecture (Android + Python/Kivy)

```text
+--------------------------------------------------------------+
| Kivy UI Layer (minimal visual, fully voice-operable)         |
| - High contrast dark theme (like provided reference)         |
| - Status-only screen: ACTIVE / INACTIVE / FAILSAFE           |
| - No interaction required for primary operation              |
+-----------------------------+--------------------------------+
                              |
                              v
+--------------------------------------------------------------+
| Foreground Safety Service (Python + PyJNIus bridge)          |
| - Keeps app alive when screen is locked                      |
| - Owns wake lock lifecycle                                   |
| - Orchestrates camera + inference + speech + watchdogs       |
+-----------------------------+--------------------------------+
                              |
            +-----------------+------------------+-------------+
            v                                    v
+-----------------------------+      +--------------------------+
| Offline Voice Command Engine|      | Camera + Inference Loop |
| - Android SpeechRecognizer  |      | - Camera frames          |
|   (offline mode only)       |      | - YOLO ONNX/TFLite       |
| - No audio file retention   |      | - Low-latency scheduling |
+-----------------------------+      +------------+-------------+
                                                  |
                                                  v
                                   +-----------------------------+
                                   | Spatial + Safety Reasoning |
                                   | - left/center/right        |
                                   | - very close/near/medium   |
                                   | - hazard severity scoring  |
                                   +-------------+---------------+
                                                 |
                                                 v
                                   +-----------------------------+
                                   | Audio Priority Manager      |
                                   | Priority 1..4 interruptive  |
                                   | TTS output only             |
                                   +-------------+---------------+
                                                 |
                                                 v
                                   +-----------------------------+
                                   | Safety Watchdogs            |
                                   | - camera fail -> immediate  |
                                   | - model fail -> immediate   |
                                   | - low confidence warning    |
                                   +-----------------------------+
```

### 1.3 Safety-critical behavior model

- **Fail-loud:** if camera/inference pipeline breaks, user immediately hears failure warning.
- **No silent unsafe state:** when confidence drops below threshold, app announces uncertainty.
- **Priority interrupt:** urgent alerts preempt descriptive narration.
- **Conservative distance/direction:** bias toward caution (false positive preferred over late warning).

### 1.4 UI profile (aligned with provided image)

- Dark translucent background, minimal text, large central status emblem.
- Top line: `SYSTEM STATUS: INACTIVE|ACTIVE|PAUSED|FAILSAFE`.
- Center prompt for voice activation phrase.
- One visible microphone indicator icon, but core interaction is voice-only.
- UI exists for reassurance; all primary workflows are hands-free.

---

## 2) Dependency List (Offline + Android-Compatible)

## 2.1 Core runtime
- `python==3.11.*` (via python-for-android toolchain constraints as supported by Buildozer profile)
- `kivy>=2.2.0`
- `pyjnius>=1.6.1`

## 2.2 On-device inference stack (choose one profile)

### Profile A (preferred for Python integration)
- `onnxruntime` (Android-supported build variant)
- `opencv-python` (or Android camera bridge + NumPy conversion path)
- `numpy`

### Profile B (if ONNX integration is constrained)
- `tflite-runtime` (Android-compatible package / bundled native libs)
- `numpy`

> Exactly one inference profile should be active per release build.

## 2.3 Speech and Android system integration
- Android `TextToSpeech` via PyJNIus
- Android `SpeechRecognizer` via PyJNIus (offline recognition mode)
- Android Foreground Service + Notification channel
- Android WakeLock APIs

## 2.4 Packaging/build
- `buildozer`
- `cython` (required by build chain)
- Android SDK/NDK managed by Buildozer

## 2.5 Explicitly excluded dependencies
- No cloud SDKs
- No analytics SDKs
- No account/auth SDKs
- No face recognition libraries

---

## 3) Project Folder Structure (Phase 0 baseline)

```text
Blind-Navigation/
├── README.md
├── buildozer.spec
├── requirements-mobile.txt
├── docs/
│   ├── phase1_architecture_dependencies_structure.md
│   └── offline_mobile_architecture_phase0.md
├── app/
│   ├── main.py
│   ├── config/
│   │   ├── settings.py
│   │   └── thresholds.py
│   ├── ui/
│   │   ├── main_screen.py
│   │   ├── widgets.py
│   │   └── theme.py
│   ├── core/
│   │   ├── state_machine.py
│   │   ├── command_router.py
│   │   ├── safety_watchdog.py
│   │   └── event_bus.py
│   ├── services/
│   │   ├── foreground_service.py
│   │   ├── wake_lock.py
│   │   ├── tts_engine.py
│   │   └── speech_engine.py
│   ├── vision/
│   │   ├── camera_stream.py
│   │   ├── yolo_runner.py
│   │   ├── label_filter.py
│   │   └── spatial_reasoner.py
│   ├── audio/
│   │   ├── priority_manager.py
│   │   └── utterance_templates.py
│   └── android/
│       ├── permissions.py
│       ├── notifications.py
│       └── service_entrypoint.py
├── models/
│   ├── yolo/
│   │   ├── model.onnx
│   │   └── labels.txt
│   └── README.md
├── tests/
│   ├── test_priority_manager.py
│   ├── test_spatial_reasoner.py
│   ├── test_state_machine.py
│   └── test_label_filter.py
└── scripts/
    ├── validate_offline_constraints.py
    └── package_android.sh
```

## 3.1 Safety scope in code boundaries
- `vision/label_filter.py`: enforces allowed classes only (no identity classes).
- `audio/priority_manager.py`: enforces mandatory interrupt order.
- `core/safety_watchdog.py`: enforces fail-loud and uncertainty policy.
- `services/speech_engine.py`: enforces no audio storage/logging.

