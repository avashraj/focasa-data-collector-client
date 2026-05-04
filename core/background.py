import base64
import io
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import mss
from PIL import Image

import api.client as client


class ScreenshotPipeline:
    def __init__(
        self,
        executor: ThreadPoolExecutor,
        stop_event: threading.Event,
        api_key: str,
        user_id: str,
        task_id: str,
    ) -> None:
        self._executor = executor
        self._stop_event = stop_event
        self._api_key = api_key
        self._user_id = user_id
        self._task_id = task_id
        self._lock = threading.Lock()
        self._running = False

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
        self._executor.submit(self._capture)

    def _finish(self) -> None:
        with self._lock:
            self._running = False

    def _capture(self) -> None:
        if self._stop_event.is_set():
            return
        timestamp = datetime.now(tz=timezone.utc)
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            raw = sct.grab(monitor)
            rgb_bytes = bytes(raw.rgb)
            size = raw.size
        self._executor.submit(self._convert, rgb_bytes, size, timestamp)

    def _convert(self, rgb_bytes: bytes, size: tuple, timestamp: datetime) -> None:
        if self._stop_event.is_set():
            return
        buf = io.BytesIO()
        Image.frombytes("RGB", size, rgb_bytes).save(buf, format="JPEG", quality=75)
        self._executor.submit(self._encode, buf.getvalue(), timestamp)

    def _encode(self, jpeg_bytes: bytes, timestamp: datetime) -> None:
        if self._stop_event.is_set():
            return
        b64 = base64.b64encode(jpeg_bytes).decode("utf-8")
        self._executor.submit(self._send, b64, timestamp, 0)

    def _send(self, b64: str, timestamp: datetime, attempt: int) -> None:
        if self._stop_event.is_set():
            self._finish()
            return
        try:
            client.upload_screenshot(
                api_key=self._api_key,
                user_id=self._user_id,
                task_id=self._task_id,
                timestamp=timestamp,
                b64_image=b64,
            )
            self._finish()
        except Exception:
            if attempt < 3 and not self._stop_event.is_set():
                time.sleep(attempt + 1)
                self._executor.submit(self._send, b64, timestamp, attempt + 1)
            else:
                self._finish()


class ScreenshotService:
    def __init__(self, api_key: str, user_id: str, task_id: str) -> None:
        workers = min(4, os.cpu_count() or 1)
        self._executor = ThreadPoolExecutor(max_workers=workers)
        self._stop_event = threading.Event()
        self._pipeline = ScreenshotPipeline(
            self._executor, self._stop_event, api_key, user_id, task_id
        )
        self._scheduler = threading.Thread(
            target=self._run, name="screenshot-scheduler", daemon=False
        )

    def start(self) -> None:
        self._scheduler.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._executor.shutdown(wait=True, cancel_futures=True)
        self._scheduler.join(timeout=5)

    def _run(self) -> None:
        while not self._stop_event.wait(timeout=10):
            self._pipeline.start()
