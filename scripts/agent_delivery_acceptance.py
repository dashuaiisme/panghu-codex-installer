import argparse
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import panghu_codex_installer as installer  # noqa: E402


def dialogue_uses_untrusted_local_config(agent_id: str) -> bool:
    if os.environ.get("PANGHU_AGENT_ACCEPTANCE_ALLOW_LOCAL_CONFIG") == "1":
        return False
    if agent_id == "claude_code" and os.environ.get("CLAUDE_CODE_SETTINGS_PATH"):
        return False
    if agent_id == "openclaw" and os.environ.get("OPENCLAW_CONFIG_PATH"):
        return False
    if agent_id == "hermes" and os.environ.get("HERMES_HOME"):
        return False
    return agent_id in {"claude_code", "openclaw", "hermes"}


def agent_mode_summary(agent: installer.AgentSpec, mode: installer.AgentMode, cli_ok: bool, client_ok: bool) -> dict:
    if mode.id == "cli":
        install_status = "ready" if cli_ok else "not_detected"
    elif mode.id == "client":
        install_status = "ready" if client_ok else "not_confirmed"
    else:
        install_status = "unknown"
    return {
        "id": mode.id,
        "label": mode.label,
        "supports_config": mode.supports_config,
        "install_status": install_status,
        "description": mode.note,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect PanghuAI Agent delivery readiness without installing anything.")
    parser.add_argument(
        "--run-dialogue",
        action="store_true",
        help="Actually run non-Codex minimal dialogue commands. Default is read-only and does not call external agents.",
    )
    parser.add_argument("--model", default=installer.DEFAULT_MODEL)
    args = parser.parse_args()

    report = {
        "public_domain": installer.DEFAULT_BASE_URL,
        "model": args.model,
        "system": installer.current_system_id(),
        "run_dialogue": bool(args.run_dialogue),
        "agents": [],
        "blocking_gaps": [],
    }

    for agent in installer.AGENTS:
        cli_ok, cli_version = installer.version_for(agent.verify_command)
        client_ok, client_detail = installer.agent_client_status(agent)
        playbook = installer.agent_delivery_playbook(agent.id)
        item = {
            "id": agent.id,
            "name": agent.name,
            "cli_detected": cli_ok,
            "cli_version": cli_version,
            "client_detected": client_ok,
            "client_detail": client_detail,
            "skip_third_party_channels": playbook.skip_third_party_channels,
            "customer_goal": playbook.customer_goal,
            "config_commands": list(playbook.config_commands),
            "minimal_dialogue_check": playbook.minimal_dialogue_check,
            "dialogue_probe_command": installer.agent_dialogue_probe_command_text(agent, args.model),
            "dialogue_probe_status": "not_run",
            "dialogue_probe_output": "",
            "modes": [agent_mode_summary(agent, mode, cli_ok, client_ok) for mode in agent.modes],
        }

        if not cli_ok:
            report["blocking_gaps"].append(f"{agent.name} CLI 未检测到，不能确认安装/启动/对话链路。")
        if not client_ok:
            report["blocking_gaps"].append(f"{agent.name} 客户端未确认：{client_detail}")

        if args.run_dialogue:
            if agent.id == "codex":
                item["dialogue_probe_status"] = "manual_required"
                item["dialogue_probe_output"] = "Codex 真实对话验收需走胖虎AI网关任务，不在此脚本直接执行。"
                report["blocking_gaps"].append("Codex 最小中文真实任务验收未在本脚本执行。")
            elif dialogue_uses_untrusted_local_config(agent.id):
                item["dialogue_probe_status"] = "isolated_config_required"
                item["dialogue_probe_output"] = (
                    f"{agent.name} 对话验收会读取本机 Agent 配置；为避免使用残留配置，"
                    "请先由部署流程写入客户配置，或显式设置隔离配置/验收环境后再运行。"
                )
                report["blocking_gaps"].append(f"{agent.name} 最小中文对话未执行；缺少隔离配置或显式本机配置授权。")
            elif cli_ok:
                ok, output = installer.run_agent_dialogue_probe(agent, "cli", args.model)
                item["dialogue_probe_status"] = "pass" if ok else "failed"
                item["dialogue_probe_output"] = output
                if not ok:
                    report["blocking_gaps"].append(f"{agent.name} 最小中文对话验收失败。")
            else:
                item["dialogue_probe_status"] = "blocked"
                item["dialogue_probe_output"] = "CLI 未检测到，无法运行最小对话。"
        else:
            report["blocking_gaps"].append(f"{agent.name} 最小中文对话未执行；默认只做只读安装状态检查。")

        report["agents"].append(item)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["blocking_gaps"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
