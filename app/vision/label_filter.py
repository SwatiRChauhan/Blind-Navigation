from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Detection:
    label: str
    confidence: float
    x_center: float
    width: float


_ALLOWED_LABELS = {
    "person",
    "car",
    "truck",
    "bus",
    "motorcycle",
    "bicycle",
    "door",
    "stairs",
    "curb",
    "wall",
    "pole",
    "chair",
    "bench",
    "table",
    "animal",
    "obstacle",
    "open_path",
    "dropoff",
}

_FORBIDDEN_LABELS = {
    "face",
    "person_id",
    "identity",
    "age",
    "gender",
    "emotion",
}


def filter_allowed_detections(detections: Iterable[Detection], min_confidence: float = 0.35) -> list[Detection]:
    out: list[Detection] = []
    for det in detections:
        label = det.label.strip().lower()
        if label in _FORBIDDEN_LABELS:
            continue
        if label not in _ALLOWED_LABELS:
            continue
        if det.confidence < min_confidence:
            continue
        out.append(Detection(label=label, confidence=det.confidence, x_center=det.x_center, width=det.width))
    return out


def is_person_presence_only(label: str) -> bool:
    return label.strip().lower() == "person"
