#!/usr/bin/env python3
"""Canonical Host Adapter Generator for AetherLoom (/supergravity).

Reads canonical manifest.json, AGENTS.md, skills/*/SKILL.md, and agents/*.md
and emits ready-to-install adapters for:
  1. Antigravity (.agents/AGENTS.md, .agents/skills/*/SKILL.md, .agents/mcp_config.json, .agents/hooks.json)
  2. Claude Code (plugin.json, commands/supergravity.md, agents/*.md, .mcp.json, hooks/warden_hook.py)
  3. Cursor (.cursor/mcp.json, .cursor/rules/aetherloom.mdc)
  4. Gemini CLI (settings.json, mcp_config.json, hooks/before_after_tool.py)
  5. Codex CLI (hooks.json, config.toml)
  6. Generic MCP (server.py, mcp_config.json)

Adapters are ALWAYS generated from canonical source, never hand-edited.
"""

from __future__ import annotations

import json
import pathlib
import shutil
from typing import Any, Dict, List


ROOT = pathlib.Path(__file__).resolve().parent
ADAPTERS_DIR = ROOT / "adapters"


GENERIC_MCP_SERVER_CODE = '''#!/usr/bin/env python3
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
        sys.stdout.write(json.dumps(resp) + "\\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
'''


WARDEN_HOOK_SCRIPT = '''#!/usr/bin/env python3
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
        sys.stdout.write(json.dumps({"decision": "allow", "reason": "Non-billed tool."}) + "\\n")
        return

    caps = probe_api_tier()
    natalie = NatalieOps(PLUGIN_ROOT / "runs", hard_cap_usd=0.0)
    warden = Warden(caps, natalie, hard_cap_usd=0.0)
    res = warden.check(agent=agent, tool=tool_name)

    if res.verdict == "ALLOW":
        sys.stdout.write(json.dumps({"decision": "allow", "reason": res.reason}) + "\\n")
    elif res.verdict == "NEED_APPROVAL":
        sys.stdout.write(
            json.dumps(
                {
                    "decision": "ask",
                    "approval_id": res.approval_id,
                    "reason": res.reason,
                }
            )
            + "\\n"
        )
    else:
        sys.stdout.write(json.dumps({"decision": "block", "reason": res.reason}) + "\\n")


if __name__ == "__main__":
    main()
'''


