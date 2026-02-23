# MASTER DEVELOPER PROMPT (No Face Recognition)

Build a mobile-first, offline-first, Python-based assistive navigation app for blind users.

## Hard requirements
- No face recognition.
- No person identification.
- Person presence only (e.g., "Person ahead", "Person on your left", "Person on your right").
- Audio-first and hands-free.
- Works with screen locked through Android foreground service.
- No cloud inference, no uploads, no accounts.
- No photo/audio storage.

## Core modules
- Object detection module
- Audio feedback module
- Voice command module
- Safety decision module
- Sensor fusion module
- Navigation logic module
- Settings module

## Audio priority order
1. Immediate danger
2. Directional guidance
3. Environmental awareness
4. User-requested descriptions

Higher priority must interrupt lower priority.

## Safety fail-safe outputs
- "Camera blocked"
- "Low light, move slowly"
- "Phone angle unsafe"
- "Unclear environment. Move slowly."

## Supported commands
- Assistant start navigation
- Assistant stop
- What's ahead?
- Describe the scene
- Is it safe to move?
- Any obstacles nearby?
- Pause alerts
- Resume alerts
- Repeat last instruction
