"""YOLO11n + NCNN object detector for cell phones.

Runs inference off the main capture thread so the 30 FPS MediaPipe
pipeline is not blocked by YOLO's ~150 ms/frame on Pi 5 CPU. The worker
consumes frames from a size-1 queue (drop-oldest) and exposes the most
recent bbox through `get_latest()`, which invalidates stale results
older than `stale_max_age_s` seconds.

The `ncnn` package is imported lazily: if it is not installed,
`create_yolo_worker()` returns None and the engine falls back to
MediaPipe-only detection. This keeps the detector runnable on dev
machines without forcing the ncnn install.
"""

import logging
import queue
import threading
import time
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

try:
    import ncnn  # type: ignore
except ImportError:
    ncnn = None


@dataclass(frozen=True)
class PhoneBBox:
    """Detected phone in normalized [0, 1] frame coordinates."""

    x1: float
    y1: float
    x2: float
    y2: float
    conf: float
    ts_monotonic: float

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) * 0.5, (self.y1 + self.y2) * 0.5)

    @property
    def area(self) -> float:
        return max(0.0, self.x2 - self.x1) * max(0.0, self.y2 - self.y1)


class YoloPhoneDetector:
    """Raw YOLO11n inference wrapper over ncnn.Net.

    One instance per process. `detect()` is thread-safe only when called
    from a single thread (the YoloWorker). The internal ncnn.Net is
    otherwise not re-entrant.
    """

    def __init__(
        self,
        param_path: str,
        bin_path: str,
        conf: float = 0.35,
        iou: float = 0.45,
        input_size: int = 416,
        num_threads: int = 4,
        target_class_id: int = 67,  # COCO "cell phone"
        min_box_area: float = 0.003,   # fraction of frame, filter tiny spurious boxes
        max_box_area: float = 0.6,     # filter absurdly large boxes
    ):
        if ncnn is None:
            raise ImportError("ncnn package is not installed")

        self._conf = conf
        self._iou = iou
        self._input_size = input_size
        self._target_class_id = target_class_id
        self._min_box_area = min_box_area
        self._max_box_area = max_box_area

        self._net = ncnn.Net()
        self._net.opt.use_vulkan_compute = False
        self._net.opt.num_threads = num_threads
        self._net.load_param(param_path)
        self._net.load_model(bin_path)

        # Warmup: first inference is 500-1000 ms slower on Pi (weights load,
        # memory allocator warmup, etc). Do it up front so the live loop is clean.
        try:
            dummy = np.zeros((input_size, input_size, 3), dtype=np.uint8)
            self.detect(dummy)
        except Exception:
            pass

    def detect(self, frame_bgr: np.ndarray) -> list[PhoneBBox]:
        """Run one forward pass and return bboxes for the target class."""
        h0, w0 = frame_bgr.shape[:2]
        img, scale, pad_x, pad_y = self._letterbox(frame_bgr, self._input_size)

        mat_in = ncnn.Mat.from_pixels(
            img, ncnn.Mat.PixelType.PIXEL_BGR2RGB, img.shape[1], img.shape[0]
        )
        mat_in.substract_mean_normalize([0.0, 0.0, 0.0], [1 / 255.0, 1 / 255.0, 1 / 255.0])

        ex = self._net.create_extractor()
        ex.input("in0", mat_in)
        _, mat_out = ex.extract("out0")

        return self._postprocess(mat_out, scale, pad_x, pad_y, w0, h0)

    @staticmethod
    def _letterbox(
        img: np.ndarray, new_size: int
    ) -> tuple[np.ndarray, float, int, int]:
        h, w = img.shape[:2]
        scale = min(new_size / h, new_size / w)
        nh, nw = int(round(h * scale)), int(round(w * scale))
        resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
        canvas = np.full((new_size, new_size, 3), 114, dtype=np.uint8)
        pad_x = (new_size - nw) // 2
        pad_y = (new_size - nh) // 2
        canvas[pad_y:pad_y + nh, pad_x:pad_x + nw] = resized
        return canvas, scale, pad_x, pad_y

    def _postprocess(
        self,
        mat_out,
        scale: float,
        pad_x: int,
        pad_y: int,
        frame_w: int,
        frame_h: int,
    ) -> list[PhoneBBox]:
        """Decode YOLO11 output, filter target class, NMS, normalize."""
        arr = np.array(mat_out)

        # YOLO11 ncnn export typically yields shape (84, N) where
        # rows 0..3 are cx,cy,w,h (absolute in input_size space) and
        # rows 4..83 are per-class scores (sigmoid already applied).
        # Older or transposed exports may give (N, 84); handle both.
        if arr.ndim == 3:
            arr = arr[0]
        if arr.shape[0] != 84 and arr.shape[1] == 84:
            arr = arr.T
        if arr.shape[0] < 5:
            return []

        boxes_cxcywh = arr[0:4, :]
        class_scores = arr[4:, :]

        target_row = self._target_class_id
        if target_row >= class_scores.shape[0]:
            return []

        confs = class_scores[target_row, :]
        keep = confs >= self._conf
        if not np.any(keep):
            return []

        cx = boxes_cxcywh[0, keep]
        cy = boxes_cxcywh[1, keep]
        bw = boxes_cxcywh[2, keep]
        bh = boxes_cxcywh[3, keep]
        kept_conf = confs[keep]

        # cxcywh -> xyxy (in letterbox input_size coordinates)
        x1 = cx - bw * 0.5
        y1 = cy - bh * 0.5

        # NMS expects [x, y, w, h] in int-ish pixel units
        boxes_for_nms = np.stack([x1, y1, bw, bh], axis=1).astype(np.float32)
        idxs = cv2.dnn.NMSBoxes(
            boxes_for_nms.tolist(), kept_conf.tolist(), self._conf, self._iou
        )
        if idxs is None or len(idxs) == 0:
            return []
        idxs = np.array(idxs).flatten()

        now = time.monotonic()
        results: list[PhoneBBox] = []
        for i in idxs:
            lx1 = float(x1[i]) - pad_x
            ly1 = float(y1[i]) - pad_y
            lx2 = lx1 + float(bw[i])
            ly2 = ly1 + float(bh[i])

            # undo letterbox scale -> original frame pixels
            fx1 = lx1 / scale
            fy1 = ly1 / scale
            fx2 = lx2 / scale
            fy2 = ly2 / scale

            # normalize to [0, 1] and clamp
            nx1 = max(0.0, min(1.0, fx1 / frame_w))
            ny1 = max(0.0, min(1.0, fy1 / frame_h))
            nx2 = max(0.0, min(1.0, fx2 / frame_w))
            ny2 = max(0.0, min(1.0, fy2 / frame_h))
            if nx2 <= nx1 or ny2 <= ny1:
                continue

            # Reject boxes with implausible area (spurious tiny detections or
            # absurdly large ones that almost never correspond to a real phone
            # in a driver's hand). The phone in hand normally covers 1%-30% of
            # the frame at the usage distance.
            area = (nx2 - nx1) * (ny2 - ny1)
            if area < self._min_box_area or area > self._max_box_area:
                continue

            results.append(
                PhoneBBox(
                    x1=nx1, y1=ny1, x2=nx2, y2=ny2,
                    conf=float(kept_conf[i]), ts_monotonic=now,
                )
            )
        return results

    def close(self):
        # ncnn.Net releases memory when garbage-collected; explicit clear
        # avoids keeping model weights alive on long-running processes.
        try:
            self._net.clear()
        except Exception:
            pass


