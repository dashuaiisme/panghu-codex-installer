import argparse
import json
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import panghu_ai_client as installer  # noqa: E402


DELIVERY_SCOPE_CHOICES = ("cli", "client", "both")


def selected_scope_modes(delivery_scope: str) -> set[str]:
    if delivery_scope == "cli":
        return {"cli"}
    if delivery_scope == "client":
        return {"client"}
    return {"cli", "client"}


def parse_agent_selection(raw_agents: str) -> list[installer.AgentSpec]:
    all_agents = {agent.id: agent for agent in installer.AGENTS}
    if not raw_agents.strip():
        return list(installer.AGENTS)
    selected_ids = [item.strip() for item in raw_agents.split(",") if item.strip()]
    if not selected_ids:
        return list(installer.AGENTS)
    unknown = [agent_id for agent_id in selected_ids if agent_id not in all_agents]
    if unknown:
        raise ValueError(f"未知 Agent：{', '.join(unknown)}")
    seen: set[str] = set()
    selected: list[installer.AgentSpec] = []
    for agent_id in selected_ids:
        if agent_id in seen:
            continue
        seen.add(agent_id)
        selected.append(all_agents[agent_id])
    return selected


def configure_isolated_acceptance_env(api_key: str, model: str) -> tempfile.TemporaryDirectory | None:
    if not api_key.strip():
        return None
    temp_dir = tempfile.TemporaryDirectory(prefix="panghu-agent-acceptance-")
    root = Path(temp_dir.name)

    claude_settings = root / "claude" / "settings.json"
    openclaw_config = root / "openclaw" / "openclaw.json"
    hermes_home = root / "hermes"

    os.environ["CLAUDE_CODE_SETTINGS_PATH"] = str(claude_settings)
    os.environ["OPENCLAW_CONFIG_PATH"] = str(openclaw_config)
    os.environ["HERMES_HOME"] = str(hermes_home)

    os.environ["GOOGLE_GEMINI_BASE_URL"] = installer.DEFAULT_BASE_URL
    os.environ["GEMINI_API_KEY"] = api_key.strip()
    os.environ["GEMINI_MODEL"] = model.strip()

    logs: list[str] = []
    installer.install_claude_code_config(api_key, model, logs.append)
    installer.install_openclaw_config(api_key, model, logs.append)
    installer.install_hermes_config(api_key, model, logs.append)
    return temp_dir


def dialogue_uses_untrusted_local_config(agent_id: str) -> bool:
    if os.environ.get("PANGHU_AGENT_ACCEPTANCE_ALLOW_LOCAL_CONFIG") == "1":
        return False
    if agent_id == "claude_code" and os.environ.get("CLAUDE_CODE_SETTINGS_PATH"):
        return False
    if agent_id == "openclaw" and os.environ.get("OPENCLAW_CONFIG_PATH"):
        return False
    if agent_id == "hermes" and os.environ.get("HERMES_HOME"):
        return False
    if agent_id == "gemini_agy" and os.environ.get("GEMINI_API_KEY"):
        return False
    return agent_id in {"claude_code", "openclaw", "hermes", "gemini_agy"}


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


def initial_mode_statuses(agent_id: str, selected_modes: set[str], cli_ok: bool, client_ok: bool) -> dict[str, str]:
    statuses: dict[str, str] = {}
    if "cli" in selected_modes:
        statuses["cli"] = "ready" if cli_ok else "not_detected"
    if "client" in selected_modes:
        statuses["client"] = "ready" if client_ok else "not_confirmed"
    statuses["dialogue"] = "not_run"
    return statuses


def agent_delivery_status(mode_statuses: dict[str, str]) -> str:
    if any(status in {"not_supported", "not_detected", "not_confirmed", "not_run", "failed", "blocked"} for status in mode_statuses.values()):
        return "blocked"
    if mode_statuses.get("dialogue") == "pass":
        return "ready"
    return "offline_guarded"


def run_agent_dialogue_probe_with_timeout(agent: installer.AgentSpec, mode_id: str, model: str, timeout: int) -> tuple[bool, str]:
    if agent.id == "codex":
        return installer.run_agent_dialogue_probe(agent, mode_id, model)
    try:
        command = installer.agent_dialogue_probe_command(agent.id, model.strip())
    except ValueError as exc:
        return False, str(exc)
    ok, output = installer.run_command(command, timeout=timeout)
    output = (output or "").strip()
    if not ok:
        if agent.id == "hermes":
            summary = installer.recent_hermes_error_summary()
            if summary:
                return False, f"{output}\nHermes 最近请求诊断：{summary}".strip()
        return False, output or f"{agent.name}/{mode_id} 最小对话命令执行失败。"
    if not output:
        return False, f"{agent.name}/{mode_id} 最小对话命令没有返回内容。"
    return True, output[:1000]


