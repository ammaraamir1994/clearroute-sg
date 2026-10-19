"""
ClearRoute SG - Historical Persistence & Observation Cache
Stores real-time hourly NEA readings in SQLite for historical analysis,
trend calibration, and offline evaluation.
"""
import os
import sqlite3
import logging
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger("nea_store")
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "nea_history.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pm25_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                region TEXT NOT NULL,
                pm25_1hr REAL NOT NULL,
                psi_24hr REAL,
                recorded_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, region)
            )
        """)
        conn.commit()

def record_observations(timestamp: str, pm25_dict: Dict[str, float], psi_dict: Dict[str, float]):
    """Insert or ignore observations into SQLite."""
    try:
        init_db()
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            for region, pm_val in pm25_dict.items():
                psi_val = psi_dict.get(region)
                cursor.execute("""
                    INSERT OR IGNORE INTO pm25_readings (timestamp, region, pm25_1hr, psi_24hr)
                    VALUES (?, ?, ?, ?)
                """, (timestamp, region.lower(), float(pm_val), float(psi_val) if psi_val is not None else None))
            conn.commit()
    except Exception as e:
        logger.warning(f"Could not write to local sqlite store: {e}")

def get_recent_history(region: str, limit: int = 24) -> List[Dict[str, Any]]:
    """Retrieve historical PM2.5 readings for a given region."""
    try:
        init_db()
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT timestamp, pm25_1hr, psi_24hr, recorded_at
                FROM pm25_readings
                WHERE region = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (region.lower(), limit))
            rows = cursor.fetchall()
            return [dict(r) for r in reversed(rows)]
    except Exception as e:
        logger.warning(f"Could not read from local sqlite store: {e}")
        return []
