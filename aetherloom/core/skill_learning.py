"""Benchmark-gated Skill Learning pipeline for AetherLoom.

Safety invariants enforced in code:
- Drafts candidates strictly into skills/candidates/<name>/SKILL.md.
- Evaluates candidates against benchmarks/ (>=5 tasks) vs a no-skill baseline.
- Promotes strictly into skills/learned/<name>/SKILL.md when pass_rate >= baseline
  AND at least one metric improved.
- Hand-written core skills in skills/<name>/SKILL.md can NEVER be overwritten.
- Old learned skills are never auto-deleted; downgrading requires human approval.
"""

from __future__ import annotations

import datetime as dt
import pathlib
import re
import shutil
import uuid
from typing import Any, Dict

from benchmarks.runner import evaluate_candidate_skill
from core.memory import MemoryStore


PROTECTED_CORE_SKILLS = {"supergravity", "memory", "dream", "meter", "skill-learning"}


def sanitize_skill_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9_-]+", "-", (name or "").lower()).strip("-")
    if not slug:
        raise ValueError("Skill name must contain alphanumeric characters.")
    if slug in PROTECTED_CORE_SKILLS:
        raise PermissionError(
            f"Core hand-written skill '{slug}' is immutable and cannot be overwritten."
        )
    return slug


class SkillLearningPipeline:
    """Drafts, benchmarks, and promotes learned skills safely."""

    def __init__(self, root_dir: str | pathlib.Path, store: MemoryStore) -> None:
        self.root_dir = pathlib.Path(root_dir)
        self.store = store
        self.candidates_dir = self.root_dir / "skills" / "candidates"
        self.learned_dir = self.root_dir / "skills" / "learned"
        self.benchmarks_path = self.root_dir / "benchmarks" / "tasks.json"
        self.candidates_dir.mkdir(parents=True, exist_ok=True)
        self.learned_dir.mkdir(parents=True, exist_ok=True)

    def draft_candidate(self, name: str, description: str, instructions: str) -> Dict[str, Any]:
        slug = sanitize_skill_name(name)
        target_dir = self.candidates_dir / slug
        target_dir.mkdir(parents=True, exist_ok=True)
        skill_file = target_dir / "SKILL.md"
        content = (
            f"---\n"
            f"name: {slug}\n"
            f"description: {description}\n"
            f"status: candidate\n"
            f"origin: learned_trajectory\n"
            f"---\n\n"
            f"# {slug}\n\n"
            f"{instructions.strip()}\n"
        )
        skill_file.write_text(content, encoding="utf-8")
        record = self.store.upsert_skill(
            skill_id=f"sk_{uuid.uuid4().hex[:8]}",
            name=slug,
            path=str(skill_file.relative_to(self.root_dir)),
            status="candidate",
        )
        return {"skill": record, "file": str(skill_file)}

    def evaluate_and_promote(self, name: str) -> Dict[str, Any]:
        slug = sanitize_skill_name(name)
        candidate_dir = self.candidates_dir / slug
        candidate_file = candidate_dir / "SKILL.md"
        if not candidate_file.exists():
            raise FileNotFoundError(f"Candidate skill '{slug}' not found at {candidate_file}")

        eval_result = evaluate_candidate_skill(
            skill_text=candidate_file.read_text(encoding="utf-8"),
            tasks_path=self.benchmarks_path,
        )

        promoted = (
            eval_result["task_count"] >= 5
            and eval_result["candidate_pass_rate"] >= eval_result["baseline_pass_rate"]
            and (
                eval_result["candidate_pass_rate"] > eval_result["baseline_pass_rate"]
                or eval_result["token_reduction_pct"] > 0.0
            )
        )

        if promoted:
            dest_dir = self.learned_dir / slug
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_file = dest_dir / "SKILL.md"
            shutil.copy2(candidate_file, dest_file)
            now_iso = dt.datetime.now(dt.timezone.utc).isoformat()
            self.store.upsert_skill(
                skill_id=f"sk_{slug}",
                name=slug,
                path=str(dest_file.relative_to(self.root_dir)),
                status="promoted",
                benchmark_score=eval_result["candidate_pass_rate"],
                promoted_at=now_iso,
            )
            return {
                "name": slug,
                "promoted": True,
                "status": "promoted",
                "destination": str(dest_file.relative_to(self.root_dir)),
                "evaluation": eval_result,
            }

        failure_reason = (
            f"Promotion blocked: candidate pass rate {eval_result['candidate_pass_rate']}% "
            f"vs baseline {eval_result['baseline_pass_rate']}%, "
            f"token reduction {eval_result['token_reduction_pct']}%."
        )
        (candidate_dir / "FAILURE_REASON.md").write_text(failure_reason + "\n", encoding="utf-8")
        self.store.upsert_skill(
            skill_id=f"sk_{slug}",
            name=slug,
            path=str(candidate_file.relative_to(self.root_dir)),
            status="rejected",
            benchmark_score=eval_result["candidate_pass_rate"],
        )
        return {
            "name": slug,
            "promoted": False,
            "status": "rejected",
            "failure_reason": failure_reason,
            "evaluation": eval_result,
        }

    def downgrade_skill(self, name: str, human_approved: bool = False) -> Dict[str, Any]:
        """Downgrading an existing learned skill requires explicit human approval; never auto-deleted."""
        slug = sanitize_skill_name(name)
        if not human_approved:
            raise PermissionError("Downgrading a learned skill requires explicit human approval.")
        dest_file = self.learned_dir / slug / "SKILL.md"
        if not dest_file.exists():
            raise FileNotFoundError(f"Learned skill '{slug}' not found.")
        self.store.upsert_skill(
            skill_id=f"sk_{slug}",
            name=slug,
            path=str(dest_file.relative_to(self.root_dir)),
            status="downgraded",
        )
        return {"name": slug, "status": "downgraded", "deleted": False}
