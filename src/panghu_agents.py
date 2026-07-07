"""胖虎AI客户端 · 数据模型与 Agent 目录（从 panghu_ai_client.py 抽出）。

AgentMode/AgentSpec/AgentDeliveryPlaybook/RiskPluginSpec 等 frozen dataclass、CodexConfigMode 枚举、
AGENTS 注册表、AGENT_DELIVERY_PLAYBOOKS 与 agent_delivery_playbook()。依赖常量来自 panghu_constants。
panghu_ai_client 通过 `from panghu_agents import *` 引入，引用点不变。
"""
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from panghu_constants import *  # noqa: F401,F403


@dataclass(frozen=True)
class AgentMode:
    id: str
    label: str
    note: str
    supports_auto_install: bool = True
    supports_config: bool = False


@dataclass(frozen=True)
class AgentSpec:
    id: str
    name: str
    description: str
    verify_command: tuple[str, ...]
    modes: tuple[AgentMode, ...]
    config_note: str


@dataclass(frozen=True)
class AgentDeliveryPlaybook:
    agent_id: str
    cli_supported: bool
    client_supported: bool
    skip_third_party_channels: bool
    customer_goal: str
    config_commands: tuple[str, ...]
    minimal_dialogue_check: str


@dataclass(frozen=True)
class RiskPluginSpec:
    id: str
    name: str
    aliases: tuple[str, ...]
    npm_packages: tuple[str, ...]
    marker_paths: tuple[Path, ...]
    uninstall_hint: str


@dataclass(frozen=True)
class RiskPluginFinding:
    name: str
    source: str
    detail: str
    uninstall_hint: str


@dataclass(frozen=True)
class TemporaryOpenAIAccessConfig:
    proxy: str
    duration_seconds: int = TEMP_OPENAI_ACCESS_SECONDS


@dataclass(frozen=True)
class CustomerPageOpenResult:
    url: str
    title: str
    method: str
    ok: bool
    message: str


class CodexConfigMode(str, Enum):
    DIRECT_API = "direct_api"
    DUAL_STATE = "dual_state"
    OFFICIAL_CHATGPT = "official_chatgpt"


AGENTS = (
    AgentSpec(
        id="codex",
        name="Codex",
        description="OpenAI 官方 Codex Agent，支持 CLI 与 Windows 客户端安装/修复。",
        verify_command=("codex", "--version"),
        modes=(
            AgentMode("cli", "CLI", "安装官方 Codex CLI。", supports_config=True),
            AgentMode("client", "客户端", "Windows 走官方 Store/App 包；其他系统打开官方入口。", supports_config=True),
        ),
        config_note="可自动写入胖虎AI API Key、接口、模型、中文规则和默认工作区。",
    ),
    AgentSpec(
        id="claude_code",
        name="ClaudeCode",
        description="Anthropic 官方 Claude Code Agent，按 CC 口径覆盖 CLI 和官方客户端入口。",
        verify_command=("claude", "--version"),
        modes=(
            AgentMode("cli", "CLI", "优先使用官方 Quickstart 原生安装入口，并写入胖虎AI网关配置。", supports_config=True),
            AgentMode("client", "客户端", "打开官方客户端入口，并按同一胖虎AI网关配置口径验收。", supports_config=True),
        ),
        config_note="写入胖虎AI网关配置，跳过 IDE 插件和第三方通道，目标是安装后可直接对话。",
    ),
    AgentSpec(
        id="openclaw",
        name="OpenClaw",
        description="OpenClaw Agent，官方未提供客户端安装，只做 CLI 交付。",
        verify_command=("openclaw", "--version"),
        modes=(
            AgentMode("cli", "CLI", "使用 OpenClaw 官方在线脚本安装，并写入胖虎AI网关配置。", supports_config=True),
        ),
        config_note="默认跳过 QQ/微信/TG 等第三方通道，只配置最短可用对话链路。",
    ),
    AgentSpec(
        id="hermes",
        name="Hermes",
        description="Nous Research Hermes Agent，官方未提供客户端安装，只做 CLI 交付。",
        verify_command=("hermes", "--version"),
        modes=(
            AgentMode("cli", "CLI", "使用 Hermes 官方在线安装入口，并写入胖虎AI网关配置。", supports_config=True),
        ),
        config_note="默认跳过 QQ/微信/TG 等第三方通道，只配置最短可用对话链路。",
    ),
    AgentSpec(
        id="gemini_agy",
        name="Gemini / agy",
        description="Google Antigravity（agy）Agent，写入胖虎AI网关 Gemini 格式配置，覆盖 CLI 与官方客户端入口。",
        verify_command=("agy", "--version"),
        modes=(
            AgentMode("cli", "CLI", "安装 Google Antigravity CLI，并写入胖虎AI网关 Gemini 格式配置。", supports_config=True),
            AgentMode("client", "客户端", "打开 Google Antigravity 官方入口；配置与 CLI 共用同一环境文件。", supports_auto_install=False, supports_config=True),
        ),
        config_note="写入 ~/.gemini/.env 的 GOOGLE_GEMINI_BASE_URL、GEMINI_API_KEY、GEMINI_MODEL，消耗胖虎AI额度。",
    ),
)

