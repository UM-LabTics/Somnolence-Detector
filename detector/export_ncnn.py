"""Export YOLOv8n to NCNN format for faster CPU inference.

Run once before starting the detector:
    python export_ncnn.py

Generates: yolov8n_ncnn_model/ in the current directory.
The detector automatically prefers this over yolov8n.pt if it exists.
"""

from pathlib import Path
from ultralytics import YOLO

MODEL_PT = "yolov8n.pt"
MODEL_NCNN = "yolov8n_ncnn_model"

if Path(MODEL_NCNN).exists():
    print(f"NCNN model already exists at ./{MODEL_NCNN}/ — delete it to re-export.")
else:
    print(f"Exporting {MODEL_PT} → NCNN …")
    model = YOLO(MODEL_PT)
    model.export(format="ncnn")
    print(f"Done. Load with: YOLO('{MODEL_NCNN}')")
