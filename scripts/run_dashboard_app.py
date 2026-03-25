from __future__ import annotations

import cgi
import json
import mimetypes
import os
import sys
import tempfile
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from predict_audio_with_baseline import predict_audio


HOST = "127.0.0.1"
PORT = 8765
MODEL_PATH = ROOT / "ml-workspace" / "artifacts" / "cnn_experiment_top200_gpu_model.pt"
UPLOAD_DIR = ROOT / "dashboard" / "uploads"


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._send_json({"status": "ok"})
            return
        if parsed.path == "/api/latest-log":
            self._handle_latest_log()
            return
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/predict":
            self._handle_predict()
            return
        if parsed.path == "/api/predict-path":
            self._handle_predict_path()
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Unknown API endpoint")

    def _handle_predict(self) -> None:
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self._send_json({"error": "multipart/form-data request required"}, status=HTTPStatus.BAD_REQUEST)
            return

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": content_type,
            },
        )

        if "audio" not in form:
            self._send_json({"error": "audio field is required"}, status=HTTPStatus.BAD_REQUEST)
            return

        file_item = form["audio"]
        if not getattr(file_item, "file", None):
            self._send_json({"error": "uploaded file is empty"}, status=HTTPStatus.BAD_REQUEST)
            return

        filename = Path(file_item.filename or "upload.wav").name
        suffix = Path(filename).suffix or ".wav"
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=UPLOAD_DIR) as handle:
            handle.write(file_item.file.read())
            tmp_path = Path(handle.name)

        try:
            result = predict_audio(tmp_path, MODEL_PATH)
            result["uploaded_name"] = filename
            result["uploaded_temp_path"] = str(tmp_path.relative_to(ROOT)).replace("\\", "/")
            self._send_json(result)
        except Exception as exc:  # noqa: BLE001
            self._send_json({"error": str(exc), "uploaded_name": filename}, status=HTTPStatus.BAD_REQUEST)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def _handle_predict_path(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            self._send_json({"error": "request body is empty"}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            body = self.rfile.read(content_length)
            payload = json.loads(body.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            self._send_json({"error": f"invalid json: {exc}"}, status=HTTPStatus.BAD_REQUEST)
            return

        audio_path_value = payload.get("audio_path")
        if not audio_path_value:
            self._send_json({"error": "audio_path is required"}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            requested = (ROOT / str(audio_path_value)).resolve()
        except Exception as exc:  # noqa: BLE001
            self._send_json({"error": f"invalid path: {exc}"}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            requested.relative_to(ROOT)
        except ValueError:
            self._send_json({"error": "path must stay within project root"}, status=HTTPStatus.BAD_REQUEST)
            return

        if not requested.exists():
            self._send_json({"error": "audio file not found"}, status=HTTPStatus.NOT_FOUND)
            return

        try:
            result = predict_audio(requested, MODEL_PATH)
            result["requested_audio_path"] = str(requested.relative_to(ROOT)).replace("\\", "/")
            self._send_json(result)
        except Exception as exc:  # noqa: BLE001
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

    def _send_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_latest_log(self) -> None:
        log_dir = ROOT / "ml-workspace" / "reports" / "ops_logs"
        logs = sorted(log_dir.glob("long_pipeline_*.log")) if log_dir.exists() else []
        if not logs:
            self._send_json({"error": "no log found"}, status=HTTPStatus.NOT_FOUND)
            return
        latest = logs[-1]
        lines = latest.read_text(encoding="utf-8", errors="replace").splitlines()
        self._send_json(
            {
                "path": str(latest.relative_to(ROOT)).replace("\\", "/"),
                "tail": lines[-40:],
                "line_count": len(lines),
            }
        )

    def guess_type(self, path: str) -> str:
        guessed = super().guess_type(path)
        if guessed == "application/octet-stream":
            return mimetypes.guess_type(path)[0] or guessed
        return guessed


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), DashboardHandler)
    print(f"Dashboard app running at http://{HOST}:{PORT}/dashboard/index.html")
    print(f"Serving project root: {ROOT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
