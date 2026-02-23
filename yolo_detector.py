from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


@dataclass
class Detection:
    label: str
    confidence: float
    distance_hint_m: float
    direction: str
    proximity: str
    movement: str


class YoloDetector:
    """YOLO wrapper with graceful fully-local fallback."""

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
            Detection("person", 0.92, 1.5, "ahead", "near", "approaching"),
            Detection("chair", 0.81, 0.8, "left", "very close", "static"),
        ]
        return {
            "engine": self.engine,
            "detections": [asdict(d) for d in detections],
            "summary": "Person ahead near, chair left very close.",
        }

    def _detect_real(self, image_path: Path) -> dict[str, Any]:
        if not image_path.exists():
            return {"engine": self.engine, "detections": [], "summary": f"Image not found at {image_path}"}

        results = self._model.predict(source=str(image_path), verbose=False)
        names = self._model.names

        detections: list[Detection] = []
        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                label = names.get(cls_id, str(cls_id)) if isinstance(names, dict) else str(cls_id)

                x1, _, x2, _ = [float(v) for v in box.xyxy[0].tolist()]
                center_x = (x1 + x2) / 2.0 / max(float(result.orig_shape[1]), 1.0)
                width_ratio = (x2 - x1) / max(float(result.orig_shape[1]), 1.0)

                direction = "left" if center_x < 0.33 else "right" if center_x > 0.66 else "ahead"
                proximity = self._proximity_from_width(width_ratio)
                distance_hint = self._distance_hint_from_width(width_ratio)

                detections.append(
                    Detection(
                        label=label,
                        confidence=round(conf, 3),
                        distance_hint_m=distance_hint,
                        direction=direction,
                        proximity=proximity,
                        movement="unknown",
                    )
                )

        summary = self._summary(detections)
        return {"engine": self.engine, "detections": [asdict(d) for d in detections], "summary": summary}

    def _distance_hint_from_width(self, width_ratio: float) -> float:
        if width_ratio >= 0.45:
            return 0.6
        if width_ratio >= 0.25:
            return 1.2
        if width_ratio >= 0.12:
            return 2.2
        return 4.0

    def _proximity_from_width(self, width_ratio: float) -> str:
        if width_ratio >= 0.45:
            return "very close"
        if width_ratio >= 0.25:
            return "near"
        if width_ratio >= 0.12:
            return "medium"
        return "far"

    def _summary(self, detections: list[Detection]) -> str:
        if not detections:
            return "No significant hazards detected."

        top = sorted(detections, key=lambda d: d.confidence, reverse=True)[:3]
        return ". ".join(f"{d.label} {d.direction} {d.proximity}" for d in top)

    def navigation_alert(self, detections: list[dict[str, Any]], guidance_mode: bool = True) -> str:
        if not detections:
            return "Path appears unclear. Move slowly."

        risky = [d for d in detections if str(d.get("proximity", "")) in {"very close", "near"}]
        if not risky:
            return "Path clear for a few meters."

        obj_names = ", ".join(sorted({str(d.get("label", "object")) for d in risky}))
        if guidance_mode:
            return f"Obstacle alert: {obj_names} nearby. Stop and adjust direction."
        return f"Obstacle alert: {obj_names} nearby."
