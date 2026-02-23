# Vision Companion (Offline Blind Navigation)

Audio-first navigation assistant for blind users with **offline local processing**.

## Safety constraints enforced
- Offline-first perception (`/api/detect` local API only).
- Person detection is **presence-only** (no identity/face analysis).
- Face/identity labels are explicitly rejected in safety core modules.
- Alerts follow strict priority: danger > guidance > awareness.

## Voice-only control
- Say **"Start safe navigation"** to activate continuous assistance.
- Say **"Stop safe navigation"** to stop immediately.
- Optional commands: "What is ahead", "Describe surroundings", "Help", "Repeat".
- Stop command is strict: only **"Stop safe navigation"** deactivates assistance.

## Run locally
```bash
python mobile_runner.py
```
Open `http://127.0.0.1:4173`.

> On first run, allow microphone/camera/location permissions in the browser.

## Run tests
```bash
python -m pytest tests -q
```
