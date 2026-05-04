import io
import time
import threading
import multiprocessing
from pathlib import Path
from PIL import Image

INPUT_DIR = Path("test_og_screenshot")
OUTPUT_DIR = Path("test_result")
SCREENSHOT_NAMES = [f"sc{i}.png" for i in range(1, 5)]


def preload_images() -> list[tuple[str, bytes]]:
    """Read all PNG files into memory before any timing starts."""
    loaded = []
    for name in SCREENSHOT_NAMES:
        data = (INPUT_DIR / name).read_bytes()
        loaded.append((name, data))
        print(f"  Pre-loaded {name} ({len(data):,} bytes)")
    return loaded


def convert_bytes(png_bytes: bytes) -> bytes:
    """Convert PNG bytes to JPEG bytes entirely in memory."""
    with Image.open(io.BytesIO(png_bytes)) as img:
        out = io.BytesIO()
        img.convert("RGB").save(out, format="JPEG")
        return out.getvalue()


# --- Threading ---

def _thread_worker(name: str, png_bytes: bytes, results: dict, index: int) -> None:
    jpeg_bytes = convert_bytes(png_bytes)
    results[index] = (name, jpeg_bytes)
    print(f"  [thread] converted {name}")


def convert_with_threading(images: list[tuple[str, bytes]]) -> tuple[float, list[tuple[str, bytes]]]:
    print("\n[Threading] Starting conversion...")
    results: dict[int, tuple[str, bytes]] = {}

    threads = [
        threading.Thread(target=_thread_worker, args=(name, data, results, i))
        for i, (name, data) in enumerate(images)
    ]

    start = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.perf_counter() - start

    print(f"[Threading] Done in {elapsed:.4f}s")
    return elapsed, [results[i] for i in range(len(images))]


# --- Multiprocessing ---

def _mp_worker(png_bytes: bytes) -> bytes:
    return convert_bytes(png_bytes)


def convert_with_multiprocessing(images: list[tuple[str, bytes]]) -> tuple[float, list[tuple[str, bytes]]]:
    print("\n[Multiprocessing] Starting conversion...")
    names = [name for name, _ in images]
    byte_chunks = [data for _, data in images]

    start = time.perf_counter()
    with multiprocessing.Pool(processes=len(images)) as pool:
        jpeg_results = pool.map(_mp_worker, byte_chunks)
    elapsed = time.perf_counter() - start

    for name in names:
        print(f"  [process] converted {name}")
    print(f"[Multiprocessing] Done in {elapsed:.4f}s")
    return elapsed, list(zip(names, jpeg_results))


def save_results(results: list[tuple[str, bytes]], prefix: str) -> None:
    for name, jpeg_bytes in results:
        stem = Path(name).stem
        out_path = OUTPUT_DIR / f"{prefix}_{stem}.jpg"
        out_path.write_bytes(jpeg_bytes)


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("Pre-loading images into memory...")
    images = preload_images()

    threading_time, threading_results = convert_with_threading(images)
    save_results(threading_results, "threading")

    print("\nWaiting 5 seconds before next test...")
    time.sleep(5)

    mp_time, mp_results = convert_with_multiprocessing(images)
    save_results(mp_results, "multiprocessing")

    print("\n--- Results ---")
    print(f"  Threading:       {threading_time:.4f}s")
    print(f"  Multiprocessing: {mp_time:.4f}s")
    faster = "Threading" if threading_time < mp_time else "Multiprocessing"
    print(f"  Winner: {faster}")


if __name__ == "__main__":
    main()
