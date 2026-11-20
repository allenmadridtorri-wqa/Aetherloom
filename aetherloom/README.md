# AetherLoom (`/supergravity`)

AetherLoom is a cross-platform multi-agent orchestration plugin invoked via `/supergravity <goal>`. It maintains one canonical Markdown + JSON source (`manifest.json`, `AGENTS.md`, `skills/`, `agents/`) and compiles host-specific adapters automatically via `python3 build_adapters.py`.

Zero dependency on any third-party `supergravity` PyPI or npm package. All core runtimes run on Python 3.10+ standard library (including built-in SQLite FTS5).

## Honesty Statement

AetherLoom is a deterministic software orchestration tool. None of its 18 subagents, Dream memory consolidation jobs, or benchmark-gated skill learning pipelines are sentient, conscious, or emotional. Dream and skill learning are scheduled file-diff and test-harness workflows.

## Free-Tier Reality & Billing Caveats

- **Free-tier default**: Designed for Gemini 3.6 Flash on the free tier (~15 requests/minute, ~1,500 requests/day).
- **Google AI Pro caveat**: The $10/month Gemini API credits included with Google AI Pro only activate when the linked API billing account has at least **$5 of deposited funds**. AetherLoom never assumes Google AI Pro alone unlocks paid APIs.
- **Startup Tier Probe (`core/tier_probe.py`)**:
  - **Nano Banana (`generate_image`)** and **Gemini TTS (`generate_speech`)**: Enabled on free-tier keys within rate limits.
  - **Veo (`generate_video`)**: Returns `BAD_REQUEST` on free-tier keys and has no free tier. AetherLoom detects free-tier keys on startup and proactively disables Veo with a clear warning rather than failing at runtime.
  - **Paid keys**: Every billed call from `Vision` or `Griot` passes through `Warden` for cost preview, hard-cap enforcement, and `N.A.T.A.L.I.E.` approval queuing.

## Architecture Overview

- **5 Layers, 18 Subagents**:
  - `L0 Command`: Commander (routes via Router, aggregates, reports briefly; no direct code writes).
  - `L1 Build`: Builder (isolated git worktrees), Tester (verbatim command output), Refactorer.
  - `L2 Research`: Scout (docs, web, free-tier YouTube transcript MCP), CodeMapper (SQLite FTS5 code map), DocMiner.
  - `L3 Quality`: Adversary (review-only live diff attacks), Critic, Challenger, Auditor, SuccessAuditor.
  - `L4 Creative + Ops`: Vision, Griot, N.A.T.A.L.I.E. (cron, budget ledger, approval queue, audit log; not a coder), Archivist, Router, Warden.
- **SQLite FTS5 Memory (`core/schema.sql`, `core/memory.py`)**: Tables `sessions`, `tasks`, `skills`, `code_map`, `notes`, `dream_diffs` with BM25 virtual indexes (`notes_fts`, `code_map_fts`, `sessions_fts`).
- **Accuracy-Preserving Token Strategy**: Targets ~85% fewer input tokens on memory-driven turns and 40–60% overall per task while holding pass rate at 90–95%. Never compresses relevant context; reverts to `conservative` mode if Meter flags `accuracy_regression` (<90%).
- **Dream (`core/dream.py`)**: Four phases (`Collect -> Propose -> Validate -> Commit-as-pending`), gated by `>= 24 hours` AND `>= 5 sessions`, defaulting to `preview` mode (`dream_diffs/<id>.patch`, `status = pending`).
- **Skill Learning (`core/skill_learning.py`)**: Candidates written to `skills/candidates/`, evaluated against `benchmarks/tasks.json` (>=5 tasks vs no-skill baseline), promoted solely to `skills/learned/`. Core `skills/` are immutable.

## Build & Verify

```bash
cd aetherloom
python3 build_adapters.py
python3 tests/test_acceptance.py
```

## Host Installation Guides (Zero Manual Editing)

Run the included cross-platform installer (`install.py`), which compiles fresh adapters, resolves exact absolute paths to Python and `server.py`, and safely merges your existing MCP config without overwriting other servers.

### 1. Antigravity IDE (Global — Works Across All Projects)
```bash
python3 aetherloom/install.py --target antigravity-global
```
Installs `AGENTS.md`, all 5 core `skills/*/SKILL.md`, `hooks.json`, and merges the `aetherloom`, `youtube-transcript`, and `gemini-media` MCP servers into `~/.gemini/antigravity/mcp_config.json`. Restart or reload Antigravity IDE and invoke `/supergravity <your goal>`.

### 2. Antigravity IDE (Single Project Workspace)
```bash
python3 aetherloom/install.py --target antigravity-workspace --workspace /path/to/your/project
```
Installs `.agents/` (`AGENTS.md`, `skills/`, `mcp_config.json`, `hooks.json`) directly into your project root.

### 3. VS Code (Copilot MCP + Antigravity Extension)
```bash
python3 aetherloom/install.py --target vscode --workspace /path/to/your/project
```
Merges `aetherloom`, `youtube-transcript`, and `gemini-media` into `<project>/.vscode/mcp.json` (VS Code's native `servers` stdio format) AND installs `<project>/.agents/` so Antigravity/agentic extensions load `AGENTS.md` and the `/supergravity` skills automatically. Reload VS Code (`Cmd/Ctrl + Shift + P` -> `Developer: Reload Window`).

### 4. Claude Code
```bash
python3 aetherloom/install.py --target claude-code --workspace /path/to/your/project
```
Installs `plugin.json`, `commands/supergravity.md`, all 18 `agents/*.md`, `.mcp.json`, and `hooks/warden_hook.py`.

### 5. Cursor
```bash
python3 aetherloom/install.py --target cursor --workspace /path/to/your/project
```
Installs `.cursor/mcp.json` and `.cursor/rules/aetherloom.mdc`.

### 6. Gemini CLI
```bash
python3 aetherloom/install.py --target gemini-cli
```
Merges MCP servers into `~/.gemini/settings.json` and `~/.gemini/mcp_config.json` with `BeforeTool` / `AfterTool` Warden hooks.

### 7. Codex CLI
```bash
python3 aetherloom/install.py --target codex-cli
```
Installs `~/.codex/hooks.json` and `~/.codex/config.toml`.

### 8. Generic MCP (OpenCode, Windsurf, or any MCP client)
Point your client's MCP configuration at `aetherloom/adapters/generic-mcp/mcp_config.json`, which launches:
```bash
python3 aetherloom/adapters/generic-mcp/server.py
```
Exposes `memory.search`, `meter.record`, `warden.check`, `router.classify`, and `supergravity.orchestrate` over JSON-RPC 2.0 stdio.
