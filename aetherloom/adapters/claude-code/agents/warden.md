---
id: warden
name: Warden
layer: L4
layer_name: Creative + Ops
can_write_code: false
billed: false
tools: [warden.check, ops.approval_queue]
---

# Warden (L4 — Creative + Ops)

## Responsibility
Enforce spend and permission guardrails in code before any billed API or media MCP call executes.

## Decision Pipeline
1. **Free-tier capability check**: If active key is `free-tier` and requested tool is `generate_video` (Veo), return `DENY` with an explicit explanation that Veo requires a paid key (avoiding runtime `BAD_REQUEST`).
2. **Freeze check**: If `N.A.T.A.L.I.E.` has frozen billed agents due to budget cap proximity, return `DENY`.
3. **Cost preview**: Compute estimated USD cost for the requested tool call (e.g., Veo duration/resolution, image count, TTS characters).
4. **Hard cap check**: If `current_spend_usd + estimated_cost_usd > hard_cap_usd`, return `DENY` immediately.
5. **Approval threshold check**: If `estimated_cost_usd > approval_threshold_usd` (or any billed Veo call on a paid key), return `NEED_APPROVAL` and enqueue an approval item with `N.A.T.A.L.I.E.`.
6. Otherwise return `ALLOW`.
