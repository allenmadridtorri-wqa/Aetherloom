---
name: skill-learning
description: Benchmark-gated skill extraction and promotion pipeline. Writes candidates to skills/candidates/, tests against benchmarks/ (>=5 tasks), and promotes solely to skills/learned/.
immutable: true
---

# Skill Learning Skill

## Pipeline
1. **Draft Candidate**: After a verified successful task, extract reusable procedural steps from the recorded trajectory.
2. **Write Candidate**: Save to `skills/candidates/<name>/SKILL.md` and register in SQLite `skills` table with `status = 'candidate'`.
3. **Benchmark Evaluation**: Execute `benchmarks/runner.py` across at least 5 deterministic tasks in `benchmarks/tasks.json`, comparing the candidate skill against a no-skill baseline.
4. **Promotion Gate**:
   - Required: `candidate_pass_rate >= baseline_pass_rate`
   - Required: At least one objective metric improved (higher pass rate, lower token usage without accuracy loss, or faster step completion).
   - The benchmark harness judges promotion—never the agent's self-assessment.
5. **Outcome Handling**:
   - **Pass**: Copy/move candidate into `skills/learned/<name>/SKILL.md`, update `skills` table with `status = 'promoted'`, `benchmark_score`, and `promoted_at`.
   - **Fail**: Keep in `skills/candidates/<name>/` with a `FAILURE_REASON.md` and `status = 'rejected'`. Never promote.

## Immutability & Retention Rules
- Hand-written core skills in `skills/<name>/SKILL.md` are **immutable** and can NEVER be overwritten by skill learning.
- Learned skills live exclusively under `skills/learned/`.
- Old learned skills are never auto-deleted; downgrading or archiving requires explicit human approval.
