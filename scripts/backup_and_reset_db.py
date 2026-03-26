#!/usr/bin/env python3
"""Back up the current captcha.db and clear test data before the user study."""

import shutil
import sqlite3
from pathlib import Path

DB_PATH = Path("data/captcha.db")
BACKUP_PATH = Path("data/captcha_pre_study_backup.db")

TABLES_TO_CLEAR = [
    "attempt_logs",
    "image_attempt_logs",
    "feedback",
    "questionnaire_responses",
]


def main() -> None:
    if not DB_PATH.exists():
        print(f"No database found at {DB_PATH}")
        return

    # Step 1: Back up
    shutil.copy2(DB_PATH, BACKUP_PATH)
    print(f"Backed up {DB_PATH} -> {BACKUP_PATH}")

    # Step 2: Report and clear
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    for table in TABLES_TO_CLEAR:
        try:
            count = cur.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]
            cur.execute(f"DELETE FROM [{table}]")
            print(f"  {table}: {count} rows backed up, cleared")
        except sqlite3.OperationalError:
            print(f"  {table}: table not found, skipping")

    # Also clear challenges/image_challenges (stale one-use tokens)
    for table in ["challenges", "image_challenges"]:
        try:
            count = cur.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]
            cur.execute(f"DELETE FROM [{table}]")
            print(f"  {table}: {count} rows backed up, cleared")
        except sqlite3.OperationalError:
            print(f"  {table}: table not found, skipping")

    conn.commit()
    conn.close()

    print("\nDatabase reset complete. Schema preserved, data cleared.")
    print(f"Backup at: {BACKUP_PATH}")


if __name__ == "__main__":
    main()
