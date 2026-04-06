"""Environmental sensor interface with mock and hardware implementations."""

import logging
import random
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class SensorInterface(ABC):
    @abstractmethod
    def read(self) -> Optional[dict]:
        """Read environmental values. Returns {temperature, humidity, co2} or None."""
        ...

    def close(self) -> None:
        pass


class MockSensor(SensorInterface):
    """Simulated sensor with realistic gradual drift."""

    def __init__(self):
        self._temp = 24.0
        self._humidity = 55.0
        self._co2 = 450.0

    def read(self) -> Optional[dict]:
        self._temp = max(15.0, min(40.0, self._temp + random.uniform(-0.3, 0.3)))
        self._humidity = max(20.0, min(90.0, self._humidity + random.uniform(-1.0, 1.0)))
        self._co2 = max(350.0, min(2000.0, self._co2 + random.uniform(-10.0, 10.0)))

        return {
            "temperature": round(self._temp, 1),
            "humidity": round(self._humidity, 1),
            "co2": round(self._co2, 0),
        }


class PiSensor(SensorInterface):
    """Real sensor for Raspberry Pi. Stub — requires hardware libraries."""

    def __init__(self, config: dict):
        logger.warning(
            "PiSensor: hardware libraries not installed. "
            "Install adafruit-circuitpython-dht and mh-z19 on Raspberry Pi."
        )

    def read(self) -> Optional[dict]:
        # TODO: Implement with BME280 (I2C) and MH-Z19C (UART)
        return None

    def close(self) -> None:
        pass


def create_sensor(config: dict) -> SensorInterface:
    if config.get("mock_sensors", True):
        logger.info("Using MockSensor (development mode)")
        return MockSensor()
    logger.info("Using PiSensor (hardware mode)")
    return PiSensor(config)
