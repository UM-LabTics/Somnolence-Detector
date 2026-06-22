"""Alert actuator interface (buzzer + LED) with mock and hardware implementations."""

import logging
import threading
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
    """Real actuator for Raspberry Pi 5.

    Delegates to sensors.buzzer.Buzzer (GPIO18, active buzzer) and
    sensors.led.LED (GPIO23). Patterns: LOW=1, MEDIUM=2, HIGH=5 beeps/blinks.
    """

    def __init__(self, config: dict):
        from sensors.buzzer import Buzzer
        from sensors.led import LED
        self._buzzer = Buzzer(pin=int(config.get("buzzer_pin", 18)))
        self._led = LED(pin=int(config.get("led_pin", 23)))
        logger.info(
            f"PiActuator ready (buzzer=GPIO{config.get('buzzer_pin', 18)}, "
            f"led=GPIO{config.get('led_pin', 23)})"
        )

    def activate(self, severity: str) -> None:
        # Run in background so buzzer/LED sleep() doesn't block the detection loop
        t = threading.Thread(target=self._fire, args=(severity,), daemon=True)
        t.start()

    def _fire(self, severity: str) -> None:
        try:
            self._buzzer.beep(severity)
            self._led.blink(severity)
        except Exception as e:
            logger.error(f"PiActuator _fire error ({severity}): {e}")

    def deactivate(self) -> None:
        self._buzzer.off()
        self._led.off()

    def close(self) -> None:
        try:
            self._buzzer.close()
            self._led.close()
        except Exception as e:
            logger.warning(f"PiActuator close error: {e}")


def create_actuator(config: dict) -> ActuatorInterface:
    if config.get("mock_actuators", True):
        logger.info("Using MockActuator (development mode)")
        return MockActuator()
    logger.info("Using PiActuator (hardware mode)")
    return PiActuator(config)
