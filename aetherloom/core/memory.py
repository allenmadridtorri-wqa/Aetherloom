"""Archivist SQLite FTS5 + BM25 memory layer for AetherLoom.

Retrieves top-k (default k=5) fragments across notes, code_map, and sessions,
strictly respecting caller token budgets by omitting lower-ranked hits rather
than compressing relevant content.
"""

from __future__ import annotations

import datetime as dt
import pathlib
import re
import sqlite3
from typing import Any, Dict, List, Optional


SCHEMA_PATH = pathlib.Path(__file__).with_name("schema.sql")


def estimate_tokens(text: str) -> int:
    """Fast deterministic token estimator (~4 chars per token)."""
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def sanitize_fts_query(raw_query: str) -> str:
    """Convert free-text query into a safe FTS5 MATCH expression."""
    tokens = re.findall(r"[A-Za-z0-9_]+", raw_query or "")
    if not tokens:
        return ""
    return " OR ".join(f'"{tok}"' for tok in tokens[:16])


class MemoryStore:
    """SQLite FTS5 memory store managed by the Archivist subagent."""

    def __init__(self, db_path: str | pathlib.Path = ":memory:") -> None:
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            pathlib.Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        self.conn.executescript(schema_sql)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # --- Writes ---

    def add_session(
        self,
        session_id: str,
        summary: str,
        raw_ref: str = "",
        ts: Optional[str] = None,
    ) -> Dict[str, Any]:
        timestamp = ts or dt.datetime.now(dt.timezone.utc).isoformat()
        self.conn.execute(
            "INSERT OR REPLACE INTO sessions(id, ts, summary, raw_ref) VALUES (?, ?, ?, ?)",
            (session_id, timestamp, summary, raw_ref),
        )
        self.conn.commit()
        return {"id": session_id, "ts": timestamp, "summary": summary, "raw_ref": raw_ref}

    def add_task(
        self,
        task_id: str,
        session_id: str,
        goal: str,
        mode: str,
        outcome: str,
        tokens_in: int = 0,
        tokens_out: int = 0,
        pass_rate: float = 100.0,
    ) -> Dict[str, Any]:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO tasks(id, session_id, goal, mode, outcome, tokens_in, tokens_out, pass_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (task_id, session_id, goal, mode, outcome, tokens_in, tokens_out, pass_rate),
        )
        self.conn.commit()
        return {
            "id": task_id,
            "session_id": session_id,
            "goal": goal,
            "mode": mode,
            "outcome": outcome,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "pass_rate": pass_rate,
        }

    def add_note(self, project: str, body: str) -> Dict[str, Any]:
        fts_tokens = " ".join(re.findall(r"[A-Za-z0-9_]+", body.lower()))
        cur = self.conn.execute(
            "INSERT INTO notes(project, body, fts) VALUES (?, ?, ?)",
            (project, body, fts_tokens),
        )
        self.conn.commit()
        return {"id": cur.lastrowid, "project": project, "body": body}

    def upsert_code_map(self, path: str, symbol: str, summary: str) -> Dict[str, Any]:
        fts_tokens = " ".join(re.findall(r"[A-Za-z0-9_]+", f"{path} {symbol} {summary}".lower()))
        existing = self.conn.execute(
            "SELECT id FROM code_map WHERE path = ? AND symbol = ?", (path, symbol)
        ).fetchone()
        if existing:
            self.conn.execute(
                "UPDATE code_map SET summary = ?, fts = ? WHERE id = ?",
                (summary, fts_tokens, existing["id"]),
            )
            row_id = existing["id"]
        else:
            cur = self.conn.execute(
                "INSERT INTO code_map(path, symbol, summary, fts) VALUES (?, ?, ?, ?)",
                (path, symbol, summary, fts_tokens),
            )
            row_id = cur.lastrowid
        self.conn.commit()
        return {"id": row_id, "path": path, "symbol": symbol, "summary": summary}

    def upsert_skill(
        self,
        skill_id: str,
        name: str,
        path: str,
        status: str,
        benchmark_score: Optional[float] = None,
        promoted_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        self.conn.execute(
            """
            INSERT INTO skills(id, name, path, status, benchmark_score, promoted_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                path = excluded.path,
                status = excluded.status,
                benchmark_score = excluded.benchmark_score,
                promoted_at = excluded.promoted_at
            """,
            (skill_id, name, path, status, benchmark_score, promoted_at),
        )
        self.conn.commit()
        return {
            "id": skill_id,
            "name": name,
            "path": path,
            "status": status,
            "benchmark_score": benchmark_score,
            "promoted_at": promoted_at,
        }

    def record_dream_diff(
        self,
        diff_id: str,
        patch_path: str,
        status: str = "pending",
        ts: Optional[str] = None,
        approved_by: Optional[str] = None,
        approved_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        timestamp = ts or dt.datetime.now(dt.timezone.utc).isoformat()
        self.conn.execute(
            """
            INSERT OR REPLACE INTO dream_diffs(id, ts, patch_path, status, approved_by, approved_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (diff_id, timestamp, patch_path, status, approved_by, approved_at),
        )
        self.conn.commit()
        return {
            "id": diff_id,
            "ts": timestamp,
            "patch_path": patch_path,
            "status": status,
            "approved_by": approved_by,
            "approved_at": approved_at,
        }

    # --- FTS5 BM25 Retrieval ---

    def search(
        self,
        query: str,
        k: int = 5,
        context_budget_tokens: int = 1200,
        sources: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Search notes, code_map, and sessions via FTS5 BM25 ranking.

        Drops lower-ranked fragments if they exceed context_budget_tokens.
        Never compresses or mutates relevant fragment text.
        """
        fts_expr = sanitize_fts_query(query)
        if not fts_expr:
            return {"query": query, "k": k, "tokens_used": 0, "budget_tokens": context_budget_tokens, "hits": []}

        allowed = set(sources or ["notes", "code_map", "sessions"])
        candidates: List[Dict[str, Any]] = []

        if "notes" in allowed:
            rows = self.conn.execute(
                """
                SELECT n.id, n.project, n.body, bm25(notes_fts) AS rank
                FROM notes_fts
                JOIN notes n ON n.id = notes_fts.rowid
                WHERE notes_fts MATCH ?
                ORDER BY rank ASC
                LIMIT ?
                """,
                (fts_expr, k),
            ).fetchall()
            for r in rows:
                candidates.append(
                    {
                        "source": "notes",
                        "id": str(r["id"]),
                        "title": f"note:{r['project']}",
                        "content": r["body"],
                        "bm25": round(float(r["rank"]), 6),
                        "tokens": estimate_tokens(r["body"]),
                    }
                )

        if "code_map" in allowed:
            rows = self.conn.execute(
                """
                SELECT c.id, c.path, c.symbol, c.summary, bm25(code_map_fts) AS rank
                FROM code_map_fts
                JOIN code_map c ON c.id = code_map_fts.rowid
                WHERE code_map_fts MATCH ?
                ORDER BY rank ASC
                LIMIT ?
                """,
                (fts_expr, k),
            ).fetchall()
            for r in rows:
                content = f"{r['path']}::{r['symbol']} — {r['summary']}"
                candidates.append(
                    {
                        "source": "code_map",
                        "id": str(r["id"]),
                        "title": f"{r['path']}::{r['symbol']}",
                        "content": content,
                        "bm25": round(float(r["rank"]), 6),
                        "tokens": estimate_tokens(content),
                    }
                )

        if "sessions" in allowed:
            rows = self.conn.execute(
                """
                SELECT s.id, s.ts, s.summary, s.raw_ref, bm25(sessions_fts) AS rank
                FROM sessions_fts
                JOIN sessions s ON s.rowid = sessions_fts.rowid
                WHERE sessions_fts MATCH ?
                ORDER BY rank ASC
                LIMIT ?
                """,
                (fts_expr, k),
            ).fetchall()
            for r in rows:
                candidates.append(
                    {
                        "source": "sessions",
                        "id": str(r["id"]),
                        "title": f"session:{r['id']}",
                        "content": r["summary"],
                        "bm25": round(float(r["rank"]), 6),
                        "tokens": estimate_tokens(r["summary"]),
                    }
                )

        # SQLite FTS5 BM25 returns more negative numbers for better matches.
        candidates.sort(key=lambda item: item["bm25"])

        selected: List[Dict[str, Any]] = []
        used_tokens = 0
        for item in candidates:
            if len(selected) >= k:
                break
            if used_tokens + item["tokens"] > context_budget_tokens:
                # Skip rather than lossily compress relevant text
                continue
            selected.append(item)
            used_tokens += item["tokens"]

        return {
            "query": query,
            "k": k,
            "tokens_used": used_tokens,
            "budget_tokens": context_budget_tokens,
            "hits": selected,
        }

    # --- Introspection helpers ---

    def list_notes(self, limit: int = 50) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT id, project, body FROM notes ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def list_code_map(self, limit: int = 50) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT id, path, symbol, summary FROM code_map ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT id, ts, summary, raw_ref FROM sessions ORDER BY ts DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def list_dream_diffs(self, limit: int = 20) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT id, ts, patch_path, status, approved_by, approved_at FROM dream_diffs ORDER BY ts DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def list_skills(self) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT id, name, path, status, benchmark_score, promoted_at FROM skills ORDER BY name ASC"
        ).fetchall()
        return [dict(r) for r in rows]
