"""SQLite-based blockchain simulation layer."""

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from typing import Optional

BLOCKCHAIN_DB_PATH = "D:/Projects/energy-trusted-data-space/backend/blockchain.db"


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(BLOCKCHAIN_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _compute_hash(height: int, prev_hash: str, data: str, timestamp: str, nonce: int) -> str:
    raw = f"{height}{prev_hash}{data}{timestamp}{nonce}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _mine_block(height: int, prev_hash: str, data: str, timestamp: str) -> tuple[int, str]:
    nonce = 0
    while True:
        h = _compute_hash(height, prev_hash, data, timestamp, nonce)
        if h.startswith("00"):
            return nonce, h
        nonce += 1


def init_chain() -> None:
    """Create table and genesis block if not exists."""
    conn = _get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS blocks (
                height INTEGER PRIMARY KEY,
                hash TEXT UNIQUE NOT NULL,
                prev_hash TEXT NOT NULL,
                data TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                nonce INTEGER NOT NULL
            )
            """
        )
        existing = conn.execute("SELECT 1 FROM blocks WHERE height = 0").fetchone()
        if not existing:
            ts = datetime.now(timezone.utc).isoformat()
            nonce, h = _mine_block(0, "0" * 64, "Genesis Block", ts)
            conn.execute(
                "INSERT INTO blocks (height, hash, prev_hash, data, timestamp, nonce) VALUES (?, ?, ?, ?, ?, ?)",
                (0, h, "0" * 64, "Genesis Block", ts, nonce),
            )
            conn.commit()
    finally:
        conn.close()


def get_latest_block() -> Optional[dict]:
    conn = _get_connection()
    try:
        row = conn.execute("SELECT * FROM blocks ORDER BY height DESC LIMIT 1").fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def submit_block(data: str, extra: dict = None) -> dict:
    payload = {"data": data}
    if extra:
        payload["extra"] = extra
    data_str = json.dumps(payload, ensure_ascii=False)

    conn = _get_connection()
    try:
        latest = conn.execute("SELECT * FROM blocks ORDER BY height DESC LIMIT 1").fetchone()
        if latest:
            prev_hash = latest["hash"]
            height = latest["height"] + 1
        else:
            prev_hash = "0" * 64
            height = 0

        ts = datetime.now(timezone.utc).isoformat()
        nonce, h = _mine_block(height, prev_hash, data_str, ts)
        conn.execute(
            "INSERT INTO blocks (height, hash, prev_hash, data, timestamp, nonce) VALUES (?, ?, ?, ?, ?, ?)",
            (height, h, prev_hash, data_str, ts, nonce),
        )
        conn.commit()
        return {"height": height, "hash": h, "prev_hash": prev_hash, "data": data_str, "timestamp": ts, "nonce": nonce}
    finally:
        conn.close()


def get_block(height: int) -> Optional[dict]:
    conn = _get_connection()
    try:
        row = conn.execute("SELECT * FROM blocks WHERE height = ?", (height,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_chain(height_range: tuple = None) -> list:
    conn = _get_connection()
    try:
        if height_range:
            rows = conn.execute(
                "SELECT * FROM blocks WHERE height >= ? AND height <= ? ORDER BY height",
                height_range,
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM blocks ORDER BY height").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def verify_chain() -> dict:
    """Verify blockchain integrity by checking hash linkage."""
    blocks = get_chain()
    total = len(blocks)
    checked = 0
    invalid = []

    if total == 0:
        return {"is_valid": True, "total_blocks": 0, "checked_blocks": 0, "invalid_blocks": []}

    for i, block in enumerate(blocks):
        checked += 1
        expected_hash = _compute_hash(
            block["height"], block["prev_hash"], block["data"], block["timestamp"], block["nonce"]
        )
        if block["hash"] != expected_hash:
            invalid.append({"height": block["height"], "reason": "hash_mismatch"})
            continue

        if i > 0:
            if block["prev_hash"] != blocks[i - 1]["hash"]:
                invalid.append({"height": block["height"], "reason": "prev_hash_mismatch"})

    return {
        "is_valid": len(invalid) == 0,
        "total_blocks": total,
        "checked_blocks": checked,
        "invalid_blocks": invalid,
    }
