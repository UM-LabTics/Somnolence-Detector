"""Active buzzer driver for Raspberry Pi 5.

Keyestudio active buzzer on GPIO18: digital HIGH = on, LOW = off.
Severity patterns: LOW=1 beep, MEDIUM=2 beeps, HIGH=5 beeps.
"""

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

_PATTERNS = {
    "LOW":    {"beeps": 1, "beep_s": 0.20, "gap_s": 0.10},
    "MEDIUM": {"beeps": 2, "beep_s": 0.20, "gap_s": 0.10},
    "HIGH":   {"beeps": 5, "beep_s": 0.15, "gap_s": 0.08},
}


class Buzzer:
    def __init__(self, pin: int = 18):
        from gpiozero import OutputDevice
        from gpiozero.pins.lgpio import LGPIOFactory
        from gpiozero import Device
        Device.pin_factory = LGPIOFactory()
        self._dev = OutputDevice(pin, active_high=True, initial_value=False)
        logger.info(f"Buzzer: ready on GPIO{pin}")

    def beep(self, severity: str) -> None:
        pat = _PATTERNS.get(severity)
        if pat is None:
            logger.warning(f"Buzzer: unknown severity '{severity}'")
            return
        for i in range(pat["beeps"]):
            self._dev.on()
            time.sleep(pat["beep_s"])
            self._dev.off()
            if i < pat["beeps"] - 1:
                time.sleep(pat["gap_s"])

    def off(self) -> None:
        self._dev.off()

    def close(self) -> None:
        try:
            self._dev.off()
            self._dev.close()
        except Exception as e:
            logger.warning(f"Buzzer close error: {e}")
