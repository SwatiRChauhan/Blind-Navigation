from app.vision.label_filter import Detection, filter_allowed_detections


def test_forbidden_face_removed():
    data = [
        Detection(label='face', confidence=0.99, x_center=0.5, width=0.3),
        Detection(label='person', confidence=0.99, x_center=0.5, width=0.3),
    ]
    out = filter_allowed_detections(data)
    assert len(out) == 1
    assert out[0].label == 'person'
