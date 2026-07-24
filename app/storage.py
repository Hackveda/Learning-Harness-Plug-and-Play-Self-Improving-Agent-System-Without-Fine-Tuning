from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable

from app.models import EpisodeLog, Playbook


DB_PATH = Path(os.getenv("DATABASE_PATH", "data/learning_harness.db"))


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS playbooks (
                version TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                is_champion INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS episodes (
                episode_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                strategy_version TEXT NOT NULL,
                reward_score REAL NOT NULL,
                final_outcome TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                details TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )


@contextmanager
def connection():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def save_playbook(playbook: Playbook, champion: bool = False) -> None:
    with connection() as conn:
        if champion:
            conn.execute("UPDATE playbooks SET is_champion = 0")
        conn.execute(
            """
            INSERT OR REPLACE INTO playbooks(version, payload, is_champion, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                playbook.version,
                playbook.model_dump_json(),
                int(champion),
                playbook.created_at,
            ),
        )


def get_playbook(version: str) -> Playbook | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT payload FROM playbooks WHERE version = ?", (version,)
        ).fetchone()
    return Playbook.model_validate_json(row["payload"]) if row else None


def get_champion() -> Playbook:
    with connection() as conn:
        row = conn.execute(
            "SELECT payload FROM playbooks WHERE is_champion = 1 LIMIT 1"
        ).fetchone()
    if not row:
        raise RuntimeError("No champion playbook exists. Seed the database first.")
    return Playbook.model_validate_json(row["payload"])


def list_playbooks() -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT version, is_champion, created_at FROM playbooks ORDER BY created_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def save_episode(episode: EpisodeLog) -> None:
    with connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO episodes
            (episode_id, agent_id, strategy_version, reward_score, final_outcome, payload, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                episode.episode_id,
                episode.agent_id,
                episode.strategy_version,
                episode.reward_score,
                episode.final_outcome,
                episode.model_dump_json(),
                episode.timestamp,
            ),
        )


def list_episodes(strategy_version: str | None = None, limit: int = 500) -> list[EpisodeLog]:
    with connection() as conn:
        if strategy_version:
            rows = conn.execute(
                """
                SELECT payload FROM episodes
                WHERE strategy_version = ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (strategy_version, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT payload FROM episodes ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [EpisodeLog.model_validate_json(row["payload"]) for row in rows]


def add_audit(event_type: str, details: dict) -> None:
    with connection() as conn:
        conn.execute(
            "INSERT INTO audits(event_type, details) VALUES (?, ?)",
            (event_type, json.dumps(details, default=str)),
        )


def list_audits(limit: int = 200) -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT id, event_type, details, created_at FROM audits ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["details"] = json.loads(item["details"])
        result.append(item)
    return result
