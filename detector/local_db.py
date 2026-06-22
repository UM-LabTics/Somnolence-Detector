"""Local SQLite persistence for offline-first store-and-forward."""

import json
import logging
import sqlite3
import threading
from typing import Optional

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    value REAL NOT NULL,
    threshold REAL NOT NULL,
    metadata TEXT,
    timestamp TEXT NOT NULL,
    synced INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS environmental_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    temperature REAL,
    humidity REAL,
    co2 REAL,
    gps_lat REAL,
    gps_lon REAL,
    gps_speed_kmh REAL,
    gps_moving INTEGER,
    gps_fix INTEGER,
    timestamp TEXT NOT NULL,
    synced INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_alerts_pending
    ON alerts(synced) WHERE synced = 0;

CREATE INDEX IF NOT EXISTS idx_env_pending
    ON environmental_readings(synced) WHERE synced = 0;
"""

# Columns added after initial schema — applied via ALTER TABLE if missing.
_ENV_MIGRATIONS = [
    "ALTER TABLE environmental_readings ADD COLUMN gps_lat REAL",
    "ALTER TABLE environmental_readings ADD COLUMN gps_lon REAL",
    "ALTER TABLE environmental_readings ADD COLUMN gps_speed_kmh REAL",
    "ALTER TABLE environmental_readings ADD COLUMN gps_moving INTEGER",
    "ALTER TABLE environmental_readings ADD COLUMN gps_fix INTEGER",
]


class LocalDB:
    """Thread-safe SQLite wrapper for local persistence."""

    def __init__(self, db_path: str):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(
            db_path, check_same_thread=False, isolation_level=None
        )
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._migrate()
        logger.info(f"LocalDB initialized: {db_path}")

    def _migrate(self) -> None:
        for stmt in _ENV_MIGRATIONS:
            try:
                self._conn.execute(stmt)
            except sqlite3.OperationalError:
                pass  # column already exists

    def save_alert(
        self,
        alert_type: str,
        severity: str,
        value: float,
        threshold: float,
        metadata: Optional[dict],
        timestamp: str,
    ) -> int:
        meta_json = json.dumps(metadata) if metadata else None
        with self._lock:
            cursor = self._conn.execute(
                "INSERT INTO alerts (alert_type, severity, value, threshold, metadata, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (alert_type, severity, value, threshold, meta_json, timestamp),
            )
            return cursor.lastrowid

    def save_environmental(
        self,
        temperature: Optional[float],
        humidity: Optional[float],
        co2: Optional[float],
        timestamp: str,
        gps_lat: Optional[float] = None,
        gps_lon: Optional[float] = None,
        gps_speed_kmh: Optional[float] = None,
        gps_moving: Optional[bool] = None,
        gps_fix: Optional[bool] = None,
    ) -> int:
        with self._lock:
            cursor = self._conn.execute(
                "INSERT INTO environmental_readings "
                "(temperature, humidity, co2, gps_lat, gps_lon, gps_speed_kmh, gps_moving, gps_fix, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    temperature, humidity, co2,
                    gps_lat, gps_lon, gps_speed_kmh,
                    int(gps_moving) if gps_moving is not None else None,
                    int(gps_fix) if gps_fix is not None else None,
                    timestamp,
                ),
            )
            return cursor.lastrowid

    def get_pending_alerts(self, limit: int = 50) -> list[dict]:
        with self._lock:
            cursor = self._conn.execute(
                "SELECT id, alert_type, severity, value, threshold, metadata, timestamp "
                "FROM alerts WHERE synced = 0 ORDER BY id ASC LIMIT ?",
                (limit,),
            )
            rows = cursor.fetchall()
        return [
            {
                "id": r[0],
                "alert_type": r[1],
                "severity": r[2],
                "value": r[3],
                "threshold": r[4],
                "metadata": json.loads(r[5]) if r[5] else None,
                "timestamp": r[6],
            }
            for r in rows
        ]

    def get_pending_environmental(self, limit: int = 50) -> list[dict]:
        with self._lock:
            cursor = self._conn.execute(
                "SELECT id, temperature, humidity, co2, "
                "gps_lat, gps_lon, gps_speed_kmh, gps_moving, gps_fix, timestamp "
                "FROM environmental_readings WHERE synced = 0 ORDER BY id ASC LIMIT ?",
                (limit,),
            )
            rows = cursor.fetchall()
        return [
            {
                "id": r[0],
                "temperature": r[1],
                "humidity": r[2],
                "co2": r[3],
                "gps_lat": r[4],
                "gps_lon": r[5],
                "gps_speed_kmh": r[6],
                "gps_moving": bool(r[7]) if r[7] is not None else None,
                "gps_fix": bool(r[8]) if r[8] is not None else None,
                "timestamp": r[9],
            }
            for r in rows
        ]

    def mark_alert_synced(self, row_id: int) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE alerts SET synced = 1 WHERE id = ?", (row_id,)
            )

    def mark_environmental_synced(self, row_id: int) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE environmental_readings SET synced = 1 WHERE id = ?",
                (row_id,),
            )

    def pending_count(self) -> dict:
        with self._lock:
            alerts = self._conn.execute(
                "SELECT COUNT(*) FROM alerts WHERE synced = 0"
            ).fetchone()[0]
            env = self._conn.execute(
                "SELECT COUNT(*) FROM environmental_readings WHERE synced = 0"
            ).fetchone()[0]
        return {"alerts": alerts, "environmental": env}

    def close(self) -> None:
        with self._lock:
            self._conn.close()
        logger.info("LocalDB closed")