class YoloWorker:
    """Background thread that runs YoloPhoneDetector off the main loop.

    The main loop calls submit(frame, ts) every capture frame. The worker
    thread drains the size-1 queue (drop-oldest) and stores the best
    bbox from the latest detect() call. get_latest() returns it only if
    the source frame is younger than stale_max_age_s.
    """

    def __init__(self, detector: YoloPhoneDetector, stale_max_age_s: float = 0.5):
        self._detector = detector
        self._stale_max_age_s = stale_max_age_s
        self._q: queue.Queue = queue.Queue(maxsize=1)
        self._latest: Optional[PhoneBBox] = None
        self._latest_lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._run, name="yolo-worker", daemon=True
        )

    def start(self):
        self._thread.start()

    def submit(self, frame_bgr: np.ndarray, ts: float):
        """Offer a frame for inference. Drops the oldest if queue is full.

        The copy is critical: cv2.VideoCapture reuses its internal buffer and
        MediaPipe mutates the frame in-place on the main thread. Without it,
        the worker can race on a half-overwritten buffer.
        """
        snapshot = frame_bgr.copy()
        try:
            self._q.put_nowait((snapshot, ts))
        except queue.Full:
            try:
                self._q.get_nowait()
            except queue.Empty:
                pass
            try:
                self._q.put_nowait((snapshot, ts))
            except queue.Full:
                pass

    def get_latest(self) -> Optional[PhoneBBox]:
        with self._latest_lock:
            bbox = self._latest
        if bbox is None:
            return None
        if time.monotonic() - bbox.ts_monotonic > self._stale_max_age_s:
            return None
        return bbox

    def stop(self, timeout: float = 2.0):
        self._stop.set()
        self._thread.join(timeout=timeout)
        self._detector.close()

    def _run(self):
        while not self._stop.is_set():
            try:
                frame, _ts = self._q.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                bboxes = self._detector.detect(frame)
            except Exception as exc:
                logger.warning("YOLO detect() failed: %s", exc)
                continue
            best = max(bboxes, key=lambda b: b.conf, default=None)
            with self._latest_lock:
                self._latest = best


def create_yolo_worker(cfg: dict) -> Optional[YoloWorker]:
    """Factory returning a started worker, or None if disabled/unavailable."""
    if not cfg.get("yolo_enabled", False):
        logger.info("YOLO worker disabled (yolo_enabled=false)")
        return None
    if ncnn is None:
        logger.warning(
            "yolo_enabled=true but 'ncnn' package not installed; skipping YOLO"
        )
        return None

    import os
    param = cfg["yolo_param_path"]
    bin_ = cfg["yolo_bin_path"]
    if not os.path.exists(param) or not os.path.exists(bin_):
        logger.warning(
            "YOLO model files missing (%s / %s); skipping YOLO", param, bin_
        )
        return None

    try:
        detector = YoloPhoneDetector(
            param_path=param,
            bin_path=bin_,
            conf=cfg["yolo_confidence"],
            iou=cfg["yolo_iou"],
            input_size=cfg["yolo_input_size"],
            num_threads=cfg["yolo_num_threads"],
            min_box_area=cfg.get("yolo_min_box_area", 0.003),
            max_box_area=cfg.get("yolo_max_box_area", 0.6),
        )
    except Exception as exc:
        logger.warning("Failed to load YOLO model: %s", exc)
        return None

    worker = YoloWorker(detector, stale_max_age_s=cfg["yolo_stale_max_age_s"])
    return worker
