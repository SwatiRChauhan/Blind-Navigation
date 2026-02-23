from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from yolo_detector import YoloDetector

BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"
DETECTOR = YoloDetector()


class BlindNavigationHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SRC_DIR), **kwargs)

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send_json({"status": "ok", "yolo_ready": DETECTOR.ready, "backend": "python"})
            return

        if self.path == "/":
            self.path = "/index.html"

        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/detect":
            self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)
            return

        content_len = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_len) if content_len else b"{}"

        try:
            payload = json.loads(body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send_json({"error": "invalid json"}, status=HTTPStatus.BAD_REQUEST)
            return

        guidance_mode = bool(payload.get("guidance_mode", True))
        image_path = payload.get("image_path")

        result = DETECTOR.detect(image_path=image_path)
        alert = DETECTOR.navigation_alert(result["detections"], guidance_mode=guidance_mode)

        self._send_json(
            {
                "engine": result["engine"],
                "detections": result["detections"],
                "summary": result["summary"],
                "alert": alert,
            }
        )


def run() -> None:
    port = int(os.getenv("PORT", "4173"))
    server = ThreadingHTTPServer(("0.0.0.0", port), BlindNavigationHandler)
    print(f"Serving Blind Navigation on http://0.0.0.0:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
