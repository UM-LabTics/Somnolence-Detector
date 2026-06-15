"""MH-Z19C NDIR CO2 sensor driver over UART1 (/dev/ttyAMA1).

GPIO0=TXD1, GPIO1=RXD1 via dtoverlay=uart1-pi5.
ABC (Auto Baseline Calibration) is disabled on init — it assumes daily
outdoor air exposure, which is wrong inside a vehicle cabin.
"""

import logging
import time
from typing import Optional

import serial

logger = logging.getLogger(__name__)

_CMD_READ_CO2    = bytes([0xFF, 0x01, 0x86, 0x00, 0x00, 0x00, 0x00, 0x00, 0x79])
_CMD_DISABLE_ABC = bytes([0xFF, 0x01, 0x79, 0x00, 0x00, 0x00, 0x00, 0x00, 0x86])
_RESPONSE_LEN = 9
_MOVING_THRESHOLD_KMH = 5.0


def _checksum(data: bytes) -> int:
    return (~sum(data[1:8]) + 1) & 0xFF


class MHZ19C:
    def __init__(self, port: str = "/dev/ttyAMA1"):
        self._ser: Optional[serial.Serial] = None
        try:
            self._ser = serial.Serial(
                port, baudrate=9600, bytesize=8, parity="N", stopbits=1, timeout=2
            )
            logger.info(f"MH-Z19C: opened {port}")
            self._disable_abc()
        except Exception as e:
            logger.error(f"MH-Z19C: failed to open {port}: {e}")

    def _disable_abc(self) -> None:
        try:
            self._ser.write(_CMD_DISABLE_ABC)
            time.sleep(0.1)
            logger.info("MH-Z19C: ABC auto-calibration disabled")
        except Exception as e:
            logger.warning(f"MH-Z19C: could not disable ABC: {e}")

    def read(self) -> Optional[float]:
        """Return CO2 concentration in ppm, or None on error."""
        if self._ser is None:
            return None
        try:
            self._ser.reset_input_buffer()
            self._ser.write(_CMD_READ_CO2)
            resp = self._ser.read(_RESPONSE_LEN)
            if len(resp) < _RESPONSE_LEN:
                logger.warning(f"MH-Z19C: short response ({len(resp)}/{_RESPONSE_LEN} bytes)")
                return None
            if resp[0] != 0xFF or resp[1] != 0x86:
                logger.warning(f"MH-Z19C: invalid header {resp[:2].hex()}")
                return None
            if _checksum(resp) != resp[8]:
                logger.warning("MH-Z19C: checksum mismatch")
                return None
            ppm = resp[2] * 256 + resp[3]
            if not 400 <= ppm <= 5000:
                logger.warning(f"MH-Z19C: ppm={ppm} out of range (sensor may still be warming up)")
                return None
            return float(ppm)
        except Exception as e:
            logger.error(f"MH-Z19C read error: {e}")
            return None

    def close(self) -> None:
        if self._ser:
            try:
                self._ser.close()
            except Exception:
                pass
            self._ser = None
