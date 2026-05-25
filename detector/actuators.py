"""Alert actuator interface (buzzer + LED) with mock and hardware implementations."""

import logging
import time
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class ActuatorInterface(ABC):
    @abstractmethod
    def activate(self, severity: str) -> None:
        """Trigger alert proportional to severity (LOW/MEDIUM/HIGH)."""
        ...

    @abstractmethod
    def deactivate(self) -> None:
        """Stop all actuator output."""
        ...

    def close(self) -> None:
        pass


class MockActuator(ActuatorInterface):
    """Simulated actuator that logs to console."""

    _SYMBOLS = {"LOW": "[!]", "MEDIUM": "[!!]", "HIGH": "[!!!]"}

    def activate(self, severity: str) -> None:
        symbol = self._SYMBOLS.get(severity, "[?]")
        logger.info(f"MockActuator {symbol} ALERT severity={severity}")

    def deactivate(self) -> None:
        logger.debug("MockActuator deactivated")


class PiActuator(ActuatorInterface):
    """Real actuator for Raspberry Pi 5 using gpiozero + lgpio.

    Buzzer: passive piezo on PWM pin (default GPIO17).
    LED: optional indicator on digital pin (default GPIO27). If the pin is
    not wired, gpiozero still allocates it harmlessly.
    """

    _PATTERNS = {
        "LOW":    {"freq_hz": 800,  "beeps": 1, "beep_s": 0.15, "gap_s": 0.10, "led_blinks": 1, "led_rate_s": 0.20},
        "MEDIUM": {"freq_hz": 1200, "beeps": 2, "beep_s": 0.15, "gap_s": 0.10, "led_blinks": 3, "led_rate_s": 0.12},
        "HIGH":   {"freq_hz": 2000, "beeps": 1, "beep_s": 1.00, "gap_s": 0.00, "led_blinks": 0, "led_rate_s": 0.00},
    }

    def __init__(self, config: dict):
        from gpiozero import PWMOutputDevice, LED  # local import: only on Pi

        self._buzzer_pin = int(config.get("buzzer_pin", 17))
        self._led_pin = config.get("led_pin")  # None = no LED wired yet
        self._duty = float(config.get("buzzer_duty", 0.5))

        self._buzzer = PWMOutputDevice(self._buzzer_pin, frequency=1000, initial_value=0)
        self._led = LED(int(self._led_pin)) if self._led_pin is not None else None
        logger.info(
            f"PiActuator ready (buzzer=GPIO{self._buzzer_pin} PWM, "
            f"led={'GPIO' + str(self._led_pin) if self._led else 'disabled'})"
        )

    def activate(self, severity: str) -> None:
        pat = self._PATTERNS.get(severity)
        if pat is None:
            logger.warning(f"PiActuator: unknown severity '{severity}', skipping")
            return

        if self._led is not None:
            if severity == "HIGH":
                self._led.on()
            else:
                for _ in range(pat["led_blinks"]):
                    self._led.on()
                    time.sleep(pat["led_rate_s"] / 2)
                    self._led.off()
                    time.sleep(pat["led_rate_s"] / 2)

        self._buzzer.frequency = pat["freq_hz"]
        for i in range(pat["beeps"]):
            self._buzzer.value = self._duty
            time.sleep(pat["beep_s"])
            self._buzzer.value = 0
            if i < pat["beeps"] - 1:
                time.sleep(pat["gap_s"])

        if self._led is not None and severity == "HIGH":
            self._led.off()

    def deactivate(self) -> None:
        self._buzzer.value = 0
        if self._led is not None:
            self._led.off()

    def close(self) -> None:
        try:
            self.deactivate()
            self._buzzer.close()
            if self._led is not None:
                self._led.close()
        except Exception as e:
            logger.warning(f"PiActuator close error: {e}")


def create_actuator(config: dict) -> ActuatorInterface:
    if config.get("mock_actuators", True):
        logger.info("Using MockActuator (development mode)")
        return MockActuator()
    logger.info("Using PiActuator (hardware mode)")
    return PiActuator(config)
