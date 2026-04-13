#!/usr/bin/env python3
"""Measure YOLO11n NCNN inference latency on the current machine.

Target Pi 5 CPU: p95 < 200 ms per detect() call at 416x416. If you see
> 200 ms consistently, drop yolo_input_size to 320 in detector/config.py.

Usage:
    python scripts/benchmark_yolo.py
    python scripts/benchmark_yolo.py --iterations 200 --input-size 320

Requires: pip install ncnn opencv-python numpy (same deps as detector/).
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parent.parent
DETECTOR_DIR = REPO_ROOT / "detector"
MODELS_DIR = DETECTOR_DIR / "models"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--input-size", type=int, default=416)
    parser.add_argument("--frame-w", type=int, default=640)
    parser.add_argument("--frame-h", type=int, default=480)
    args = parser.parse_args()

    sys.path.insert(0, str(DETECTOR_DIR))
    try:
        from yolo_phone_detector import YoloPhoneDetector
    except ImportError as exc:
        print(f"Failed to import detector module: {exc}", file=sys.stderr)
        return 1

    param = MODELS_DIR / "yolo11n_416.ncnn.param"
    bin_ = MODELS_DIR / "yolo11n_416.ncnn.bin"
    if not param.exists() or not bin_.exists():
        print(
            f"Model files missing in {MODELS_DIR}. "
            "Run scripts/export_yolo_ncnn.py on your laptop first.",
            file=sys.stderr,
        )
        return 2

    detector = YoloPhoneDetector(
        param_path=str(param),
        bin_path=str(bin_),
        input_size=args.input_size,
    )

    # Synthetic noise frames — more realistic than zeros for cache/branch behavior
    rng = np.random.default_rng(42)
    frames = [
        rng.integers(0, 256, (args.frame_h, args.frame_w, 3), dtype=np.uint8)
        for _ in range(args.warmup + args.iterations)
    ]

    for i in range(args.warmup):
        detector.detect(frames[i])

    samples_ms: list[float] = []
    for i in range(args.warmup, args.warmup + args.iterations):
        t0 = time.perf_counter()
        detector.detect(frames[i])
        samples_ms.append((time.perf_counter() - t0) * 1000.0)

    samples_ms.sort()
    n = len(samples_ms)
    mean_ms = sum(samples_ms) / n
    p50 = samples_ms[n // 2]
    p95 = samples_ms[min(n - 1, int(n * 0.95))]
    stdev = statistics.stdev(samples_ms) if n > 1 else 0.0

    print(f"YOLO11n NCNN @ {args.input_size}x{args.input_size} — {n} iterations")
    print(f"  mean : {mean_ms:7.2f} ms")
    print(f"  p50  : {p50:7.2f} ms")
    print(f"  p95  : {p95:7.2f} ms")
    print(f"  std  : {stdev:7.2f} ms")
    target = 200.0
    status = "OK" if p95 < target else "SLOW — consider input_size=320"
    print(f"  Pi 5 target p95 < {target} ms → {status}")

    detector.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
