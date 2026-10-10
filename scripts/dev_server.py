#!/usr/bin/env python3
"""Dub Studio lightweight dev mock server.
Answers the REST API contract on port 8793 (DUB_STUDIO_PORT) so the frontend (Vite)
can run in dev mode on macOS without Windows CUDA engines.
"""
from __future__ import annotations

import json
import os
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

PORT = int(os.environ.get("DUB_STUDIO_PORT", 8793))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WHISPER_LANGS = [
    "en", "ru", "zh", "es", "fr", "pt", "de", "it", "ja", "ko", "vi", "ar", "hi",
    "tr", "pl", "uk", "nl", "id", "sv", "cs", "ro", "el", "hu", "th", "da", "fi"
]

state = {
    "launch_defaults": {
        "audio": "dub",
        "subs": "translate",
        "burn": True,
        "detect_text": False,
        "src_lang": "auto",
        "speaker_count": 0,
        "tgt_lang": None,
        "casting": False,
        "casting_ref": "",
        "content_type": "auto",
        "vo_gain_db": -12.0,
        "tr_style": "",
        "tr_style_custom": "",
        "sub_blur": True,
        "keep_orig": False,
        "container": "mp4",
        "voice_src": "clone",
        "voice_slots_m": [],
        "voice_slots_f": [],
    },
    "selection": {
        "asr_engine": "whisper",
        "whisper_model": "base",
        "whisper_compute": "int8",
        "tts_provider": "local",
        "duck_on": "1",
    },
    "hub_state": {
        "telemetry": {
            "enabled": False,
            "acknowledged": True,
            "disabledByEnv": False,
            "install": None,
        },
        "source": None,
        "fetchedAt": int(time.time()),
        "lastError": None,
        "items": [],
    },
    "projects": [],
}


