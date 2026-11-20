-- AetherLoom SQLite FTS5 Memory & Telemetry Schema
-- Lightweight local persistence optimized for low-RAM laptops.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    ts TEXT NOT NULL,
    summary TEXT NOT NULL,
    raw_ref TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    goal TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('swarm', 'teamwork', 'hybrid')),
    outcome TEXT NOT NULL,
    tokens_in INTEGER NOT NULL DEFAULT 0,
    tokens_out INTEGER NOT NULL DEFAULT 0,
    pass_rate REAL NOT NULL DEFAULT 100.0,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS skills (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    path TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('core', 'candidate', 'promoted', 'rejected', 'downgraded')),
    benchmark_score REAL DEFAULT NULL,
    promoted_at TEXT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS code_map (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL,
    symbol TEXT NOT NULL,
    summary TEXT NOT NULL,
    fts TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT NOT NULL,
    body TEXT NOT NULL,
    fts TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS dream_diffs (
    id TEXT PRIMARY KEY,
    ts TEXT NOT NULL,
    patch_path TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected', 'applied')),
    approved_by TEXT DEFAULT NULL,
    approved_at TEXT DEFAULT NULL
);

-- Detailed Meter telemetry records per subagent task
CREATE TABLE IF NOT EXISTS meter_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    agent TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cached_tokens INTEGER NOT NULL DEFAULT 0,
    baseline_input_tokens INTEGER NOT NULL DEFAULT 0,
    baseline_total_tokens INTEGER NOT NULL DEFAULT 0,
    memory_driven INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL NOT NULL DEFAULT 0.0,
    pass_rate REAL NOT NULL DEFAULT 100.0,
    mode TEXT NOT NULL CHECK (mode IN ('swarm', 'teamwork', 'hybrid')),
    timestamp TEXT NOT NULL
);

-- FTS5 Virtual Tables indexed for BM25 ranking
CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
    body,
    project,
    content='notes',
    content_rowid='id',
    tokenize='porter unicode61'
);

CREATE VIRTUAL TABLE IF NOT EXISTS code_map_fts USING fts5(
    summary,
    symbol,
    path,
    content='code_map',
    content_rowid='id',
    tokenize='porter unicode61'
);

CREATE VIRTUAL TABLE IF NOT EXISTS sessions_fts USING fts5(
    summary,
    raw_ref,
    content='sessions',
    content_rowid='rowid',
    tokenize='porter unicode61'
);

-- Keep FTS5 tables synchronized via triggers
CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
    INSERT INTO notes_fts(rowid, body, project) VALUES (new.id, new.body, new.project);
END;

CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
    INSERT INTO notes_fts(notes_fts, rowid, body, project) VALUES ('delete', old.id, old.body, old.project);
END;

CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
    INSERT INTO notes_fts(notes_fts, rowid, body, project) VALUES ('delete', old.id, old.body, old.project);
    INSERT INTO notes_fts(rowid, body, project) VALUES (new.id, new.body, new.project);
END;

CREATE TRIGGER IF NOT EXISTS code_map_ai AFTER INSERT ON code_map BEGIN
    INSERT INTO code_map_fts(rowid, summary, symbol, path) VALUES (new.id, new.summary, new.symbol, new.path);
END;

CREATE TRIGGER IF NOT EXISTS code_map_ad AFTER DELETE ON code_map BEGIN
    INSERT INTO code_map_fts(code_map_fts, rowid, summary, symbol, path) VALUES ('delete', old.id, old.summary, old.symbol, old.path);
END;

CREATE TRIGGER IF NOT EXISTS code_map_au AFTER UPDATE ON code_map BEGIN
    INSERT INTO code_map_fts(code_map_fts, rowid, summary, symbol, path) VALUES ('delete', old.id, old.summary, old.symbol, old.path);
    INSERT INTO code_map_fts(rowid, summary, symbol, path) VALUES (new.id, new.summary, new.symbol, new.path);
END;

CREATE TRIGGER IF NOT EXISTS sessions_ai AFTER INSERT ON sessions BEGIN
    INSERT INTO sessions_fts(rowid, summary, raw_ref) VALUES (new.rowid, new.summary, new.raw_ref);
END;

CREATE TRIGGER IF NOT EXISTS sessions_ad AFTER DELETE ON sessions BEGIN
    INSERT INTO sessions_fts(sessions_fts, rowid, summary, raw_ref) VALUES ('delete', old.rowid, old.summary, old.raw_ref);
END;

CREATE TRIGGER IF NOT EXISTS sessions_au AFTER UPDATE ON sessions BEGIN
    INSERT INTO sessions_fts(sessions_fts, rowid, summary, raw_ref) VALUES ('delete', old.rowid, old.summary, old.raw_ref);
    INSERT INTO sessions_fts(rowid, summary, raw_ref) VALUES (new.rowid, new.summary, new.raw_ref);
END;
