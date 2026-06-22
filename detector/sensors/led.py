"""Red LED indicator driver for Raspberry Pi 5.

LED on GPIO23 with 220-330Ω series resistor: HIGH = on.
Severity patterns: LOW=1 blink, MEDIUM=2 blinks, HIGH=5 blinks.
"""

import logging
import time

logger = logging.getLogger(__name__)

_PATTERNS = {
    "LOW":    {"blinks": 1, "on_s": 0.20, "off_s": 0.20},
    "MEDIUM": {"blinks": 2, "on_s": 0.20, "off_s": 0.20},
    "HIGH":   {"blinks": 5, "on_s": 0.15, "off_s": 0.10},
}


class LED:
    def __init__(self, pin: int = 23):
        from gpiozero import LED as _LED
        from gpiozero.pins.lgpio import LGPIOFactory
        from gpiozero import Device
        Device.pin_factory = LGPIOFactory()
        self._dev = _LED(pin)
        logger.info(f"LED: ready on GPIO{pin}")

    def blink(self, severity: str) -> None:
        pat = _PATTERNS.get(severity)
        if pat is None:
            logger.warning(f"LED: unknown severity '{severity}'")
            return
        for i in range(pat["blinks"]):
            self._dev.on()
            time.sleep(pat["on_s"])
            self._dev.off()
            if i < pat["blinks"] - 1:
                time.sleep(pat["off_s"])

    def off(self) -> None:
        self._dev.off()

    def close(self) -> None:
        try:
            self._dev.off()
            self._dev.close()
        except Exception as e:
            logger.warning(f"LED close error: {e}")