def _write_json(path: pathlib.Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def _write_text(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _base_mcp_servers() -> Dict[str, Any]:
    return {
        "aetherloom": {
            "command": "python3",
            "args": ["aetherloom/adapters/generic-mcp/server.py"],
            "env": {"AETHERLOOM_FREE_TIER_DEFAULT": "true"},
        },
        "youtube-transcript": {
            "command": "npx",
            "args": ["-y", "yt-transcript-mcp"],
            "description": "Free-tier YouTube transcript MCP used by Scout (alternatives: tubetotranscript-mcp, iflow-mcp-boxabirds-yt-gemini-mcp).",
        },
        "gemini-media": {
            "command": "npx",
            "args": ["-y", "gstudioaimcp"],
            "description": "Gemini media MCP (generate_image Nano Banana, generate_speech TTS; generate_video Veo disabled on free-tier keys and gated by Warden).",
        },
    }


def build_all_adapters() -> Dict[str, List[str]]:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    root_agents_md = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    generated: Dict[str, List[str]] = {}

    # Clean adapters directory to guarantee generated-only artifacts
    if ADAPTERS_DIR.exists():
        shutil.rmtree(ADAPTERS_DIR)
    ADAPTERS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Generic MCP
    generic_dir = ADAPTERS_DIR / "generic-mcp"
    _write_text(generic_dir / "server.py", GENERIC_MCP_SERVER_CODE)
    _write_json(generic_dir / "mcp_config.json", {"mcpServers": _base_mcp_servers()})
    generated["generic-mcp"] = [
        "adapters/generic-mcp/server.py",
        "adapters/generic-mcp/mcp_config.json",
    ]

    # 2. Antigravity (MCP-only + .agents/AGENTS.md + .agents/skills/*/SKILL.md + .agents/mcp_config.json + hooks)
    ag_dir = ADAPTERS_DIR / "antigravity" / ".agents"
    _write_text(ag_dir / "AGENTS.md", root_agents_md)
    _write_json(ag_dir / "mcp_config.json", {"mcpServers": _base_mcp_servers()})
    _write_json(
        ag_dir / "hooks.json",
        {
            "generated_from": "manifest.json",
            "environment_hooks": {
                "before_tool_call": {
                    "match": ["generate_video", "generate_image", "generate_speech"],
                    "command": "python3 aetherloom/adapters/claude-code/hooks/warden_hook.py",
                    "mode": "block_or_audit",
                }
            },
            "scheduled_tasks": [
                {
                    "name": "natalie-dream-check",
                    "owner": "N.A.T.A.L.I.E.",
                    "cron": "0 */6 * * *",
                    "command": "python3 -c \"from core.dream import DreamJob; print('Check >=24h and >=5 sessions in preview mode')\"",
                    "default_mode": "preview",
                }
            ],
        },
    )
    ag_files = [
        "adapters/antigravity/.agents/AGENTS.md",
        "adapters/antigravity/.agents/mcp_config.json",
        "adapters/antigravity/.agents/hooks.json",
    ]
    for skill_rel in manifest["skills"]:
        src = ROOT / skill_rel
        dst = ag_dir / skill_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        ag_files.append(f"adapters/antigravity/.agents/{skill_rel}")
    generated["antigravity"] = ag_files

    # 3. Claude Code (plugin.json + commands/supergravity.md + agents/*.md + .mcp.json + hooks)
    cc_dir = ADAPTERS_DIR / "claude-code"
    _write_json(
        cc_dir / "plugin.json",
        {
            "name": manifest["name"],
            "version": manifest["version"],
            "description": manifest["description"],
            "commands": ["commands/supergravity.md"],
            "agents": [a["file"] for a in manifest["agents"]],
            "mcpServers": ".mcp.json",
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "generate_video|generate_image|generate_speech",
                        "command": "python3 hooks/warden_hook.py",
                    }
                ]
            },
        },
    )
    _write_text(
        cc_dir / "commands" / "supergravity.md",
        (ROOT / "skills" / "supergravity" / "SKILL.md").read_text(encoding="utf-8"),
    )
    _write_json(cc_dir / ".mcp.json", {"mcpServers": _base_mcp_servers()})
    _write_text(cc_dir / "hooks" / "warden_hook.py", WARDEN_HOOK_SCRIPT)
    cc_files = [
        "adapters/claude-code/plugin.json",
        "adapters/claude-code/commands/supergravity.md",
        "adapters/claude-code/.mcp.json",
        "adapters/claude-code/hooks/warden_hook.py",
    ]
    for agent_meta in manifest["agents"]:
        src = ROOT / agent_meta["file"]
        dst = cc_dir / agent_meta["file"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        cc_files.append(f"adapters/claude-code/{agent_meta['file']}")
    generated["claude-code"] = cc_files

    # 4. Cursor (.cursor/mcp.json + .cursor/rules/aetherloom.mdc)
    cur_dir = ADAPTERS_DIR / "cursor" / ".cursor"
    _write_json(cur_dir / "mcp.json", {"mcpServers": _base_mcp_servers()})
    _write_text(
        cur_dir / "rules" / "aetherloom.mdc",
        "---\ndescription: AetherLoom (/supergravity) multi-agent orchestration rules\nalwaysApply: true\n---\n\n"
        + root_agents_md,
    )
    generated["cursor"] = [
        "adapters/cursor/.cursor/mcp.json",
        "adapters/cursor/.cursor/rules/aetherloom.mdc",
    ]

    # 5. Gemini CLI (settings.json + mcp_config.json + hooks/before_after_tool.py)
    gem_dir = ADAPTERS_DIR / "gemini-cli"
    _write_json(gem_dir / "mcp_config.json", {"mcpServers": _base_mcp_servers()})
    _write_text(gem_dir / "hooks" / "before_after_tool.py", WARDEN_HOOK_SCRIPT)
    _write_json(
        gem_dir / "settings.json",
        {
            "mcpServers": _base_mcp_servers(),
            "hooks": {
                "BeforeTool": [
                    {
                        "matcher": "generate_video|generate_image|generate_speech",
                        "command": "python3 aetherloom/adapters/gemini-cli/hooks/before_after_tool.py",
                    }
                ],
                "AfterTool": [
                    {
                        "matcher": "*",
                        "command": "python3 -c \"import sys, json; print(json.dumps({'logged': True}))\"",
                    }
                ],
            },
            "model": manifest["free_tier_policy"]["default_model"],
        },
    )
    generated["gemini-cli"] = [
        "adapters/gemini-cli/settings.json",
        "adapters/gemini-cli/mcp_config.json",
        "adapters/gemini-cli/hooks/before_after_tool.py",
    ]

    # 6. Codex CLI (hooks.json + config.toml)
    codex_dir = ADAPTERS_DIR / "codex-cli"
    _write_json(
        codex_dir / "hooks.json",
        {
            "hooks": {
                "before_tool": [
                    {
                        "matcher": "generate_video|generate_image|generate_speech",
                        "command": "python3 aetherloom/adapters/claude-code/hooks/warden_hook.py",
                    }
                ]
            }
        },
    )
    _write_text(
        codex_dir / "config.toml",
        '''# Generated by AetherLoom build_adapters.py — do not hand-edit.
[mcp_servers.aetherloom]
command = "python3"
args = ["aetherloom/adapters/generic-mcp/server.py"]

[mcp_servers.youtube_transcript]
command = "npx"
args = ["-y", "yt-transcript-mcp"]

[mcp_servers.gemini_media]
command = "npx"
args = ["-y", "gstudioaimcp"]

[aetherloom]
command = "/supergravity"
default_model = "gemini-3.6-flash"
dream_default_mode = "preview"
warden_hard_cap_usd = 0.0
''',
    )
    generated["codex-cli"] = [
        "adapters/codex-cli/hooks.json",
        "adapters/codex-cli/config.toml",
    ]

    return generated


if __name__ == "__main__":
    summary = build_all_adapters()
    print(json.dumps({"generated_targets": list(summary.keys()), "files": summary}, indent=2))
