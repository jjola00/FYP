import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import config


def _get_conn() -> sqlite3.Connection:
    config.DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS challenges (
                id TEXT PRIMARY KEY,
                seed TEXT NOT NULL,
                points_json TEXT NOT NULL,
                path_length REAL NOT NULL,
                ttl_ms INTEGER NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS attempt_logs (
                attempt_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                challenge_id TEXT NOT NULL,
                pointer_type TEXT NOT NULL,
                os_family TEXT,
                browser_family TEXT,
                path_seed TEXT NOT NULL,
                path_length_px REAL NOT NULL,
                tolerance_px REAL NOT NULL,
                ttl_ms INTEGER NOT NULL,
                started_at REAL NOT NULL,
                ended_at REAL NOT NULL,
                duration_ms REAL NOT NULL,
                outcome_reason TEXT NOT NULL,
                coverage_ratio REAL NOT NULL,
                mean_speed REAL,
                max_speed REAL,
                pause_count INTEGER,
                pause_durations_json TEXT,
                deviation_stats_json TEXT,
                trajectory_json TEXT,
                created_at REAL NOT NULL
            )
            """
        )
        conn.commit()


def save_challenge(
    challenge_id: str,
    seed: str,
    points: List[List[float]],
    path_length: float,
    ttl_ms: int,
) -> None:
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO challenges (id, seed, points_json, path_length, ttl_ms, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                challenge_id,
                seed,
                json.dumps(points),
                path_length,
                ttl_ms,
                time.time(),
            ),
        )
        conn.commit()


def get_challenge(challenge_id: str) -> Optional[sqlite3.Row]:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM challenges WHERE id = ?", (challenge_id,)
        ).fetchone()
        return row


def save_attempt(log: Dict[str, Any]) -> None:
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO attempt_logs (
                attempt_id,
                session_id,
                challenge_id,
                pointer_type,
                os_family,
                browser_family,
                path_seed,
                path_length_px,
                tolerance_px,
                ttl_ms,
                started_at,
                ended_at,
                duration_ms,
                outcome_reason,
                coverage_ratio,
                mean_speed,
                max_speed,
                pause_count,
                pause_durations_json,
                deviation_stats_json,
                trajectory_json,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                log["attempt_id"],
                log["session_id"],
                log["challenge_id"],
                log["pointer_type"],
                log.get("os_family"),
                log.get("browser_family"),
                log["path_seed"],
                log["path_length_px"],
                log["tolerance_px"],
                log["ttl_ms"],
                log["started_at"],
                log["ended_at"],
                log["duration_ms"],
                log["outcome_reason"],
                log["coverage_ratio"],
                log.get("mean_speed"),
                log.get("max_speed"),
                log.get("pause_count"),
                json.dumps(log.get("pause_durations_ms") or []),
                json.dumps(log.get("deviation_stats") or {}),
                json.dumps(log.get("trajectory") or []),
                time.time(),
            ),
        )
        conn.commit()
