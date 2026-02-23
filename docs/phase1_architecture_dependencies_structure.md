# Phase 1: Blind Navigation App Architecture, Dependencies, and Structure

## Product goals (Phase 1)
- Provide **audio-first indoor/outdoor guidance** for blind and low-vision users.
- Offer **keyboard-first and screen-reader-friendly interactions**.
- Support **simple voice commands** (`start`, `next`, `repeat`, `scan`, `where am I`, `stop`).
- Include a **safe simulation mode** for obstacle alerts and route progression.
- Add **Python + YOLO obstacle detection API** with fallback behavior.

## Architecture

### Web UI + Python backend (MVP)

```text
+-----------------------------+
| Accessible Web UI           |
| - Large controls            |
| - Status + route panels     |
| - Aria-live announcements   |
+-------------+---------------+
              |
              v
+-----------------------------+
| Python API (Flask)          |
| - /health                   |
| - /api/detect               |
| - static app hosting        |
+-------------+---------------+
              |
              v
+-----------------------------+
| YOLO Detection Engine       |
| - ultralytics YOLOv8n       |
| - fallback simulation mode  |
+-----------------------------+
```

## Dependencies (Phase 1)
- **Runtime:** Python 3.10+ and modern browser.
- **Backend required: none beyond Python standard library (`http.server`).
- **Vision optional:** `ultralytics` (fallback mode works without real model).
- **Front-end required:** None (vanilla HTML/CSS/JS).
- **Optional browser APIs:** `window.speechSynthesis`, `webkitSpeechRecognition` / `SpeechRecognition`.

## Folder structure
```text
Blind-Navigation/
├── docs/
│   └── phase1_architecture_dependencies_structure.md
├── src/
│   ├── app.js
│   ├── index.html
│   └── styles.css
├── server.py
├── yolo_detector.py
├── requirements.txt
└── README.md
```

## Non-functional requirements
- WCAG-friendly contrast and focus styles.
- Works without browser voice APIs.
- Works without YOLO runtime through fallback simulation responses.
- Lightweight and easy to run locally.