def run_codex_gateway_probe(api_key: str, model: str) -> tuple[bool, str]:
    if not api_key.strip():
        return False, "缺少 PANGHU_AGENT_ACCEPTANCE_API_KEY，无法执行 Codex 胖虎AI网关真实任务。"
    ok, output = installer.run_real_task_probe(installer.DEFAULT_BASE_URL, api_key.strip(), model)
    return ok, installer.sanitize_log_text(output, api_key)


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect PanghuAI Agent delivery readiness without installing anything.")
    parser.add_argument(
        "--delivery-scope",
        choices=DELIVERY_SCOPE_CHOICES,
        default="both",
        help="Limit acceptance to CLI, client, or both. CLI and client are separate paid/delivery scopes.",
    )
    parser.add_argument(
        "--agents",
        default="",
        help="Comma-separated Agent ids to evaluate. Default evaluates all configured agents.",
    )
    parser.add_argument(
        "--run-dialogue",
        action="store_true",
        help="Actually run non-Codex minimal dialogue commands. Default is read-only and does not call external agents.",
    )
    parser.add_argument("--model", default=installer.DEFAULT_MODEL)
    parser.add_argument("--dialogue-timeout", type=int, default=30)
    parser.add_argument(
        "--isolated-config-from-env",
        action="store_true",
        help="When PANGHU_AGENT_ACCEPTANCE_API_KEY is set, write temporary isolated configs before dialogue probes.",
    )
    parser.add_argument(
        "--run-codex-gateway-probe",
        action="store_true",
        help="When --run-dialogue is set, use PANGHU_AGENT_ACCEPTANCE_API_KEY to run Codex's minimal PanghuAI gateway task.",
    )
    args = parser.parse_args()
    try:
        selected_agents = parse_agent_selection(args.agents)
    except ValueError as exc:
        parser.error(str(exc))
    selected_modes = selected_scope_modes(args.delivery_scope)
    temp_env = None
    api_key = os.environ.get("PANGHU_AGENT_ACCEPTANCE_API_KEY", "")
    if args.run_dialogue and args.isolated_config_from_env and api_key.strip():
        temp_env = configure_isolated_acceptance_env(api_key, args.model)

    report = {
        "public_domain": installer.DEFAULT_BASE_URL,
        "model": args.model,
        "system": installer.current_system_id(),
        "delivery_scope": args.delivery_scope,
        "selected_agent_ids": [agent.id for agent in selected_agents],
        "selected_modes": sorted(selected_modes),
        "run_dialogue": bool(args.run_dialogue),
        "isolated_config": bool(temp_env),
        "agents": [],
        "blocking_gaps": [],
    }

    for agent in selected_agents:
        cli_ok, cli_version = installer.version_for(agent.verify_command)
        # 用户决策（修正版）：有官方客户端的按真实客户端检测；没有的（CLI-only）明确不适用
        client_ok, client_detail = installer.verify_agent_client_scope(agent, "client")
        playbook = installer.agent_delivery_playbook(agent.id)
        selected_agent_modes = [
            mode for mode in agent.modes
            if mode.id in selected_modes
        ]
        mode_statuses = initial_mode_statuses(agent.id, selected_modes, cli_ok, client_ok)
        item = {
            "id": agent.id,
            "name": agent.name,
            "selected_modes": [mode.id for mode in selected_agent_modes],
            "mode_statuses": mode_statuses,
            "delivery_status": "blocked",
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
            "modes": [agent_mode_summary(agent, mode, cli_ok, client_ok) for mode in selected_agent_modes],
        }

        if "cli" in selected_modes and not cli_ok:
            report["blocking_gaps"].append(f"{agent.name} CLI 未检测到，不能确认安装/启动/对话链路。")
        if "client" in selected_modes and not client_ok:
            report["blocking_gaps"].append(f"{agent.name} 客户端未确认：{client_detail}")

        if args.run_dialogue:
            if agent.id == "codex":
                if args.run_codex_gateway_probe:
                    ok, output = run_codex_gateway_probe(api_key, args.model)
                    item["dialogue_probe_status"] = "pass" if ok else "failed"
                    item["mode_statuses"]["dialogue"] = "pass" if ok else "failed"
                    item["dialogue_probe_output"] = output
                    if not ok:
                        report["blocking_gaps"].append("Codex 胖虎AI网关最小中文真实任务验收失败。")
                else:
                    item["dialogue_probe_status"] = "manual_required"
                    item["mode_statuses"]["dialogue"] = "not_run"
                    item["dialogue_probe_output"] = "Codex 真实对话验收需走胖虎AI网关任务；传入 --run-codex-gateway-probe 后才会执行。"
                    report["blocking_gaps"].append("Codex 最小中文真实任务验收未在本脚本执行。")
            elif dialogue_uses_untrusted_local_config(agent.id):
                item["dialogue_probe_status"] = "isolated_config_required"
                item["mode_statuses"]["dialogue"] = "blocked"
                item["dialogue_probe_output"] = (
                    f"{agent.name} 对话验收会读取本机 Agent 配置；为避免使用残留配置，"
                    "请先由部署流程写入客户配置，或显式设置隔离配置/验收环境后再运行。"
                )
                report["blocking_gaps"].append(f"{agent.name} 最小中文对话未执行；缺少隔离配置或显式本机配置授权。")
            elif cli_ok:
                ok, output = run_agent_dialogue_probe_with_timeout(agent, "cli", args.model, max(5, args.dialogue_timeout))
                item["dialogue_probe_status"] = "pass" if ok else "failed"
                item["mode_statuses"]["dialogue"] = "pass" if ok else "failed"
                item["dialogue_probe_output"] = installer.sanitize_log_text(output, api_key)
                if not ok:
                    report["blocking_gaps"].append(f"{agent.name} 最小中文对话验收失败。")
            else:
                item["dialogue_probe_status"] = "blocked"
                item["mode_statuses"]["dialogue"] = "blocked"
                item["dialogue_probe_output"] = "CLI 未检测到，无法运行最小对话。"
        else:
            report["blocking_gaps"].append(f"{agent.name} 最小中文对话未执行；默认只做只读安装状态检查。")

        item["delivery_status"] = agent_delivery_status(item["mode_statuses"])
        report["agents"].append(item)

    report["delivery_status"] = "blocked" if report["blocking_gaps"] else "ready"
    try:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1 if report["blocking_gaps"] else 0
    finally:
        if temp_env is not None:
            temp_env.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
