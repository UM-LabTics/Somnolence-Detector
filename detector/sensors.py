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
    """Real sensor for Raspberry Pi 5 — DHT11 via adafruit-circuitpython-dht.

    The Pi 5 GPIO is routed through the RP1 chip (PCIe), which introduces
    timing jitter the kernel `dht11` driver cannot tolerate. The userspace
    Adafruit library is more forgiving but still misses many reads, so we
    retry up to `max_retries` times per call with a short cooldown.

    CO2 is not measured (no MH-Z19C sensor wired). Field returned as None.
    """

    def __init__(self, config: dict):
        import adafruit_dht
        import board

        pin_num = int(config.get("dht11_pin", 4))
        pin_obj = getattr(board, f"D{pin_num}")
        self._dht = adafruit_dht.DHT11(pin_obj, use_pulseio=False)
        self._max_retries = int(config.get("dht11_max_retries", 15))
        self._retry_sleep = float(config.get("dht11_retry_sleep_s", 0.5))
        logger.info(
            f"PiSensor ready (DHT11 on GPIO{pin_num}, max_retries={self._max_retries})"
        )

    def read(self) -> Optional[dict]:
        import time

        last_err = None
        for attempt in range(1, self._max_retries + 1):
            try:
                t = self._dht.temperature
                h = self._dht.humidity
                if t is not None and h is not None:
                    if attempt > 1:
                        logger.debug(f"DHT11 read OK after {attempt} attempts")
                    return {
                        "temperature": round(float(t), 1),
                        "humidity": round(float(h), 1),
                        "co2": None,
                    }
            except RuntimeError as e:
                last_err = str(e)
            time.sleep(self._retry_sleep)

        logger.warning(
            f"DHT11 read failed after {self._max_retries} attempts (last error: {last_err})"
        )
        return None

    def close(self) -> None:
        try:
            self._dht.exit()
        except Exception as e:
            logger.warning(f"PiSensor close error: {e}")


def create_sensor(config: dict) -> SensorInterface:
    if config.get("mock_sensors", True):
        logger.info("Using MockSensor (development mode)")
        return MockSensor()
    logger.info("Using PiSensor (hardware mode)")
    return PiSensor(config)
