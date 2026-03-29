import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from . import config


# ─── Supabase backup (fire-and-forget) ────────────────────────────────────

def _supabase_insert(table: str, row: Dict[str, Any]) -> None:
    """POST a row to Supabase REST API. Silently skips if not configured."""
    url = config.SUPABASE_URL
    key = config.SUPABASE_SERVICE_KEY
    if not url or not key:
        return
    try:
        httpx.post(
            f"{url}/rest/v1/{table}",
            headers={
                "Authorization": f"Bearer {key}",
                "apikey": key,
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            json=row,
            timeout=5.0,
        )
    except Exception as exc:
        print(f"[supabase] {table} insert failed: {exc}")


def _get_conn() -> sqlite3.Connection:
    config.DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    with _get_conn() as conn:
        # ── Feedback ────────────────────────────────────────────────
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY,
                name TEXT,
                category TEXT NOT NULL,
                device TEXT NOT NULL DEFAULT 'unknown',
                message TEXT NOT NULL,
                image_filenames_json TEXT NOT NULL DEFAULT '[]',
                created_at REAL NOT NULL
            )
            """
        )
        conn.commit()

        # Migration: add device column if missing
        try:
            conn.execute("ALTER TABLE feedback ADD COLUMN device TEXT NOT NULL DEFAULT 'unknown'")
            conn.commit()
        except sqlite3.OperationalError:
            pass

        # ── Image CAPTCHA challenges ─────────────────────────────
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS image_challenges (
                id TEXT PRIMARY KEY,
                intersections_json TEXT NOT NULL,
                num_intersections INTEGER NOT NULL,
                ttl_ms INTEGER NOT NULL,
                used INTEGER DEFAULT 0,
                created_at REAL NOT NULL
            )
            """
        )
        conn.commit()

        # ── Image CAPTCHA attempt logs ────────────────────────────
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS image_attempt_logs (
                attempt_id TEXT PRIMARY KEY,
                challenge_id TEXT NOT NULL,
                num_lines INTEGER NOT NULL,
                num_intersections INTEGER NOT NULL,
                num_clicks INTEGER NOT NULL,
                matched INTEGER NOT NULL,
                excess INTEGER NOT NULL,
                passed INTEGER NOT NULL,
                reason TEXT NOT NULL,
                solve_time_ms REAL NOT NULL,
                too_fast INTEGER NOT NULL,
                clicks_json TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        conn.commit()

        # Migration: add pointer_type and tolerance_px columns to image_attempt_logs
        for col_def in [
            "ALTER TABLE image_attempt_logs ADD COLUMN pointer_type TEXT",
            "ALTER TABLE image_attempt_logs ADD COLUMN tolerance_px REAL",
        ]:
            try:
                conn.execute(col_def)
                conn.commit()
            except sqlite3.OperationalError:
                pass

        # ── Questionnaire responses ─────────────────────────────
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS questionnaire_responses (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                device_type TEXT,
                age_range TEXT NOT NULL,
                captcha_frequency INTEGER NOT NULL,
                captcha1_difficulty INTEGER NOT NULL,
                captcha1_frustration INTEGER NOT NULL,
                captcha2_difficulty INTEGER NOT NULL,
                captcha2_frustration INTEGER NOT NULL,
                comments TEXT,
                created_at REAL NOT NULL
            )
            """
        )
        conn.commit()

        # Migration: add device_type column to questionnaire_responses
        try:
            conn.execute("ALTER TABLE questionnaire_responses ADD COLUMN device_type TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass

        # ── Line CAPTCHA challenges ──────────────────────────────
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS challenges (
                id TEXT PRIMARY KEY,
                seed TEXT NOT NULL,
                points_json TEXT NOT NULL,
                path_length REAL NOT NULL,
                ttl_ms INTEGER NOT NULL,
                nonce TEXT,
                tolerance_mouse REAL,
                tolerance_touch REAL,
                jitter_mouse REAL,
                jitter_touch REAL,
                peek_pos REAL DEFAULT 0,
                last_peek_at REAL,
                peek_count INTEGER DEFAULT 0,
                nonce_used INTEGER DEFAULT 0,
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
                device_pixel_ratio REAL,
                path_seed TEXT NOT NULL,
                path_length_px REAL NOT NULL,
                tolerance_px REAL NOT NULL,
                tolerance_jitter_px REAL,
                ttl_ms INTEGER NOT NULL,
                started_at REAL NOT NULL,
                ended_at REAL NOT NULL,
                duration_ms REAL NOT NULL,
                outcome_reason TEXT NOT NULL,
                coverage_ratio REAL NOT NULL,
                coverage_len_ratio REAL,
                mean_speed REAL,
                max_speed REAL,
                pause_count INTEGER,
                pause_durations_json TEXT,
                deviation_stats_json TEXT,
                speed_const_flag INTEGER,
                accel_flag INTEGER,
                behavioural_flag INTEGER,
                speed_violation INTEGER,
                too_perfect_flag INTEGER,
                bot_score REAL,
                regularity_dt_cv REAL,
                regularity_dd_cv REAL,
                curvature_var_low REAL,
                curvature_var_high REAL,
                trajectory_json TEXT,
                created_at REAL NOT NULL
            )
            """
        )
        conn.commit()

        # Attempt to add new columns if missing (SQLite is forgiving with extra columns)
        try:
            conn.execute("ALTER TABLE challenges ADD COLUMN nonce TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass
        for col_def in [
            "ALTER TABLE challenges ADD COLUMN tolerance_mouse REAL",
            "ALTER TABLE challenges ADD COLUMN tolerance_touch REAL",
            "ALTER TABLE challenges ADD COLUMN jitter_mouse REAL",
            "ALTER TABLE challenges ADD COLUMN jitter_touch REAL",
            "ALTER TABLE challenges ADD COLUMN peek_pos REAL DEFAULT 0",
            "ALTER TABLE challenges ADD COLUMN last_peek_at REAL",
            "ALTER TABLE challenges ADD COLUMN peek_count INTEGER DEFAULT 0",
            "ALTER TABLE challenges ADD COLUMN nonce_used INTEGER DEFAULT 0",
        ]:
            try:
                conn.execute(col_def)
                conn.commit()
            except sqlite3.OperationalError:
                pass
        for col_def in [
            "ALTER TABLE attempt_logs ADD COLUMN device_pixel_ratio REAL",
            "ALTER TABLE attempt_logs ADD COLUMN tolerance_jitter_px REAL",
            "ALTER TABLE attempt_logs ADD COLUMN coverage_len_ratio REAL",
            "ALTER TABLE attempt_logs ADD COLUMN speed_const_flag INTEGER",
            "ALTER TABLE attempt_logs ADD COLUMN accel_flag INTEGER",
            "ALTER TABLE attempt_logs ADD COLUMN behavioural_flag INTEGER",
            "ALTER TABLE attempt_logs ADD COLUMN speed_violation INTEGER",
            "ALTER TABLE attempt_logs ADD COLUMN too_perfect_flag INTEGER",
            "ALTER TABLE attempt_logs ADD COLUMN bot_score REAL",
            "ALTER TABLE attempt_logs ADD COLUMN regularity_dt_cv REAL",
            "ALTER TABLE attempt_logs ADD COLUMN regularity_dd_cv REAL",
            "ALTER TABLE attempt_logs ADD COLUMN curvature_var_low REAL",
            "ALTER TABLE attempt_logs ADD COLUMN curvature_var_high REAL",
        ]:
            try:
                conn.execute(col_def)
                conn.commit()
            except sqlite3.OperationalError:
                pass


def save_challenge(
    challenge_id: str,
    seed: str,
    points: List[List[float]],
    path_length: float,
    ttl_ms: int,
    nonce: str,
    tolerance_mouse: float,
    tolerance_touch: float,
    jitter_mouse: float,
    jitter_touch: float,
) -> None:
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO challenges (
                id,
                seed,
                points_json,
                path_length,
                ttl_ms,
                nonce,
                tolerance_mouse,
                tolerance_touch,
                jitter_mouse,
                jitter_touch,
                peek_pos,
                last_peek_at,
                peek_count,
                nonce_used,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (
                challenge_id,
                seed,
                json.dumps(points),
                path_length,
                ttl_ms,
                nonce,
                tolerance_mouse,
                tolerance_touch,
                jitter_mouse,
                jitter_touch,
                0.0,
                None,
                0,
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
                device_pixel_ratio,
                path_seed,
                path_length_px,
                tolerance_px,
                tolerance_jitter_px,
                ttl_ms,
                started_at,
                ended_at,
                duration_ms,
                outcome_reason,
                coverage_ratio,
                coverage_len_ratio,
                mean_speed,
                max_speed,
                pause_count,
                pause_durations_json,
                deviation_stats_json,
                speed_const_flag,
                accel_flag,
                behavioural_flag,
                speed_violation,
                too_perfect_flag,
                bot_score,
                regularity_dt_cv,
                regularity_dd_cv,
                curvature_var_low,
                curvature_var_high,
                trajectory_json,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                log["attempt_id"],
                log["session_id"],
                log["challenge_id"],
                log["pointer_type"],
                log.get("os_family"),
                log.get("browser_family"),
                log.get("device_pixel_ratio"),
                log["path_seed"],
                log["path_length_px"],
                log["tolerance_px"],
                log.get("tolerance_jitter_px"),
                log["ttl_ms"],
                log["started_at"],
                log["ended_at"],
                log["duration_ms"],
                log["outcome_reason"],
                log["coverage_ratio"],
                log.get("coverage_len_ratio"),
                log.get("mean_speed"),
                log.get("max_speed"),
                log.get("pause_count"),
                json.dumps(log.get("pause_durations_ms") or []),
                json.dumps(log.get("deviation_stats") or {}),
                1 if log.get("speed_const_flag") else 0,
                1 if log.get("accel_flag") else 0,
                1 if log.get("behavioural_flag") else 0,
                1 if log.get("speed_violation") else 0,
                1 if log.get("too_perfect_flag") else 0,
                log.get("bot_score"),
                log.get("regularity_dt_cv"),
                log.get("regularity_dd_cv"),
                log.get("curvature_var_low"),
                log.get("curvature_var_high"),
                json.dumps(log.get("trajectory") or []),
                time.time(),
            ),
        )
        conn.commit()

    _supabase_insert("attempt_logs", {
        "attempt_id": log["attempt_id"],
        "session_id": log["session_id"],
        "challenge_id": log["challenge_id"],
        "pointer_type": log["pointer_type"],
        "os_family": log.get("os_family"),
        "browser_family": log.get("browser_family"),
        "device_pixel_ratio": log.get("device_pixel_ratio"),
        "path_seed": log["path_seed"],
        "path_length_px": log["path_length_px"],
        "tolerance_px": log["tolerance_px"],
        "tolerance_jitter_px": log.get("tolerance_jitter_px"),
        "ttl_ms": log["ttl_ms"],
        "started_at": log["started_at"],
        "ended_at": log["ended_at"],
        "duration_ms": log["duration_ms"],
        "outcome_reason": log["outcome_reason"],
        "coverage_ratio": log["coverage_ratio"],
        "coverage_len_ratio": log.get("coverage_len_ratio"),
        "mean_speed": log.get("mean_speed"),
        "max_speed": log.get("max_speed"),
        "pause_count": log.get("pause_count"),
        "pause_durations_json": json.dumps(log.get("pause_durations_ms") or []),
        "deviation_stats_json": json.dumps(log.get("deviation_stats") or {}),
        "speed_const_flag": 1 if log.get("speed_const_flag") else 0,
        "accel_flag": 1 if log.get("accel_flag") else 0,
        "behavioural_flag": 1 if log.get("behavioural_flag") else 0,
        "speed_violation": 1 if log.get("speed_violation") else 0,
        "too_perfect_flag": 1 if log.get("too_perfect_flag") else 0,
        "bot_score": log.get("bot_score"),
        "regularity_dt_cv": log.get("regularity_dt_cv"),
        "regularity_dd_cv": log.get("regularity_dd_cv"),
        "curvature_var_low": log.get("curvature_var_low"),
        "curvature_var_high": log.get("curvature_var_high"),
        "trajectory_json": json.dumps(log.get("trajectory") or []),
        "created_at": time.time(),
    })


def mark_challenge_used(challenge_id: str) -> None:
    with _get_conn() as conn:
        conn.execute(
            "UPDATE challenges SET nonce_used = 1 WHERE id = ?", (challenge_id,)
        )
        conn.commit()


def update_peek_progress(
    challenge_id: str,
    peek_pos: float,
    last_peek_at: float,
    peek_count: int,
) -> None:
    with _get_conn() as conn:
        conn.execute(
            "UPDATE challenges SET peek_pos = ?, last_peek_at = ?, peek_count = ? WHERE id = ?",
            (peek_pos, last_peek_at, peek_count, challenge_id),
        )
        conn.commit()


# ─── Image CAPTCHA helpers ───────────────────────────────────────────────


def save_image_challenge(
    challenge_id: str,
    intersections: List[List[float]],
    num_intersections: int,
    ttl_ms: int,
) -> None:
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO image_challenges (id, intersections_json, num_intersections, ttl_ms, used, created_at)
            VALUES (?, ?, ?, ?, 0, ?)
            """,
            (
                challenge_id,
                json.dumps(intersections),
                num_intersections,
                ttl_ms,
                time.time(),
            ),
        )
        conn.commit()


def get_image_challenge(challenge_id: str) -> Optional[sqlite3.Row]:
    with _get_conn() as conn:
        return conn.execute(
            "SELECT * FROM image_challenges WHERE id = ?", (challenge_id,)
        ).fetchone()


def mark_image_challenge_used(challenge_id: str) -> None:
    with _get_conn() as conn:
        conn.execute(
            "UPDATE image_challenges SET used = 1 WHERE id = ?", (challenge_id,)
        )
        conn.commit()


def save_feedback(
    feedback_id: str,
    name: Optional[str],
    category: str,
    device: str,
    message: str,
    image_filenames: List[str],
) -> None:
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO feedback (id, name, category, device, message, image_filenames_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                feedback_id,
                name,
                category,
                device,
                message,
                json.dumps(image_filenames),
                time.time(),
            ),
        )
        conn.commit()

    _supabase_insert("feedback", {
        "id": feedback_id,
        "name": name,
        "category": category,
        "device": device,
        "message": message,
        "image_filenames_json": json.dumps(image_filenames),
        "created_at": time.time(),
    })


def get_all_feedback() -> List[Dict[str, Any]]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM feedback ORDER BY created_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def save_questionnaire_response(data: Dict[str, Any]) -> None:
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO questionnaire_responses (
                id, session_id, device_type, age_range, captcha_frequency,
                captcha1_difficulty, captcha1_frustration,
                captcha2_difficulty, captcha2_frustration,
                comments, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["id"],
                data["session_id"],
                data.get("device_type"),
                data["age_range"],
                data["captcha_frequency"],
                data["captcha1_difficulty"],
                data["captcha1_frustration"],
                data["captcha2_difficulty"],
                data["captcha2_frustration"],
                data.get("comments"),
                time.time(),
            ),
        )
        conn.commit()

    _supabase_insert("questionnaire_responses", {
        "id": data["id"],
        "session_id": data["session_id"],
        "device_type": data.get("device_type"),
        "age_range": data["age_range"],
        "captcha_frequency": data["captcha_frequency"],
        "captcha1_difficulty": data["captcha1_difficulty"],
        "captcha1_frustration": data["captcha1_frustration"],
        "captcha2_difficulty": data["captcha2_difficulty"],
        "captcha2_frustration": data["captcha2_frustration"],
        "comments": data.get("comments"),
        "created_at": time.time(),
    })


def save_image_attempt(log: Dict[str, Any]) -> None:
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO image_attempt_logs (
                attempt_id, challenge_id,
                num_lines, num_intersections,
                num_clicks, matched, excess,
                passed, reason, solve_time_ms, too_fast,
                clicks_json, pointer_type, tolerance_px,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                log["attempt_id"],
                log["challenge_id"],
                log["num_lines"],
                log["num_intersections"],
                log["num_clicks"],
                log["matched"],
                log["excess"],
                1 if log["passed"] else 0,
                log["reason"],
                log["solve_time_ms"],
                1 if log["too_fast"] else 0,
                json.dumps(log.get("clicks") or []),
                log.get("pointer_type"),
                log.get("tolerance_px"),
                time.time(),
            ),
        )
        conn.commit()

    _supabase_insert("image_attempt_logs", {
        "attempt_id": log["attempt_id"],
        "challenge_id": log["challenge_id"],
        "num_lines": log["num_lines"],
        "num_intersections": log["num_intersections"],
        "num_clicks": log["num_clicks"],
        "matched": log["matched"],
        "excess": log["excess"],
        "passed": 1 if log["passed"] else 0,
        "reason": log["reason"],
        "solve_time_ms": log["solve_time_ms"],
        "too_fast": 1 if log["too_fast"] else 0,
        "clicks_json": json.dumps(log.get("clicks") or []),
        "pointer_type": log.get("pointer_type"),
        "tolerance_px": log.get("tolerance_px"),
        "created_at": time.time(),
    })