class DevHandler(BaseHTTPRequestHandler):
    def _send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Expose-Headers", "x-project-rev, x-dub-window")

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors()
        self.end_headers()

    def _json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._send_cors()
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        path = u.path

        if path == "/health":
            self._json({
                "status": "ok",
                "app": "dub-studio",
                "version": "2.0.0",
                "service_executable": sys.argv[0],
                "repo_root": ROOT,
                "port": PORT,
            })
        elif path == "/setup/status":
            self._json({
                "components": [
                    {
                        "id": "parakeet",
                        "name": "Parakeet-TDT 0.6B v3 int8",
                        "purpose": "ASR",
                        "requirement": "required",
                        "delivery": "download",
                        "installed": True,
                        "size": 671000000,
                        "bytesOnDisk": 671000000,
                        "spaceNeeded": 0,
                        "missing": [],
                    }
                ],
                "ready": True,
                "downloadPending": 0,
                "driverOk": True,
                "llamaBuild": "metal",
                "modelsDir": os.path.join(ROOT, "models"),
                "freeBytes": 50000000000,
                "gpu": {
                    "nvidia": False,
                    "name": "Apple Silicon (macOS dev mode)",
                    "vendor": "apple",
                    "vramBytes": 17179869184,
                    "driverVersion": "macOS Metal",
                    "cudaDriver": None,
                    "compute": None,
                    "cuda13Ok": False,
                    "reason": "no_nvidia",
                    "minDriver": 580,
                    "minCompute": "7.5",
                },
                "active": None,
            })
        elif path == "/engine/capabilities":
            self._json({
                "device": "Apple Silicon (macOS)",
                "tts_quant": "q8_0",
                "asr_model": "Parakeet-TDT",
                "models": {
                    "asr": "Parakeet-TDT",
                    "llm": "Gemma-4 12B",
                    "vision": "mmproj",
                    "tts": "Higgs Audio v3",
                },
                "ffmpeg": True,
                "languages": WHISPER_LANGS,
                "voice_modes": ["clone", "autocast", "auto", "voice"],
                "selection": state["selection"],
                "asr_engines": ["whisper", "parakeet"],
                "whisper_models": ["tiny", "base", "small", "medium", "large-v3", "large-v3-turbo"],
                "whisper_computes": ["int8", "float32"],
                "llama_ubatches": ["0", "512", "256", "128"],
                "higgs_ref_secs_opts": ["12", "8", "6", "4"],
            })
        elif path == "/v1/hub/state":
            self._json(state["hub_state"])
        elif path == "/mcp/status":
            self._json({
                "agent_connected": False,
                "agent_last_call": None,
                "agent_seconds_ago": None,
                "agent_calls": 0,
                "window_open": True,
            })
        elif path == "/mcp/window":
            # SSE stream for window events
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self._send_cors()
            self.end_headers()
            try:
                self.wfile.write(b": connected\n\n")
                self.wfile.flush()
                while True:
                    time.sleep(15)
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
        elif path == "/projects":
            self._json({"projects": state["projects"]})
        elif path == "/settings/launch":
            self._json({
                "defaults": state["launch_defaults"],
                "saved": True,
            })
        elif path == "/app/paths":
            self._json({
                "data_dir": ROOT,
                "projects_dir": os.path.join(ROOT, "workspace"),
                "models_dir": os.path.join(ROOT, "models"),
            })
        elif path == "/hw/snapshot":
            self._json({
                "gpuName": "Apple Silicon (macOS)",
                "totalVram": 17179869184,
                "usedVram": 0,
                "freeVram": 17179869184,
                "gpuUtilization": 0,
                "temperature": 35,
                "powerDraw": 5,
                "powerLimit": 30,
                "processRam": 50000000,
                "totalRam": 17179869184,
                "usedRam": 8000000000,
                "message": "",
            })
        elif path == "/url/tool":
            self._json({
                "installed": False,
                "version": "",
                "pinnedVersion": "2026.08.19",
                "updated": False,
                "latest": None,
                "checkedAt": 0,
                "updateAvailable": False,
                "updating": False,
                "lastError": None,
                "lastErrorCode": None,
            })
        elif path == "/url/fetches":
            self._json({"fetches": []})
        elif path == "/engine/proxy/settings":
            self._json({
                "mode": "off",
                "kind": "http",
                "on": False,
                "url": "",
                "password_set": False,
                "problem": None,
            })
        elif path == "/presets":
            self._json({"presets": {}, "reveals": []})
        elif path == "/fonts":
            self._json({"fonts": []})
        elif path == "/voices":
            self._json({"voices": []})
        elif path == "/voices/catalog":
            self._json({"voices": []})
        elif path == "/casting/library":
            self._json({"casts": []})
        elif path == "/record/devices":
            self._json({"devices": []})
        elif path == "/record/level":
            self._json({"level": 0})
        elif path == "/engine/presets":
            self._json({"presets": []})
        elif path == "/engine/openrouter/models":
            self._json({"models": []})
        elif path == "/engine/openrouter/settings":
            self._json({"key": "", "model": ""})
        elif path == "/engine/google/models":
            self._json({"models": []})
        elif path == "/engine/google/settings":
            self._json({"key": "", "model": ""})
        elif path == "/engine/server/models":
            self._json({"models": []})
        elif path == "/jobs":
            self._json({"jobs": [], "project_job": None})
        else:
            self._json({"status": "ok", "path": path})

    def do_POST(self):
        u = urlparse(self.path)
        path = u.path
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length > 0 else b""
        try:
            body = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            body = {}

        if path == "/engine/select":
            k, v = body.get("key"), body.get("val")
            if k:
                state["selection"][k] = v
            self._json({"ok": True, "selection": state["selection"]})
        elif path == "/setup/cancel":
            self._json({"ok": True})
        elif path == "/setup/download":
            self._json({"ok": True, "job_id": "mock_dl"})
        elif path == "/projects":
            self._json({"project_id": "mock_project_1", "imported_subs": False})
        elif path in ("/mcp/window/focus", "/mcp/window/result"):
            self._json({"ok": True})
        elif path == "/v1/hub/telemetry":
            self._json(state["hub_state"]["telemetry"])
        else:
            self._json({"ok": True, "path": path})

    def do_PATCH(self):
        u = urlparse(self.path)
        path = u.path
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length > 0 else b""
        try:
            body = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            body = {}

        if path == "/settings/launch":
            state["launch_defaults"].update(body)
            self._json({
                "defaults": state["launch_defaults"],
                "saved": True,
            })
        else:
            self._json({"ok": True})

    def do_PUT(self):
        self._json({"ok": True})

    def do_DELETE(self):
        self._json({"ok": True})

    def log_message(self, format, *args):
        sys.stderr.write(f"[dev-server] {args[0]} {args[1]} -> {args[2]}\n")


if __name__ == "__main__":
    from socketserver import ThreadingMixIn

    class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
        daemon_threads = True

    server = ThreadedHTTPServer(("127.0.0.1", PORT), DevHandler)
    print(f"Dub Studio dev mock server listening on http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
