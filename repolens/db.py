from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from repolens.models import CodeChunk


SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS repos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  root_path TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  indexed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chunks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  repo_id INTEGER NOT NULL,
  path TEXT NOT NULL,
  language TEXT NOT NULL,
  symbol TEXT,
  start_line INTEGER NOT NULL,
  end_line INTEGER NOT NULL,
  content TEXT NOT NULL,
  summary TEXT NOT NULL,
  embedding TEXT NOT NULL,
  FOREIGN KEY(repo_id) REFERENCES repos(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chunks_repo ON chunks(repo_id);
CREATE INDEX IF NOT EXISTS idx_chunks_path ON chunks(path);
CREATE INDEX IF NOT EXISTS idx_chunks_symbol ON chunks(symbol);
"""


def connect(db_path: Path | str) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.executescript(SCHEMA)
    return connection


def upsert_repo(connection: sqlite3.Connection, root_path: str, name: str) -> int:
    connection.execute(
        """
        INSERT INTO repos(root_path, name, indexed_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(root_path)
        DO UPDATE SET name=excluded.name, indexed_at=CURRENT_TIMESTAMP
        """,
        (root_path, name),
    )
    row = connection.execute("SELECT id FROM repos WHERE root_path = ?", (root_path,)).fetchone()
    if row is None:
        raise RuntimeError("failed to create repository record")
    repo_id = int(row["id"])
    connection.execute("DELETE FROM chunks WHERE repo_id = ?", (repo_id,))
    return repo_id


def insert_chunks(connection: sqlite3.Connection, chunks: list[CodeChunk]) -> None:
    rows = [
        (
            chunk.repo_id,
            chunk.path,
            chunk.language,
            chunk.symbol,
            chunk.start_line,
            chunk.end_line,
            chunk.content,
            chunk.summary,
            json.dumps(chunk.embedding),
        )
        for chunk in chunks
    ]
    connection.executemany(
        """
        INSERT INTO chunks(
          repo_id, path, language, symbol, start_line, end_line, content, summary, embedding
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def list_repos(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        "SELECT id, root_path, name, indexed_at FROM repos ORDER BY indexed_at DESC"
    ).fetchall()
    return [dict(row) for row in rows]


def latest_repo_id(connection: sqlite3.Connection) -> int | None:
    row = connection.execute("SELECT id FROM repos ORDER BY indexed_at DESC LIMIT 1").fetchone()
    return int(row["id"]) if row else None


def fetch_chunks(connection: sqlite3.Connection, repo_id: int | None = None) -> list[CodeChunk]:
    if repo_id is None:
        rows = connection.execute(
            """
            SELECT id, repo_id, path, language, symbol, start_line, end_line, content, summary, embedding
            FROM chunks
            """
        ).fetchall()
    else:
        rows = connection.execute(
            """
            SELECT id, repo_id, path, language, symbol, start_line, end_line, content, summary, embedding
            FROM chunks WHERE repo_id = ?
            """,
            (repo_id,),
        ).fetchall()
    return [_row_to_chunk(row) for row in rows]


def repo_map(connection: sqlite3.Connection, repo_id: int) -> dict[str, Any]:
    repo = connection.execute(
        "SELECT id, root_path, name, indexed_at FROM repos WHERE id = ?", (repo_id,)
    ).fetchone()
    if repo is None:
        raise KeyError(f"repository {repo_id} not found")

    chunks = fetch_chunks(connection, repo_id)
    files: dict[str, dict[str, Any]] = {}
    languages: dict[str, int] = {}
    for chunk in chunks:
        languages[chunk.language] = languages.get(chunk.language, 0) + 1
        file_entry = files.setdefault(
            chunk.path,
            {"path": chunk.path, "language": chunk.language, "chunks": 0, "symbols": []},
        )
        file_entry["chunks"] += 1
        if chunk.symbol and chunk.symbol not in file_entry["symbols"]:
            file_entry["symbols"].append(chunk.symbol)

    return {
        "repo": dict(repo),
        "languages": languages,
        "files": sorted(files.values(), key=lambda item: item["path"]),
        "chunk_count": len(chunks),
    }


def _row_to_chunk(row: sqlite3.Row) -> CodeChunk:
    return CodeChunk(
        id=int(row["id"]),
        repo_id=int(row["repo_id"]),
        path=str(row["path"]),
        language=str(row["language"]),
        symbol=str(row["symbol"]) if row["symbol"] else None,
        start_line=int(row["start_line"]),
        end_line=int(row["end_line"]),
        content=str(row["content"]),
        summary=str(row["summary"]),
        embedding=[float(value) for value in json.loads(row["embedding"])],
    )
