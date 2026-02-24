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

Runtime permissions:
- On Android, the app now explicitly requests **microphone, camera, and location** at startup and again before start if still missing.
- Navigation will not start until all required permissions are granted.

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


## Android build (Buildozer)
1. Install Buildozer and Android prerequisites on Linux.
2. Initialize config:
```bash
buildozer init
```
3. In `buildozer.spec`, set:
   - `source.include_exts = py,kv,png,jpg,atlas`
   - `requirements = python3,kivy,plyer`
   - `android.permissions = RECORD_AUDIO,CAMERA,ACCESS_FINE_LOCATION,FOREGROUND_SERVICE,WAKE_LOCK`
4. Build APK:
```bash
buildozer -v android debug
```
5. Install on device:
```bash
buildozer android deploy run
```

## 100% voice control flow
- App starts by requesting microphone/camera/location permissions on Android.
- Voice engine listens continuously and maps spoken text to command intents.
- Synonyms supported for scene query: "What's ahead", "Describe my surroundings", "Tell me what is in front of me".
- No TextInput is used in UI or command handling.

