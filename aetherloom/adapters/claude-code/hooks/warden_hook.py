#!/usr/bin/env python3
"""JSON stdin/stdout PreTool/BeforeTool hook enforcing Warden & free-tier Veo guardrails."""

from __future__ import annotations

import json
import pathlib
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from core.natalie import NatalieOps
from core.tier_probe import probe_api_tier
from core.warden import Warden


def main() -> None:
    raw = sys.stdin.read().strip() or "{}"
    payload = json.loads(raw)
    tool_name = payload.get("tool_name") or payload.get("tool") or ""
    agent = payload.get("agent", "Vision")

    if tool_name not in ("generate_video", "generate_image", "generate_speech", "paid_llm_call"):
        sys.stdout.write(json.dumps({"decision": "allow", "reason": "Non-billed tool."}) + "\n")
        return

    caps = probe_api_tier()
    natalie = NatalieOps(PLUGIN_ROOT / "runs", hard_cap_usd=0.0)
    warden = Warden(caps, natalie, hard_cap_usd=0.0)
    res = warden.check(agent=agent, tool=tool_name)

    if res.verdict == "ALLOW":
        sys.stdout.write(json.dumps({"decision": "allow", "reason": res.reason}) + "\n")
    elif res.verdict == "NEED_APPROVAL":
        sys.stdout.write(
            json.dumps(
                {
                    "decision": "ask",
                    "approval_id": res.approval_id,
                    "reason": res.reason,
                }
            )
            + "\n"
        )
    else:
        sys.stdout.write(json.dumps({"decision": "block", "reason": res.reason}) + "\n")


if __name__ == "__main__":
    main()
