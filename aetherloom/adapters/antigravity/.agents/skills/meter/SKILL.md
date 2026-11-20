---
name: meter
description: Accuracy-preserving token, cost, and pass-rate telemetry skill. Separates memory-turn savings, overall task savings, and pass-rate regression monitoring.
immutable: true
---

# Meter Telemetry Skill

## Recorded Per-Task Schema
Every subagent task records:
- `task_id`
- `agent`
- `model`
- `input_tokens`
- `output_tokens`
- `cached_tokens`
- `cost_usd`
- `pass_rate`
- `mode` (`swarm`, `teamwork`, `hybrid`)
- `timestamp`

## Three Mandatory Separate Reports
1. **Memory-Turn Input-Token Savings (%)**: Measured against unindexed full-context baseline on memory-driven turns. Target: `~85%`.
2. **Overall Per-Task Token Savings (%)**: Combined input + output reduction across full runs via selective retrieval, prefix caching, and model routing. Target: `40–60%`.
3. **Pass-Rate Delta & Floor (%)**: Measured against real test execution outcomes (never self-graded). Must remain within `90–95%`.

## Accuracy Regression Circuit Breaker
If observed `pass_rate` falls below the configured floor (`90.0%`), `Meter` emits `accuracy_regression = true`. `Router` immediately switches to `conservative` routing (broader unpruned slices and stronger reasoning tier) until pass rate recovers. Meter never rewards lossy compression of relevant context.
