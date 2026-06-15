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

    def current_speed_kmh(self) -> Optional[float]:
        """Return vehicle speed in km/h without doing a full sensor read. Non-blocking."""
        return None

    def close(self) -> None:
        pass


class MockSensor(SensorInterface):
    """Simulated sensor with realistic gradual drift."""

    def __init__(self):
        self._temp = 24.0
        self._humidity = 55.0
        self._co2 = 450.0
        self._lat = -34.6037
        self._lon = -58.3816
        self._speed = 60.0  # start as if moving

    def current_speed_kmh(self) -> Optional[float]:
        return round(self._speed, 1)

    def read(self) -> Optional[dict]:
        self._temp = max(15.0, min(40.0, self._temp + random.uniform(-0.3, 0.3)))
        self._humidity = max(20.0, min(90.0, self._humidity + random.uniform(-1.0, 1.0)))
        self._co2 = max(350.0, min(2000.0, self._co2 + random.uniform(-10.0, 10.0)))
        self._speed = max(0.0, min(130.0, self._speed + random.uniform(-2.0, 2.0)))
        return {
            "temperature": round(self._temp, 1),
            "humidity": round(self._humidity, 1),
            "co2": round(self._co2, 0),
            "gps_lat": round(self._lat + random.uniform(-0.0001, 0.0001), 6),
            "gps_lon": round(self._lon + random.uniform(-0.0001, 0.0001), 6),
            "gps_speed_kmh": round(self._speed, 1),
            "gps_moving": self._speed >= 5.0,
            "gps_fix": True,
            "gps_utc": None,
        }


class PiSensor(SensorInterface):
    """Real sensor stack for Raspberry Pi 5.

    - DHT22 via kernel IIO sysfs (dtoverlay=dht11,gpiopin=4)
    - MH-Z19C CO2 via UART1 (/dev/ttyAMA1, uart1-pi5 overlay)
    - GPS GY-NEO6MV2 via UART0 (/dev/ttyAMA0, uart0-pi5 overlay) — background thread
    """

    def __init__(self, config: dict):
        from sensors.dht22 import DHT22
        from sensors.mhz19c import MHZ19C
        from sensors.gps import GPS
        self._dht = DHT22()
        self._co2 = MHZ19C(port=config.get("co2_port", "/dev/ttyAMA1"))
        self._gps = GPS(port=config.get("gps_port", "/dev/ttyAMA0"))
        logger.info("PiSensor ready (DHT22 IIO + MH-Z19C UART1 + GPS UART0)")

    def current_speed_kmh(self) -> Optional[float]:
        return self._gps.get_fix().speed_kmh

    def read(self) -> Optional[dict]:
        result: dict = {}

        dht = self._dht.read()
        if dht:
            result["temperature"] = dht["temperature"]
            result["humidity"] = dht["humidity"]

        result["co2"] = self._co2.read()

        fix = self._gps.get_fix()
        result["gps_lat"] = fix.latitude
        result["gps_lon"] = fix.longitude
        result["gps_speed_kmh"] = fix.speed_kmh
        result["gps_moving"] = fix.is_moving
        result["gps_fix"] = fix.has_fix
        result["gps_utc"] = fix.utc_time

        return result

    def close(self) -> None:
        try:
            self._co2.close()
            self._gps.close()
        except Exception as e:
            logger.warning(f"PiSensor close error: {e}")


def create_sensor(config: dict) -> SensorInterface:
    if config.get("mock_sensors", True):
        logger.info("Using MockSensor (development mode)")
        return MockSensor()
    logger.info("Using PiSensor (hardware mode)")
    return PiSensor(config)
