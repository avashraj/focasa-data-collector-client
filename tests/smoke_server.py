"""
Smoke test server for the screenshot background service.

Usage:
    python tests/smoke_server.py

Then run the app in a separate terminal:
    python main.py

Expected output every ~10 seconds:
    [2026-05-04 01:24:00] POST /screenshot — 45231 bytes — first 2: ff d8 (JPEG ok)
"""

import base64
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            jpeg = base64.b64decode(body)
            first_two = jpeg[:2].hex()
            is_jpeg = jpeg[:2] == b"\xff\xd8"
            status = "JPEG ok" if is_jpeg else f"UNEXPECTED ({first_two})"
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{ts}] POST /screenshot — {len(jpeg)} bytes — first 2: {first_two} ({status})",
                  flush=True)
        except Exception as exc:
            print(f"[ERROR] Could not decode body: {exc}", flush=True)

        self.send_response(200)
        self.end_headers()

    def log_message(self, fmt, *args):
        pass


def main(port: int = 8000):
    server = HTTPServer(("", port), Handler)
    print(f"Smoke server listening on http://localhost:{port}/screenshot")
    print("Press Ctrl-C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    main(port)