AGENT_DELIVERY_PLAYBOOKS = {
    "codex": AgentDeliveryPlaybook(
        agent_id="codex",
        cli_supported=True,
        client_supported=True,
        skip_third_party_channels=True,
        customer_goal="安装和配置后，买家可以直接打开 Codex 对话。",
        config_commands=(
            f"写入 Codex config.toml: base_url={CODEX_BASE_URL}, model={DEFAULT_MODEL}",
            "写入 Codex auth.json: OPENAI_API_KEY=买家胖虎AI API Key",
        ),
        minimal_dialogue_check="用胖虎AI /v1/chat/completions 执行一句中文回复验证。",
    ),
    "claude_code": AgentDeliveryPlaybook(
        agent_id="claude_code",
        cli_supported=True,
        client_supported=True,
        skip_third_party_channels=True,
        customer_goal="安装和配置后，买家可以直接打开 Claude Code/CC 对话。",
        config_commands=(
            f"设置 ANTHROPIC_BASE_URL={CLAUDE_CODE_BASE_URL}",
            "设置 ANTHROPIC_AUTH_TOKEN / ANTHROPIC_API_KEY=买家胖虎AI API Key",
            f"设置默认模型={DEFAULT_MODEL}",
        ),
        minimal_dialogue_check="运行 claude/CC 最小中文对话命令，确认能返回模型回复。",
    ),
    "openclaw": AgentDeliveryPlaybook(
        agent_id="openclaw",
        cli_supported=True,
        client_supported=False,
        skip_third_party_channels=True,
        customer_goal="安装和配置后，买家可以直接打开 OpenClaw 对话。",
        config_commands=(
            f"设置 OpenClaw OpenAI-compatible base_url={CODEX_BASE_URL}",
            "设置 OpenClaw API key=买家胖虎AI API Key",
            f"设置 OpenClaw model={DEFAULT_MODEL}",
        ),
        minimal_dialogue_check="运行 OpenClaw 最小 prompt，对胖虎AI网关发起一次中文对话验证。",
    ),
    "hermes": AgentDeliveryPlaybook(
        agent_id="hermes",
        cli_supported=True,
        client_supported=False,
        skip_third_party_channels=True,
        customer_goal="安装和配置后，买家可以直接打开 Hermes 对话。",
        config_commands=(
            f"写入 custom_providers.panghuai.base_url={CODEX_BASE_URL}",
            "写入 custom_providers.panghuai.key_env=PANGHUAI_API_KEY",
            f"设置 model.provider=custom:panghuai, model.default={DEFAULT_MODEL}",
        ),
        minimal_dialogue_check="运行 Hermes 官方 oneshot 命令，确认能通过胖虎AI网关返回。",
    ),
    "gemini_agy": AgentDeliveryPlaybook(
        agent_id="gemini_agy",
        cli_supported=True,
        client_supported=True,
        skip_third_party_channels=True,
        customer_goal="安装和配置后，买家可以直接打开 Gemini / agy 对话。",
        config_commands=(
            f"写入 ~/.gemini/.env: GOOGLE_GEMINI_BASE_URL={DEFAULT_BASE_URL}",
            "写入 ~/.gemini/.env: GEMINI_API_KEY=买家胖虎AI API Key",
            f"写入 ~/.gemini/.env: GEMINI_MODEL={DEFAULT_MODEL}",
        ),
        minimal_dialogue_check="运行 agy 最小中文对话命令，确认能通过胖虎AI网关（Gemini 格式）返回。",
    ),
}


def agent_delivery_playbook(agent_id: str) -> AgentDeliveryPlaybook:
    try:
        return AGENT_DELIVERY_PLAYBOOKS[agent_id]
    except KeyError as exc:
        raise ValueError(f"未知 Agent：{agent_id}") from exc
