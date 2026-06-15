"""DHT22 temperature+humidity reader via kernel IIO sysfs interface.

The Pi 5 loads dtoverlay=dht11,gpiopin=4 which exposes readings through the
Linux IIO subsystem. This avoids userspace bitbanging timing issues on RP1.
"""

import logging
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_IIO_BASE = Path("/sys/bus/iio/devices")


def _find_iio_device() -> Optional[Path]:
    for dev in sorted(_IIO_BASE.iterdir()):
        if (dev / "in_temp_input").exists() and (dev / "in_humidityrelative_input").exists():
            return dev
    return None


class DHT22:
    def __init__(self, max_retries: int = 5, retry_delay: float = 2.5):
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._device = _find_iio_device()
        if self._device is None:
            logger.warning("DHT22: no IIO device found — check dtoverlay=dht11,gpiopin=4 in config.txt")
        else:
            logger.info(f"DHT22: using {self._device.name}")

    def read(self) -> Optional[dict]:
        if self._device is None:
            return None
        for attempt in range(self._max_retries):
            try:
                temp = int((self._device / "in_temp_input").read_text()) / 1000.0
                hum = int((self._device / "in_humidityrelative_input").read_text()) / 1000.0
                if -40 <= temp <= 80 and 0 <= hum <= 100:
                    return {"temperature": round(temp, 1), "humidity": round(hum, 1)}
                logger.debug(f"DHT22 out-of-range: temp={temp} hum={hum}")
            except OSError as e:
                logger.debug(f"DHT22 attempt {attempt + 1}: {e}")
            if attempt < self._max_retries - 1:
                time.sleep(self._retry_delay)
        logger.warning(f"DHT22: no valid reading after {self._max_retries} attempts")
        return None
