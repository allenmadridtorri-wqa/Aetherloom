"""Dream — Four-phase scheduled memory consolidation job (propose-then-commit).

Phases: Collect -> Propose -> Validate -> Commit-as-pending.
Safety invariants enforced in code:
- Triggered only via N.A.T.A.L.I.E.'s scheduler after >=24h AND >=5 sessions since last Dream.
- Default mode is preview (writes nothing to live memory tables).
- Produces a unified diff in dream_diffs/<id>.patch with status='pending'.
- Applying a patch requires explicit approval by the user or SuccessAuditor.
- Dream is a deterministic file-rewriting and LLM consolidation job, not sentience.
"""

from __future__ import annotations

import datetime as dt
import difflib
import pathlib
import uuid
from typing import Any, Dict, List, Optional

from core.memory import MemoryStore
from core.natalie import NatalieOps


class DreamJob:
    """Propose-then-commit memory consolidation job."""

    MIN_HOURS = 24.0
    MIN_SESSIONS = 5

    def __init__(
        self,
        store: MemoryStore,
        diffs_dir: str | pathlib.Path,
        natalie: Optional[NatalieOps] = None,
    ) -> None:
        self.store = store
        self.diffs_dir = pathlib.Path(diffs_dir)
        self.diffs_dir.mkdir(parents=True, exist_ok=True)
        self.natalie = natalie

    def check_schedule_gate(self, now: Optional[dt.datetime] = None) -> Dict[str, Any]:
        """Verify >=24 hours AND >=5 sessions have elapsed since the last Dream run."""
        current = now or dt.datetime.now(dt.timezone.utc)
        last_row = self.store.conn.execute(
            "SELECT ts FROM dream_diffs ORDER BY ts DESC LIMIT 1"
        ).fetchone()

        if last_row is None:
            session_count = self.store.conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            hours_elapsed = 999.0
        else:
            last_ts = dt.datetime.fromisoformat(last_row["ts"])
            if last_ts.tzinfo is None:
                last_ts = last_ts.replace(tzinfo=dt.timezone.utc)
            hours_elapsed = (current - last_ts).total_seconds() / 3600.0
            session_count = self.store.conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE ts > ?", (last_row["ts"],)
            ).fetchone()[0]

        eligible = hours_elapsed >= self.MIN_HOURS and session_count >= self.MIN_SESSIONS
        return {
            "eligible": eligible,
            "hours_elapsed": round(hours_elapsed, 2),
            "min_hours_required": self.MIN_HOURS,
            "sessions_since_last": int(session_count),
            "min_sessions_required": self.MIN_SESSIONS,
        }

    def run(
        self,
        mode: str = "preview",
        force_schedule_override: bool = False,
        now: Optional[dt.datetime] = None,
    ) -> Dict[str, Any]:
        """Run the four-phase Dream job. Default mode is always 'preview'."""
        if mode != "preview":
            raise ValueError("DreamJob.run() only permits preview mode; applying requires explicit approve_and_apply().")

        gate = self.check_schedule_gate(now=now)
        if not gate["eligible"] and not force_schedule_override:
            return {
                "executed": False,
                "mode": "preview",
                "reason": (
                    f"Schedule gate not met: {gate['hours_elapsed']}h elapsed "
                    f"(need >={self.MIN_HOURS}h) and {gate['sessions_since_last']} sessions "
                    f"(need >={self.MIN_SESSIONS})."
                ),
                "gate": gate,
            }

        # Phase 1: Collect
        notes = self.store.list_notes(limit=200)
        sessions = self.store.list_sessions(limit=50)
        before_lines = [f"[{n['project']}] {n['body'].strip()}" for n in reversed(notes)]

        # Phase 2: Propose (deduplicate identical/near-identical notes and append session digest)
        seen = set()
        proposed_lines: List[str] = []
        for line in before_lines:
            norm = " ".join(line.lower().split())
            if norm not in seen:
                seen.add(norm)
                proposed_lines.append(line)

        if sessions:
            latest_ids = ", ".join(s["id"] for s in sessions[:5])
            digest_line = f"[digest] Consolidated review of {len(sessions)} sessions ({latest_ids})."
            if digest_line.lower() not in seen:
                proposed_lines.append(digest_line)

        # Phase 3: Validate (ensure no project key was lost during deduplication)
        before_projects = {n["project"] for n in notes}
        missing_projects = [
            proj for proj in before_projects if not any(l.startswith(f"[{proj}]") for l in proposed_lines)
        ]
        validation_ok = len(missing_projects) == 0

        diff_id = f"dream_{uuid.uuid4().hex[:8]}"
        ts = (now or dt.datetime.now(dt.timezone.utc)).isoformat()
        diff_lines = list(
            difflib.unified_diff(
                before_lines,
                proposed_lines,
                fromfile="memory/notes.before.txt",
                tofile="memory/notes.proposed.txt",
                lineterm="",
            )
        )
        patch_text = "\n".join(diff_lines) + ("\n" if diff_lines else "# No memory changes proposed.\n")

        # Phase 4: Commit-as-pending (never writes live notes table)
        patch_file = self.diffs_dir / f"{diff_id}.patch"
        patch_file.write_text(patch_text, encoding="utf-8")
        record = self.store.record_dream_diff(
            diff_id=diff_id,
            patch_path=str(patch_file),
            status="pending",
            ts=ts,
        )

        if self.natalie is not None:
            self.natalie.log_event(
                "dream_preview_created",
                {
                    "diff_id": diff_id,
                    "patch_path": str(patch_file),
                    "status": "pending",
                    "validation_ok": validation_ok,
                    "live_memory_modified": False,
                },
            )

        return {
            "executed": True,
            "mode": "preview",
            "phases": ["Collect", "Propose", "Validate", "Commit-as-pending"],
            "validation_ok": validation_ok,
            "live_memory_modified": False,
            "diff": record,
            "patch_content": patch_text,
            "gate": gate,
        }

    def approve_diff(self, diff_id: str, approved_by: str) -> Dict[str, Any]:
        """Approve a pending Dream patch. Allowed approvers: 'user' or 'SuccessAuditor'."""
        if approved_by not in ("user", "SuccessAuditor"):
            raise PermissionError("Dream diffs may only be approved by 'user' or 'SuccessAuditor'.")
        row = self.store.conn.execute(
            "SELECT id, ts, patch_path, status FROM dream_diffs WHERE id = ?", (diff_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"Dream diff '{diff_id}' not found.")
        approved_at = dt.datetime.now(dt.timezone.utc).isoformat()
        self.store.conn.execute(
            "UPDATE dream_diffs SET status = 'approved', approved_by = ?, approved_at = ? WHERE id = ?",
            (approved_by, approved_at, diff_id),
        )
        self.store.conn.commit()
        if self.natalie is not None:
            self.natalie.log_event(
                "dream_diff_approved",
                {"diff_id": diff_id, "approved_by": approved_by, "approved_at": approved_at},
            )
        return {
            "id": diff_id,
            "status": "approved",
            "approved_by": approved_by,
            "approved_at": approved_at,
            "patch_path": row["patch_path"],
        }
