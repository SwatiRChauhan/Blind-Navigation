# Blind Navigation App (Phase 1, Python + YOLO)

A lightweight accessible navigation prototype with a **Python backend** and **YOLO-based obstacle detection**.

## Features
- Predefined route guidance with waypoint progression.
- Voice announcements via browser speech synthesis.
- Optional voice commands where speech recognition is available.
- Keyboard-first controls for non-mouse interaction.
- YOLO obstacle scan endpoint (`/api/detect`) with fallback simulation.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
python server.py
```

Open `http://localhost:4173`.

## Notes on YOLO
- If `ultralytics` is available, the backend initializes `YOLO("yolov8n.pt")`.
- If the model/runtime is unavailable, the backend gracefully falls back to simulated detections so the app still works.

## Keyboard shortcuts
- `S` Start guidance
- `N` Next step
- `R` Repeat step
- `O` Simulate obstacle
- `V` Scan scene (YOLO API)
- `X` Stop guidance
