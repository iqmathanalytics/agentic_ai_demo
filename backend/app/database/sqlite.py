import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent / "agent_runs.sqlite3"


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_runs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              agent TEXT NOT NULL,
              provider TEXT NOT NULL,
              model TEXT NOT NULL,
              status TEXT NOT NULL,
              created_at TEXT NOT NULL,
              result_json TEXT
            )
            """
        )
        conn.commit()


def save_run(agent: str, provider: str, model: str, status: str, result: dict[str, Any] | None = None):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO agent_runs(agent, provider, model, status, created_at, result_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                agent,
                provider,
                model,
                status,
                datetime.utcnow().isoformat(),
                json.dumps(result or {}),
            ),
        )
        conn.commit()

