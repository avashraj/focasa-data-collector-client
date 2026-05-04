import base64
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, call, patch

import pytest
from PIL import Image

from core.background import ScreenshotPipeline, ScreenshotService


def make_pipeline(stop_event=None):
    executor = ThreadPoolExecutor(max_workers=1)
    event = stop_event or threading.Event()
    pipeline = ScreenshotPipeline(executor, event)
    return pipeline, executor, event


def sync_submit(fn, *args):
    """Replaces executor.submit with a synchronous direct call, so retry chains
    in _send can be exercised without a real thread pool."""
    fn(*args)



# ---------------------------------------------------------------------------
# _capture
# ---------------------------------------------------------------------------

class TestCapture:
    def test_submits_convert_with_rgb_bytes(self):
        pipeline, executor, _ = make_pipeline()

        rgb = b"\xff\xff\xff"
        size = (1, 1)

        mock_grab = MagicMock()
        mock_grab.rgb = rgb
        mock_grab.size = size

        mock_sct = MagicMock()
        mock_sct.monitors = [None, {"top": 0, "left": 0, "width": 1, "height": 1}]
        mock_sct.grab.return_value = mock_grab

        with patch("core.background.mss.mss") as mock_mss, \
             patch.object(pipeline._executor, "submit") as mock_submit:

            mock_mss.return_value.__enter__ = MagicMock(return_value=mock_sct)
            mock_mss.return_value.__exit__ = MagicMock(return_value=False)

            pipeline._capture()

        mock_submit.assert_called_once_with(pipeline._convert, bytes(rgb), size)
        executor.shutdown(wait=False)

    def test_stop_event_short_circuits(self):
        stop = threading.Event()
        stop.set()
        pipeline, executor, _ = make_pipeline(stop_event=stop)

        with patch("core.background.mss.mss") as mock_mss:
            pipeline._capture()
            mock_mss.assert_not_called()

        executor.shutdown(wait=False)


# ---------------------------------------------------------------------------
# _convert
# ---------------------------------------------------------------------------

def make_rgb_bytes(width=2, height=2):
    img = Image.new("RGB", (width, height), color=(128, 64, 32))
    return img.tobytes(), (width, height)


class TestConvert:
    def test_produces_jpeg_bytes(self):
        pipeline, executor, _ = make_pipeline()
        rgb, size = make_rgb_bytes()

        received = []

        with patch.object(pipeline._executor, "submit", side_effect=lambda fn, arg: received.append(arg)):
            pipeline._convert(rgb, size)

        assert len(received) == 1
        assert received[0][:2] == b"\xff\xd8", "Expected JPEG magic bytes ff d8"
        executor.shutdown(wait=False)

    def test_stop_event_short_circuits(self):
        stop = threading.Event()
        stop.set()
        pipeline, executor, _ = make_pipeline(stop_event=stop)
        rgb, size = make_rgb_bytes()

        with patch.object(pipeline._executor, "submit") as mock_submit:
            pipeline._convert(rgb, size)
            mock_submit.assert_not_called()

        executor.shutdown(wait=False)


# ---------------------------------------------------------------------------
# _encode
# ---------------------------------------------------------------------------

class TestEncode:
    def test_produces_valid_base64(self):
        pipeline, executor, _ = make_pipeline()
        jpeg_bytes = b"\xff\xd8\xff\xe0test"

        received = []

        with patch.object(pipeline._executor, "submit", side_effect=lambda fn, b64, attempt: received.append(b64)):
            pipeline._encode(jpeg_bytes)

        assert len(received) == 1
        assert base64.b64decode(received[0]) == jpeg_bytes
        executor.shutdown(wait=False)

    def test_stop_event_short_circuits(self):
        stop = threading.Event()
        stop.set()
        pipeline, executor, _ = make_pipeline(stop_event=stop)

        with patch.object(pipeline._executor, "submit") as mock_submit:
            pipeline._encode(b"\xff\xd8\xff\xe0test")
            mock_submit.assert_not_called()

        executor.shutdown(wait=False)


# ---------------------------------------------------------------------------
# _send
# ---------------------------------------------------------------------------

