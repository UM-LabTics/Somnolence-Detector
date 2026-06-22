"""Passive piezo buzzer driver for Raspberry Pi 5.

Keyestudio passive buzzer on GPIO18, driven via PWMOutputDevice.
Duty cycle 0.5 (square wave) at the target frequency gives maximum volume.

Severity patterns:
  LOW    — 800 Hz,  2 short beeps
  MEDIUM — 1500 Hz, 3 beeps
  HIGH   — 2800 Hz, continuous 1.5 s tone (near piezo resonance)
"""

import logging
import time

logger = logging.getLogger(__name__)

_DUTY = 0.5  # square wave — loudest for passive piezo

_PATTERNS = {
    "LOW":    {"freq": 800,  "beeps": 2, "beep_s": 0.20, "gap_s": 0.10},
    "MEDIUM": {"freq": 1500, "beeps": 3, "beep_s": 0.18, "gap_s": 0.08},
    "HIGH":   {"freq": 2800, "beeps": 1, "beep_s": 1.50, "gap_s": 0.00},
}


class Buzzer:
    def __init__(self, pin: int = 18):
        from gpiozero import PWMOutputDevice
        from gpiozero.pins.lgpio import LGPIOFactory
        from gpiozero import Device
        Device.pin_factory = LGPIOFactory()
        self._dev = PWMOutputDevice(pin, frequency=1000, initial_value=0)
        logger.info(f"Buzzer: ready on GPIO{pin} (PWM passive)")

    def beep(self, severity: str) -> None:
        pat = _PATTERNS.get(severity)
        if pat is None:
            logger.warning(f"Buzzer: unknown severity '{severity}'")
            return
        self._dev.frequency = pat["freq"]
        for i in range(pat["beeps"]):
            self._dev.value = _DUTY
            time.sleep(pat["beep_s"])
            self._dev.value = 0
            if i < pat["beeps"] - 1:
                time.sleep(pat["gap_s"])

    def off(self) -> None:
        self._dev.value = 0

    def close(self) -> None:
        try:
            self._dev.value = 0
            self._dev.close()
        except Exception as e:
            logger.warning(f"Buzzer close error: {e}")
