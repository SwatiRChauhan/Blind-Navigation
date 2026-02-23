from app.services.safety_engine import SafetyEngine
from app.vision.label_filter import Detection


def test_person_presence_phrase_only():
    engine = SafetyEngine()
    event = engine.detections_to_alert([
        Detection(label="person", confidence=0.9, x_center=0.2, width=0.2)
    ])
    assert event.text in {"Person on your left", "Person ahead", "Person on your right"}


def test_vehicle_close_is_immediate_danger():
    engine = SafetyEngine()
    event = engine.detections_to_alert([
        Detection(label="car", confidence=0.95, x_center=0.5, width=0.5)
    ])
    assert event.text == "Vehicle approaching"
