#!/usr/bin/env python3
"""AetherLoom (/supergravity) Cross-Platform Installer.

Installs AetherLoom cleanly with resolved absolute paths and non-destructive
JSON merging into:
  - antigravity-global   (~/.gemini/antigravity/mcp_config.json + global skills & AGENTS.md)
  - antigravity-workspace (<workspace>/.agents/)
  - vscode               (<workspace>/.vscode/mcp.json + <workspace>/.agents/)
  - claude-code          (<workspace>/.claude-plugin/aetherloom/)
  - cursor               (<workspace>/.cursor/)
  - gemini-cli           (~/.gemini/settings.json + mcp_config.json)
  - codex-cli            (~/.codex/hooks.json + config.toml)

Works on macOS, Linux, and Windows using Python 3.10+ standard library only.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys
from typing import Any, Dict

ROOT = pathlib.Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from build_adapters import build_all_adapters


def _python_cmd() -> str:
    return sys.executable or ("python" if sys.platform.startswith("win") else "python3")


def _resolved_mcp_servers() -> Dict[str, Any]:
    server_py = str((ROOT / "adapters" / "generic-mcp" / "server.py").resolve())
    return {
        "aetherloom": {
            "command": _python_cmd(),
            "args": [server_py],
            "env": {"AETHERLOOM_FREE_TIER_DEFAULT": "true"},
        },
        "youtube-transcript": {
            "command": "npx",
            "args": ["-y", "yt-transcript-mcp"],
        },
        "gemini-media": {
            "command": "npx",
            "args": ["-y", "gstudioaimcp"],
        },
    }


def _merge_json_file(target_path: pathlib.Path, top_key: str, entries: Dict[str, Any]) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    existing: Dict[str, Any] = {}
    if target_path.exists():
        try:
            existing = json.loads(target_path.read_text(encoding="utf-8"))
        except Exception:
            backup = target_path.with_suffix(target_path.suffix + ".bak")
            shutil.copy2(target_path, backup)
            existing = {}
    section = existing.get(top_key)
    if not isinstance(section, dict):
        section = {}
    section.update(entries)
    existing[top_key] = section
    target_path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")


def _copy_agents_folder(dest_agents_dir: pathlib.Path) -> None:
    src_agents = ROOT / "adapters" / "antigravity" / ".agents"
    dest_agents_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_agents / "AGENTS.md", dest_agents_dir / "AGENTS.md")

    # Copy core skills
    skills_dst = dest_agents_dir / "skills"
    if skills_dst.exists():
        shutil.rmtree(skills_dst)
    shutil.copytree(src_agents / "skills", skills_dst)

    # Write resolved MCP config and hooks with absolute script paths
    _merge_json_file(dest_agents_dir / "mcp_config.json", "mcpServers", _resolved_mcp_servers())

    warden_hook = str((ROOT / "adapters" / "claude-code" / "hooks" / "warden_hook.py").resolve())
    hooks_payload = {
        "generated_from": "manifest.json",
        "environment_hooks": {
            "before_tool_call": {
                "match": ["generate_video", "generate_image", "generate_speech"],
                "command": f'"{_python_cmd()}" "{warden_hook}"',
                "mode": "block_or_audit",
            }
        },
        "scheduled_tasks": [
            {
                "name": "natalie-dream-check",
                "owner": "N.A.T.A.L.I.E.",
                "cron": "0 */6 * * *",
                "command": f'"{_python_cmd()}" "{ROOT / "cli_bridge.py"}" dream_preview',
                "default_mode": "preview",
            }
        ],
    }
    (dest_agents_dir / "hooks.json").write_text(json.dumps(hooks_payload, indent=2) + "\n", encoding="utf-8")


def install(target: str, workspace: pathlib.Path) -> Dict[str, Any]:
    build_all_adapters()
    installed_paths = []

    if target == "antigravity-global":
        ag_home = pathlib.Path.home() / ".gemini" / "antigravity"
        _copy_agents_folder(ag_home)
        installed_paths.append(str(ag_home))

    elif target == "antigravity-workspace":
        dest = workspace.resolve() / ".agents"
        _copy_agents_folder(dest)
        installed_paths.append(str(dest))

    elif target == "vscode":
        ws = workspace.resolve()
        # VS Code MCP config uses top-level "servers" with "type": "stdio"
        vscode_servers = {
            name: {"type": "stdio", **cfg}
            for name, cfg in _resolved_mcp_servers().items()
        }
        vscode_mcp = ws / ".vscode" / "mcp.json"
        _merge_json_file(vscode_mcp, "servers", vscode_servers)
        # Also copy .agents/ so Antigravity / agentic extensions inside VS Code load AGENTS.md & skills
        agents_dst = ws / ".agents"
        _copy_agents_folder(agents_dst)
        installed_paths.extend([str(vscode_mcp), str(agents_dst)])

    elif target == "claude-code":
        dest = workspace.resolve() / ".claude-plugin" / "aetherloom"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(ROOT / "adapters" / "claude-code", dest)
        _merge_json_file(dest / ".mcp.json", "mcpServers", _resolved_mcp_servers())
        installed_paths.append(str(dest))

    elif target == "cursor":
        dest = workspace.resolve() / ".cursor"
        dest.mkdir(parents=True, exist_ok=True)
        rules_dst = dest / "rules"
        rules_dst.mkdir(parents=True, exist_ok=True)
        shutil.copy2(
            ROOT / "adapters" / "cursor" / ".cursor" / "rules" / "aetherloom.mdc",
            rules_dst / "aetherloom.mdc",
        )
        _merge_json_file(dest / "mcp.json", "mcpServers", _resolved_mcp_servers())
        installed_paths.append(str(dest))

    elif target == "gemini-cli":
        gem_home = pathlib.Path.home() / ".gemini"
        _merge_json_file(gem_home / "mcp_config.json", "mcpServers", _resolved_mcp_servers())
        _merge_json_file(gem_home / "settings.json", "mcpServers", _resolved_mcp_servers())
        installed_paths.append(str(gem_home))

    elif target == "codex-cli":
        codex_home = pathlib.Path.home() / ".codex"
        codex_home.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "adapters" / "codex-cli" / "hooks.json", codex_home / "hooks.json")
        shutil.copy2(ROOT / "adapters" / "codex-cli" / "config.toml", codex_home / "config.toml")
        installed_paths.append(str(codex_home))

    else:
        raise ValueError(f"Unsupported install target: {target}")

    return {
        "target": target,
        "python": _python_cmd(),
        "plugin_root": str(ROOT),
        "installed_paths": installed_paths,
        "status": "installed",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Install AetherLoom (/supergravity) plugin into your AI IDE or CLI.")
    parser.add_argument(
        "--target",
        required=True,
        choices=[
            "antigravity-global",
            "antigravity-workspace",
            "vscode",
            "claude-code",
            "cursor",
            "gemini-cli",
            "codex-cli",
        ],
        help="Host target to install AetherLoom into.",
    )
    parser.add_argument(
        "--workspace",
        default=".",
        help="Target project workspace path (used for workspace targets like vscode, antigravity-workspace, cursor, claude-code).",
    )
    args = parser.parse_args()
    result = install(args.target, pathlib.Path(args.workspace))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
