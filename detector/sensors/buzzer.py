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
    "LOW":    {"beeps": 2, "beep_s": 0.35, "gap_s": 0.10},
    "MEDIUM": {"beeps": 3, "beep_s": 0.35, "gap_s": 0.08},
}

# HIGH: solid continuous buzz — no gaps so the internal oscillator
# runs at full resonance the entire time (loudest possible in software)
_HIGH_DURATION = 2.0   # seconds of uninterrupted buzz


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
        """Solid uninterrupted buzz for HIGH — max resonance, loudest possible."""
        self._dev.on()
        time.sleep(_HIGH_DURATION)
        self._dev.off()

    def off(self) -> None:
        self._dev.off()

    def close(self) -> None:
        try:
            self._dev.off()
            self._dev.close()
        except Exception as e:
            logger.warning(f"Buzzer close error: {e}")
