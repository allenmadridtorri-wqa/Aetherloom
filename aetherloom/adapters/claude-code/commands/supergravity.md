---
name: supergravity
description: Canonical /supergravity multi-agent orchestration skill for AetherLoom. Routes goals across swarm, teamwork, and hybrid modes with Archivist FTS5 memory, Meter tracking, and Warden spend guardrails.
immutable: true
---

# `/supergravity` Orchestration Skill

## Invocation
`/supergravity <goal>`

## Step-by-Step Execution Protocol
1. **Startup Tier Check**: Invoke `core/tier_probe.py` to detect whether the active API key is `free-tier` or `paid`. On free-tier keys, immediately mark `generate_video` (Veo) as disabled with an explicit warning and retain `generate_image` (Nano Banana) and `generate_speech` (TTS) within free-tier rate limits (~15 RPM / ~1,500 RPD on Gemini 3.6 Flash).
2. **Goal Registration**: `Commander` records the user's goal, creates a run ID, and initializes the append-only message board at `runs/<run_id>/board.ndjson`. Commander never writes repository source code directly.
3. **Mode Classification (`Router`)**:
   - `swarm`: Multi-file, multi-module, parallelizable implementation or refactor. Builders work in isolated git worktrees (`git worktree add`). `Adversary` attacks diffs live with review-only permissions. Idle subagents hold zero tokens.
   - `teamwork`: Multi-milestone, cross-day, deep research, or verification-heavy work. Organized into layered milestones; every milestone must pass `Critic` + `Challenger` + `Auditor` before advancing. Final release gate is `SuccessAuditor`.
   - `hybrid`: Both parallel implementation and multi-milestone research/verification signals are present. Executes parallel sprints bounded by formal milestone verification gates.
4. **Always-On Services**:
   - **Archivist (`memory`)**: Queries SQLite FTS5 BM25 (`k=5` default) for relevant `notes`, `code_map`, and `sessions`, injecting only fragments that fit the subagent's context budget.
   - **Meter (`meter`)**: Records `task_id, agent, model, input_tokens, output_tokens, cached_tokens, cost_usd, pass_rate, mode, timestamp` on every subagent invocation. Flags `accuracy_regression` if pass rate drops below 90% and forces `Router` back to `conservative` strategy.
   - **Warden (`warden`)**: Intercepts every billed tool call (`Vision`, `Griot`, Veo, or paid API endpoints) before execution. Returns `ALLOW`, `DENY`, or `NEED_APPROVAL`. `DENY` halts immediately; `NEED_APPROVAL` pauses and submits to `N.A.T.A.L.I.E.`'s approval queue.
5. **User Reporting**: `Commander` emits a concise summary containing status, active blockers, and next step. The full execution trace lives in `runs/<run_id>/board.ndjson`.

## Hard Prohibitions
- Never compress relevant context to meet a token budget.
- Never claim sentience, consciousness, or emotional states.
- Never depend on any third-party `supergravity` PyPI or npm package.
