---
name: memory
description: SQLite FTS5 BM25 memory management skill owned by Archivist. Handles lightweight local storage, top-k retrieval within caller context budgets, and code-map indexing.
immutable: true
---

# Memory Skill (SQLite FTS5 + BM25)

## Purpose
Provide deterministic, low-RAM persistent memory on local laptops using Python's built-in `sqlite3` with FTS5 full-text indexing and BM25 ranking.

## Schema Tables (`core/schema.sql`)
- `sessions(id, ts, summary, raw_ref)`
- `tasks(id, session_id, goal, mode, outcome, tokens_in, tokens_out, pass_rate)`
- `skills(id, name, path, status, benchmark_score, promoted_at)`
- `code_map(id, path, symbol, summary, fts)`
- `notes(id, project, body, fts)`
- `dream_diffs(id, ts, patch_path, status, approved_by, approved_at)`

## Retrieval Rules
1. Query FTS5 virtual tables (`notes_fts`, `code_map_fts`, `sessions_fts`) ordered by SQLite `bm25(...)` score (lower/more negative score = stronger match).
2. Retrieve `top-k` (default `k=5`) per subagent call.
3. Enforce the caller's token budget strictly by dropping lower-ranked hits—**never** by lossy summarization or truncation inside a relevant code slice.
4. Maintain `code_map` entries whenever `Builder` or `Refactorer` commits symbol changes so `CodeMapper` returns exact minimal slices.
5. Long-term memory rewrites are never performed automatically during live tasks; consolidation runs exclusively via the `dream` propose-then-commit workflow.
