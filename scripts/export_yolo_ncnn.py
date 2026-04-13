#!/usr/bin/env python3
"""Export YOLO11n (COCO pre-trained) to NCNN format for the edge detector.

Run this on your laptop (not on the Raspberry Pi) — it pulls a few
hundred MB of torch+ultralytics wheels that the Pi does not need.

Usage:
    pip install ultralytics
    python scripts/export_yolo_ncnn.py

The script:
  1. Downloads yolo11n.pt if not cached (~5 MB).
  2. Exports to NCNN with imgsz=416, FP32.
  3. Moves the resulting .param/.bin into detector/models/ with the
     canonical filenames expected by detector/config.py.

After it finishes, commit the two files or copy them to the Pi.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = REPO_ROOT / "detector" / "models"
TARGET_PARAM = MODELS_DIR / "yolo11n_416.ncnn.param"
TARGET_BIN = MODELS_DIR / "yolo11n_416.ncnn.bin"


def main() -> int:
    try:
        from ultralytics import YOLO
    except ImportError:
        print("ultralytics is not installed. Run: pip install ultralytics", file=sys.stderr)
        return 1

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading yolo11n.pt (downloads on first run)...")
    model = YOLO("yolo11n.pt")

    print("Exporting to NCNN with imgsz=416, FP32...")
    export_path = model.export(format="ncnn", imgsz=416, half=False)
    export_dir = Path(export_path)

    src_param = export_dir / "model.ncnn.param"
    src_bin = export_dir / "model.ncnn.bin"
    if not src_param.exists() or not src_bin.exists():
        print(f"Expected output not found in {export_dir}", file=sys.stderr)
        return 2

    shutil.copyfile(src_param, TARGET_PARAM)
    shutil.copyfile(src_bin, TARGET_BIN)

    print(f"Wrote {TARGET_PARAM} ({TARGET_PARAM.stat().st_size:,} bytes)")
    print(f"Wrote {TARGET_BIN} ({TARGET_BIN.stat().st_size:,} bytes)")
    print("Done. Commit the two files or scp them to the Pi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
