from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpatialCue:
    direction: str
    proximity: str


def direction_from_x(x_center: float) -> str:
    if x_center < 0.33:
        return "left"
    if x_center > 0.66:
        return "right"
    return "center"


def proximity_from_box_width(width: float) -> str:
    if width >= 0.45:
        return "very close"
    if width >= 0.25:
        return "near"
    if width >= 0.12:
        return "medium"
    return "far"


def build_spatial_cue(x_center: float, width: float) -> SpatialCue:
    return SpatialCue(direction=direction_from_x(x_center), proximity=proximity_from_box_width(width))
