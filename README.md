# AEGIS Offline Blind Safety Navigation (Python)

This repository now includes a **safety-critical Python core** for an offline, audio-first navigation assistant for blind users.

## Safety constraints enforced
- Offline-first processing only.
- Person detection is **presence-only** (no identity/face analysis).
- Face/identity labels are explicitly rejected by the filter layer.
- Alert output follows priority: immediate danger > guidance > awareness > on-demand.

## Implemented Python modules
- `app/core/command_router.py` — voice command normalization and routing.
- `app/core/safety_watchdog.py` — camera/low-light/angle/confidence fail-safe messages.
- `app/vision/label_filter.py` — allowed-class filter + forbidden labels.
- `app/vision/spatial_reasoner.py` — left/center/right and conservative proximity cues.
- `app/audio/priority_manager.py` — interrupt policy manager.
- `app/services/safety_engine.py` — end-to-end detection-to-alert policy.

## Run tests
```bash
python -m pytest tests -q
```


## Vision Companion mobile web mode
- Set Gemini key in browser console once:
  `localStorage.setItem("GEMINI_API_KEY", "YOUR_KEY")`
- Run mobile server:
  `python mobile_runner.py`
- Open on your phone browser (same device): `http://127.0.0.1:4173`
- Tap anywhere to start: app requests microphone, camera, and location permissions.
