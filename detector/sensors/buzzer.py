"""Active buzzer driver for Raspberry Pi 5.

Keyestudio active buzzer on GPIO18: digital HIGH = on, LOW = off.

Severity patterns (designed for maximum perceived loudness):
  LOW    — 2 short beeps
  MEDIUM — 4 rapid beeps
  HIGH   — continuous rapid alarm (on/off cycle) for ~1.5 s, no silence gaps
"""

import logging
import time

logger = logging.getLogger(__name__)

# LOW / MEDIUM: classic beep pattern with short gaps
_PATTERNS = {
    "LOW":    {"beeps": 2, "beep_s": 0.25, "gap_s": 0.08},
    "MEDIUM": {"beeps": 4, "beep_s": 0.20, "gap_s": 0.06},
}

# HIGH: continuous rapid on/off alarm — no silence, just alternating cycles
_HIGH_CYCLE_ON  = 0.08   # seconds ON per cycle
_HIGH_CYCLE_OFF = 0.04   # seconds OFF per cycle  (brief — keeps buzzer near-continuous)
_HIGH_DURATION  = 1.5    # total alarm duration in seconds


class Buzzer:
    def __init__(self, pin: int = 18):
        from gpiozero import OutputDevice
        from gpiozero.pins.lgpio import LGPIOFactory
        from gpiozero import Device
        Device.pin_factory = LGPIOFactory()
        self._dev = OutputDevice(pin, active_high=True, initial_value=False)
        logger.info(f"Buzzer: ready on GPIO{pin}")

    def beep(self, severity: str) -> None:
        if severity == "HIGH":
            self._alarm()
            return
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

    def _alarm(self) -> None:
        """Rapid on/off cycle for HIGH — sounds like a continuous alarm."""
        deadline = time.monotonic() + _HIGH_DURATION
        while time.monotonic() < deadline:
            self._dev.on()
            time.sleep(_HIGH_CYCLE_ON)
            self._dev.off()
            time.sleep(_HIGH_CYCLE_OFF)

    def off(self) -> None:
        self._dev.off()

    def close(self) -> None:
        try:
            self._dev.off()
            self._dev.close()
        except Exception as e:
            logger.warning(f"Buzzer close error: {e}")
