from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Detection:
    label: str
    confidence: float
    distance_hint_m: float


class YoloDetector:
    """YOLO wrapper with graceful fallback for environments without model deps."""

    def __init__(self) -> None:
        self.ready = False
        self.engine = "fallback"
        self._model = None

        try:
            from ultralytics import YOLO  # type: ignore

            self._model = YOLO("yolov8n.pt")
            self.ready = True
            self.engine = "ultralytics-yolov8n"
        except Exception:
            self._model = None
            self.ready = False
            self.engine = "fallback-simulated"

    def detect(self, image_path: str | None = None) -> dict[str, Any]:
        if self.ready and self._model and image_path:
            return self._detect_real(Path(image_path))

        detections = [
            Detection(label="person", confidence=0.92, distance_hint_m=1.5),
            Detection(label="chair", confidence=0.81, distance_hint_m=0.8),
        ]
        return {
            "engine": self.engine,
            "detections": [d.__dict__ for d in detections],
            "summary": "Simulated frame analyzed. Nearby person and chair detected.",
        }

    def _detect_real(self, image_path: Path) -> dict[str, Any]:
        if not image_path.exists():
            return {
                "engine": self.engine,
                "detections": [],
                "summary": f"Image not found at {image_path}",
            }

        results = self._model.predict(source=str(image_path), verbose=False)
        names = self._model.names

        detections: list[Detection] = []
        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                label = names.get(cls_id, str(cls_id)) if isinstance(names, dict) else str(cls_id)
                # Phase 1 heuristic only: placeholder distance from confidence.
                distance_hint = max(0.4, round(3.0 - conf * 2.0, 2))
                detections.append(
                    Detection(label=label, confidence=round(conf, 3), distance_hint_m=distance_hint)
                )

        if not detections:
            summary = "No significant obstacles detected."
        else:
            top = sorted(detections, key=lambda d: d.confidence, reverse=True)[:3]
            summary = "Detected: " + ", ".join(f"{d.label} ({d.confidence:.2f})" for d in top)

        return {
            "engine": self.engine,
            "detections": [d.__dict__ for d in detections],
            "summary": summary,
        }

    def navigation_alert(self, detections: list[dict[str, Any]], guidance_mode: bool = True) -> str:
        if not detections:
            return "Path appears clear. Continue forward."

        risky = [d for d in detections if float(d.get("distance_hint_m", 99)) <= 1.2]
        if not risky:
            return "Objects nearby, but no immediate obstacle on path."

        obj_names = ", ".join(sorted({str(d.get('label', 'object')) for d in risky}))
        if guidance_mode:
            return f"Obstacle alert: {obj_names} ahead within 1.2 meters. Slow down and veer left."
        return f"Obstacle alert: {obj_names} nearby."
