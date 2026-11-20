---
name: dream
description: Scheduled four-phase memory consolidation job (Collect, Propose, Validate, Commit-as-pending) triggered by N.A.T.A.L.I.E. Defaults to preview mode and never mutates long-term memory automatically.
immutable: true
---

# Dream Consolidation Skill

## What Dream Actually Is
Dream is a scheduled batch job that inspects recent session logs and proposes unified diff patches to deduplicate or organize memory notes. It is a deterministic script plus LLM proposal step over local files—not consciousness, dreaming, or sentience.

## Scheduling Gate (Enforced in Code)
Dream is triggered ONLY by `N.A.T.A.L.I.E.`'s cron scheduler (never inline during live tasks) and ONLY when BOTH conditions hold:
1. At least `24 hours` have elapsed since the previous Dream run.
2. At least `5 sessions` have been logged since the previous Dream run.

## Four Phases
1. **Collect**: Read recent `sessions` and `notes` from SQLite since the last Dream watermark.
2. **Propose**: Generate a proposed consolidation text (deduplicating redundant notes and normalizing references) without modifying any live table or file.
3. **Validate**: Run structural and citation checks to ensure no factual keys, symbol names, or constraints were dropped or hallucinated.
4. **Commit-as-pending**: Write a unified diff patch to `dream_diffs/<dream_id>.patch` and record a row in `dream_diffs` with `status = 'pending'`.

## Safety Invariant
- Default execution mode is `preview` (`apply=False`).
- Because an LLM proposing memory edits can hallucinate, automatic commits are prohibited.
- Applying a pending patch requires explicit approval from the human user or `SuccessAuditor`, which records `approved_by` and `approved_at` in `dream_diffs`.
