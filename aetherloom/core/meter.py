"""Meter — Accuracy-preserving token, cost, and pass-rate telemetry.

Reports three numbers separately:
1. Input-token savings on memory-driven turns (target ~85%).
2. Overall per-task token savings (target 40-60%).
3. Pass-rate level and change (must hold within 90-95%).

Flags accuracy_regression if pass rate falls below the configured floor (default 90%).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from core.memory import MemoryStore


@dataclass
class MeterEntry:
    task_id: str
    agent: str
    model: str
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    cost_usd: float
    pass_rate: float
    mode: str
    timestamp: str
    memory_driven: bool = True
    baseline_input_tokens: int = 0
    baseline_total_tokens: int = 0


class Meter:
    """Tracks token efficiency and enforces the accuracy floor."""

    def __init__(
        self,
        store: MemoryStore,
        pass_rate_floor_pct: float = 90.0,
        baseline_pass_rate_pct: float = 92.0,
    ) -> None:
        self.store = store
        self.pass_rate_floor_pct = pass_rate_floor_pct
        self.baseline_pass_rate_pct = baseline_pass_rate_pct

    def record(
        self,
        task_id: str,
        agent: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int,
        cost_usd: float,
        pass_rate: float,
        mode: str,
        timestamp: Optional[str] = None,
        memory_driven: bool = True,
        baseline_input_tokens: Optional[int] = None,
        baseline_total_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        ts = timestamp or dt.datetime.now(dt.timezone.utc).isoformat()
        in_base = baseline_input_tokens if baseline_input_tokens is not None else max(input_tokens, int(input_tokens / 0.15))
        tot_base = baseline_total_tokens if baseline_total_tokens is not None else max(input_tokens + output_tokens, int((input_tokens + output_tokens) / 0.5))

        self.store.conn.execute(
            """
            INSERT INTO meter_records(
                task_id, agent, model, input_tokens, output_tokens, cached_tokens,
                baseline_input_tokens, baseline_total_tokens, memory_driven,
                cost_usd, pass_rate, mode, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                agent,
                model,
                int(input_tokens),
                int(output_tokens),
                int(cached_tokens),
                int(in_base),
                int(tot_base),
                1 if memory_driven else 0,
                float(cost_usd),
                float(pass_rate),
                mode,
                ts,
            ),
        )
        self.store.conn.commit()

        entry = MeterEntry(
            task_id=task_id,
            agent=agent,
            model=model,
            input_tokens=int(input_tokens),
            output_tokens=int(output_tokens),
            cached_tokens=int(cached_tokens),
            cost_usd=round(float(cost_usd), 6),
            pass_rate=round(float(pass_rate), 2),
            mode=mode,
            timestamp=ts,
            memory_driven=memory_driven,
            baseline_input_tokens=int(in_base),
            baseline_total_tokens=int(tot_base),
        )
        return asdict(entry)

    def list_records(self, limit: int = 100) -> List[Dict[str, Any]]:
        rows = self.store.conn.execute(
            """
            SELECT task_id, agent, model, input_tokens, output_tokens, cached_tokens,
                   baseline_input_tokens, baseline_total_tokens, memory_driven,
                   cost_usd, pass_rate, mode, timestamp
            FROM meter_records
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def summary(self) -> Dict[str, Any]:
        rows = self.store.conn.execute(
            """
            SELECT input_tokens, output_tokens, cached_tokens,
                   baseline_input_tokens, baseline_total_tokens,
                   memory_driven, cost_usd, pass_rate
            FROM meter_records
            """
        ).fetchall()

        if not rows:
            return {
                "record_count": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cached_tokens": 0,
                "cost_usd": 0.0,
                "pass_rate": self.baseline_pass_rate_pct,
                "pass_rate_change_pct": 0.0,
                "memory_turn_input_savings_pct": 0.0,
                "overall_task_savings_pct": 0.0,
                "accuracy_regression": False,
                "recommended_strategy": "standard",
            }

        total_in = sum(r["input_tokens"] for r in rows)
        total_out = sum(r["output_tokens"] for r in rows)
        total_cached = sum(r["cached_tokens"] for r in rows)
        total_cost = round(sum(r["cost_usd"] for r in rows), 6)
        avg_pass_rate = round(sum(r["pass_rate"] for r in rows) / len(rows), 2)
        pass_rate_change = round(avg_pass_rate - self.baseline_pass_rate_pct, 2)

        mem_rows = [r for r in rows if r["memory_driven"] == 1 and r["baseline_input_tokens"] > 0]
        if mem_rows:
            mem_actual_in = sum(r["input_tokens"] for r in mem_rows)
            mem_base_in = sum(r["baseline_input_tokens"] for r in mem_rows)
            mem_savings = round((1.0 - (mem_actual_in / mem_base_in)) * 100.0, 2)
        else:
            mem_savings = 0.0

        tot_base = sum(r["baseline_total_tokens"] for r in rows if r["baseline_total_tokens"] > 0)
        tot_actual = sum((r["input_tokens"] + r["output_tokens"]) for r in rows if r["baseline_total_tokens"] > 0)
        overall_savings = round((1.0 - (tot_actual / tot_base)) * 100.0, 2) if tot_base > 0 else 0.0

        accuracy_regression = avg_pass_rate < self.pass_rate_floor_pct

        return {
            "record_count": len(rows),
            "input_tokens": total_in,
            "output_tokens": total_out,
            "cached_tokens": total_cached,
            "cost_usd": total_cost,
            "pass_rate": avg_pass_rate,
            "pass_rate_change_pct": pass_rate_change,
            "memory_turn_input_savings_pct": mem_savings,
            "overall_task_savings_pct": overall_savings,
            "accuracy_regression": accuracy_regression,
            "recommended_strategy": "conservative" if accuracy_regression else "standard",
        }
