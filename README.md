# Vision Companion (Offline Blind Navigation)

Audio-first navigation assistant for blind users with **offline local processing** and a native **Kivy mobile app**.

## Safety constraints enforced
- Offline-first perception (`/api/detect` local API only).
- Person detection is **presence-only** (no identity/face analysis).
- Face/identity labels are explicitly rejected in safety core modules.
- Alerts follow strict priority: danger > guidance > awareness.


## Kivy mobile app (offline)
- Entry point: `main.py`
- Run mobile app locally:
```bash
python main.py
```

Voice lifecycle:
- Say **"Start safe navigation"** to activate continuous assistance.
- Say **"Stop safe navigation"** to stop immediately.

## Voice-only control
- Say **"Start safe navigation"** to activate continuous assistance.
- Say **"Stop safe navigation"** to stop immediately.
- Optional commands: "What is ahead", "Describe surroundings", "Help", "Repeat".
- Stop command is strict: only **"Stop safe navigation"** deactivates assistance.

## Legacy web preview (optional)
If you still want the browser prototype:
```bash
python server.py
```
Then open `http://127.0.0.1:4173`.

## Run tests
```bash
python -m pytest tests -q
```
