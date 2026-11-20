#!/usr/bin/env python3
"""Standalone Generic MCP Server for AetherLoom (/supergravity).

Exposes JSON-RPC 2.0 stdio tools usable by any MCP-compatible host:
  - memory.search
  - meter.record
  - warden.check
  - router.classify
  - supergravity.orchestrate
"""

from __future__ import annotations

import json
import pathlib
import sys
from typing import Any, Dict

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from core.memory import MemoryStore
from core.meter import Meter
from core.natalie import NatalieOps
from core.orchestrator import SupergravityOrchestrator
from core.router import Router
from core.tier_probe import probe_api_tier
from core.warden import Warden


TOOLS_MANIFEST = [
    {
        "name": "memory.search",
        "description": "Search SQLite FTS5 memory (notes, code_map, sessions) ranked by BM25 within context budget.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "k": {"type": "integer", "default": 5},
                "context_budget_tokens": {"type": "integer", "default": 1200}
            },
            "required": ["query"]
        }
    },
    {
        "name": "meter.record",
        "description": "Record task token, cost, cached token, and pass-rate metrics.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "agent": {"type": "string"},
                "model": {"type": "string"},
                "input_tokens": {"type": "integer"},
                "output_tokens": {"type": "integer"},
                "cached_tokens": {"type": "integer", "default": 0},
                "cost_usd": {"type": "number", "default": 0.0},
                "pass_rate": {"type": "number", "default": 100.0},
                "mode": {"type": "string", "enum": ["swarm", "teamwork", "hybrid"]}
            },
            "required": ["task_id", "agent", "model", "input_tokens", "output_tokens", "mode"]
        }
    },
    {
        "name": "warden.check",
        "description": "Preflight spend and free-tier capability check returning ALLOW, DENY, or NEED_APPROVAL.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent": {"type": "string"},
                "tool": {"type": "string"},
                "units": {"type": "integer", "default": 1},
                "custom_cost_usd": {"type": "number"}
            },
            "required": ["agent", "tool"]
        }
    },
    {
        "name": "router.classify",
        "description": "Classify a goal into swarm, teamwork, or hybrid with accuracy-preserving model routing.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "goal": {"type": "string"},
                "accuracy_regression": {"type": "boolean", "default": False}
            },
            "required": ["goal"]
        }
    },
    {
        "name": "supergravity.orchestrate",
        "description": "Execute /supergravity orchestration and append trace to runs/<id>/board.ndjson.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "goal": {"type": "string"},
                "requested_media_tool": {"type": "string"}
            },
            "required": ["goal"]
        }
    }
]


class AetherLoomMCPServer:
    def __init__(self, data_dir: pathlib.Path | None = None) -> None:
        base = data_dir or (PLUGIN_ROOT / "data")
        base.mkdir(parents=True, exist_ok=True)
        self.store = MemoryStore(base / "aetherloom.db")
        self.natalie = NatalieOps(PLUGIN_ROOT / "runs", hard_cap_usd=0.0)
        self.caps = probe_api_tier()
        self.meter = Meter(self.store)
        self.router = Router(fast_model=self.caps.default_model)
        self.warden = Warden(self.caps, self.natalie, hard_cap_usd=0.0)
        self.orchestrator = SupergravityOrchestrator(
            root_dir=PLUGIN_ROOT,
            store=self.store,
            natalie=self.natalie,
            capabilities=self.caps,
            hard_cap_usd=0.0,
        )

    def handle_request(self, req: Dict[str, Any]) -> Dict[str, Any]:
        req_id = req.get("id")
        method = req.get("method", "")
        params = req.get("params") or {}

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "aetherloom-mcp", "version": "1.0.0"},
                    "capabilities": {"tools": {}},
                },
            }

        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS_MANIFEST}}

        if method == "tools/call":
            name = params.get("name", "")
            args = params.get("arguments") or {}
            try:
                if name == "memory.search":
                    data = self.store.search(
                        query=args["query"],
                        k=int(args.get("k", 5)),
                        context_budget_tokens=int(args.get("context_budget_tokens", 1200)),
                    )
                elif name == "meter.record":
                    data = self.meter.record(
                        task_id=args["task_id"],
                        agent=args["agent"],
                        model=args["model"],
                        input_tokens=int(args["input_tokens"]),
                        output_tokens=int(args["output_tokens"]),
                        cached_tokens=int(args.get("cached_tokens", 0)),
                        cost_usd=float(args.get("cost_usd", 0.0)),
                        pass_rate=float(args.get("pass_rate", 100.0)),
                        mode=args["mode"],
                    )
                elif name == "warden.check":
                    data = self.warden.check(
                        agent=args["agent"],
                        tool=args["tool"],
                        units=int(args.get("units", 1)),
                        custom_cost_usd=args.get("custom_cost_usd"),
                    ).to_dict()
                elif name == "router.classify":
                    data = self.router.classify(
                        goal=args["goal"],
                        accuracy_regression=bool(args.get("accuracy_regression", False)),
                    ).to_dict()
                elif name == "supergravity.orchestrate":
                    data = self.orchestrator.orchestrate(
                        goal=args["goal"],
                        requested_media_tool=args.get("requested_media_tool"),
                    )
                else:
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32601, "message": f"Unknown tool: {name}"},
                    }
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": json.dumps(data)}]},
                }
            except Exception as exc:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32000, "message": str(exc)},
                }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }


def main() -> None:
    server = AetherLoomMCPServer()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        req = json.loads(line)
        resp = server.handle_request(req)
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
