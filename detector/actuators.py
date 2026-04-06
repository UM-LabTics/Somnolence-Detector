"""Alert actuator interface (buzzer + LED) with mock and hardware implementations."""

import logging
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
    """Real actuator for Raspberry Pi GPIO. Stub — requires RPi.GPIO."""

    def __init__(self, config: dict):
        logger.warning(
            "PiActuator: GPIO libraries not installed. "
            "Install RPi.GPIO or gpiozero on Raspberry Pi."
        )

    def activate(self, severity: str) -> None:
        # TODO: Implement buzzer + LED patterns by severity
        pass

    def deactivate(self) -> None:
        # TODO: Set all GPIO pins LOW
        pass

    def close(self) -> None:
        self.deactivate()


def create_actuator(config: dict) -> ActuatorInterface:
    if config.get("mock_actuators", True):
        logger.info("Using MockActuator (development mode)")
        return MockActuator()
    logger.info("Using PiActuator (hardware mode)")
    return PiActuator(config)
