"""N.A.T.A.L.I.E. — Operations & Scheduling subagent runtime.

Mandate:
- Owns cron triggers (including Dream scheduling >=24h AND >=5 sessions).
- Owns the budget ledger and freezes billed agents (Vision, Griot) near hard cap.
- Owns the approval queue for every NEED_APPROVAL verdict from Warden.
- Writes every escalation and decision to an operations audit log (ops_audit.ndjson).
- NOT a coder: produces operational logs and approval decisions only.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import uuid
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class ApprovalRequest:
    id: str
    agent: str
    tool: str
    estimated_cost_usd: float
    reason: str
    status: str  # pending, approved, denied
    created_at: str
    decided_by: Optional[str] = None
    decided_at: Optional[str] = None


class NatalieOps:
    """Operations controller owned by N.A.T.A.L.I.E."""

    def __init__(
        self,
        ops_dir: str | pathlib.Path,
        hard_cap_usd: float = 0.0,
        freeze_ratio: float = 0.90,
    ) -> None:
        self.ops_dir = pathlib.Path(ops_dir)
        self.ops_dir.mkdir(parents=True, exist_ok=True)
        self.audit_log_path = self.ops_dir / "ops_audit.ndjson"
        self.state_path = self.ops_dir / "natalie_state.json"
        self.hard_cap_usd = float(hard_cap_usd)
        self.freeze_ratio = float(freeze_ratio)
        self.spent_usd: float = 0.0
        self.billed_agents_frozen: bool = False
        self.approval_queue: List[ApprovalRequest] = []
        self._load_state()

    def _load_state(self) -> None:
        if not self.state_path.exists():
            return
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            self.spent_usd = float(data.get("spent_usd", 0.0))
            self.hard_cap_usd = float(data.get("hard_cap_usd", self.hard_cap_usd))
            self.billed_agents_frozen = bool(data.get("billed_agents_frozen", False))
            self.approval_queue = [
                ApprovalRequest(**item) for item in data.get("approval_queue", [])
            ]
        except Exception:
            pass

    def _save_state(self) -> None:
        payload = {
            "spent_usd": round(self.spent_usd, 6),
            "hard_cap_usd": round(self.hard_cap_usd, 6),
            "billed_agents_frozen": self.billed_agents_frozen,
            "approval_queue": [asdict(item) for item in self.approval_queue],
        }
        self.state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def log_event(self, event_type: str, details: Dict[str, Any]) -> Dict[str, Any]:
        entry = {
            "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
            "actor": "N.A.T.A.L.I.E.",
            "event": event_type,
            "details": details,
        }
        with self.audit_log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
        return entry

    def set_hard_cap(self, hard_cap_usd: float) -> Dict[str, Any]:
        self.hard_cap_usd = max(0.0, float(hard_cap_usd))
        self._evaluate_freeze()
        self._save_state()
        return self.log_event(
            "hard_cap_updated",
            {"hard_cap_usd": self.hard_cap_usd, "billed_agents_frozen": self.billed_agents_frozen},
        )

    def record_spend(self, agent: str, tool: str, cost_usd: float) -> Dict[str, Any]:
        self.spent_usd = round(self.spent_usd + float(cost_usd), 6)
        frozen_now = self._evaluate_freeze()
        self._save_state()
        return self.log_event(
            "spend_recorded",
            {
                "agent": agent,
                "tool": tool,
                "cost_usd": round(float(cost_usd), 6),
                "cumulative_spend_usd": self.spent_usd,
                "hard_cap_usd": self.hard_cap_usd,
                "billed_agents_frozen": frozen_now,
            },
        )

    def _evaluate_freeze(self) -> bool:
        if self.hard_cap_usd > 0 and self.spent_usd >= self.hard_cap_usd * self.freeze_ratio:
            if not self.billed_agents_frozen:
                self.billed_agents_frozen = True
                self.log_event(
                    "billed_agents_frozen",
                    {
                        "reason": "Spend reached freeze threshold near hard cap",
                        "spent_usd": self.spent_usd,
                        "hard_cap_usd": self.hard_cap_usd,
                        "frozen_agents": ["vision", "griot"],
                    },
                )
        elif self.hard_cap_usd > 0 and self.spent_usd < self.hard_cap_usd * self.freeze_ratio:
            self.billed_agents_frozen = False
        return self.billed_agents_frozen

    def enqueue_approval(
        self, agent: str, tool: str, estimated_cost_usd: float, reason: str
    ) -> ApprovalRequest:
        req = ApprovalRequest(
            id=f"apr_{uuid.uuid4().hex[:8]}",
            agent=agent,
            tool=tool,
            estimated_cost_usd=round(float(estimated_cost_usd), 6),
            reason=reason,
            status="pending",
            created_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        )
        self.approval_queue.insert(0, req)
        self._save_state()
        self.log_event("approval_enqueued", asdict(req))
        return req

    def decide_approval(
        self, approval_id: str, decision: str, decided_by: str = "user"
    ) -> Optional[ApprovalRequest]:
        normalized = decision.lower().strip()
        if normalized not in ("approved", "denied"):
            raise ValueError("Decision must be 'approved' or 'denied'")
        for req in self.approval_queue:
            if req.id == approval_id:
                req.status = normalized
                req.decided_by = decided_by
                req.decided_at = dt.datetime.now(dt.timezone.utc).isoformat()
                if normalized == "approved":
                    self.spent_usd = round(self.spent_usd + req.estimated_cost_usd, 6)
                    self._evaluate_freeze()
                self._save_state()
                self.log_event("approval_decided", asdict(req))
                return req
        return None

    def read_audit_log(self, limit: int = 40) -> List[Dict[str, Any]]:
        if not self.audit_log_path.exists():
            return []
        lines = self.audit_log_path.read_text(encoding="utf-8").splitlines()
        parsed = [json.loads(line) for line in lines if line.strip()]
        return list(reversed(parsed[-limit:]))

    def snapshot(self) -> Dict[str, Any]:
        return {
            "spent_usd": round(self.spent_usd, 6),
            "hard_cap_usd": round(self.hard_cap_usd, 6),
            "billed_agents_frozen": self.billed_agents_frozen,
            "approval_queue": [asdict(item) for item in self.approval_queue],
            "audit_log": self.read_audit_log(),
        }