class TestSend:
    def test_success_calls_upload_once(self):
        pipeline, executor, _ = make_pipeline()

        with patch("core.background.client.upload_screenshot") as mock_upload, \
             patch("core.background.time.sleep"):
            pipeline._send("abc123", 0)
            mock_upload.assert_called_once_with("abc123")

        executor.shutdown(wait=False)

    def test_retries_then_succeeds(self):
        pipeline, executor, _ = make_pipeline()
        call_count = 0

        def flaky(b64):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("network error")

        with patch("core.background.client.upload_screenshot", side_effect=flaky) as mock_upload, \
             patch("core.background.time.sleep") as mock_sleep, \
             patch.object(pipeline._executor, "submit", side_effect=sync_submit):
            pipeline._send("abc123", 0)

        assert mock_upload.call_count == 3
        mock_sleep.assert_has_calls([call(1), call(2)])

    def test_drops_after_max_retries(self):
        pipeline, executor, _ = make_pipeline()

        with patch("core.background.client.upload_screenshot", side_effect=ConnectionError("fail")) as mock_upload, \
             patch("core.background.time.sleep"), \
             patch.object(pipeline._executor, "submit", side_effect=sync_submit):
            pipeline._send("abc123", 0)

        assert mock_upload.call_count == 4

    def test_retry_uses_executor_submit(self):
        """Retry must re-submit to the executor, not recurse synchronously."""
        pipeline, executor, _ = make_pipeline()

        with patch("core.background.client.upload_screenshot", side_effect=ConnectionError("fail")), \
             patch("core.background.time.sleep"), \
             patch.object(pipeline._executor, "submit") as mock_submit:
            pipeline._send("abc123", 0)

        mock_submit.assert_called_once_with(pipeline._send, "abc123", 1)
        executor.shutdown(wait=False)

    def test_retry_stops_when_stop_event_set(self):
        stop = threading.Event()
        pipeline, executor, _ = make_pipeline(stop_event=stop)

        def fail_then_stop(b64):
            stop.set()
            raise ConnectionError("fail")

        with patch("core.background.client.upload_screenshot", side_effect=fail_then_stop), \
             patch("core.background.time.sleep"), \
             patch.object(pipeline._executor, "submit") as mock_submit:
            pipeline._send("abc123", 0)

        mock_submit.assert_not_called()
        executor.shutdown(wait=False)

    def test_stop_event_short_circuits(self):
        stop = threading.Event()
        stop.set()
        pipeline, executor, _ = make_pipeline(stop_event=stop)

        with patch("core.background.client.upload_screenshot") as mock_upload:
            pipeline._send("abc123", 0)
            mock_upload.assert_not_called()

        executor.shutdown(wait=False)


# ---------------------------------------------------------------------------
# ScreenshotService lifecycle
# ---------------------------------------------------------------------------

class TestPipelineIdleGuard:
    def test_start_skips_when_already_running(self):
        pipeline, executor, _ = make_pipeline()

        with patch.object(pipeline._executor, "submit") as mock_submit:
            pipeline._running = True
            pipeline.start()
            mock_submit.assert_not_called()

        executor.shutdown(wait=False)

    def test_start_fires_when_idle(self):
        pipeline, executor, _ = make_pipeline()

        with patch.object(pipeline._executor, "submit") as mock_submit:
            pipeline.start()
            mock_submit.assert_called_once_with(pipeline._capture)

        executor.shutdown(wait=False)

    def test_idle_after_send_success(self):
        pipeline, executor, _ = make_pipeline()
        pipeline._running = True

        with patch("core.background.client.upload_screenshot"), \
             patch.object(pipeline._executor, "submit"):
            pipeline._send("abc123", 0)

        assert not pipeline._running
        executor.shutdown(wait=False)

    def test_idle_after_send_drop(self):
        pipeline, executor, _ = make_pipeline()
        pipeline._running = True

        with patch("core.background.client.upload_screenshot", side_effect=ConnectionError("fail")), \
             patch("core.background.time.sleep"), \
             patch.object(pipeline._executor, "submit", side_effect=sync_submit):
            pipeline._send("abc123", 3)

        assert not pipeline._running
        executor.shutdown(wait=False)

    def test_idle_after_stop_event_in_send(self):
        stop = threading.Event()
        stop.set()
        pipeline, executor, _ = make_pipeline(stop_event=stop)
        pipeline._running = True

        with patch("core.background.client.upload_screenshot") as mock_upload:
            pipeline._send("abc123", 0)
            mock_upload.assert_not_called()

        assert not pipeline._running
        executor.shutdown(wait=False)


class TestScreenshotService:
    def test_stop_joins_scheduler(self):
        with patch.object(ScreenshotPipeline, "_capture"):
            service = ScreenshotService()
            service.start()
            service.stop()
            assert not service._scheduler.is_alive()

    def test_stop_event_set_after_stop(self):
        service = ScreenshotService()
        service.start()
        service.stop()
        assert service._stop_event.is_set()
