"""GPS reader for GY-NEO6MV2 (u-blox NEO-6M) over UART0 (/dev/ttyAMA0).

Runs a daemon thread that continuously parses NMEA sentences and caches the
latest fix. get_fix() is non-blocking — safe to call from the main loop.

Provides position (lat/lon), UTC timestamp, speed in km/h and is_moving flag
(speed > 5 km/h). In indoor conditions the module sends valid NMEA frames
but without a satellite fix — this is reported as has_fix=False.
"""

import logging
import threading
import time
from dataclasses import dataclass
from typing import Optional

import pynmea2
import serial

logger = logging.getLogger(__name__)

_MOVING_THRESHOLD_KMH = 5.0
_KNOTS_TO_KMH = 1.852


@dataclass
class GPSFix:
    has_fix: bool
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    speed_kmh: Optional[float] = None
    is_moving: bool = False
    utc_time: Optional[str] = None


class GPS:
    def __init__(self, port: str = "/dev/ttyAMA0", baud: int = 9600):
        self._lock = threading.Lock()
        self._latest: GPSFix = GPSFix(has_fix=False)
        self._stop = threading.Event()
        self._ser: Optional[serial.Serial] = None

        try:
            self._ser = serial.Serial(port, baud, timeout=1)
            logger.info(f"GPS: opened {port}")
        except Exception as e:
            logger.error(f"GPS: failed to open {port}: {e}")
            return

        t = threading.Thread(target=self._reader_loop, daemon=True, name="gps-reader")
        t.start()

    def _reader_loop(self) -> None:
        while not self._stop.is_set():
            try:
                raw = self._ser.readline().decode("ascii", errors="replace").strip()
                if not raw.startswith("$"):
                    continue
                sentence_type = raw[1:6]
                if sentence_type not in ("GPRMC", "GNRMC", "GPGGA", "GNGGA"):
                    continue
                msg = pynmea2.parse(raw)
                self._ingest(msg)
            except pynmea2.ParseError:
                pass
            except Exception as e:
                if not self._stop.is_set():
                    logger.debug(f"GPS reader: {e}")
                    time.sleep(1)

    def _ingest(self, msg) -> None:
        has_fix = False
        lat = lon = speed_kmh = utc_time = None

        if hasattr(msg, "status"):
            has_fix = msg.status == "A"
        elif hasattr(msg, "gps_qual"):
            has_fix = int(msg.gps_qual or 0) > 0

        if has_fix:
            try:
                lat = round(float(msg.latitude), 6)
                lon = round(float(msg.longitude), 6)
            except (ValueError, AttributeError):
                has_fix = False

        if hasattr(msg, "spd_over_grnd") and msg.spd_over_grnd not in (None, ""):
            try:
                speed_kmh = round(float(msg.spd_over_grnd) * _KNOTS_TO_KMH, 1)
            except ValueError:
                pass

        if hasattr(msg, "timestamp") and msg.timestamp:
            utc_time = str(msg.timestamp)

        with self._lock:
            self._latest = GPSFix(
                has_fix=has_fix,
                latitude=lat,
                longitude=lon,
                speed_kmh=speed_kmh,
                is_moving=(speed_kmh or 0) >= _MOVING_THRESHOLD_KMH,
                utc_time=utc_time,
            )

    def get_fix(self) -> GPSFix:
        """Return the latest cached GPS fix. Non-blocking."""
        with self._lock:
            return self._latest

    def close(self) -> None:
        self._stop.set()
        if self._ser:
            try:
                self._ser.close()
            except Exception:
                pass
