import base64
import http.cookiejar
import hashlib
import io
import json
from datetime import datetime
import os
import platform
import re
import shlex
import shutil
import ssl
import subprocess
import sys
import tempfile
import queue
import threading
import time
import tkinter as tk
import uuid
import webbrowser
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from tkinter import messagebox, ttk
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import HTTPCookieProcessor, HTTPSHandler, Request, build_opener, urlopen

from commercial_api import (
    CommercialApiContract,
    build_agent_apply_request,
    build_agent_center_request,
    build_agent_commissions_request,
    build_agent_downstreams_request,
    build_agent_public_offering_request,
    build_agent_settlement_request,
    build_api_key_owner_verify_request,
    build_config_session_complete_request,
    build_config_session_fail_request,
    build_config_session_reserve_request,
    build_entitlement_query_request,
    build_communication_software_link_offering_request,
    build_communication_software_link_order_create_request,
    build_communication_software_link_order_get_request,
    build_communication_software_link_session_acceptance_request,
    build_communication_software_link_session_create_request,
    build_communication_software_link_session_disable_request,
    build_communication_software_link_session_get_request,
    build_communication_software_link_platform_auth_create_request,
    build_communication_software_link_platform_auth_get_request,
    build_communication_software_link_session_test_request,
    build_order_create_request,
    build_payment_poll_request,
    build_referral_bind_request,
    execute_commercial_api_request,
    mask_business_identifier,
    parse_config_session_reserve_data,
    parse_agent_center_snapshot_data,
    parse_communication_software_link_order_status_data,
    parse_communication_software_link_state_fields,
    parse_payment_status_data,
    sanitize_commercial_text,
    stable_config_reserve_idempotency_key,
    stable_config_session_idempotency_key,
    stable_agent_business_idempotency_key,
    stable_communication_software_link_idempotency_key,
    stable_order_idempotency_key,
    with_operator_auth,
)
from commercial_core import (
    BuyerSelfServiceNode,
    DeliveryScope,
    DeploymentNode,
    DeploymentProgress,
    EntitlementContract,
    NodeStatus,
    RealTaskVerificationResult,
    UserContext,
    build_agent_center_summary_lines,
    build_agent_customer_state,
    build_buyer_self_service_status_rows,
    build_commercial_agent_capabilities,
    build_commercial_entry_cards,
    build_commercial_product_catalog,
    build_customer_commercial_summary_lines,
    build_customer_delivery_report,
    build_customer_purchase_product_lines,
    build_entitlement_summary_rows,
    build_node_status_rows,
    build_persistent_profile_payload,
    build_real_task_diagnostic_summary,
    build_value_added_service_catalog,
    build_value_added_service_summary_lines,
    api_key_owner_gate,
    commercial_config_gate,
    commercial_deployment_blockers,
    config_session_terminal_action,
    create_buyer_contexts,
    create_commercial_web_profile,
    find_listed_product,
    find_orderable_product,
    validate_commercial_manifest_trust,
    verify_real_task_evidence,
    verify_client_scope_delivery_evidence,
)

try:
    import certifi
except Exception:  # pragma: no cover - runtime fallback for incomplete dev environments
    certifi = None

try:
    import webview
except Exception:  # pragma: no cover - optional dependency for embedded customer pages
    webview = None


APP_NAME = "胖虎AI客户端"
APP_VERSION = "1.0.16"
HTTP_USER_AGENT = f"PanghuAI-Client/{APP_VERSION}"
# 本地联调开关（仅开发/集成测试用）：设置 PANGHU_DEV_BASE_URL_OVERRIDE 可将
# 全部服务端地址指向本地联调网关。生产构建不设置此环境变量，行为不变；
# 启动时若覆盖生效会在日志和窗口标题打出醒目提示，防止误用。
PANGHU_DEV_BASE_URL_OVERRIDE = os.environ.get("PANGHU_DEV_BASE_URL_OVERRIDE", "").strip().rstrip("/")
DEFAULT_BASE_URL = PANGHU_DEV_BASE_URL_OVERRIDE or "https://aitokenapi.cc"
DEFAULT_MODEL = "gpt-5.5"
CODEX_PROVIDER_NAME = "panghuAI"
CODEX_BASE_URL = f"{DEFAULT_BASE_URL}/v1"
CLAUDE_CODE_BASE_URL = DEFAULT_BASE_URL
TEMP_OPENAI_ACCESS_SECONDS = 600
TEMP_OPENAI_ACCESS_MAX_SECONDS = 600
AGENT_DIALOGUE_PROBE_PROMPT = "请用一句中文回复：胖虎AI配置验证成功"


def empty_flow_logs() -> dict[int, list]:
    return {idx: [] for idx, _title, _subtitle in FLOW_STEPS}


def load_commercial_manifest_public_key() -> str:
    # 本地联调开关（仅开发用）：src/commercial_manifest_public_key.py 是构建
    # 注入的生成文件，会遮蔽 PYTHONPATH；联调时用环境变量显式指定测试公钥
    # PEM 文件。生产构建不设置此变量，行为不变。
    dev_override_file = os.environ.get("PANGHU_DEV_MANIFEST_PUBLIC_KEY_FILE", "").strip()
    if dev_override_file:
        try:
            return Path(dev_override_file).read_text(encoding="utf-8").strip()
        except Exception:
            return ""
    try:
        from commercial_manifest_public_key import PUBLIC_KEY_PEM
    except Exception:
        return ""
    return str(PUBLIC_KEY_PEM or "").strip()


COMMERCIAL_MANIFEST_PUBLIC_KEY_PEM = load_commercial_manifest_public_key()
GITHUB_RELEASE_API = "https://api.github.com/repos/dashuaiisme/panghu-ai-client/releases/latest"
PUBLIC_UPDATE_MANIFEST_URL = f"{DEFAULT_BASE_URL}/deployer/latest.json"
WINDOWS_RELEASE_DIR_NAME = APP_NAME
WINDOWS_RELEASE_ASSET_NAME = f"{WINDOWS_RELEASE_DIR_NAME}-Windows.zip"
WINDOWS_RELEASE_ASSET_ALIASES = (
    WINDOWS_RELEASE_ASSET_NAME,
)
MAC_RELEASE_ASSET_NAME = f"{WINDOWS_RELEASE_DIR_NAME}-Mac.zip"
MAC_RELEASE_ASSET_ALIASES = (
    MAC_RELEASE_ASSET_NAME,
)
MAC_APPLE_SILICON_RELEASE_ASSET_NAME = f"{WINDOWS_RELEASE_DIR_NAME}-Mac-AppleSilicon.zip"
MAC_INTEL_RELEASE_ASSET_NAME = f"{WINDOWS_RELEASE_DIR_NAME}-Mac-Intel.zip"
MAC_APPLE_SILICON_RELEASE_ASSET_ALIASES = (
    MAC_APPLE_SILICON_RELEASE_ASSET_NAME,
    MAC_RELEASE_ASSET_NAME,
)
MAC_INTEL_RELEASE_ASSET_ALIASES = (
    MAC_INTEL_RELEASE_ASSET_NAME,
)
LOGIN_URL = f"{DEFAULT_BASE_URL}/api/user/login?turnstile="
DEPLOYER_ACTIVATE_URL = f"{DEFAULT_BASE_URL}/api/deployer/activate"
DEPLOYER_MANIFEST_URL = f"{DEFAULT_BASE_URL}/api/deployer/manifest"
REGISTER_URL = f"{DEFAULT_BASE_URL}/register"
PANGHU_HOME_URL = DEFAULT_BASE_URL
KEY_CREATE_URL = f"{DEFAULT_BASE_URL}/console/token"
CONSOLE_URL = f"{DEFAULT_BASE_URL}/console"
BUY_URL = f"{DEFAULT_BASE_URL}/buy"
AFFILIATE_URL = f"{DEFAULT_BASE_URL}/affiliate"
SIM_CONTROL_URL = "https://sim.aitokenapi.cc"
AGENT_CENTER_URL = f"{DEFAULT_BASE_URL}/agent"
AGENT_CUSTOMERS_URL = f"{DEFAULT_BASE_URL}/agent/customers"
AGENT_TOKEN_COMM_URL = f"{DEFAULT_BASE_URL}/agent/token-commission"
AGENT_ACTIVATION_COMM_URL = f"{DEFAULT_BASE_URL}/agent/activation-commission"
AGENT_INSTALL_COMM_URL = f"{DEFAULT_BASE_URL}/agent/install-commission"
AGENT_PROXY_URL = f"{DEFAULT_BASE_URL}/agent/proxy"
AGENT_RULES_URL = f"{DEFAULT_BASE_URL}/agent/rules"
AGENT_JOIN_URL = f"{DEFAULT_BASE_URL}/agent/join"
VALUE_ADDED_URLS = {
    "gpt_plus": f"{DEFAULT_BASE_URL}/services?entry=gpt-plus",
    "phone_card": f"{DEFAULT_BASE_URL}/services?entry=phone-card",
    "sms_code": SIM_CONTROL_URL,
}
COMMUNICATION_SOFTWARE_LINK_AGENT_OPTIONS = ("codex", "claude_code", "openclaw", "hermes")
COMMUNICATION_SOFTWARE_LINK_CHANNEL_OPTIONS = ("qq_bot", "weixin", "feishu", "dingtalk", "wecom")
COMMUNICATION_SOFTWARE_LINK_AGENT_SOURCE_OPTIONS = ("existing_local_agent", "historical_delivery", "current_delivery", "manual_review")
COMMUNICATION_SOFTWARE_LINK_GATEWAY_MODE_OPTIONS = ("official_bot", "customer_bot", "manual_bridge")
COMMUNICATION_SOFTWARE_LINK_DEFAULT_PROMPT = "请回复连接通讯软件验收成功"
COMMUNICATION_SOFTWARE_LINK_LOCAL_EVIDENCE_BASE_URL = "local://communication-software-link/evidence"
COMMUNICATION_SOFTWARE_LINK_PLATFORM_AUTH_MAX_POLLS = 24
COMMUNICATION_SOFTWARE_LINK_PLATFORM_AUTH_POLL_SECONDS = 5
INVITE_QUERY_KEYS = ("invite", "invite_code", "aff", "aff_code", "ref", "referral", "referral_code")
CODEX_WINDOWS_STORE_URL = "https://get.microsoft.com/installer/download/9PLM9XGG6VKS?cid=website_cta_psi"
CODEX_DOWNLOAD_URL = "https://developers.openai.com/codex/"
CLAUDE_CODE_DOCS_URL = "https://code.claude.com/docs/en/quickstart"
OPENCLAW_DOCS_URL = "https://docs.openclaw.ai/start/getting-started"
HERMES_DOCS_URL = "https://hermes-agent.nousresearch.com/docs/zh-Hans/getting-started/installation"
GEMINI_AGY_DOCS_URL = "https://antigravity.google/"
OFFICIAL_PACKAGE_SUFFIXES = (".msixbundle", ".msix", ".appx", ".appxbundle", ".appinstaller")
PANGHU_AGENTS_START = "<!-- PANGHUAI_CODEX_RULES_START -->"
PANGHU_AGENTS_END = "<!-- PANGHUAI_CODEX_RULES_END -->"
APP_BG = "#e8e8ed"
SURFACE_BG = "#f5f5f7"
SIDEBAR_BG = "#ebebec"
CARD_BG = "#ffffff"
PANEL_BG = "#f7f7f8"
INK = "#1d1d1f"
SECONDARY = "#424245"
MUTED = "#86868b"
FAINT = "#b0b0b5"
PRIMARY = "#0071e3"
PRIMARY_HOVER = "#0077ed"
PRIMARY_DARK = "#0062c0"
PRIMARY_LIGHT = "#eff7ff"
PRIMARY_TINT = "#e8f2ff"
ACCENT = "#1a7f37"
BORDER = "#d2d2d7"
LIGHT_BORDER = "#e5e5e7"
WARNING_BG = "#fff7df"
GOLD = "#b06000"
GOLD_SOFT = "#fff7df"
LOCKED_BG = "#f1f3f4"
WAIT_BG = "#f1f3f4"
WAIT_BORDER = "#dadce0"
SUCCESS_BG = "#e6f4ea"
SUCCESS_BORDER = "#ceead6"
INFO_BG = "#eaf4ff"
FAIL_BG = "#fdebe5"
FAIL_BORDER = "#fad2cf"
FAIL = "#c5221f"
RUNNING = "#b06000"
SUCCESS = "#1a7f37"
NEUTRAL_DOT = "#9a9aa0"
INPUT_BG = "#ffffff"
LOG_BG = "#1d1d1f"
LOG_FG = "#f5f5f7"
SEGMENTED_BG = "#e3e3e6"
SEGMENTED_ACTIVE = "#ffffff"
APP_FRAME_BG = SURFACE_BG
APP_FRAME_BORDER = BORDER
TOPBAR_HEIGHT = 52
LEFT_PANEL_WIDTH = 220
RIGHT_PANEL_WIDTH = 300
FLOW_STEPS = (
    (1, "创建/填写 API Key", "填入调用令牌并测试"),
    (2, "检测环境", "先排查电脑和风险工具"),
    (3, "选择 Agent", "选择要交付的 Agent"),
    (4, "执行安装", "按引导安装并配置"),
    (5, "写入配置", "写入网关、Key 和模型"),
    (6, "启动检测", "确认入口可以打开"),
    (7, "最小中文对话", "确认能直接中文对话"),
    (8, "功能验收矩阵", "逐项确认是否达标"),
    (9, "基础交付验收", "完成基础验收后收口"),
    (10, "连接通讯软件", "配置通讯软件通道"),
    (11, "连接通讯软件交付验收", "通讯软件发送消息验证"),
)

MODULE_AGENT = "agent"
MODULE_SITE = "site"
MODULE_VALUE_ADDED = "value_added"
MODULE_COURSES = "courses"
TOP_MODULES = (
    (MODULE_AGENT, "配置Agent", "安装配置与验收"),
    (MODULE_SITE, "胖虎AI网站", "控制台、Key、充值"),
    (MODULE_VALUE_ADDED, "增值业务", "账号会员与服务"),
    (MODULE_COURSES, "代理中心", "代理分销与返佣"),
)
MODULE_SIDE_NAV_ITEMS = {
    MODULE_AGENT: tuple((str(idx), title, subtitle) for idx, title, subtitle in FLOW_STEPS),
    MODULE_SITE: (
        ("account", "控制台", "打开胖虎AI首页或控制台"),
        ("key", "创建 API Key", "进入令牌管理页面"),
        ("recharge", "充值购买", "跳转官方在线购买页"),
        ("register", "推广返佣", "查看邀请码与返佣入口"),
    ),
    MODULE_VALUE_ADDED: (
        ("gpt_plus", "GPT 账号会员", "Plus、Team、Pro 服务入口"),
        ("phone_card", "国外手机卡", "海外号码与通信服务"),
        ("sms_code", "接码控制台", "手机号接码控制中心"),
    ),
    MODULE_COURSES: (
        ("agent_home", "代理总览", "代理等级、邀请入口与结算摘要"),
        ("agent_customers", "下游客户", "查看服务端下游客户归因"),
        ("agent_token_comm", "token 返佣", "下游 token 消费返佣摘要"),
        ("agent_activation_comm", "激活返佣", "下游付费激活返佣摘要"),
        ("agent_install_comm", "安装返佣", "下游客户付费安装 Agent 返佣"),
        ("agent_proxy", "工具代理后端", "进入工具代理业务后台"),
        ("agent_join", "招商介绍", "查看代理公开招商政策与加入条件"),
        ("agent_rules", "代理规则", "查看结算、升级与风控规则"),
    ),
}
MODULE_PAGE_META = {
    MODULE_SITE: {
        "account": ("胖虎AI控制台", CONSOLE_URL, "主工作区直接显示胖虎AI首页或控制台入口，登录后可继续管理账号、额度和节点。"),
        "key": ("令牌管理", KEY_CREATE_URL, "从网站服务端打开令牌管理页面，创建或复制当前买家自己的 API Key。"),
        "recharge": ("在线购买", BUY_URL, "从网站服务端打开官方在线购买页，完成套餐、余额或升级购买。"),
        "register": ("推广返佣", AFFILIATE_URL, "从网站服务端打开推广返佣页，查看邀请码、返佣记录和邀请入口。"),
    },
    MODULE_VALUE_ADDED: {
        "gpt_plus": ("GPT 账号会员", VALUE_ADDED_URLS["gpt_plus"], "进入增值业务页的 GPT 账号会员分区，具体上架状态和价格以服务端为准。"),
        "phone_card": ("国外手机卡", VALUE_ADDED_URLS["phone_card"], "进入增值业务页的海外号码与通信服务分区，所有商品信息由网站服务端控制。"),
        "sms_code": ("接码控制台", VALUE_ADDED_URLS["sms_code"], "打开手机号接码控制中心；价格、订单、可用号码和短信回传仍以服务端为准。"),
    },
    MODULE_COURSES: {
        "agent_home": ("代理总览", AGENT_CENTER_URL, "查看当前代理状态、等级、邀请入口和结算摘要。"),
        "agent_customers": ("下游客户", AGENT_CUSTOMERS_URL, "查看下游客户归因、绑定时间和服务端客户摘要。"),
        "agent_token_comm": ("token 返佣", AGENT_TOKEN_COMM_URL, "查看下游 token/API 消费产生的返佣摘要。"),
        "agent_activation_comm": ("激活返佣", AGENT_ACTIVATION_COMM_URL, "查看下游付费激活、充值或购买产生的返佣摘要。"),
        "agent_install_comm": ("安装返佣", AGENT_INSTALL_COMM_URL, "查看下游客户付费安装 Agent 服务产生的返佣摘要。"),
        "agent_proxy": ("工具代理后端", AGENT_PROXY_URL, "进入工具代理业务后台，管理代理业务入口和服务端状态。"),
        "agent_join": ("招商介绍", AGENT_JOIN_URL, "查看代理公开招商政策、合作优势与加入条件。"),
        "agent_rules": ("代理规则", AGENT_RULES_URL, "查看代理费用、升级、返佣、提现、冻结和冲正规则。"),
    },
}
MODULE_ACTION_CARDS = {
    MODULE_SITE: {
        "account": (
            ("先看哪里", "优先看控制台首页、额度余额、节点状态和当前账号信息。"),
            ("适合做什么", "登录后直接继续管理控制台，不需要再单独打开第三方浏览器。"),
            ("客服怎么指引", "客服只需要让客户在这里完成控制台里的下一步操作。"),
            ("注意事项", "控制台内的业务状态以胖虎AI网站服务端返回为准。"),
        ),
        "key": (
            ("现在要做什么", "进入令牌管理后创建新 Key，复制完整的 sk- 内容回来填写。"),
            ("做完看哪里", "返回本工具第一步，粘贴后点“保存并测试 Key”。"),
            ("客服确认点", "确认 Key 属于当前买家账号，且账户已充值或有可用额度。"),
            ("安全边界", "API Key 不写入执行日志；profile.json 只保存账号提示、Key、模型和界面偏好。"),
        ),
        "recharge": (
            ("现在要做什么", "在官方在线购买页完成套餐购买、余额充值或升级付款。"),
            ("做完看哪里", "支付完成后回到工具，再继续创建 Key 或执行部署步骤。"),
            ("客服确认点", "若余额仍不足，先刷新网站订单状态，再继续本地配置。"),
            ("注意事项", "价格、次数、有效期、设备数都以服务端页面为准，不在本地写死。"),
        ),
        "register": (
            ("现在要做什么", "打开推广返佣页，查看邀请码、推广链接和返佣记录。"),
            ("做完看哪里", "需要创建新的胖虎AI账号时，也从这里继续进入返佣或邀请相关入口。"),
            ("客服确认点", "代理身份、邀请码绑定和返佣结算全部以网站服务端为准。"),
            ("注意事项", "邀请码、返佣和代理身份均由胖虎AI网站服务端处理。"),
        ),
    },
    MODULE_VALUE_ADDED: {
        "gpt_plus": (
            ("服务入口", "展示 GPT Plus、Team、Pro 等会员服务的独立入口。"),
            ("订单承接", "具体服务能否购买、如何购买，以服务端上架内容为准。"),
            ("客服协同", "客户可把本页记录复制给客服，继续人工确认套餐细节。"),
            ("交付边界", "本地工具不保存这类第三方账号的登录态或支付信息。"),
        ),
        "phone_card": (
            ("服务入口", "展示国外手机卡、海外通信号码和辅助服务入口。"),
            ("适用场景", "用于 OpenAI、Claude 等海外平台注册或长期通信场景。"),
            ("客服协同", "具体国家、库存与价格只从网站服务端读取。"),
            ("交付边界", "客户端不硬编码国家库存、价格或开卡规则。"),
        ),
        "sms_code": (
            ("控制台入口", "打开 sim 子域名的手机号接码控制中心，承接号码托管和接码工作台。"),
            ("平台绑定", "用户开始接码前必须选择 OpenAI、Google 等本次接收平台。"),
            ("短信回传", "验证码必须匹配用户、号码、当前会话、时间窗口和本次平台。"),
            ("服务状态", "可用号码、订单、价格、失败处理和退款规则以服务端返回为准。"),
        ),
    },
    MODULE_COURSES: {
        "agent_home": (
            ("先看哪里", "优先查看当前代理等级、邀请入口、下游数量和结算摘要。"),
            ("收益来源", "服务端区分 token 返佣、激活返佣和安装返佣三类收入。"),
            ("如何邀请", "通过专属邀请链接或注册邀请码绑定下游客户，已有上级不覆盖。"),
            ("结算边界", "所有收益、冻结、冲正和提现状态以服务端账本为准。"),
        ),
        "agent_customers": (
            ("数据来源", "下游客户归因只来自胖虎AI服务端，不从本地邀请码记录推算。"),
            ("客户分类", "可按注册、付费激活、已安装 Agent 服务等状态查看。"),
            ("跟进策略", "客服可结合后端诊断码和客户状态辅助交付。"),
            ("绑定边界", "已有上级代理的客户不能被新邀请码覆盖。"),
        ),
        "agent_token_comm": (
            ("收益类型", "展示下游 token/API 真实消费产生的返佣摘要。"),
            ("事件来源", "以服务端结算后的真实消费事件为准，重复事件不重复入账。"),
            ("结算周期", "默认 T+7 从待结算转为可结算，具体以后台设置为准。"),
            ("状态说明", "退款、异常消费或风控命中后可冻结或冲正。"),
        ),
        "agent_activation_comm": (
            ("收益类型", "展示下游付费激活、购买或充值产生的返佣摘要。"),
            ("订单快照", "佣金按订单发生时的代理链路和返佣规则快照计算。"),
            ("结算周期", "默认 T+7 进入可结算，后台可按业务策略调整。"),
            ("异常处理", "订单撤销或退款后必须写入冲正记录。"),
        ),
        "agent_install_comm": (
            ("安装返佣", "每当下游客户成功安装并激活一个 Agent，您可获得专属返佣。"),
            ("结算比例", "服务端按实际安装的 Agent 类型和授权节点数量动态计算。"),
            ("状态说明", "需要客户完成“功能验收矩阵”并在本地成功跑通中文对话。"),
            ("注意事项", "已退款或非正常部署的节点不会计入有效安装返佣。"),
        ),
        "agent_proxy": (
            ("后端入口", "工具代理相关后端统一从胖虎AI网站和服务端代理中心进入。"),
            ("服务开关", "哪些代理能力已开放，由服务端和代理后端决定。"),
            ("接入计划", "后续代理工具诊断、回调和售后入口也统一归到这里。"),
            ("注意事项", "客户端只提供入口和状态衔接，不在本地重做代理业务规则。"),
        ),
        "agent_join": (
            ("招募说明", "公开招商页面展示代理合作优势、费用模式和升级路径。"),
            ("加入申请", "代理级别、结算条款和风险控制以服务端规则为准。"),
            ("注意事项", "客户端仅提供招商介绍入口，本地不写死招商费用或分成费率。"),
            ("服务端为准", "所有活动细则、结算及佣金分配比例由胖虎AI服务端定义。"),
        ),
        "agent_rules": (
            ("费用规则", "代理费用、免费开通、付费升级、押金或年费都由管理员后台配置。"),
            ("等级规则", "代理采用 L1-L5 纯五级模型，等级越高可覆盖的下游层级越深。"),
            ("风控说明", "禁止自行邀请自己或利用多账号刷取安装返佣，异常收益可冻结。"),
            ("服务端为准", "所有比例、费率、提现、冲正和待接入状态以胖虎AI服务端实时规则为准。"),
        ),
    },
}


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


def build_agent_config_plan(agent_id: str, mode_id: str, api_key: str, model: str) -> list[str]:
    if agent_id == "gemini_agy":
        playbook = agent_delivery_playbook(agent_id)
        masked_key = mask_key(api_key)
        return [
            f"gemini_agy/{mode_id}：使用 Google Antigravity 官方入口安装或检测。",
            f"gemini_agy/{mode_id}：写入胖虎AI网关（Gemini 格式）{DEFAULT_BASE_URL}。",
            f"gemini_agy/{mode_id}：写入模型 {model}。",
            f"gemini_agy/{mode_id}：写入买家胖虎AI API Key {masked_key}。",
            f"gemini_agy/{mode_id}：第三方通道默认跳过。",
            f"gemini_agy/{mode_id}：{('；'.join(playbook.config_commands))}",
            f"gemini_agy/{mode_id}：最小对话验证：{playbook.minimal_dialogue_check}",
        ]
    playbook = agent_delivery_playbook(agent_id)
    masked_key = mask_key(api_key)
    return [
        f"{agent_id}/{mode_id}：使用官方发行入口安装或检测。",
        f"{agent_id}/{mode_id}：写入胖虎AI网关 https://aitokenapi.cc/v1。",
        f"{agent_id}/{mode_id}：写入模型 {model}。",
        f"{agent_id}/{mode_id}：写入买家胖虎AI API Key {masked_key}。",
        f"{agent_id}/{mode_id}：第三方通道默认跳过。",
        f"{agent_id}/{mode_id}：{('；'.join(playbook.config_commands))}",
        f"{agent_id}/{mode_id}：最小对话验证：{playbook.minimal_dialogue_check}",
    ]

RISK_PLUGIN_SPECS = (
    RiskPluginSpec(
        id="ccswitch",
        name="CCSwitch",
        aliases=("ccswitch", "cc-switch", "claude-code-switch"),
        npm_packages=("ccswitch", "cc-switch", "claude-code-switch"),
        marker_paths=(Path.home() / ".ccswitch", Path.home() / ".claude-code-switch"),
        uninstall_hint="如果是 npm 安装，请执行 npm uninstall -g ccswitch cc-switch claude-code-switch；如果是单独客户端，请在系统应用列表里卸载。",
    ),
    RiskPluginSpec(
        id="codex_plus_plus",
        name="Codex++",
        aliases=("codex++", "codexpp", "codex-plus-plus", "codex-plusplus"),
        npm_packages=("codex++", "codexpp", "codex-plus-plus", "codex-plusplus"),
        marker_paths=(Path.home() / ".codex++", Path.home() / ".codexpp", Path.home() / ".codex-plus-plus"),
        uninstall_hint="如果是 npm 安装，请执行 npm uninstall -g codex++ codexpp codex-plus-plus codex-plusplus；如果是压缩包或客户端安装，请删除对应程序并移除 PATH。",
    ),
    RiskPluginSpec(
        id="claude_code_router",
        name="Claude Code Router / CCR",
        aliases=("ccr", "claude-code-router"),
        npm_packages=("ccr", "claude-code-router", "@musistudio/claude-code-router"),
        marker_paths=(Path.home() / ".claude-code-router", Path.home() / ".config" / "claude-code-router"),
        uninstall_hint="如果是 npm 安装，请执行 npm uninstall -g ccr claude-code-router @musistudio/claude-code-router；如果仍在运行，请先退出该工具。",
    ),
)


def toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def mask_key(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 12:
        return "******"
    return f"{value[:6]}...{value[-4:]}"


def sanitize_log_text(message: str, *known_secrets: str) -> str:
    text = str(message)
    for secret in known_secrets:
        secret = str(secret or "").strip()
        if secret:
            text = text.replace(secret, mask_key(secret))
    text = re.sub(r"\bsk[-_][A-Za-z0-9][A-Za-z0-9._-]{8,}\b", lambda match: mask_key(match.group(0)), text)
    return sanitize_commercial_text(text)


def sanitize_worker_message(message: str) -> str:
    return sanitize_commercial_text(str(message))


def customer_error_with_diagnostic(message: object, diagnostic_code: str) -> str:
    safe_message = sanitize_worker_message(str(message))
    code = str(diagnostic_code or "").strip()
    if not code:
        return safe_message
    if code in safe_message:
        return safe_message
    return f"诊断码：{code}\n{safe_message}\n请把诊断码发给客服排查。"


def codex_home() -> Path:
    return Path.home() / ".codex"


def codex_auth_path() -> Path:
    return codex_home() / "auth.json"


def codex_mode_snapshots_root() -> Path:
    return codex_home() / "panghu_modes"


def workspace_root() -> Path:
    return Path.home() / "Documents" / "胖虎AI-Agent工作区"


def claude_code_settings_path() -> Path:
    return Path(os.environ.get("CLAUDE_CODE_SETTINGS_PATH") or (Path.home() / ".claude" / "settings.json"))


def openclaw_config_path() -> Path:
    return Path(os.environ.get("OPENCLAW_CONFIG_PATH") or (Path.home() / ".openclaw" / "openclaw.json"))


def hermes_home_path() -> Path:
    explicit = os.environ.get("HERMES_HOME")
    if explicit:
        return Path(explicit)
    if platform.system() == "Windows":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "hermes"
    return Path.home() / ".hermes"


def hermes_config_path() -> Path:
    return hermes_home_path() / "config.yaml"


def hermes_env_path() -> Path:
    return hermes_home_path() / ".env"


def customer_acceptance_matrix_path() -> Path:
    return workspace_root() / "胖虎AI-Agent功能验收矩阵.txt"


def app_data_dir() -> Path:
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / "PanghuAI-Client"
    return Path.home() / ".panghuai-client"


def profile_path() -> Path:
    return app_data_dir() / "profile.json"


def buyer_session_metadata_path() -> Path:
    return app_data_dir() / "buyer_session.json"


def buyer_session_cookie_path() -> Path:
    return app_data_dir() / "buyer_session_cookies.txt"


def login_account_store_path() -> Path:
    return app_data_dir() / "login_accounts.json"


def web_profile_root() -> Path:
    return app_data_dir() / "web_profiles"


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def asset_path(name: str) -> Path:
    bundled_root = getattr(sys, "_MEIPASS", None)
    if bundled_root:
        bundled = Path(bundled_root) / "assets" / name
        if bundled.exists():
            return bundled
    root = app_root()
    for candidate in (
        root / "assets" / name,
        root.parent / "Resources" / "assets" / name,
        root.parent / "Frameworks" / "assets" / name,
    ):
        if candidate.exists():
            return candidate
    return app_root() / "assets" / name


def ui_path(name: str) -> Path:
    bundled_root = getattr(sys, "_MEIPASS", None)
    if bundled_root:
        bundled = Path(bundled_root) / "ui" / name
        if bundled.exists():
            return bundled
    root = app_root()
    for candidate in (
        root / "src" / "ui" / name,
        root / "ui" / name,
        root.parent / "Resources" / "ui" / name,
    ):
        if candidate.exists():
            return candidate
    return app_root() / "src" / "ui" / name


def require_webview_runtime_and_ui() -> tuple[object, Path]:
    shell = ui_path("index.html")
    if not shell.exists():
        raise RuntimeError(
            f"胖虎AI客户端正式界面缺失：{shell}。客户包必须包含 WebView UI，不能回退到旧 Tkinter 业务界面。"
        )
    if webview is None:
        raise RuntimeError(
            "胖虎AI客户端正式界面依赖 pywebview，但当前运行包未加载该依赖。"
            "请修复打包依赖后重新发布，不能回退到旧 Tkinter 业务界面。"
        )
    return webview, shell


def save_theme_preference(theme: str) -> None:
    try:
        pref_file = app_data_dir() / "theme.txt"
        pref_file.parent.mkdir(parents=True, exist_ok=True)
        pref_file.write_text(theme, encoding="utf-8")
    except Exception:
        pass


def load_theme_preference() -> str:
    try:
        pref_file = app_data_dir() / "theme.txt"
        if pref_file.exists():
            return pref_file.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return "light"


def _normalize_login_username(username: str) -> str:
    return str(username or "").strip().lower()


def _xor_local_secret(data: bytes) -> bytes:
    seed = f"{APP_NAME}:{device_fingerprint()}".encode("utf-8", errors="ignore")
    key = hashlib.sha256(seed).digest()
    return bytes(value ^ key[index % len(key)] for index, value in enumerate(data))


def _dpapi_protect(data: bytes) -> bytes:
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    input_buffer = ctypes.create_string_buffer(data)
    input_blob = DATA_BLOB(len(data), ctypes.cast(input_buffer, ctypes.POINTER(ctypes.c_char)))
    output_blob = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(input_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(output_blob),
    ):
        raise OSError("CryptProtectData failed")
    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(output_blob.pbData)


def _dpapi_unprotect(data: bytes) -> bytes:
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    input_buffer = ctypes.create_string_buffer(data)
    input_blob = DATA_BLOB(len(data), ctypes.cast(input_buffer, ctypes.POINTER(ctypes.c_char)))
    output_blob = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(input_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(output_blob),
    ):
        raise OSError("CryptUnprotectData failed")
    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(output_blob.pbData)


def protect_local_secret(value: str) -> str:
    text = str(value or "")
    if not text:
        return ""
    raw = text.encode("utf-8")
    if platform.system() == "Windows":
        try:
            return "dpapi:" + base64.b64encode(_dpapi_protect(raw)).decode("ascii")
        except Exception:
            pass
    return "local-v1:" + base64.b64encode(_xor_local_secret(raw)).decode("ascii")


def unprotect_local_secret(value: str) -> str:
    text = str(value or "")
    if not text:
        return ""
    try:
        if text.startswith("dpapi:") and platform.system() == "Windows":
            data = base64.b64decode(text[6:].encode("ascii"))
            return _dpapi_unprotect(data).decode("utf-8")
        if text.startswith("local-v1:"):
            data = base64.b64decode(text[9:].encode("ascii"))
            return _xor_local_secret(data).decode("utf-8")
        if text.startswith("fallback:"):
            data = base64.b64decode(text[9:].encode("ascii"))
            return data[::-1].decode("utf-8")
    except Exception:
        return ""
    return ""


def _write_login_account_store(state: dict) -> None:
    accounts = []
    for item in state.get("accounts") or []:
        if not isinstance(item, dict):
            continue
        username = _normalize_login_username(item.get("username") or "")
        if not username:
            continue
        protected_password = str(item.get("protected_password") or "")
        remember_password = bool(item.get("remember_password") and protected_password)
        auto_login = bool(item.get("auto_login") and remember_password)
        stored = {
            "username": username,
            "user_id": str(item.get("user_id") or ""),
            "remember_password": remember_password,
            "auto_login": auto_login,
            "protected_password": protected_password if remember_password else "",
        }
        accounts.append(stored)
    last_username = _normalize_login_username(state.get("last_username") or "")
    if last_username and all(item["username"] != last_username for item in accounts):
        last_username = accounts[0]["username"] if accounts else ""
    payload = {"base_url": DEFAULT_BASE_URL, "last_username": last_username, "accounts": accounts}
    write_text(login_account_store_path(), json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    try:
        os.chmod(login_account_store_path(), 0o600)
    except Exception:
        pass


def load_login_account_state() -> dict:
    path = login_account_store_path()
    if not path.exists():
        return {"last_username": "", "accounts": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"last_username": "", "accounts": []}
    if not isinstance(payload, dict):
        return {"last_username": "", "accounts": []}
    accounts = []
    seen: set[str] = set()
    for raw in payload.get("accounts") or []:
        if not isinstance(raw, dict):
            continue
        username = _normalize_login_username(raw.get("username") or "")
        if not username or username in seen:
            continue
        seen.add(username)
        protected_password = str(raw.get("protected_password") or "")
        password = unprotect_local_secret(protected_password) if protected_password else ""
        if not password:
            legacy_protected_password = str(raw.get("password") or "")
            legacy_password = unprotect_local_secret(legacy_protected_password) if legacy_protected_password else ""
            if legacy_password:
                protected_password = legacy_protected_password
                password = legacy_password
        remember_password = bool(raw.get("remember_password") and protected_password and password)
        accounts.append(
            {
                "username": username,
                "user_id": str(raw.get("user_id") or ""),
                "remember_password": remember_password,
                "auto_login": bool(raw.get("auto_login") and remember_password and password),
                "password": password if remember_password else "",
                "protected_password": protected_password if remember_password else "",
            }
        )
    last_username = _normalize_login_username(payload.get("last_username") or "")
    if last_username and last_username not in seen:
        last_username = accounts[0]["username"] if accounts else ""
    return {"last_username": last_username, "accounts": accounts}


def load_login_account_public_state() -> dict:
    state = load_login_account_state()
    public_accounts = []
    for account in state.get("accounts", []):
        public_accounts.append(
            {
                "username": account.get("username", ""),
                "user_id": account.get("user_id", ""),
                "remember_password": bool(account.get("remember_password")),
                "auto_login": bool(account.get("auto_login")),
                "has_password": bool(account.get("password")),
            }
        )
    return {"last_username": state.get("last_username", ""), "accounts": public_accounts}


def login_account_public_entry(username: str) -> dict:
    normalized = _normalize_login_username(username)
    for account in load_login_account_public_state().get("accounts", []):
        if _normalize_login_username(account.get("username") or "") == normalized:
            return account
    return {
        "username": normalized,
        "user_id": "",
        "remember_password": False,
        "auto_login": False,
        "has_password": False,
    }


def login_account_private_entry(username: str) -> dict:
    normalized = _normalize_login_username(username)
    for account in load_login_account_state().get("accounts", []):
        if _normalize_login_username(account.get("username") or "") == normalized:
            return account
    return {}


def save_login_account_state(
    username: str,
    password: str = "",
    remember_password: bool = False,
    auto_login: bool = False,
    user_id: str = "",
) -> None:
    normalized = _normalize_login_username(username)
    if not normalized:
        return
    state = load_login_account_state()
    existing = next(
        (account for account in state["accounts"] if _normalize_login_username(account.get("username") or "") == normalized),
        {},
    )
    protected_password = ""
    if remember_password:
        protected_password = protect_local_secret(password) if password else str(existing.get("protected_password") or "")
    account = {
        "username": normalized,
        "user_id": str(user_id or existing.get("user_id") or ""),
        "remember_password": bool(remember_password and protected_password),
        "auto_login": bool(auto_login and remember_password and protected_password),
        "protected_password": protected_password if remember_password else "",
    }
    accounts = [
        item
        for item in state["accounts"]
        if _normalize_login_username(item.get("username") or "") != normalized
    ]
    accounts.insert(0, account)
    _write_login_account_store({"last_username": normalized, "accounts": accounts})


def disable_login_account_auto_login(username: str) -> dict:
    normalized = _normalize_login_username(username)
    if not normalized:
        return load_login_account_public_state()
    state = load_login_account_state()
    changed = False
    for account in state.get("accounts", []):
        if _normalize_login_username(account.get("username") or "") == normalized:
            account["auto_login"] = False
            changed = True
            break
    if changed:
        _write_login_account_store(state)
    return load_login_account_public_state()


def remove_login_account_state(username: str) -> dict:
    normalized = _normalize_login_username(username)
    state = load_login_account_state()
    removed = next(
        (item for item in state["accounts"] if _normalize_login_username(item.get("username") or "") == normalized),
        {},
    )
    accounts = [
        item
        for item in state["accounts"]
        if _normalize_login_username(item.get("username") or "") != normalized
    ]
    last_username = str(state.get("last_username") or "")
    if _normalize_login_username(last_username) == normalized:
        last_username = accounts[0]["username"] if accounts else ""
    _write_login_account_store({"last_username": last_username, "accounts": accounts})
    user_id = str(removed.get("user_id") or "")
    if user_id:
        seed = f"buyer:{user_id}"
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
        path = web_profile_root() / f"buyer-{digest}"
        if path.exists() and path.is_dir():
            try:
                shutil.rmtree(path)
            except Exception:
                pass
    current_session = load_buyer_session_user()
    if _normalize_login_username(current_session.get("username") or "") == normalized:
        clear_buyer_session_state()
    return load_login_account_public_state()



def color_to_char(color: str) -> str:
    if color == SUCCESS:
        return "✓"
    elif color == RUNNING:
        return "•"
    elif color == FAIL:
        return "✗"
    else:
        return "-"


def tag_to_css(tag: str) -> str:
    if tag == "failed":
        return "log-text-bad"
    elif tag == "success":
        return "log-text-ok"
    elif tag == "running":
        return "log-text-run"
    else:
        return "log-text-info"


def current_system_id() -> str:
    name = platform.system()
    if name == "Windows":
        return "windows"
    if name == "Darwin":
        return "mac"
    return "other"


def run_command(command: list[str], timeout: int = 900) -> tuple[bool, str]:
    return run_command_with_env(command, timeout=timeout)


def run_command_with_env(command: list[str], timeout: int = 900, env: dict[str, str] | None = None) -> tuple[bool, str]:
    if not command:
        return False, "命令不能为空。"
    executable = shutil.which(command[0]) or command[0]
    resolved_command = [executable, *command[1:]]
    try:
        merged_env = os.environ.copy()
        if env:
            merged_env.update({str(key): str(value) for key, value in env.items()})
        result = subprocess.run(
            resolved_command,
            text=True,
            capture_output=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
            env=merged_env,
        )
    except FileNotFoundError:
        return False, f"未找到命令：{command[0]}"
    except subprocess.TimeoutExpired:
        return False, "命令执行超时。"
    except Exception as exc:
        return False, f"命令执行失败：{exc}"
    output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
    if result.returncode == 0:
        return True, output or "命令执行完成。"
    return False, output or f"命令退出码：{result.returncode}"


def command_exists(command: str) -> tuple[bool, str]:
    exe = shutil.which(command)
    return bool(exe), exe or ""


def version_for(command: tuple[str, ...]) -> tuple[bool, str]:
    if not shutil.which(command[0]):
        return False, ""
    ok, output = run_command(list(command), timeout=12)
    return ok, output.splitlines()[0] if output else ""


def npm_global_packages() -> set[str]:
    if not shutil.which("npm"):
        return set()
    try:
        result = subprocess.run(
            ["npm", "list", "-g", "--depth=0", "--json"],
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
        )
    except Exception:
        return set()
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return set()
    dependencies = payload.get("dependencies") or {}
    if not isinstance(dependencies, dict):
        return set()
    return {str(name).lower() for name in dependencies}


def running_process_text() -> str:
    if platform.system() == "Windows":
        ok, output = run_command(["tasklist", "/FO", "CSV", "/NH"], timeout=5)
    else:
        ok, output = run_command(["ps", "-ax", "-o", "command="], timeout=5)
    return output.lower() if ok else ""


def process_text_contains_alias(process_text: str, alias: str) -> bool:
    alias = alias.strip().lower()
    if not process_text or not alias:
        return False
    pattern = rf"(?<![a-z0-9_.+\-]){re.escape(alias)}(?![a-z0-9_.+\-])"
    return re.search(pattern, process_text.lower()) is not None


def detect_risk_plugins() -> list[RiskPluginFinding]:
    findings: list[RiskPluginFinding] = []
    npm_packages = npm_global_packages()
    process_text = running_process_text()
    seen: set[tuple[str, str, str]] = set()

    def add(spec: RiskPluginSpec, source: str, detail: str) -> None:
        key = (spec.id, source, detail)
        if key in seen:
            return
        seen.add(key)
        findings.append(RiskPluginFinding(spec.name, source, detail, spec.uninstall_hint))

    for spec in RISK_PLUGIN_SPECS:
        for alias in spec.aliases:
            exists, path = command_exists(alias)
            if exists:
                add(spec, "命令", f"{alias} -> {path}")
            if process_text_contains_alias(process_text, alias):
                add(spec, "运行中", f"检测到进程关键字：{alias}")
        for package_name in spec.npm_packages:
            if package_name.lower() in npm_packages:
                add(spec, "npm 全局包", package_name)
        for marker_path in spec.marker_paths:
            if marker_path.exists():
                add(spec, "配置目录", str(marker_path))
    return findings


def risk_plugin_report_lines(findings: list[RiskPluginFinding]) -> list[str]:
    if not findings:
        return ["风险插件：未发现 ccswitch、codex++、CCR 等第三方配置切换工具。"]
    lines = [
        "风险插件：发现第三方配置切换工具，已禁止继续安装。",
        "原因：这类工具可能接管或改写 Codex / ClaudeCode 配置，导致胖虎AI写入的配置被改坏。",
    ]
    for finding in findings:
        lines.append(f"- {finding.name}：{finding.source}，{finding.detail}")
    lines.append("请先卸载或禁用这些工具，重新打开本工具后再部署。")
    return lines


def build_local_communication_software_link_acceptance_evidence(
    session_id: str,
    order_id: str,
    agent_id: str,
    channel: str,
    platform_chat_id: str,
    test_prompt: str,
    agent_response: str,
) -> dict[str, str]:
    clean_session_id = str(session_id or "").strip()
    clean_order_id = str(order_id or "").strip()
    clean_agent_id = str(agent_id or "").strip()
    clean_channel = str(channel or "").strip() or "manual_bridge"
    clean_chat_id = str(platform_chat_id or "").strip()
    clean_prompt = str(test_prompt or COMMUNICATION_SOFTWARE_LINK_DEFAULT_PROMPT).strip()
    clean_response = str(agent_response or "").strip()
    if not clean_session_id:
        raise ValueError("连接通讯软件本地验收缺少配置会话 ID。")
    if not clean_order_id:
        raise ValueError("连接通讯软件本地验收缺少订单 ID。")
    if not clean_agent_id:
        raise ValueError("连接通讯软件本地验收缺少 Agent。")
    if not clean_response:
        raise ValueError("连接通讯软件本地验收缺少 Agent 响应内容。")
    seed_payload = {
        "session_id": clean_session_id,
        "order_id": clean_order_id,
        "agent_id": clean_agent_id,
        "channel": clean_channel,
        "platform_chat_id": clean_chat_id,
        "test_prompt": clean_prompt,
        "agent_response": clean_response,
    }
    digest = hashlib.sha256(json.dumps(seed_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    short_digest = digest[:16]
    return {
        "order_id": clean_order_id,
        "session_id": clean_session_id,
        "status": "local_runtime_verified",
        "source_event_id": f"csl-local-{short_digest}",
        "inbound_platform_message_id": f"local-{clean_channel}-in-{short_digest}",
        "outbound_platform_message_id": f"local-{clean_channel}-out-{short_digest}",
        "test_prompt": clean_prompt,
        "agent_response_digest": f"sha256:{digest}",
        "evidence_url": f"{COMMUNICATION_SOFTWARE_LINK_LOCAL_EVIDENCE_BASE_URL}/{quote(clean_session_id)}/{short_digest}",
    }


def format_risk_plugin_block_message(findings: list[RiskPluginFinding]) -> str:
    lines = [
        "检测到会改写 Agent 配置的第三方插件，已停止安装。",
        "",
        "为了防止这些软件把 Codex / ClaudeCode 配置改坏，请先卸载或禁用后再继续。",
        "",
        "发现项目：",
    ]
    for finding in findings:
        lines.append(f"- {finding.name}（{finding.source}）：{finding.detail}")
    hints = []
    for finding in findings:
        if finding.uninstall_hint not in hints:
            hints.append(finding.uninstall_hint)
    if hints:
        lines.extend(["", "处理建议："])
        lines.extend(f"- {hint}" for hint in hints)
    lines.extend(["", "处理完成后，请重新打开本工具并重新检测环境。"])
    return "\n".join(lines)


def codex_command_exists() -> tuple[bool, str]:
    return version_for(("codex", "--version"))


def codex_app_package_exists() -> tuple[bool, str]:
    if platform.system() != "Windows":
        return False, ""
    ok, output = run_command(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            "Get-AppxPackage -Name OpenAI.Codex | Select-Object -First 1 -ExpandProperty PackageFullName",
        ],
        timeout=12,
    )
    package = output.strip() if ok else ""
    return bool(package), package


def create_codex_shortcuts(log) -> None:
    if platform.system() != "Windows":
        return
    package_ok, _package = codex_app_package_exists()
    if not package_ok:
        return
    shortcut_targets = [
        Path.home() / "Desktop" / "Codex.lnk",
        Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Codex.lnk",
    ]
    shortcut_commands = []
    for target in shortcut_targets:
        if not str(target):
            continue
        safe_target = str(target).replace("'", "''")
        shortcut_commands.append(
            f"$s = $shell.CreateShortcut('{safe_target}'); "
            "$s.TargetPath = 'explorer.exe'; "
            "$s.Arguments = 'shell:AppsFolder\\OpenAI.Codex_8wekyb3d8bbwe!App'; "
            "$s.IconLocation = 'shell32.dll,220'; "
            "$s.Save()"
        )
    script = "\n".join(
        [
            "$shell = New-Object -ComObject WScript.Shell",
            *shortcut_commands,
        ]
    )
    ok, output = run_command(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script], timeout=20)
    if ok:
        log("已创建 Codex 快捷方式：桌面和开始菜单。")
    else:
        log(f"Codex 快捷方式创建失败：{output}")


def _detect_desktop_app(candidates: list[Path], app_name: str) -> tuple[bool, str]:
    for path in candidates:
        if not str(path):
            continue
        try:
            if path.exists():
                return True, f"{app_name}：{path}"
            matches = sorted(path.parent.glob(path.name)) if any(ch in path.name for ch in "*?[") else []
            if matches:
                return True, f"{app_name}：{matches[-1]}"
        except OSError:
            continue
    return False, f"{app_name} 未在常见安装位置检测到。"


def claude_desktop_client_status() -> tuple[bool, str]:
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        Path(local_app_data) / "AnthropicClaude" / "claude.exe" if local_app_data else Path(""),
        Path(local_app_data) / "AnthropicClaude" / "app-*" / "claude.exe" if local_app_data else Path(""),
        Path(local_app_data) / "Programs" / "Claude" / "Claude.exe" if local_app_data else Path(""),
        Path("/Applications/Claude.app"),
        Path.home() / "Applications" / "Claude.app",
    ]
    return _detect_desktop_app(candidates, "Claude Desktop 官方客户端")


def antigravity_client_status() -> tuple[bool, str]:
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        Path(local_app_data) / "Programs" / "Antigravity" / "Antigravity.exe" if local_app_data else Path(""),
        Path(local_app_data) / "Antigravity" / "Antigravity.exe" if local_app_data else Path(""),
        Path("/Applications/Antigravity.app"),
        Path.home() / "Applications" / "Antigravity.app",
        Path.home() / ".antigravity",
    ]
    return _detect_desktop_app(candidates, "Google Antigravity 官方客户端")


def agent_client_status(agent: AgentSpec) -> tuple[bool, str]:
    if agent.id == "codex":
        return codex_app_package_exists()
    if agent.id == "claude_code":
        return claude_desktop_client_status()
    if agent.id == "gemini_agy":
        return antigravity_client_status()
    if agent.id in CLI_ONLY_DELIVERY_AGENTS:
        return False, f"{agent.name} 官方未提供客户端安装，本产品只销售 CLI 交付。"
    return False, "未配置客户端检测规则。"


def agent_install_status_lines() -> list[str]:
    lines = ["Agent 检测："]
    for agent in AGENTS:
        cli_ok, cli_version = version_for(agent.verify_command)
        client_ok, client_detail = agent_client_status(agent)
        cli_text = f"CLI 已找到 {cli_version}" if cli_ok else "CLI 未找到"
        if client_ok:
            client_text = f"客户端已找到 {client_detail}"
        else:
            client_text = f"客户端未确认：{client_detail}"
        lines.append(f"- {agent.name}: {cli_text}；{client_text}")
    return lines


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_saved_profile() -> dict:
    path = profile_path()
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def save_profile_data(data: dict, contexts=None) -> None:
    safe = build_persistent_profile_payload(
        current_profile=load_saved_profile(),
        updates=data,
        contexts=contexts,
        default_base_url=DEFAULT_BASE_URL,
        default_model=DEFAULT_MODEL,
    )
    write_text(profile_path(), json.dumps(safe, ensure_ascii=False, indent=2) + "\n")


def load_buyer_cookie_jar() -> http.cookiejar.MozillaCookieJar:
    path = buyer_session_cookie_path()
    jar = http.cookiejar.MozillaCookieJar(str(path))
    if path.exists():
        try:
            jar.load(ignore_discard=True, ignore_expires=False)
        except Exception:
            jar.clear()
    return jar


def save_buyer_cookie_jar(cookie_jar: http.cookiejar.CookieJar) -> None:
    path = buyer_session_cookie_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    jar_to_save = http.cookiejar.MozillaCookieJar(str(path))
    for cookie in cookie_jar:
        domain = str(getattr(cookie, "domain", "") or "").lstrip(".").lower()
        if domain == "aitokenapi.cc" or domain.endswith(".aitokenapi.cc"):
            jar_to_save.set_cookie(cookie)
    jar_to_save.save(ignore_discard=True, ignore_expires=True)
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass


def safe_buyer_session_user(user: dict) -> dict:
    if not isinstance(user, dict):
        return {}
    user_id = str(user.get("id") or user.get("user_id") or "").strip()
    if not user_id:
        return {}
    role = str(user.get("role") or "buyer").strip().lower()
    if role == "agent":
        return {}
    username = str(user.get("username") or user.get("email") or user.get("account") or "").strip()
    display_name = str(user.get("display_name") or username or user_id).strip()
    return {
        "id": user_id,
        "username": username,
        "display_name": display_name,
        "role": "buyer",
    }


def save_buyer_session_state(user: dict, cookie_jar: http.cookiejar.CookieJar) -> None:
    safe_user = safe_buyer_session_user(user)
    if not safe_user:
        return
    save_buyer_cookie_jar(cookie_jar)
    payload = {
        "base_url": DEFAULT_BASE_URL,
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "user": safe_user,
    }
    write_text(buyer_session_metadata_path(), json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def load_buyer_session_user() -> dict:
    path = buyer_session_metadata_path()
    if not path.exists() or not buyer_session_cookie_path().exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(payload, dict) or str(payload.get("base_url") or "") != DEFAULT_BASE_URL:
        return {}
    return safe_buyer_session_user(payload.get("user") or {})


def clear_buyer_session_state(cookie_jar: http.cookiejar.CookieJar | None = None) -> None:
    if cookie_jar is not None:
        try:
            cookie_jar.clear()
        except Exception:
            pass
    for path in (buyer_session_metadata_path(), buyer_session_cookie_path()):
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        except Exception:
            pass


def ensure_commercial_web_profile_dir(profile) -> Path:
    path = Path(profile.path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def cleanup_ephemeral_web_profile(profile) -> None:
    if not getattr(profile, "ephemeral", False):
        return
    path = Path(profile.path)
    root = Path(profile.root_dir)
    try:
        resolved_path = path.resolve()
        resolved_root = root.resolve()
    except OSError:
        return
    if resolved_path == resolved_root or resolved_root not in resolved_path.parents:
        return
    if path.exists():
        shutil.rmtree(path)


def cleanup_legacy_ephemeral_web_profiles(root_dir: str | None = None) -> None:
    root = Path(root_dir or web_profile_root())
    if not root.exists():
        return
    try:
        resolved_root = root.resolve()
    except OSError:
        return
    for path in root.glob("agent-assist-*"):
        try:
            resolved_path = path.resolve()
        except OSError:
            continue
        if resolved_path == resolved_root or resolved_root not in resolved_path.parents:
            continue
        if path.is_dir():
            shutil.rmtree(path)


def backup_file(path: Path) -> Path | None:
    if not path.exists():
        return None
    backup = path.with_name(f"{path.name}.bak-{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(path, backup)
    return backup


def restore_backup(path: Path, backup: Path | None, existed_before: bool) -> None:
    if backup and backup.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup, path)
    elif not existed_before and path.exists():
        path.unlink()


def latest_backup_for(path: Path) -> Path | None:
    if not path.parent.exists():
        return None
    backups = sorted(
        path.parent.glob(f"{path.name}.bak-*"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    return backups[0] if backups else None


def restore_latest_backups(log) -> bool:
    targets = [
        codex_home() / "config.toml",
        codex_auth_path(),
        codex_home() / "AGENTS.md",
        workspace_root() / "AGENTS.md",
    ]
    restored = False
    for target in targets:
        backup = latest_backup_for(target)
        if not backup:
            log(f"未找到可恢复备份：{target}")
            continue
        restore_backup(target, backup, True)
        restored = True
        log(f"已恢复：{target} <- {backup}")
    return restored


CODEX_MANAGED_TOP_LEVEL_KEYS = {
    "model_provider",
    "model",
    "review_model",
    "model_reasoning_effort",
    "disable_response_storage",
    "network_access",
    "windows_wsl_setup_acknowledged",
    "model_context_window",
    "model_auto_compact_token_limit",
}


CODEX_OFFICIAL_TOP_LEVEL_CONFIG = [
    'model_provider = "openai"',
    'model = "gpt-5.5"',
    'review_model = "gpt-5.5"',
    'model_reasoning_effort = "xhigh"',
    "disable_response_storage = true",
    'network_access = "enabled"',
    "windows_wsl_setup_acknowledged = true",
    "model_context_window = 1000000",
    "model_auto_compact_token_limit =600000",
]


CODEX_MODE_FILE_NAMES = {
    "config": "config.toml",
    "auth": "auth.json",
    "global_agents": "AGENTS.global.md",
    "workspace_agents": "AGENTS.workspace.md",
}


def safe_read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def has_chatgpt_auth_state(auth_text: str) -> bool:
    try:
        payload = json.loads(auth_text) if auth_text.strip() else {}
    except json.JSONDecodeError:
        return False
    if not isinstance(payload, dict):
        return False
    if str(payload.get("auth_mode") or "").lower() == "chatgpt":
        return True
    tokens = payload.get("tokens")
    if isinstance(tokens, dict):
        return bool(str(tokens.get("access_token") or "").strip() or str(tokens.get("refresh_token") or "").strip())
    return False


def detect_codex_config_mode(config_text: str, auth_text: str) -> CodexConfigMode | None:
    if "model_provider = \"panghuAI\"" in config_text or "[model_providers.panghuAI]" in config_text:
        if "experimental_bearer_token" in config_text:
            return CodexConfigMode.DUAL_STATE
        return CodexConfigMode.DIRECT_API
    if has_chatgpt_auth_state(auth_text):
        return CodexConfigMode.OFFICIAL_CHATGPT
    try:
        payload = json.loads(auth_text) if auth_text.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    if isinstance(payload, dict) and str(payload.get("OPENAI_API_KEY") or "").strip():
        return CodexConfigMode.DIRECT_API
    return None


def codex_mode_snapshot_dir(mode: CodexConfigMode) -> Path:
    return codex_mode_snapshots_root() / mode.value


def save_codex_mode_snapshot(
    mode: CodexConfigMode | None,
    config_path: Path,
    auth_path: Path,
    global_agents: Path,
    workspace_agents: Path,
    log,
) -> None:
    if mode is None:
        history_dir = codex_mode_snapshots_root() / "history" / time.strftime("%Y%m%d-%H%M%S")
        snapshot_dir = history_dir
        label = "未知模式"
    else:
        snapshot_dir = codex_mode_snapshot_dir(mode)
        label = mode.value
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    sources = {
        "config": config_path,
        "auth": auth_path,
        "global_agents": global_agents,
        "workspace_agents": workspace_agents,
    }
    saved_any = False
    for key, source in sources.items():
        target = snapshot_dir / CODEX_MODE_FILE_NAMES[key]
        if source.exists():
            shutil.copy2(source, target)
            saved_any = True
        elif target.exists():
            target.unlink()
    if saved_any:
        manifest = {
            "mode": mode.value if mode else "unknown",
            "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "files": CODEX_MODE_FILE_NAMES,
        }
        write_text(snapshot_dir / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        log(f"已保存当前 Codex 模式快照：{label} -> {snapshot_dir}")


def restore_codex_mode_snapshot(
    mode: CodexConfigMode,
    config_path: Path,
    auth_path: Path,
    global_agents: Path,
    workspace_agents: Path,
    log,
) -> bool:
    snapshot_dir = codex_mode_snapshot_dir(mode)
    config_snapshot = snapshot_dir / CODEX_MODE_FILE_NAMES["config"]
    auth_snapshot = snapshot_dir / CODEX_MODE_FILE_NAMES["auth"]
    if not config_snapshot.exists() or not auth_snapshot.exists():
        return False
    targets = {
        "config": config_path,
        "auth": auth_path,
        "global_agents": global_agents,
        "workspace_agents": workspace_agents,
    }
    for key, target in targets.items():
        source = snapshot_dir / CODEX_MODE_FILE_NAMES[key]
        if source.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    log(f"已恢复 Codex 模式快照：{mode.value} <- {snapshot_dir}")
    return True


def load_codex_mode_snapshot(mode: CodexConfigMode) -> dict[str, str] | None:
    snapshot_dir = codex_mode_snapshot_dir(mode)
    config_snapshot = snapshot_dir / CODEX_MODE_FILE_NAMES["config"]
    auth_snapshot = snapshot_dir / CODEX_MODE_FILE_NAMES["auth"]
    if not config_snapshot.exists() or not auth_snapshot.exists():
        return None
    return {
        "config": safe_read_text(config_snapshot),
        "auth": safe_read_text(auth_snapshot),
        "global_agents": safe_read_text(snapshot_dir / CODEX_MODE_FILE_NAMES["global_agents"]),
        "workspace_agents": safe_read_text(snapshot_dir / CODEX_MODE_FILE_NAMES["workspace_agents"]),
    }


def build_config(api_key: str, base_url: str, model: str) -> str:
    return '''model_provider = "panghuAI"
model = "gpt-5.5"
review_model = "gpt-5.5"
model_reasoning_effort = "xhigh"
disable_response_storage = true
network_access = "enabled"
windows_wsl_setup_acknowledged = true
model_context_window = 1000000
model_auto_compact_token_limit =600000

[model_providers.panghuAI]
name = "panghuAI"
base_url = "https://aitokenapi.cc/v1"
wire_api = "responses"
requires_openai_auth = true
'''


def build_dual_state_config(api_key: str, base_url: str, model: str) -> str:
    safe_api_key = api_key.strip().replace("\\", "\\\\").replace('"', '\\"')
    config = build_config(api_key, base_url, model)
    return config.replace(
        'wire_api = "responses"\n',
        f'wire_api = "responses"\nexperimental_bearer_token = "{safe_api_key}"\n',
    )


def build_official_chatgpt_config(existing: str, model: str) -> str:
    lines = existing.splitlines() if existing.strip() else []
    lines = remove_sections(lines, {"model_providers.panghuAI"})
    lines = update_top_level_keys(lines, CODEX_OFFICIAL_TOP_LEVEL_CONFIG, CODEX_MANAGED_TOP_LEVEL_KEYS)
    return "\n".join(lines).rstrip() + "\n"


def chinese_rules() -> str:
    return """# 胖虎AI Agent 客户默认规则

- 默认使用简体中文回答。
- 用户没有明确要求英文时，不要切换到英文。
- 解释步骤时使用普通用户能看懂的说法，少用英文术语。
- 遇到 API、模型、网络、权限问题时，先给出可执行的修复步骤。
"""


def managed_chinese_rules_block() -> str:
    return f"{PANGHU_AGENTS_START}\n{chinese_rules().strip()}\n{PANGHU_AGENTS_END}\n"


def merge_agents_rules(existing: str) -> str:
    block = managed_chinese_rules_block()
    pattern = re.compile(
        rf"{re.escape(PANGHU_AGENTS_START)}.*?{re.escape(PANGHU_AGENTS_END)}\s*",
        re.DOTALL,
    )
    if pattern.search(existing):
        return pattern.sub(block, existing)
    prefix = existing.rstrip()
    if prefix:
        return f"{prefix}\n\n{block}"
    return block


def section_name(line: str) -> str | None:
    match = re.match(r"^\s*\[([^\]]+)\]\s*$", line)
    if match:
        return match.group(1).strip()
    return None


def remove_sections(lines: list[str], names: set[str]) -> list[str]:
    kept: list[str] = []
    skipping = False
    for line in lines:
        name = section_name(line)
        if name is not None:
            skipping = name in names
        if not skipping:
            kept.append(line)
    return kept


def update_top_level_keys(lines: list[str], values: list[str], keys: set[str]) -> list[str]:
    first_section = next((idx for idx, line in enumerate(lines) if section_name(line) is not None), len(lines))
    top = []
    for line in lines[:first_section]:
        key = line.split("=", 1)[0].strip() if "=" in line else ""
        if key not in keys:
            top.append(line)
    while top and top[-1].strip() == "":
        top.pop()
    rest = lines[first_section:]
    merged = top + values
    if rest:
        merged.append("")
        merged.extend(rest)
    return merged


def update_or_append_section(lines: list[str], name: str, values: list[str], keys: set[str]) -> list[str]:
    start = next((idx for idx, line in enumerate(lines) if section_name(line) == name), None)
    if start is None:
        result = lines[:]
        if result and result[-1].strip():
            result.append("")
        result.append(f"[{name}]")
        result.extend(values)
        return result

    end = len(lines)
    for idx in range(start + 1, len(lines)):
        if section_name(lines[idx]) is not None:
            end = idx
            break

    body = []
    for line in lines[start + 1 : end]:
        key = line.split("=", 1)[0].strip() if "=" in line else ""
        if key not in keys:
            body.append(line)
    return lines[: start + 1] + values + body + lines[end:]


def merge_config(existing: str, api_key: str, base_url: str, model: str) -> str:
    return build_config(api_key, base_url, model)


def build_auth_json(existing: str, api_key: str) -> str:
    return build_direct_api_auth_json(existing, api_key)


def build_direct_api_auth_json(existing: str, api_key: str) -> str:
    payload = {"OPENAI_API_KEY": api_key.strip()}
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_dual_state_auth_json(existing: str, api_key: str) -> str:
    try:
        payload = json.loads(existing) if existing.strip() else {}
        if not isinstance(payload, dict):
            payload = {}
    except json.JSONDecodeError:
        payload = {}
    payload["auth_mode"] = "chatgpt"
    payload["OPENAI_API_KEY"] = None
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_official_chatgpt_auth_json(existing: str) -> str:
    try:
        payload = json.loads(existing) if existing.strip() else {}
        if not isinstance(payload, dict):
            payload = {}
    except json.JSONDecodeError:
        payload = {}
    if not has_chatgpt_auth_state(json.dumps(payload, ensure_ascii=False)):
        raise ValueError("未检测到 ChatGPT 登录态。请先打开 Codex，用自己的 ChatGPT 账号登录一次，再切换官方直登模式。")
    payload["auth_mode"] = "chatgpt"
    payload["OPENAI_API_KEY"] = None
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def trusted_ssl_context() -> ssl.SSLContext:
    if certifi is not None:
        return ssl.create_default_context(cafile=certifi.where())
    return ssl.create_default_context()


def trusted_urlopen(req: Request, timeout: int = 20):
    return urlopen(req, timeout=timeout, context=trusted_ssl_context())


def build_trusted_opener(cookie_jar: http.cookiejar.CookieJar | None = None):
    handlers = [HTTPSHandler(context=trusted_ssl_context())]
    if cookie_jar is not None:
        handlers.insert(0, HTTPCookieProcessor(cookie_jar))
    return build_opener(*handlers)


def download_with_trusted_certs(url: str, target: Path) -> None:
    req = Request(url, headers={"User-Agent": HTTP_USER_AGENT})
    with trusted_urlopen(req, timeout=60) as resp, target.open("wb") as file:
        shutil.copyfileobj(resp, file)


def test_api(base_url: str, api_key: str) -> tuple[bool, str]:
    url = base_url.rstrip("/") + "/v1/models"
    req = Request(url, headers={"Authorization": f"Bearer {api_key}"}, method="GET")
    try:
        with trusted_urlopen(req, timeout=20) as resp:
            return True, f"接口连通正常：HTTP {resp.status}"
    except HTTPError as exc:
        return False, f"接口返回错误：HTTP {exc.code}"
    except URLError as exc:
        return False, f"接口连接失败：{exc.reason}"
    except Exception as exc:
        return False, f"接口测试失败：{exc}"


def build_real_task_probe_payload(base_url: str, model: str) -> tuple[str, dict]:
    return (
        base_url.rstrip("/") + "/v1/chat/completions",
        {
            "model": model,
            "messages": [{"role": "user", "content": "请用一句中文回复：胖虎AI配置验证成功"}],
            "temperature": 0,
            "max_tokens": 16,
        },
    )


def run_real_task_probe(base_url: str, api_key: str, model: str) -> tuple[bool, str]:
    url, payload = build_real_task_probe_payload(base_url, model)
    req = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with trusted_urlopen(req, timeout=45) as resp:
            raw = resp.read(4096).decode("utf-8", errors="replace")
        data = json.loads(raw)
        choices = data.get("choices") if isinstance(data, dict) else None
        if not isinstance(choices, list) or not choices:
            return False, "真实任务返回缺少 choices。"
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else ""
        if not str(content).strip():
            return False, "真实任务返回内容为空。"
        return True, str(content).strip()
    except HTTPError as exc:
        return False, f"真实任务接口返回错误：HTTP {exc.code}"
    except URLError as exc:
        return False, f"真实任务接口连接失败：{exc.reason}"
    except json.JSONDecodeError:
        return False, "真实任务接口返回内容无法解析。"
    except Exception as exc:
        return False, f"真实任务验证失败：{exc}"


def current_platform_for_license() -> str:
    system = current_system_id()
    return system if system in {"windows", "mac"} else "unknown"


def device_fingerprint() -> str:
    raw = "|".join(
        [
            platform.node(),
            platform.system(),
            platform.release(),
            platform.machine(),
            str(uuid.getnode()),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def open_json_with_cookies(
    cookie_jar: http.cookiejar.CookieJar,
    url: str,
    method: str,
    body: dict | None = None,
    headers: dict | None = None,
) -> dict:
    opener = build_trusted_opener(cookie_jar)
    data = json.dumps(body or {}).encode("utf-8") if body is not None else None
    request_headers = {
        "Accept": "application/json",
        "User-Agent": HTTP_USER_AGENT,
        **(headers or {}),
    }
    if data is not None:
        request_headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=request_headers, method=method)
    with opener.open(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def execute_commercial_api_with_trusted_certs(request, timeout: int = 20) -> tuple[dict, str]:
    return execute_commercial_api_request(request, trusted_urlopen, timeout=timeout)


# 服务端（new-api）错误 message 为英文原文，客户可见处统一映射为中文；
# 未收录的原文原样透传，不做猜测性翻译。
SERVER_MESSAGE_ZH_MAP = {
    "username or password is incorrect, or user has been banned": "账号或密码错误，或该账号已被封禁。",
    "username or password is incorrect": "账号或密码错误。",
    "user has been banned": "该账号已被封禁，请联系客服。",
    "invalid credentials": "账号或密码错误。",
    "too many requests": "请求过于频繁，请稍后再试。",
    "email address verification failed": "邮箱验证失败。",
    "captcha verification failed": "人机验证失败，请稍后再试。",
    "turnstile verification failed": "人机验证失败，请稍后再试。",
}


def localize_server_message(message) -> str:
    text = str(message or "").strip()
    if not text:
        return text
    key = text.rstrip("。.!？?").strip().lower()
    mapped = SERVER_MESSAGE_ZH_MAP.get(key)
    if mapped:
        return mapped
    for english, chinese in SERVER_MESSAGE_ZH_MAP.items():
        if english in key:
            return chinese
    return text


def login_panghuai(username: str, password: str, cookie_jar: http.cookiejar.CookieJar) -> tuple[bool, str, dict]:
    if not username.strip() or not password:
        return False, "请输入胖虎AI账号和密码。", {}
    opener = build_trusted_opener(cookie_jar)
    body = json.dumps({"username": username.strip(), "password": password}).encode("utf-8")
    req = Request(
        LOGIN_URL,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": HTTP_USER_AGENT},
        method="POST",
    )
    try:
        with opener.open(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        return False, f"登录接口返回错误：HTTP {exc.code}", {}
    except URLError as exc:
        return False, f"登录接口连接失败：{exc.reason}", {}
    except json.JSONDecodeError:
        return False, "登录接口返回内容无法解析。", {}
    except Exception as exc:
        return False, f"登录失败：{exc}", {}

    if not payload.get("success"):
        return False, localize_server_message(payload.get("message")) or "账号或密码错误。", {}
    data = payload.get("data") or {}
    return True, "登录成功。", data


def activate_deployer(user: dict, cookie_jar: http.cookiejar.CookieJar) -> tuple[bool, str, dict]:
    user_id = str(user.get("id") or "").strip()
    if not user_id:
        return False, "登录返回缺少用户 ID，无法申请部署授权。", {}
    try:
        payload = open_json_with_cookies(
            cookie_jar,
            DEPLOYER_ACTIVATE_URL,
            "POST",
            {
                "device_id": device_fingerprint(),
                "platform": current_platform_for_license(),
                "app_version": APP_VERSION,
            },
            {"New-Api-User": user_id},
        )
    except HTTPError as exc:
        return False, f"部署授权接口返回错误：HTTP {exc.code}", {}
    except URLError as exc:
        return False, f"部署授权接口连接失败：{exc.reason}", {}
    except json.JSONDecodeError:
        return False, "部署授权接口返回内容无法解析。", {}
    except Exception as exc:
        return False, f"部署授权失败：{exc}", {}
    if not payload.get("success"):
        return False, localize_server_message(payload.get("message")) or "部署授权被拒绝。", {}
    data = payload.get("data") or {}
    token = str(data.get("token") or "")
    if not token:
        return False, "部署授权返回缺少 token。", {}
    return True, "部署授权已通过。", data


def fetch_deployer_manifest(user: dict, cookie_jar: http.cookiejar.CookieJar, deployer_token: str) -> tuple[bool, str, dict]:
    user_id = str(user.get("id") or "").strip()
    if not user_id or not deployer_token:
        return False, "缺少部署授权，请重新登录。", {}
    try:
        payload = open_json_with_cookies(
            cookie_jar,
            DEPLOYER_MANIFEST_URL,
            "GET",
            None,
            {"New-Api-User": user_id, "X-Panghu-Deployer-Token": deployer_token},
        )
    except HTTPError as exc:
        return False, f"部署清单接口返回错误：HTTP {exc.code}", {}
    except URLError as exc:
        return False, f"部署清单接口连接失败：{exc.reason}", {}
    except json.JSONDecodeError:
        return False, "部署清单接口返回内容无法解析。", {}
    except Exception as exc:
        return False, f"部署清单获取失败：{exc}", {}
    if not payload.get("success"):
        return False, str(payload.get("message") or "部署清单被拒绝。"), {}
    return True, "部署清单校验通过。", payload.get("data") or {}


def manifest_allowed_agents(manifest: dict) -> list[str]:
    agents = manifest.get("agents") or []
    allowed: list[str] = []
    if isinstance(agents, list):
        for item in agents:
            if isinstance(item, dict) and item.get("id"):
                allowed.append(str(item["id"]))
    return allowed


def manifest_commercial_capabilities(manifest: dict):
    return build_commercial_agent_capabilities(manifest)


def manifest_commercial_products(manifest: dict):
    return build_commercial_product_catalog(manifest)


def manifest_value_added_services(manifest: dict):
    return build_value_added_service_catalog(manifest)


def parse_manifest_delivery_scope(value: object) -> DeliveryScope:
    try:
        return DeliveryScope(str(value or DeliveryScope.INSTALL_GUIDED.value))
    except ValueError:
        return DeliveryScope.INSTALL_GUIDED


def manifest_commercial_entitlements(manifest: dict) -> list[EntitlementContract]:
    entitlements = manifest.get("entitlements") or []
    parsed: list[EntitlementContract] = []
    if not isinstance(entitlements, list):
        return parsed
    for item in entitlements:
        if not isinstance(item, dict) or not item.get("entitlement_id"):
            continue
        buyer_user_id = str(item.get("buyer_user_id") or "")
        agent_id = str(item.get("agent_id") or "")
        mode_key = str(item.get("mode_key") or "")
        valid_until = str(item.get("valid_until") or "")
        delivery_scope_value = str(item.get("delivery_scope") or "")
        status = str(item.get("status") or "")
        source = str(item.get("source") or "paid")
        if not all((buyer_user_id, agent_id, mode_key, valid_until, delivery_scope_value, status)):
            continue
        try:
            delivery_scope = DeliveryScope(delivery_scope_value)
            remaining_uses = int(item["remaining_uses"])
            device_limit = int(item["device_limit"])
        except (KeyError, TypeError, ValueError):
            continue
        is_unlimited = bool(item.get("is_unlimited"))
        if remaining_uses < 0 or (remaining_uses < 1 and not is_unlimited) or device_limit < 1:
            continue
        parsed.append(
            EntitlementContract(
                entitlement_id=str(item["entitlement_id"]),
                buyer_user_id=buyer_user_id,
                agent_id=agent_id,
                mode_key=mode_key,
                remaining_uses=remaining_uses,
                valid_until=valid_until,
                delivery_scope=delivery_scope,
                includes_dual_state=bool(item.get("includes_dual_state")),
                device_limit=device_limit,
                status=status,
                source=source,
                is_unlimited=is_unlimited,
            )
        )
    return parsed


def manifest_has_commercial_controls(manifest: dict) -> bool:
    return any(
        key in manifest
        for key in ("products", "entitlements", "commercial", "commercial_enabled", "agent_center", "value_added_services")
    )


def ensure_commercial_manifest_trusted(manifest: dict, public_key_pem: str = COMMERCIAL_MANIFEST_PUBLIC_KEY_PEM) -> None:
    decision = validate_commercial_manifest_trust(manifest, public_key_pem=public_key_pem)
    if not decision.trusted:
        raise RuntimeError(decision.message)


def commercial_mode_key_for_deployment(agent_id: str, install_mode: str) -> str:
    if agent_id == "codex":
        return CodexConfigMode.DIRECT_API.value
    return install_mode


def commercial_mode_key_for_config_mode(mode: CodexConfigMode) -> str:
    return mode.value


def codex_config_mode_requires_panghu_key(mode: CodexConfigMode) -> bool:
    return mode in (CodexConfigMode.DIRECT_API, CodexConfigMode.DUAL_STATE)


def deployment_commercial_contexts(user: dict) -> "CommercialSessionContexts":
    buyer = UserContext(
        user_id=str(user.get("id") or ""),
        display_name=str(user.get("username") or user.get("display_name") or "当前买家"),
        role="buyer",
    )
    return create_buyer_contexts(buyer)


def agent_center_summary_text(manifest: dict | None) -> str:
    return "\n".join(build_agent_center_summary_lines(manifest or {}))


def value_added_services_summary_text(manifest: dict | None) -> str:
    return "\n".join(build_value_added_service_summary_lines(manifest_value_added_services(manifest or {})))


def build_commercial_config_session_reserve_preview(
    entitlement_id: str,
    buyer_user_id: str,
    operator_user_id: str,
    agent_id: str,
    mode_key: str,
    diagnostic_code: str,
):
    if not entitlement_id:
        raise ValueError("配置会话预占缺少真实权益 ID。")
    device_id = device_fingerprint()
    return build_config_session_reserve_request(
        CommercialApiContract(DEFAULT_BASE_URL),
        entitlement_id=entitlement_id,
        buyer_user_id=buyer_user_id,
        operator_user_id=operator_user_id,
        agent_id=agent_id,
        mode_key=mode_key,
        device_id=device_id,
        diagnostic_code=diagnostic_code,
        idempotency_key=stable_config_reserve_idempotency_key(
            entitlement_id=entitlement_id,
            buyer_user_id=buyer_user_id,
            operator_user_id=operator_user_id,
            agent_id=agent_id,
            mode_key=mode_key,
            device_id=device_id,
            diagnostic_code=diagnostic_code,
        ),
    )


def operator_auth_token(contexts, deployer_auth: dict | None = None) -> str:
    return str((deployer_auth or {}).get("token") or contexts.operator.token or "").strip()


def commercial_api_request_with_auth(
    action: str,
    contexts,
    deployer_auth: dict | None = None,
    **kwargs,
):
    token = operator_auth_token(contexts, deployer_auth)
    if action == "api_key_owner_verify":
        request = build_api_key_owner_verify_request(
            CommercialApiContract(DEFAULT_BASE_URL),
            api_key=str(kwargs["api_key"]),
            target_buyer_user_id=contexts.target_buyer.user_id,
            operator_user_id=contexts.operator.user_id,
        )
    elif action == "order_create":
        request = build_order_create_request(
            CommercialApiContract(DEFAULT_BASE_URL),
            product_id=str(kwargs["product_id"]),
            buyer_user_id=contexts.target_buyer.user_id,
            operator_user_id=contexts.operator.user_id,
            idempotency_key=stable_order_idempotency_key(
                product_id=str(kwargs["product_id"]),
                buyer_user_id=contexts.target_buyer.user_id,
                operator_user_id=contexts.operator.user_id,
            ),
        )
    elif action == "payment_poll":
        request = build_payment_poll_request(
            CommercialApiContract(DEFAULT_BASE_URL),
            order_id=str(kwargs["order_id"]),
            buyer_user_id=contexts.target_buyer.user_id,
            operator_user_id=contexts.operator.user_id,
        )
    elif action == "entitlement_query":
        request = build_entitlement_query_request(
            CommercialApiContract(DEFAULT_BASE_URL),
            buyer_user_id=contexts.target_buyer.user_id,
            operator_user_id=contexts.operator.user_id,
        )
    elif action == "agent_center":
        request = build_agent_center_request(CommercialApiContract(DEFAULT_BASE_URL))
    elif action == "agent_downstreams":
        request = build_agent_downstreams_request(
            CommercialApiContract(DEFAULT_BASE_URL),
            cursor=str(kwargs.get("cursor") or ""),
            limit=int(kwargs.get("limit") or 50),
        )
    elif action == "agent_commissions":
        request = build_agent_commissions_request(
            CommercialApiContract(DEFAULT_BASE_URL),
            status=str(kwargs.get("status") or ""),
            event_type=str(kwargs.get("event_type") or ""),
            cursor=str(kwargs.get("cursor") or ""),
            limit=int(kwargs.get("limit") or 50),
        )
    elif action == "agent_public_offering":
        request = build_agent_public_offering_request(CommercialApiContract(DEFAULT_BASE_URL))
    elif action == "agent_apply":
        product_id = str(kwargs["product_id"])
        request = build_agent_apply_request(
            CommercialApiContract(DEFAULT_BASE_URL),
            product_id=product_id,
            idempotency_key=stable_agent_business_idempotency_key(
                "agent_apply",
                contexts.operator.user_id,
                product_id,
            ),
        )
    elif action == "referral_bind":
        invite_code = normalize_referral_invite_code(str(kwargs["invite_code"]))
        request = build_referral_bind_request(
            CommercialApiContract(DEFAULT_BASE_URL),
            invite_code=invite_code,
            idempotency_key=stable_agent_business_idempotency_key(
                "referral_bind",
                contexts.target_buyer.user_id,
                invite_code,
            ),
        )
    elif action == "agent_settlement":
        requested_cents = int(kwargs["requested_cents"])
        request = build_agent_settlement_request(
            CommercialApiContract(DEFAULT_BASE_URL),
            requested_cents=requested_cents,
            idempotency_key=stable_agent_business_idempotency_key(
                "agent_settlement",
                contexts.operator.user_id,
                str(requested_cents),
            ),
        )
    elif action == "communication_software_link_offering":
        request = build_communication_software_link_offering_request(CommercialApiContract(DEFAULT_BASE_URL))
    elif action == "communication_software_link_order_create":
        service_product_id = str(kwargs["service_product_id"])
        agent_id = str(kwargs["agent_id"])
        channel = str(kwargs["channel"])
        agent_source = str(kwargs["agent_source"])
        request = build_communication_software_link_order_create_request(
            CommercialApiContract(DEFAULT_BASE_URL),
            service_product_id=service_product_id,
            buyer_user_id=contexts.target_buyer.user_id,
            agent_id=agent_id,
            channel=channel,
            agent_source=agent_source,
            idempotency_key=stable_communication_software_link_idempotency_key(
                "order",
                contexts.target_buyer.user_id,
                contexts.operator.user_id,
                service_product_id,
                agent_id,
                channel,
                agent_source,
            ),
        )
    elif action == "communication_software_link_order_get":
        request = build_communication_software_link_order_get_request(
            CommercialApiContract(DEFAULT_BASE_URL),
            order_id=str(kwargs["order_id"]),
        )
    elif action == "communication_software_link_session_create":
        order_id = str(kwargs["order_id"])
        agent_id = str(kwargs["agent_id"])
        channel = str(kwargs["channel"])
        platform_account_id = str(kwargs["platform_account_id"])
        platform_chat_id = str(kwargs["platform_chat_id"])
        gateway_mode = str(kwargs["gateway_mode"])
        agent_source = str(kwargs["agent_source"])
        request = build_communication_software_link_session_create_request(
            CommercialApiContract(DEFAULT_BASE_URL),
            order_id=order_id,
            agent_id=agent_id,
            channel=channel,
            platform_account_id=platform_account_id,
            platform_chat_id=platform_chat_id,
            gateway_mode=gateway_mode,
            agent_source=agent_source,
            idempotency_key=stable_communication_software_link_idempotency_key(
                "session",
                contexts.target_buyer.user_id,
                contexts.operator.user_id,
                order_id,
                agent_id,
                channel,
                platform_account_id,
                platform_chat_id,
                gateway_mode,
                agent_source,
            ),
        )
    elif action == "communication_software_link_session_get":
        request = build_communication_software_link_session_get_request(
            CommercialApiContract(DEFAULT_BASE_URL),
            session_id=str(kwargs["session_id"]),
        )
    elif action == "communication_software_link_session_test":
        session_id = str(kwargs["session_id"])
        test_prompt = str(kwargs["test_prompt"])
        request = build_communication_software_link_session_test_request(
            CommercialApiContract(DEFAULT_BASE_URL),
            session_id=session_id,
            test_prompt=test_prompt,
            idempotency_key=stable_communication_software_link_idempotency_key(
                "test",
                contexts.target_buyer.user_id,
                contexts.operator.user_id,
                session_id,
                test_prompt,
            ),
        )
    elif action == "communication_software_link_session_acceptance":
        session_id = str(kwargs["session_id"])
        source_event_id = str(kwargs["source_event_id"])
        inbound_platform_message_id = str(kwargs["inbound_platform_message_id"])
        outbound_platform_message_id = str(kwargs["outbound_platform_message_id"])
        test_prompt = str(kwargs["test_prompt"])
        agent_response_digest = str(kwargs["agent_response_digest"])
        evidence_url = str(kwargs["evidence_url"])
        request = build_communication_software_link_session_acceptance_request(
            CommercialApiContract(DEFAULT_BASE_URL),
            session_id=session_id,
            source_event_id=source_event_id,
            inbound_platform_message_id=inbound_platform_message_id,
            outbound_platform_message_id=outbound_platform_message_id,
            test_prompt=test_prompt,
            agent_response_digest=agent_response_digest,
            evidence_url=evidence_url,
            idempotency_key=stable_communication_software_link_idempotency_key(
                "acceptance",
                contexts.target_buyer.user_id,
                contexts.operator.user_id,
                session_id,
                source_event_id,
                inbound_platform_message_id,
                outbound_platform_message_id,
            ),
        )
    elif action == "communication_software_link_session_disable":
        session_id = str(kwargs["session_id"])
        request = build_communication_software_link_session_disable_request(
            CommercialApiContract(DEFAULT_BASE_URL),
            session_id=session_id,
            reason=str(kwargs.get("reason") or "buyer_disabled_from_client"),
            idempotency_key=stable_communication_software_link_idempotency_key(
                "disable",
                contexts.target_buyer.user_id,
                contexts.operator.user_id,
                session_id,
            ),
        )
    elif action == "communication_software_link_platform_auth_create":
        order_id = str(kwargs["order_id"])
        agent_id = str(kwargs["agent_id"])
        channel = str(kwargs["channel"])
        gateway_mode = str(kwargs["gateway_mode"])
        platform_chat_hint = str(kwargs.get("platform_chat_hint") or "")
        request = build_communication_software_link_platform_auth_create_request(
            CommercialApiContract(DEFAULT_BASE_URL),
            order_id=order_id,
            agent_id=agent_id,
            channel=channel,
            gateway_mode=gateway_mode,
            platform_chat_hint=platform_chat_hint,
            idempotency_key=stable_communication_software_link_idempotency_key(
                "platform_auth",
                contexts.target_buyer.user_id,
                contexts.operator.user_id,
                order_id,
                agent_id,
                channel,
                gateway_mode,
                platform_chat_hint,
            ),
        )
    elif action == "communication_software_link_platform_auth_get":
        request = build_communication_software_link_platform_auth_get_request(
            CommercialApiContract(DEFAULT_BASE_URL),
            auth_session_id=str(kwargs["auth_session_id"]),
        )
    elif action == "reserve":
        request = build_commercial_config_session_reserve_preview(
            entitlement_id=str(kwargs["entitlement_id"]),
            buyer_user_id=contexts.target_buyer.user_id,
            operator_user_id=contexts.operator.user_id,
            agent_id=str(kwargs["agent_id"]),
            mode_key=str(kwargs["mode_key"]),
            diagnostic_code=str(kwargs["diagnostic_code"]),
        )
    elif action == "complete":
        config_session_id = str(kwargs["config_session_id"])
        diagnostic_code = str(kwargs["diagnostic_code"])
        request = build_config_session_complete_request(
            CommercialApiContract(DEFAULT_BASE_URL),
            config_session_id=config_session_id,
            diagnostic_code=diagnostic_code,
            real_task_verified=True,
            idempotency_key=stable_config_session_idempotency_key("complete", config_session_id, diagnostic_code),
        )
    elif action == "fail":
        config_session_id = str(kwargs["config_session_id"])
        diagnostic_code = str(kwargs["diagnostic_code"])
        request = build_config_session_fail_request(
            CommercialApiContract(DEFAULT_BASE_URL),
            config_session_id=config_session_id,
            diagnostic_code=diagnostic_code,
            failure_reason=str(kwargs["failure_reason"]),
            idempotency_key=stable_config_session_idempotency_key("fail", config_session_id, diagnostic_code),
        )
    else:
        raise ValueError(f"Unknown commercial api action: {action}")
    return with_operator_auth(request, token)


def build_payment_qr_data_url(payment_url: str, box_size: int = 8, border: int = 2) -> str:
    """把支付链接离线编码成二维码 PNG 的 base64 data URL。

    服务端（Codex 约定）对工具订单返回支付宝手机网站支付(WAP)链接 payment_url，
    不返回 qr_code；由桌面客户端自己把 payment_url 生成二维码，买家用手机支付宝扫码付款。
    离线本地生成，不依赖外网，不把链接写进日志。
    """
    url = str(payment_url or "").strip()
    if not url:
        raise ValueError("缺少支付链接，无法生成支付二维码。")
    import qrcode

    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def build_customer_payment_instruction(data: dict) -> str:
    lines = ["订单已由服务端创建。请在软件内按下面信息完成支付，然后点击“查询支付”。"]
    payment_url = str(data.get("payment_url") or data.get("pay_url") or data.get("checkout_url") or "").strip()
    payment_qr_url = str(data.get("payment_qr_url") or data.get("pay_qr_url") or data.get("qr_url") or "").strip()
    expires_at = str(data.get("expires_at") or data.get("expire_at") or "").strip()
    if payment_url:
        lines.append(f"付款链接：{payment_url}")
    if payment_qr_url:
        lines.append(f"支付二维码：{payment_qr_url}")
    if expires_at:
        lines.append(f"有效期：{expires_at}")
    if not payment_url and not payment_qr_url:
        lines.append("服务端没有返回付款链接或二维码。请联系后台确认订单支付入口。")
    return "\n".join(lines)


def execute_config_session_reserve(
    entitlement_id: str,
    buyer_user_id: str,
    operator_user_id: str,
    agent_id: str,
    mode_key: str,
    diagnostic_code: str,
    opener,
    contexts=None,
    deployer_auth: dict | None = None,
) -> tuple[str, str]:
    if contexts is None:
        request = build_commercial_config_session_reserve_preview(
            entitlement_id=entitlement_id,
            buyer_user_id=buyer_user_id,
            operator_user_id=operator_user_id,
            agent_id=agent_id,
            mode_key=mode_key,
            diagnostic_code=diagnostic_code,
        )
    else:
        request = commercial_api_request_with_auth(
            "reserve",
            contexts,
            deployer_auth=deployer_auth,
            entitlement_id=entitlement_id,
            agent_id=agent_id,
            mode_key=mode_key,
            diagnostic_code=diagnostic_code,
        )
    data, summary = execute_commercial_api_request(request, opener, timeout=20)
    reserve = parse_config_session_reserve_data(data)
    return reserve["config_session_id"], summary


def execute_config_session_complete(
    config_session_id: str,
    diagnostic_code: str,
    opener,
    contexts=None,
    deployer_auth: dict | None = None,
) -> tuple[dict, str]:
    if not config_session_id:
        raise ValueError("配置会话成功提交缺少服务端会话 ID。")
    if contexts is None:
        request = build_config_session_complete_request(
            CommercialApiContract(DEFAULT_BASE_URL),
            config_session_id=config_session_id,
            diagnostic_code=diagnostic_code,
            real_task_verified=True,
            idempotency_key=stable_config_session_idempotency_key("complete", config_session_id, diagnostic_code),
        )
    else:
        request = commercial_api_request_with_auth(
            "complete",
            contexts,
            deployer_auth=deployer_auth,
            config_session_id=config_session_id,
            diagnostic_code=diagnostic_code,
        )
    return execute_commercial_api_request(request, opener, timeout=20)


def execute_config_session_fail(
    config_session_id: str,
    diagnostic_code: str,
    failure_reason: str,
    opener,
    contexts=None,
    deployer_auth: dict | None = None,
) -> tuple[dict, str]:
    if not config_session_id:
        raise ValueError("配置会话失败提交缺少服务端会话 ID。")
    if contexts is None:
        request = build_config_session_fail_request(
            CommercialApiContract(DEFAULT_BASE_URL),
            config_session_id=config_session_id,
            diagnostic_code=diagnostic_code,
            failure_reason=failure_reason,
            idempotency_key=stable_config_session_idempotency_key("fail", config_session_id, diagnostic_code),
        )
    else:
        request = commercial_api_request_with_auth(
            "fail",
            contexts,
            deployer_auth=deployer_auth,
            config_session_id=config_session_id,
            diagnostic_code=diagnostic_code,
            failure_reason=failure_reason,
        )
    return execute_commercial_api_request(request, opener, timeout=20)


def fail_unfinished_config_sessions(
    config_session_ids: dict[tuple[str, str], str],
    completed_session_keys: set[tuple[str, str]],
    diagnostic_code: str,
    reason: str,
    opener,
    contexts=None,
    deployer_auth: dict | None = None,
) -> list[str]:
    summaries: list[str] = []
    for session_key, session_id in list(config_session_ids.items()):
        if session_key in completed_session_keys or not session_id:
            continue
        try:
            _data, summary = execute_config_session_fail(
                session_id,
                diagnostic_code,
                reason,
                opener=opener,
                contexts=contexts,
                deployer_auth=deployer_auth,
            )
            summaries.append(f"{session_key[0]}/{session_key[1]}：{summary}")
        except Exception as exc:
            summaries.append(f"{session_key[0]}/{session_key[1]}：失败兜底提交异常：{sanitize_worker_message(str(exc))}")
    return summaries


def execute_api_key_owner_verify(api_key: str, contexts, opener, deployer_auth: dict | None = None) -> str:
    if not api_key.strip():
        raise ValueError("API Key 归属校验缺少 Key。")
    request = commercial_api_request_with_auth(
        "api_key_owner_verify",
        contexts,
        deployer_auth=deployer_auth,
        api_key=api_key.strip(),
    )
    data, summary = execute_commercial_api_request(request, opener, timeout=20)
    owner_user_id = str(data.get("owner_user_id") or "").strip()
    decision = api_key_owner_gate(contexts, verified_owner_user_id=owner_user_id)
    if not decision.allowed:
        raise ValueError(decision.message)
    return f"{decision.message}；{summary}"


def codex_config_session_reserve_from_manifest(
    manifest: dict,
    mode: CodexConfigMode,
    contexts,
    diagnostic_code: str,
    opener,
    public_key_pem: str = COMMERCIAL_MANIFEST_PUBLIC_KEY_PEM,
    deployer_auth: dict | None = None,
) -> tuple[str, str]:
    if mode == CodexConfigMode.OFFICIAL_CHATGPT:
        return "", "官方直登模式为本地免费切换，未创建商业配置会话。"
    ensure_commercial_manifest_trusted(manifest, public_key_pem)
    commercial_manifest_present = manifest_has_commercial_controls(manifest)
    capabilities = manifest_commercial_capabilities(manifest)
    entitlements = manifest_commercial_entitlements(manifest)
    mode_key = commercial_mode_key_for_config_mode(mode)
    gate = commercial_config_gate(
        agent_id="codex",
        mode_key=mode_key,
        capabilities=capabilities,
        entitlements=entitlements,
        commercial_manifest_present=commercial_manifest_present,
    )
    if not gate.allowed:
        raise RuntimeError(gate.message)
    if not gate.entitlement_id:
        return "", "兼容旧版清单，未创建配置会话。"
    return execute_config_session_reserve(
        entitlement_id=gate.entitlement_id,
        buyer_user_id=contexts.target_buyer.user_id,
        operator_user_id=contexts.operator.user_id,
        agent_id="codex",
        mode_key=mode_key,
        diagnostic_code=diagnostic_code,
        opener=opener,
        contexts=contexts,
        deployer_auth=deployer_auth,
    )


def parse_temporary_openai_access_config(manifest: dict) -> TemporaryOpenAIAccessConfig | None:
    raw = manifest.get("temporary_openai_access")
    if not isinstance(raw, dict) or not raw.get("enabled"):
        return None
    proxy = str(raw.get("proxy") or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9.-]+:\d{2,5}", proxy):
        return None
    host, port_text = proxy.rsplit(":", 1)
    try:
        port = int(port_text)
    except ValueError:
        return None
    if not host or port < 1 or port > 65535:
        return None
    duration = raw.get("duration_seconds", TEMP_OPENAI_ACCESS_SECONDS)
    try:
        duration_seconds = int(duration)
    except (TypeError, ValueError):
        duration_seconds = TEMP_OPENAI_ACCESS_SECONDS
    duration_seconds = max(60, min(duration_seconds, TEMP_OPENAI_ACCESS_MAX_SECONDS))
    return TemporaryOpenAIAccessConfig(proxy=proxy, duration_seconds=duration_seconds)


def build_openai_access_pac(proxy: str, fallback: str = "DIRECT") -> str:
    return f"""function FindProxyForURL(url, host) {{
  host = host.toLowerCase();
  if (
    shExpMatch(host, "openai.com") ||
    shExpMatch(host, "*.openai.com") ||
    shExpMatch(host, "chatgpt.com") ||
    shExpMatch(host, "*.chatgpt.com") ||
    shExpMatch(host, "auth0.openai.com") ||
    shExpMatch(host, "cdn.openai.com") ||
    shExpMatch(host, "*.oaistatic.com") ||
    shExpMatch(host, "*.oaiusercontent.com")
  ) {{
    return "PROXY {proxy}; DIRECT";
  }}
  return "{fallback}";
}}
"""


def build_windows_temp_openai_access_script() -> str:
    return r'''
param(
    [Parameter(Mandatory=$true)][string]$PacPath,
    [int]$Seconds = 600,
    [switch]$RestoreOnly
)
$ErrorActionPreference = "Stop"
$internetSettings = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
$statePath = "$PacPath.state.json"
$restoreTaskName = "PanghuAI-OpenAI-Access-Restore-" + [IO.Path]::GetFileNameWithoutExtension($PacPath)
$scriptSelf = $MyInvocation.MyCommand.Path
$refreshType = @"
using System;
using System.Runtime.InteropServices;
public static class NativeInternetOptions {
    [DllImport("wininet.dll", SetLastError=true)]
    public static extern bool InternetSetOption(IntPtr hInternet, int dwOption, IntPtr lpBuffer, int dwBufferLength);
}
"@
try {
    Add-Type -TypeDefinition $refreshType -ErrorAction SilentlyContinue
} catch {}

function Update-InternetProxySettings {
    try {
        [NativeInternetOptions]::InternetSetOption([IntPtr]::Zero, 39, [IntPtr]::Zero, 0) | Out-Null
        [NativeInternetOptions]::InternetSetOption([IntPtr]::Zero, 37, [IntPtr]::Zero, 0) | Out-Null
    } catch {}
}

function Get-InternetProxyState {
    $item = Get-ItemProperty -Path $internetSettings
    return [ordered]@{
        ProxyEnable = if ($null -ne $item.ProxyEnable) { [int]$item.ProxyEnable } else { $null }
        ProxyServer = if ($null -ne $item.ProxyServer) { [string]$item.ProxyServer } else { $null }
        ProxyOverride = if ($null -ne $item.ProxyOverride) { [string]$item.ProxyOverride } else { $null }
        AutoConfigURL = if ($null -ne $item.AutoConfigURL) { [string]$item.AutoConfigURL } else { $null }
    }
}

function Set-InternetProxyState($state) {
    if ($null -ne $state.ProxyEnable) {
        Set-ItemProperty -Path $internetSettings -Name ProxyEnable -Value ([int]$state.ProxyEnable)
    } else {
        Remove-ItemProperty -Path $internetSettings -Name ProxyEnable -ErrorAction SilentlyContinue
    }
    foreach ($name in @("ProxyServer", "ProxyOverride", "AutoConfigURL")) {
        if ($null -ne $state.$name -and [string]$state.$name -ne "") {
            Set-ItemProperty -Path $internetSettings -Name $name -Value ([string]$state.$name)
        } else {
            Remove-ItemProperty -Path $internetSettings -Name $name -ErrorAction SilentlyContinue
        }
    }
}

function Restore-InternetProxyState {
    if (Test-Path -LiteralPath $statePath) {
        $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
        Set-InternetProxyState $state
        Remove-Item -LiteralPath $statePath -Force -ErrorAction SilentlyContinue
    }
    Update-InternetProxySettings
    Unregister-ScheduledTask -TaskName $restoreTaskName -Confirm:$false -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $PacPath -Force -ErrorAction SilentlyContinue
}

function Register-FallbackRestoreTask {
    if (-not $scriptSelf) {
        return
    }
    $runAt = (Get-Date).AddSeconds([Math]::Max(60, $Seconds + 15))
    $argument = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptSelf`" -PacPath `"$PacPath`" -RestoreOnly"
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argument
    $trigger = New-ScheduledTaskTrigger -Once -At $runAt
    Register-ScheduledTask -TaskName $restoreTaskName -Action $action -Trigger $trigger -Description "PanghuAI temporary OpenAI access restore" -Force | Out-Null
}

if ($RestoreOnly) {
    Restore-InternetProxyState
    exit 0
}

try {
    Get-InternetProxyState | ConvertTo-Json -Compress | Set-Content -LiteralPath $statePath -Encoding UTF8
    Register-FallbackRestoreTask
    $pacUrl = (New-Object System.Uri($PacPath)).AbsoluteUri
    Set-ItemProperty -Path $internetSettings -Name AutoConfigURL -Value $pacUrl
    Set-ItemProperty -Path $internetSettings -Name ProxyEnable -Value 0
    Update-InternetProxySettings
    Start-Sleep -Seconds $Seconds
} finally {
    Restore-InternetProxyState
}
'''


def build_macos_temp_openai_access_script() -> str:
    return r'''#!/bin/zsh
set -euo pipefail

PAC_PATH=""
SECONDS_VALUE="600"
RESTORE_ONLY="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --pac)
      PAC_PATH="$2"
      shift 2
      ;;
    --seconds)
      SECONDS_VALUE="$2"
      shift 2
      ;;
    --restore-only)
      RESTORE_ONLY="1"
      shift
      ;;
    *)
      shift
      ;;
  esac
done

if [[ -z "$PAC_PATH" ]]; then
  exit 2
fi

STATE_PATH="${PAC_PATH}.state"
SCRIPT_SELF="$0"
LAUNCH_DAEMON_DIR="/Library/LaunchDaemons"
LAUNCH_DAEMON_LABEL="cc.panghuai.openai-access-restore-$(basename "$PAC_PATH" .pac)"
LAUNCH_DAEMON_PLIST="$LAUNCH_DAEMON_DIR/${LAUNCH_DAEMON_LABEL}.plist"
PAC_URL="file://${PAC_PATH}"

networksetup_path="/usr/sbin/networksetup"
scutil_path="/usr/sbin/scutil"
launchctl_path="/bin/launchctl"

list_services() {
  "$networksetup_path" -listallnetworkservices 2>/dev/null | sed '1d;s/^\*//'
}

refresh_proxy_settings() {
  "$scutil_path" --proxy >/dev/null 2>&1 || true
}

save_state() {
  : > "$STATE_PATH"
  while IFS= read -r service; do
    [[ -z "$service" ]] && continue
    auto_enabled="$("$networksetup_path" -getautoproxyurl "$service" 2>/dev/null | awk -F': ' '/Enabled:/ {print $2; exit}')"
    auto_url="$("$networksetup_path" -getautoproxyurl "$service" 2>/dev/null | awk -F': ' '/URL:/ {print $2; exit}')"
    web_enabled="$("$networksetup_path" -getwebproxy "$service" 2>/dev/null | awk -F': ' '/Enabled:/ {print $2; exit}')"
    secure_enabled="$("$networksetup_path" -getsecurewebproxy "$service" 2>/dev/null | awk -F': ' '/Enabled:/ {print $2; exit}')"
    printf '%s\t%s\t%s\t%s\t%s\n' "$service" "${auto_enabled:-No}" "${auto_url:-}" "${web_enabled:-No}" "${secure_enabled:-No}" >> "$STATE_PATH"
  done < <(list_services)
}

restore_state() {
  if [[ -f "$STATE_PATH" ]]; then
    while IFS=$'\t' read -r service auto_enabled auto_url web_enabled secure_enabled; do
      [[ -z "$service" ]] && continue
      if [[ -n "${auto_url:-}" ]]; then
        "$networksetup_path" -setautoproxyurl "$service" "$auto_url" >/dev/null 2>&1 || true
      fi
      if [[ "${auto_enabled:-No}" == "Yes" ]]; then
        "$networksetup_path" -setautoproxystate "$service" on >/dev/null 2>&1 || true
      else
        "$networksetup_path" -setautoproxystate "$service" off >/dev/null 2>&1 || true
      fi
      if [[ "${web_enabled:-No}" == "Yes" ]]; then
        "$networksetup_path" -setwebproxystate "$service" on >/dev/null 2>&1 || true
      else
        "$networksetup_path" -setwebproxystate "$service" off >/dev/null 2>&1 || true
      fi
      if [[ "${secure_enabled:-No}" == "Yes" ]]; then
        "$networksetup_path" -setsecurewebproxystate "$service" on >/dev/null 2>&1 || true
      else
        "$networksetup_path" -setsecurewebproxystate "$service" off >/dev/null 2>&1 || true
      fi
    done < "$STATE_PATH"
    rm -f "$STATE_PATH"
  fi
  if [[ -f "$LAUNCH_DAEMON_PLIST" ]]; then
    "$launchctl_path" bootout system "$LAUNCH_DAEMON_PLIST" >/dev/null 2>&1 || true
    "$launchctl_path" unload "$LAUNCH_DAEMON_PLIST" >/dev/null 2>&1 || true
    rm -f "$LAUNCH_DAEMON_PLIST"
  fi
  rm -f "$PAC_PATH"
  refresh_proxy_settings
}

register_fallback_restore() {
  mkdir -p "$LAUNCH_DAEMON_DIR"
  cat > "$LAUNCH_DAEMON_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LAUNCH_DAEMON_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>${SCRIPT_SELF}</string>
    <string>--pac</string>
    <string>${PAC_PATH}</string>
    <string>--restore-only</string>
  </array>
  <key>StartInterval</key>
  <integer>$((SECONDS_VALUE + 15))</integer>
  <key>RunAtLoad</key>
  <false/>
</dict>
</plist>
PLIST
  chown root:wheel "$LAUNCH_DAEMON_PLIST" >/dev/null 2>&1 || true
  chmod 644 "$LAUNCH_DAEMON_PLIST" >/dev/null 2>&1 || true
  "$launchctl_path" bootstrap system "$LAUNCH_DAEMON_PLIST" >/dev/null 2>&1 || "$launchctl_path" load "$LAUNCH_DAEMON_PLIST" >/dev/null 2>&1 || true
}

enable_pac() {
  while IFS= read -r service; do
    [[ -z "$service" ]] && continue
    "$networksetup_path" -setautoproxyurl "$service" "$PAC_URL" >/dev/null 2>&1 || true
    "$networksetup_path" -setautoproxystate "$service" on >/dev/null 2>&1 || true
    "$networksetup_path" -setwebproxystate "$service" off >/dev/null 2>&1 || true
    "$networksetup_path" -setsecurewebproxystate "$service" off >/dev/null 2>&1 || true
  done < <(list_services)
  refresh_proxy_settings
}

if [[ "$RESTORE_ONLY" == "1" ]]; then
  restore_state
  exit 0
fi

trap restore_state EXIT INT TERM
save_state
register_fallback_restore
enable_pac
/bin/sleep "$SECONDS_VALUE"
'''


def start_temporary_openai_access(config: TemporaryOpenAIAccessConfig | None, log) -> bool:
    if not config:
        return False
    system = platform.system()
    if system not in {"Windows", "Darwin"}:
        log("临时 OpenAI 访问窗口当前只支持 Windows 和 Mac，其他系统不会改动系统代理。")
        return False
    runtime_dir = app_data_dir() / "temporary-openai-access"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    active_states = list(runtime_dir.glob("*.state.json")) + list(runtime_dir.glob("*.state"))
    if active_states:
        log("检测到已有 OpenAI 官网临时访问窗口，本次不重复改动系统代理。")
        return True
    suffix = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
    pac_path = runtime_dir / f"openai-access-{suffix}.pac"
    write_text(pac_path, build_openai_access_pac(config.proxy))
    if system == "Windows":
        script_path = runtime_dir / "restore-openai-access.ps1"
        write_text(script_path, build_windows_temp_openai_access_script())
        command = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
            "-PacPath",
            str(pac_path),
            "-Seconds",
            str(config.duration_seconds),
        ]
    else:
        script_path = runtime_dir / "restore-openai-access.command"
        write_text(script_path, build_macos_temp_openai_access_script())
        try:
            script_path.chmod(0o755)
        except Exception:
            pass
        shell_command = " ".join(
            [
                shlex.quote("/bin/zsh"),
                shlex.quote(str(script_path)),
                "--pac",
                shlex.quote(str(pac_path)),
                "--seconds",
                shlex.quote(str(config.duration_seconds)),
            ]
        )
        command = [
            "osascript",
            "-e",
            "do shell script " + json.dumps(shell_command) + " with administrator privileges",
        ]
    try:
        kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        subprocess.Popen(command, **kwargs)
    except Exception as exc:
        log(f"临时 OpenAI 访问窗口启动失败：{exc}")
        return False
    minutes = max(1, config.duration_seconds // 60)
    log(f"已开启 OpenAI 官网临时访问窗口：约 {minutes} 分钟后自动关闭并恢复系统代理。")
    return True


def open_path(path: Path) -> None:
    if platform.system() == "Windows":
        os.startfile(str(path))
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def normalize_referral_invite_code(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    if parsed.query:
        query = parse_qs(parsed.query, keep_blank_values=False)
        for key in INVITE_QUERY_KEYS:
            values = query.get(key)
            if values and str(values[0]).strip():
                return str(values[0]).strip()
    if parsed.scheme and parsed.netloc:
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2 and parts[-2].lower() in {"invite", "referral"}:
            return parts[-1].strip()
        return ""
    if "=" in raw:
        key, _, candidate = raw.partition("=")
        if key.strip().lower() in INVITE_QUERY_KEYS:
            return candidate.strip()
    return raw


def build_register_url(invite_code_or_url: str = "") -> str:
    invite_code = normalize_referral_invite_code(invite_code_or_url)
    if not invite_code:
        return REGISTER_URL
    return f"{REGISTER_URL}?invite={quote(invite_code, safe='')}"


def open_url(
    url: str,
    cookie_jar: http.cookiejar.CookieJar | None = None,
    log=None,
    storage_path: Path | str | None = None,
) -> CustomerPageOpenResult:
    res = open_customer_page(url, cookie_jar=cookie_jar, log=log, storage_path=storage_path)
    import sys
    if res.method == "external_browser" and res.title != "外部页面" and not ("pytest" in sys.modules or "unittest" in sys.modules):
        # webview 模式无 Tk mainloop，messagebox 不可用；走调用方提供的 log 回调提示。
        if log:
            try:
                log("该链接不属于胖虎AI客户内置网站白名单，正在使用系统默认浏览器打开。")
            except Exception:
                pass
    return res


def build_webview_cookie_bridge_script(cookie_jar: http.cookiejar.CookieJar | None) -> str:
    if cookie_jar is None:
        return ""
    statements: list[str] = []
    for cookie in cookie_jar:
        domain = (cookie.domain or "").lstrip(".").lower()
        if domain and not DEFAULT_BASE_URL.lower().endswith(domain):
            continue
        if not cookie.name or cookie.value is None:
            continue
        rest = getattr(cookie, "_rest", {}) or {}
        if any(str(key).lower() == "httponly" for key in rest):
            continue
        parts = [f"{cookie.name}={cookie.value}", "path=/", "SameSite=Lax"]
        if cookie.secure:
            parts.append("Secure")
        statements.append(f"document.cookie = {json.dumps('; '.join(parts))};")
    return "\n".join(statements)


def open_customer_page(
    url: str,
    cookie_jar: http.cookiejar.CookieJar | None = None,
    log=None,
    storage_path: Path | str | None = None,
) -> CustomerPageOpenResult:
    title = embedded_customer_page_title(url)
    page_url = str(url or "").strip()
    if not page_url:
        return CustomerPageOpenResult("", title, "none", False, "页面地址为空，未打开。")
    bridge_script = build_webview_cookie_bridge_script(cookie_jar)
    if title:
        if cookie_jar is None and log is None:
            embedded_ok = try_open_embedded_webview(page_url, title=title, storage_path=storage_path)
        else:
            embedded_ok = try_open_embedded_webview(
                page_url,
                title=title,
                cookie_jar=cookie_jar,
                log=log,
                storage_path=storage_path,
            )
    else:
        embedded_ok = False
    if title and embedded_ok:
        bridge_note = "并已尝试桥接本次胖虎AI登录态" if bridge_script else "；当前会话没有可通过 JS 桥接的登录 cookie"
        return CustomerPageOpenResult(
            page_url,
            title,
            "embedded_webview",
            True,
            f"已在软件内 WebView 窗口打开：{title}{bridge_note}。",
        )
    if title:
        if webview is None:
            reason = "当前运行环境未加载 pywebview，未打开系统浏览器；胖虎AI网站内置浏览器闭环未完成。"
        else:
            reason = "内置 WebView 未能启动，未打开系统浏览器；胖虎AI网站内置浏览器闭环未完成。"
        if log:
            log(reason)
        return CustomerPageOpenResult(
            page_url,
            title,
            "embedded_webview_blocked",
            False,
            reason,
        )
    browser_ok = bool(webbrowser.open(page_url))
    reason = "该链接不属于客户内置网站白名单，已使用系统浏览器打开。"
    return CustomerPageOpenResult(
        page_url,
        "外部页面",
        "external_browser",
        browser_ok,
        reason,
    )


def embedded_webview_available() -> bool:
    return webview is not None


def embedded_customer_page_title(url: str) -> str:
    safe = str(url or "").strip().lower()
    if not safe:
        return ""
    if safe.rstrip("/") in {DEFAULT_BASE_URL, CONSOLE_URL.lower()}:
        return "胖虎AI 控制台"
    if safe.rstrip("/") == SIM_CONTROL_URL.lower():
        return "手机号接码控制中心"
    if "/agent" in safe:
        return "胖虎AI 代理中心"
    if "/services" in safe:
        return "胖虎AI 增值业务"
    if "/console/token" in safe or "/token" in safe:
        return "胖虎AI API Key 创建页面"
    if "/buy" in safe or "/pay/" in safe or "payment" in safe or "recharge" in safe or "topup" in safe:
        return "胖虎AI 购买与充值"
    if "/affiliate" in safe or "/register" in safe or "invite" in safe:
        return "胖虎AI 推广返佣"
    return ""


def try_open_embedded_webview(
    url: str,
    title: str = "",
    cookie_jar: http.cookiejar.CookieJar | None = None,
    log=None,
    storage_path: Path | str | None = None,
) -> bool:
    if webview is None:
        return False
    page_url = str(url or "").strip()
    if not page_url:
        return False
    window_title = title or "胖虎AI"
    bridge_script = build_webview_cookie_bridge_script(cookie_jar)
    persistent_storage_path = Path(storage_path) if storage_path else web_profile_root() / "buyer-site"
    persistent_storage_path.mkdir(parents=True, exist_ok=True)

    def launch() -> None:
        start_url = PANGHU_HOME_URL if bridge_script else page_url
        window = webview.create_window(window_title, start_url, width=1180, height=860, resizable=True)
        if bridge_script:
            state = {"bridged": False}

            def on_loaded() -> None:
                if state["bridged"]:
                    return
                state["bridged"] = True
                window.evaluate_js(bridge_script)
                window.load_url(page_url)
                if log:
                    log(f"已向内置 WebView 桥接本次胖虎AI登录态：{window_title}")

            window.events.loaded += on_loaded
        webview.start(private_mode=False, storage_path=str(persistent_storage_path))

    threading.Thread(target=launch, daemon=True).start()
    return True


def normalize_version(value: str) -> tuple[int, ...]:
    cleaned = value.strip().lower().lstrip("v")
    parts: list[int] = []
    for item in re.split(r"[^0-9]+", cleaned):
        if item:
            parts.append(int(item))
    return tuple(parts or [0])


def downloads_dir() -> Path:
    path = Path.home() / "Downloads"
    if path.exists():
        return path
    return Path.home() / "下载"


def current_mac_package_suffix() -> str:
    machine = platform.machine().lower()
    if machine in {"arm64", "aarch64"}:
        return "AppleSilicon"
    if machine in {"x86_64", "amd64"}:
        return "Intel"
    return machine or "Unknown"


def release_asset_name_for_current_system() -> str:
    if current_system_id() != "mac":
        return WINDOWS_RELEASE_ASSET_NAME
    return MAC_APPLE_SILICON_RELEASE_ASSET_NAME if current_mac_package_suffix() == "AppleSilicon" else MAC_INTEL_RELEASE_ASSET_NAME


def release_asset_aliases_for_current_system() -> tuple[str, ...]:
    if current_system_id() != "mac":
        return WINDOWS_RELEASE_ASSET_ALIASES
    if current_mac_package_suffix() == "AppleSilicon":
        return MAC_APPLE_SILICON_RELEASE_ASSET_ALIASES
    return MAC_INTEL_RELEASE_ASSET_ALIASES


def public_manifest_asset_url(payload: dict) -> str:
    if current_system_id() == "mac":
        if current_mac_package_suffix() == "AppleSilicon":
            return str(
                payload.get("mac_apple_silicon_zip_url")
                or payload.get("mac_arm64_zip_url")
                or payload.get("mac_zip_url")
                or payload.get("mac_download_url")
                or ""
            )
        return str(payload.get("mac_intel_zip_url") or payload.get("mac_x64_zip_url") or payload.get("mac_x86_64_zip_url") or "")
    return str(payload.get("windows_zip_url") or payload.get("download_url") or "")


def platform_label_for_update() -> str:
    if current_system_id() == "mac":
        return f"Mac {current_mac_package_suffix()}"
    return "Windows"


@dataclass
class UpdateInfo:
    latest_tag: str
    asset_url: str
    release_url: str
    asset_name: str
    platform_label: str


def find_available_update() -> tuple[UpdateInfo | None, str, str | None]:
    try:
        req = Request(PUBLIC_UPDATE_MANIFEST_URL, headers={"Accept": "application/json", "User-Agent": HTTP_USER_AGENT})
        with trusted_urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception:
        payload = {}

    if payload:
        latest_tag = str(payload.get("version") or payload.get("tag_name") or "").strip()
        release_url = str(payload.get("html_url") or payload.get("release_url") or DEFAULT_BASE_URL)
        asset_url = public_manifest_asset_url(payload)
        if not latest_tag:
            return None, "检查更新失败：公开更新清单缺少版本号。", release_url
        if normalize_version(latest_tag) <= normalize_version(APP_VERSION):
            return None, f"当前已是最新版本：{APP_VERSION}", release_url
        if not asset_url:
            return None, f"发现新版本 {latest_tag}，但公开更新清单缺少 {platform_label_for_update()} 下载地址。", release_url
        info = UpdateInfo(latest_tag, asset_url, release_url, release_asset_name_for_current_system(), platform_label_for_update())
        return info, f"发现新版本 {latest_tag}。", release_url

    req = Request(GITHUB_RELEASE_API, headers={"Accept": "application/vnd.github+json", "User-Agent": HTTP_USER_AGENT})
    try:
        with trusted_urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return None, f"检查更新失败：{exc}", None

    latest_tag = str(payload.get("tag_name") or "").strip()
    release_url = str(payload.get("html_url") or "https://github.com/dashuaiisme/panghu-ai-client/releases")
    if not latest_tag:
        return None, "检查更新失败：GitHub Release 没有版本号。", release_url
    if normalize_version(latest_tag) <= normalize_version(APP_VERSION):
        return None, f"当前已是最新版本：{APP_VERSION}", release_url

    asset_url = ""
    for asset in payload.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "")
        if name in release_asset_aliases_for_current_system():
            asset_url = str(asset.get("browser_download_url") or "")
            break
    if not asset_url:
        return None, f"发现新版本 {latest_tag}，但未找到 {platform_label_for_update()} 更新包，已打开发布页。", release_url

    info = UpdateInfo(latest_tag, asset_url, release_url, release_asset_name_for_current_system(), platform_label_for_update())
    return info, f"发现新版本 {latest_tag}。", release_url


def download_update_package(update: UpdateInfo, log) -> Path:
    target_dir = downloads_dir() / "胖虎AI工具更新"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{update.latest_tag}-{update.asset_name}"
    log(f"开始下载 {update.platform_label} 更新包：{update.latest_tag}")
    download_with_trusted_certs(update.asset_url, target)
    return target


def check_and_download_update(log) -> tuple[bool, str, Path | None, str | None]:
    update, msg, release_url = find_available_update()
    if update is None:
        return False, msg, None, release_url
    try:
        target = download_update_package(update, log)
    except Exception as exc:
        return False, f"下载更新失败：{exc}", None, update.release_url
    return True, f"新版本 {update.latest_tag} 已下载。", target, update.release_url


def update_script_path() -> Path:
    root = Path(tempfile.gettempdir()) / "PanghuAI-Client-Updater"
    root.mkdir(parents=True, exist_ok=True)
    return root / ("apply-update.ps1" if platform.system() == "Windows" else "apply-update.sh")


def powershell_single_quoted(value: Path | str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def mac_app_bundle_path() -> Path | None:
    executable = Path(sys.executable).resolve()
    for parent in (executable, *executable.parents):
        if parent.suffix == ".app":
            return parent
    return None


def app_update_root() -> Path:
    if platform.system() == "Darwin":
        bundle = mac_app_bundle_path()
        if bundle:
            return bundle
    return app_root()


def app_launch_target() -> Path:
    if platform.system() == "Darwin":
        bundle = mac_app_bundle_path()
        if bundle:
            return bundle
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    return Path(sys.argv[0]).resolve()


def build_windows_update_script(zip_path: Path, app_dir: Path, launch_target: Path, pid: int) -> str:
    return f"""$ErrorActionPreference = "Stop"
$zipPath = {powershell_single_quoted(zip_path)}
$appDir = {powershell_single_quoted(app_dir)}
$launchTarget = {powershell_single_quoted(launch_target)}
$pidToWait = {pid}
$staging = Join-Path $env:TEMP ("PanghuAI-Client-Update-" + [guid]::NewGuid().ToString("N"))
try {{
    Wait-Process -Id $pidToWait -Timeout 30 -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 800
    New-Item -ItemType Directory -Force -Path $staging | Out-Null
    Expand-Archive -LiteralPath $zipPath -DestinationPath $staging -Force
    $payload = Get-ChildItem -LiteralPath $staging -Directory | Select-Object -First 1
    if ($null -eq $payload) {{ throw "更新包里没有找到程序目录。" }}
    Copy-Item -Path (Join-Path $payload.FullName "*") -Destination $appDir -Recurse -Force
    Start-Process -FilePath $launchTarget
}} finally {{
    Remove-Item -LiteralPath $staging -Recurse -Force -ErrorAction SilentlyContinue
}}
"""


def build_macos_update_script(zip_path: Path, app_dir: Path, launch_target: Path, pid: int) -> str:
    return f"""#!/bin/zsh
set -euo pipefail
ZIP_PATH={shlex.quote(str(zip_path))}
APP_DIR={shlex.quote(str(app_dir))}
LAUNCH_TARGET={shlex.quote(str(launch_target))}
PID_TO_WAIT={pid}
STAGING="$(mktemp -d "${{TMPDIR:-/tmp}}/panghuai-agent-update.XXXXXX")"
cleanup() {{
  rm -rf "$STAGING"
}}
trap cleanup EXIT
while kill -0 "$PID_TO_WAIT" >/dev/null 2>&1; do
  sleep 0.5
done
ditto -x -k "$ZIP_PATH" "$STAGING"
PAYLOAD="$(find "$STAGING" -maxdepth 1 -name '*.app' -type d | head -n 1)"
if [ -z "$PAYLOAD" ]; then
  echo "更新包里没有找到 app。"
  exit 1
fi
rm -rf "$APP_DIR"
cp -R "$PAYLOAD" "$APP_DIR"
open "$LAUNCH_TARGET"
"""


def start_online_update(zip_path: Path, log) -> None:
    app_dir = app_update_root()
    launch_target = app_launch_target()
    pid = os.getpid()
    script_path = update_script_path()
    if platform.system() == "Windows":
        script = build_windows_update_script(zip_path, app_dir, launch_target, pid)
        write_text(script_path, script)
        subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script_path)])
    elif platform.system() == "Darwin":
        script = build_macos_update_script(zip_path, app_dir, launch_target, pid)
        write_text(script_path, script)
        script_path.chmod(0o755)
        subprocess.Popen(["/bin/zsh", str(script_path)])
    else:
        raise RuntimeError("当前系统暂不支持自动覆盖更新。")
    log("在线更新程序已启动，本工具即将退出并由更新程序覆盖安装。")


def open_codex_download_page() -> None:
    if platform.system() == "Windows":
        open_url(CODEX_WINDOWS_STORE_URL)
    else:
        open_url(CODEX_DOWNLOAD_URL)


def find_official_codex_package() -> Path | None:
    roots = [app_root(), app_root() / "offline", app_root() / "codex-official"]
    candidates: list[tuple[int, float, Path]] = []
    for root in roots:
        if not root.exists() or not root.is_dir():
            continue
        for child in root.iterdir():
            if child.is_file() and child.suffix.lower() in OFFICIAL_PACKAGE_SUFFIXES:
                name = child.name.lower()
                score = 0
                if "codex" in name:
                    score += 2
                if "openai" in name:
                    score += 1
                candidates.append((score, child.stat().st_mtime, child))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][2]


def validate_official_package_signature(package_path: Path) -> tuple[bool, str]:
    if platform.system() != "Windows":
        return False, "当前系统不支持 Windows Codex 安装包签名校验。"
    safe_path = str(package_path).replace("'", "''")
    command = (
        "$sig = Get-AuthenticodeSignature -LiteralPath "
        f"'{safe_path}'; "
        "[pscustomobject]@{"
        "Status=$sig.Status.ToString();"
        "Subject=if($sig.SignerCertificate){$sig.SignerCertificate.Subject}else{''};"
        "Issuer=if($sig.SignerCertificate){$sig.SignerCertificate.Issuer}else{''}"
        "} | ConvertTo-Json -Compress"
    )
    ok, output = run_command(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        timeout=30,
    )
    if not ok:
        return False, f"签名校验失败：{output}"
    try:
        data = json.loads(output.strip())
    except json.JSONDecodeError:
        return False, "签名校验失败：无法解析 Windows 签名信息。"
    status = str(data.get("Status", ""))
    subject = str(data.get("Subject", ""))
    issuer = str(data.get("Issuer", ""))
    if status != "Valid":
        return False, f"签名无效：{status or '未知状态'}"
    signer_text = f"{subject} {issuer}".lower()
    name_text = package_path.name.lower()
    if "openai" not in signer_text and "microsoft" not in signer_text:
        return False, f"签名发布者不是 OpenAI/Microsoft：{subject or issuer or '未知发布者'}"
    if "microsoft" in signer_text and "openai" not in name_text and "codex" not in name_text:
        return False, "Microsoft 签名包文件名未包含 OpenAI/Codex，已拒绝安装。"
    return True, f"签名校验通过：{subject or issuer}"


def install_official_package(package_path: Path) -> tuple[bool, str]:
    signature_ok, signature_msg = validate_official_package_signature(package_path)
    if not signature_ok:
        return False, signature_msg
    suffix = package_path.suffix.lower()
    safe_path = str(package_path).replace("'", "''")
    if suffix == ".appinstaller":
        install_command = f"Add-AppxPackage -AppInstallerFile '{safe_path}'"
    else:
        install_command = f"Add-AppxPackage -Path '{safe_path}'"
    return run_command(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", install_command],
        timeout=600,
    )


def install_with_winget() -> tuple[bool, str]:
    if not shutil.which("winget"):
        return False, "未检测到 winget，无法自动调用 Microsoft Store 命令行安装。"
    return run_command(
        [
            "winget",
            "install",
            "Codex",
            "-s",
            "msstore",
            "--accept-source-agreements",
            "--accept-package-agreements",
        ],
        timeout=900,
    )


def wait_for_codex_ready(timeout_seconds: int = 90, require_windows_app: bool = False) -> tuple[bool, str]:
    deadline = time.time() + timeout_seconds
    last_version = ""
    last_package = ""
    while time.time() < deadline:
        cli_ok, version = codex_command_exists()
        package_ok, package = codex_app_package_exists()
        last_version = version or last_version
        last_package = package or last_package
        if require_windows_app and platform.system() == "Windows":
            if package_ok:
                return True, "已检测到 Codex Windows App 本体：" + (package or "已安装")
        elif cli_ok or package_ok:
            details = [item for item in (version, package) if item]
            return True, "已检测到 Codex：" + ("；".join(details) if details else "已安装")
        time.sleep(3)
    return False, f"等待 Codex 安装完成超时。{last_version or last_package}".strip()


def install_codex_app(log) -> bool:
    log("开始检测 Codex 客户端。")
    cli_ok, version = codex_command_exists()
    package_ok, package = codex_app_package_exists()
    if package_ok:
        if cli_ok:
            log(f"已检测到 Codex CLI：{version or '已安装'}")
        log(f"已检测到 Codex Windows App 本体：{package}")
        create_codex_shortcuts(log)
        log("最近安装：Codex 客户端。可从桌面快捷方式或开始菜单打开。")
        return True
    if cli_ok:
        log(f"已检测到 Codex CLI：{version or '已安装'}")
        if platform.system() != "Windows":
            return True
        log("未检测到 Codex Windows App 本体，将继续安装/修复 App。")

    if platform.system() != "Windows":
        log("当前系统没有可确认的自动客户端安装路径，已打开 Codex 官方入口。")
        open_codex_download_page()
        return False

    package_path = find_official_codex_package()
    if package_path:
        log(f"发现官方离线包：{package_path}")
        signature_ok, signature_msg = validate_official_package_signature(package_path)
        log(signature_msg)
        if signature_ok:
            ok, msg = install_official_package(package_path)
            log(msg)
            if ok:
                ready, ready_msg = wait_for_codex_ready(require_windows_app=True)
                log(ready_msg)
                if ready:
                    create_codex_shortcuts(log)
                    log("最近安装：Codex 客户端。可从桌面快捷方式或开始菜单打开。")
                return ready
        else:
            log("离线包未通过签名校验，将尝试 Microsoft Store 命令行安装。")
    else:
        log("未发现官方离线包，将尝试 Microsoft Store 命令行安装。")

    ok, msg = install_with_winget()
    log(msg)
    if ok:
        ready, ready_msg = wait_for_codex_ready(require_windows_app=True)
        log(ready_msg)
        if ready:
            create_codex_shortcuts(log)
            log("最近安装：Codex 客户端。可从桌面快捷方式或开始菜单打开。")
        return ready

    log("自动安装失败，已打开官方 Codex 下载页，请按页面提示安装。")
    open_codex_download_page()
    return False


def install_codex_cli(log) -> bool:
    exists, version = codex_command_exists()
    if exists:
        log(f"Codex CLI 已安装：{version or '已安装'}")
        return True
    if platform.system() == "Windows":
        command = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            "irm https://chatgpt.com/codex/install.ps1 | iex",
        ]
    else:
        command = ["/bin/bash", "-lc", "curl -fsSL https://chatgpt.com/codex/install.sh | sh"]
    ok, output = run_command(command, timeout=900)
    log(output)
    return ok


def install_claude_code_cli(log) -> bool:
    if platform.system() == "Windows":
        command = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            "irm https://claude.ai/install.ps1 | iex",
        ]
    else:
        command = ["/bin/bash", "-lc", "curl -fsSL https://claude.ai/install.sh | bash"]
    log("按 Claude Code 官方 Quickstart 原生安装入口安装 CLI。")
    ok, output = run_command(command, timeout=900)
    log(output)
    if ok:
        return True
    if shutil.which("npm"):
        log("Claude Code 原生安装未确认，改用官方 npm 包替代入口：npm install -g @anthropic-ai/claude-code")
        ok, output = run_command(["npm", "install", "-g", "@anthropic-ai/claude-code"], timeout=900)
        log(output)
        if ok:
            return True
    log("Claude Code 自动安装未确认，已打开官方 Quickstart。")
    open_url(CLAUDE_CODE_DOCS_URL)
    return False


def install_openclaw_cli(log) -> bool:
    if shutil.which("npm"):
        log("按 OpenClaw 官方 npm 包安装 CLI：npm install -g openclaw@latest")
        ok, output = run_command(["npm", "install", "-g", "openclaw@latest"], timeout=900)
        log(output)
        if ok:
            return True
        log("npm 安装 OpenClaw 未成功，改用官方安装脚本入口。")
    if platform.system() == "Windows":
        command = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            "iwr -useb https://openclaw.ai/install.ps1 | iex",
        ]
    else:
        command = ["/bin/bash", "-lc", "curl -fsSL https://openclaw.ai/install.sh | sh"]
    ok, output = run_command(command, timeout=900)
    log(output)
    return ok


def install_hermes_cli(log) -> bool:
    if platform.system() == "Windows":
        command = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            "iex (irm https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.ps1)",
        ]
    else:
        command = [
            "/bin/bash",
            "-lc",
            "curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash",
        ]
    ok, output = run_command(command, timeout=900)
    log(output)
    return ok


def install_gemini_agy_cli(log) -> bool:
    if platform.system() == "Windows":
        command = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            "iwr -useb https://antigravity.google/cli/install.ps1 | iex",
        ]
    else:
        command = ["/bin/bash", "-lc", "curl -fsSL https://antigravity.google/cli/install.sh | bash"]
    ok, output = run_command(command, timeout=900)
    log(output)
    if ok:
        log("Gemini / agy CLI 安装入口已执行；首次使用请按 Google 官方流程登录账号。")
    else:
        open_url(GEMINI_AGY_DOCS_URL)
        log("Gemini / agy CLI 自动安装未确认，已打开 Google Antigravity 官方入口。")
    return ok


def codex_thread_url(workdir: Path) -> str:
    return "codex://threads/new?path=" + quote(str(workdir), safe="")


def open_codex_app(workdir: Path) -> tuple[bool, str]:
    package_ok, _ = codex_app_package_exists()
    if package_ok:
        webbrowser.open(codex_thread_url(workdir))
        return True, "已尝试通过 Codex App 官方链接打开工作区。"
    exists, _ = codex_command_exists()
    if not exists:
        return False, "未检测到 Codex App 本体或 codex 命令，请手动打开 Codex App。"
    try:
        subprocess.Popen(["codex", "app"], cwd=str(workdir))
        return True, "已尝试打开 Codex App。"
    except Exception as exc:
        return False, f"自动打开 Codex App 失败：{exc}"


def install_codex_config(
    api_key: str,
    base_url: str,
    model: str,
    skip_test: bool,
    open_app: bool,
    log,
    temporary_openai_access: TemporaryOpenAIAccessConfig | None = None,
    mode: CodexConfigMode = CodexConfigMode.DIRECT_API,
) -> bool:
    requires_panghu_key = mode in (CodexConfigMode.DIRECT_API, CodexConfigMode.DUAL_STATE)
    if requires_panghu_key and not api_key.strip():
        raise ValueError("请先输入胖虎AI API Key。")
    if not model.strip():
        raise ValueError("模型不能为空。")

    api_key = api_key.strip()
    base_url = DEFAULT_BASE_URL
    model = model.strip()
    home = codex_home()
    workdir = workspace_root()
    config_path = home / "config.toml"
    auth_path = codex_auth_path()
    global_agents = home / "AGENTS.md"
    workspace_agents = workdir / "AGENTS.md"

    mode_labels = {
        CodexConfigMode.DIRECT_API: "普通直接 API 配置",
        CodexConfigMode.DUAL_STATE: "双态模式配置",
        CodexConfigMode.OFFICIAL_CHATGPT: "官方直登配置",
    }
    mode_label = mode_labels.get(mode, mode.value)
    log(f"开始应用 Codex {mode_label}。")
    home.mkdir(parents=True, exist_ok=True)
    workdir.mkdir(parents=True, exist_ok=True)

    existed_before = {
        config_path: config_path.exists(),
        auth_path: auth_path.exists(),
        global_agents: global_agents.exists(),
        workspace_agents: workspace_agents.exists(),
    }
    backups = {
        config_path: backup_file(config_path),
        auth_path: backup_file(auth_path),
        global_agents: backup_file(global_agents),
        workspace_agents: backup_file(workspace_agents),
    }
    for target, backup in backups.items():
        if backup:
            log(f"已备份旧文件：{backup}")
        else:
            log(f"将创建新文件：{target}")

    old_config = safe_read_text(config_path)
    old_auth = safe_read_text(auth_path)
    current_mode = detect_codex_config_mode(old_config, old_auth)
    save_codex_mode_snapshot(current_mode, config_path, auth_path, global_agents, workspace_agents, log)

    snapshot = load_codex_mode_snapshot(mode)
    base_config = snapshot["config"] if snapshot else old_config
    base_auth = snapshot["auth"] if snapshot else old_auth
    new_global_agents = snapshot["global_agents"] if snapshot else safe_read_text(global_agents)
    new_workspace_agents = snapshot["workspace_agents"] if snapshot else safe_read_text(workspace_agents)
    if snapshot:
        log(f"已读取 Codex 模式快照：{mode.value} <- {codex_mode_snapshot_dir(mode)}")

    if mode == CodexConfigMode.DUAL_STATE:
        auth_base = old_auth if has_chatgpt_auth_state(old_auth) else base_auth
        new_config = build_dual_state_config(api_key, base_url, model)
        new_auth = build_dual_state_auth_json(auth_base, api_key)
    elif mode == CodexConfigMode.OFFICIAL_CHATGPT:
        auth_base = old_auth if has_chatgpt_auth_state(old_auth) else base_auth
        new_config = build_official_chatgpt_config(base_config, model)
        new_auth = build_official_chatgpt_auth_json(auth_base)
    else:
        new_config = merge_config(base_config, api_key, base_url, model)
        new_auth = build_direct_api_auth_json(base_auth, api_key)

    write_text(config_path, new_config)
    write_text(auth_path, new_auth)
    write_text(global_agents, merge_agents_rules(new_global_agents))
    write_text(workspace_agents, merge_agents_rules(new_workspace_agents))
    log(f"已写入 Codex 配置：{config_path}")
    log(f"已写入 Codex 登录授权文件：{auth_path}")
    log(f"模型：{model}")
    if mode == CodexConfigMode.OFFICIAL_CHATGPT:
        log("官方直登模式：模型请求走用户自己的 ChatGPT 账号额度，不写入胖虎AI中转站 Key。")
    else:
        log(f"接口地址：{CODEX_BASE_URL}")
        log(f"Key：{mask_key(api_key)}")
    if mode == CodexConfigMode.DUAL_STATE:
        log("配置生效提示：配置写完后，请先完全退出 Codex，再重新打开 Codex；否则 Codex 可能继续使用旧配置。")
        log("双态模式需要用户重新打开后自行登录自己的 ChatGPT 账号；登录态来自用户账号，模型消耗走胖虎AI API Key。")
    elif mode == CodexConfigMode.OFFICIAL_CHATGPT:
        log("官方直登提示：请完全退出 Codex 后重新打开；如未登录，请在 Codex 内登录自己的 ChatGPT 账号。")
    else:
        log("普通模式提示：已写入直接 API 配置；配置写完后，请先完全退出 Codex，再重新打开 Codex。")

    ok = True
    if mode == CodexConfigMode.OFFICIAL_CHATGPT:
        log("官方直登模式不执行胖虎AI接口测试；请重开 Codex 后用官方账号额度完成最小对话验证。")
    elif skip_test:
        log("已跳过接口测试。")
    else:
        ok, msg = test_api(base_url, api_key)
        log(msg)
        if not ok:
            for target, backup in backups.items():
                restore_backup(target, backup, existed_before[target])
            log("接口测试失败，已自动恢复本次写入前的配置备份。")

    if open_app:
        start_temporary_openai_access(temporary_openai_access, log)
        _, msg = open_codex_app(workdir)
        log(msg)

    return ok


def load_json_object(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"{path} 不是标准 JSON，已停止自动写入：{exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{path} 顶层不是 JSON 对象，已停止自动写入。")
    return payload


def install_claude_code_config(api_key: str, model: str, log) -> bool:
    if not api_key.strip():
        raise ValueError("请先输入胖虎AI API Key。")
    if not model.strip():
        raise ValueError("模型不能为空。")

    settings_path = claude_code_settings_path()
    existed_before = settings_path.exists()
    backup = backup_file(settings_path)
    if backup:
        log(f"已备份 Claude Code 设置：{backup}")
    else:
        log(f"将创建 Claude Code 设置：{settings_path}")

    try:
        settings = load_json_object(settings_path)
        env = settings.get("env")
        if not isinstance(env, dict):
            env = {}
        env.update(
            {
                "ANTHROPIC_BASE_URL": CLAUDE_CODE_BASE_URL,
                "ANTHROPIC_AUTH_TOKEN": api_key.strip(),
                "ANTHROPIC_API_KEY": api_key.strip(),
                "ANTHROPIC_MODEL": model.strip(),
                "ANTHROPIC_SMALL_FAST_MODEL": model.strip(),
                "ANTHROPIC_CUSTOM_MODEL_OPTION": model.strip(),
                "ANTHROPIC_CUSTOM_MODEL_OPTION_NAME": f"PanghuAI {model.strip()}",
                "ANTHROPIC_CUSTOM_MODEL_OPTION_DESCRIPTION": "胖虎AI网关模型",
            }
        )
        settings["env"] = env
        write_text(settings_path, json.dumps(settings, ensure_ascii=False, indent=2) + "\n")
    except Exception:
        restore_backup(settings_path, backup, existed_before)
        raise

    log(f"已写入 Claude Code/CC 设置：{settings_path}")
    log(f"Claude Code/CC 网关：{CLAUDE_CODE_BASE_URL}")
    log(f"Claude Code/CC 模型：{model.strip()}")
    log(f"Claude Code/CC Key：{mask_key(api_key.strip())}")
    log("Claude Code/CC 提示：请完全退出后重新打开，再执行最小中文对话验收。")
    return True


def build_openclaw_config(api_key: str, model: str) -> dict:
    provider_model = f"panghuai/{model}"
    return {
        "$schema": "https://docs.openclaw.ai/schemas/config.json",
        "agents": {
            "defaults": {
                "model": {"primary": provider_model},
                "models": {provider_model: {}},
            }
        },
        "models": {
            "mode": "merge",
            "providers": {
                "panghuai": {
                    "baseUrl": CODEX_BASE_URL,
                    "api": "openai-completions",
                    "apiKey": api_key,
                    "models": [
                        {
                            "id": model,
                            "name": f"PanghuAI {model}",
                        }
                    ],
                }
            }
        },
    }


def install_openclaw_config(api_key: str, model: str, log) -> bool:
    if not api_key.strip():
        raise ValueError("请先输入胖虎AI API Key。")
    if not model.strip():
        raise ValueError("模型不能为空。")

    config_path = openclaw_config_path()
    existed_before = config_path.exists()
    backup = backup_file(config_path)
    if backup:
        log(f"已备份 OpenClaw 配置：{backup}")
    else:
        log(f"将创建 OpenClaw 配置：{config_path}")

    try:
        write_text(config_path, json.dumps(build_openclaw_config(api_key.strip(), model.strip()), ensure_ascii=False, indent=2) + "\n")
        if shutil.which("openclaw"):
            ok, output = run_command_with_env(
                ["openclaw", "config", "validate"],
                timeout=120,
                env={"OPENCLAW_CONFIG_PATH": str(config_path)},
            )
            log(output)
            if not ok:
                raise RuntimeError("OpenClaw 官方配置校验失败，已恢复本次写入前配置。")
    except Exception:
        restore_backup(config_path, backup, existed_before)
        raise

    log(f"已写入 OpenClaw 配置：{config_path}")
    log(f"OpenClaw 网关：{CODEX_BASE_URL}")
    log(f"OpenClaw 模型：panghuai/{model.strip()}")
    log(f"OpenClaw Key：{mask_key(api_key.strip())}")
    log("OpenClaw 第三方通道默认跳过；请执行官方最小中文对话验收。")
    return True


def build_hermes_config(model: str) -> str:
    escaped_model = model.strip().replace('"', '\\"')
    return "\n".join(
        [
            "# PanghuAI generated Hermes configuration",
            "custom_providers:",
            "  - name: panghuai",
            f"    base_url: {CODEX_BASE_URL}",
            "    key_env: PANGHUAI_API_KEY",
            "    api_mode: chat_completions",
            "model:",
            "  provider: custom:panghuai",
            f'  default: "{escaped_model}"',
            "  base_url: ''",
            "  api_mode: chat_completions",
            "auxiliary:",
            "  compression:",
            "    provider: auto",
            "",
        ]
    )


def install_hermes_config(api_key: str, model: str, log) -> bool:
    if not api_key.strip():
        raise ValueError("请先输入胖虎AI API Key。")
    if not model.strip():
        raise ValueError("模型不能为空。")

    config_path = hermes_config_path()
    env_path = hermes_env_path()
    existed_before = {config_path: config_path.exists(), env_path: env_path.exists()}
    backups = {config_path: backup_file(config_path), env_path: backup_file(env_path)}
    for target, backup in backups.items():
        if backup:
            log(f"已备份 Hermes 配置：{backup}")
        else:
            log(f"将创建 Hermes 配置：{target}")

    try:
        write_text(config_path, build_hermes_config(model.strip()))
        write_text(env_path, f"PANGHUAI_API_KEY={api_key.strip()}\n")
        if shutil.which("hermes"):
            ok, output = run_command_with_env(
                ["hermes", "config", "check"],
                timeout=120,
                env={"HERMES_HOME": str(config_path.parent)},
            )
            log(output)
            if not ok:
                raise RuntimeError("Hermes 官方配置检查失败，已恢复本次写入前配置。")
    except Exception:
        for target, backup in backups.items():
            restore_backup(target, backup, existed_before[target])
        raise

    log(f"已写入 Hermes 配置：{config_path}")
    log(f"已写入 Hermes 环境密钥文件：{env_path}")
    log(f"Hermes 网关：{CODEX_BASE_URL}")
    log(f"Hermes 模型：{model.strip()}")
    log(f"Hermes Key：{mask_key(api_key.strip())}")
    log("Hermes 第三方通道默认跳过；请重新打开 Hermes 后执行最小中文对话验收。")
    return True


def gemini_agy_home_path() -> Path:
    return Path.home() / ".gemini"


def gemini_agy_env_path() -> Path:
    return gemini_agy_home_path() / ".env"


def build_gemini_agy_env(existing_text: str, api_key: str, model: str) -> str:
    managed = {
        "GOOGLE_GEMINI_BASE_URL": DEFAULT_BASE_URL,
        "GEMINI_API_KEY": api_key.strip(),
        "GEMINI_MODEL": model.strip(),
    }
    lines: list[str] = []
    seen: set[str] = set()
    for raw_line in (existing_text or "").splitlines():
        stripped = raw_line.strip()
        key = ""
        if "=" in stripped and not stripped.startswith("#"):
            key = stripped.split("=", 1)[0].strip()
        if key in managed:
            if key not in seen:
                lines.append(f"{key}={managed[key]}")
                seen.add(key)
            continue
        lines.append(raw_line)
    for key, value in managed.items():
        if key not in seen:
            lines.append(f"{key}={value}")
    return "\n".join(lines).strip() + "\n"


def install_gemini_agy_config(api_key: str, model: str, log) -> bool:
    if not api_key.strip():
        raise ValueError("请先输入胖虎AI API Key。")
    if not model.strip():
        raise ValueError("模型不能为空。")

    env_path = gemini_agy_env_path()
    existed_before = env_path.exists()
    backup = backup_file(env_path)
    if backup:
        log(f"已备份 Gemini / agy 环境配置：{backup}")
    else:
        log(f"将创建 Gemini / agy 环境配置：{env_path}")

    try:
        existing_text = env_path.read_text(encoding="utf-8") if existed_before else ""
        write_text(env_path, build_gemini_agy_env(existing_text, api_key, model))
    except Exception:
        restore_backup(env_path, backup, existed_before)
        raise

    log(f"已写入 Gemini / agy 环境配置：{env_path}")
    log(f"Gemini / agy 网关（Gemini 格式）：{DEFAULT_BASE_URL}")
    log(f"Gemini / agy 模型：{model.strip()}")
    log(f"Gemini / agy Key：{mask_key(api_key.strip())}")
    log("Gemini / agy 提示：请完全退出 agy 后重新打开，再执行最小中文对话验收。")
    return True


# ---------------------------------------------------------------------------
# 统一配置快照层（对标 cc-switch Profile 机制 / Codex++ 官方切回，2026-07-03 方案 P0）
# - 每个 Agent 独立快照目录；写配置前自动快照；保留最近 SNAPSHOT_KEEP_COUNT 份。
# - "original" 初始快照在首次接管前留存，永不清理，用于一键恢复官方初始配置。
# - 回滚前先做 pre-restore 快照，保证"回滚的回滚"可行。
# ---------------------------------------------------------------------------

SNAPSHOT_KEEP_COUNT = 10  # 快照保留份数（用户决策）
ORIGINAL_SNAPSHOT_NAME = "original"


def panghu_snapshot_root() -> Path:
    override = os.environ.get("PANGHU_SNAPSHOT_ROOT")
    if override:
        return Path(override)
    return Path.home() / ".panghu_config_snapshots"


def agent_config_target_paths(agent_id: str) -> list[Path]:
    if agent_id == "codex":
        return [codex_home() / "config.toml", codex_auth_path()]
    if agent_id == "claude_code":
        return [claude_code_settings_path()]
    if agent_id == "openclaw":
        return [openclaw_config_path()]
    if agent_id == "hermes":
        return [hermes_config_path(), hermes_env_path()]
    if agent_id == "gemini_agy":
        return [gemini_agy_env_path()]
    raise ValueError(f"未知 Agent：{agent_id}")


def _agent_snapshot_dir(agent_id: str) -> Path:
    return panghu_snapshot_root() / agent_id


def _prune_config_snapshots(agent_id: str) -> None:
    base = _agent_snapshot_dir(agent_id)
    if not base.exists():
        return
    snapshots = sorted(
        [item for item in base.iterdir() if item.is_dir() and item.name != ORIGINAL_SNAPSHOT_NAME],
        key=lambda item: item.name,
        reverse=True,
    )
    for stale in snapshots[SNAPSHOT_KEEP_COUNT:]:
        shutil.rmtree(stale, ignore_errors=True)


def create_config_snapshot(agent_id: str, reason: str, log=None, name: str | None = None) -> Path:
    targets = agent_config_target_paths(agent_id)
    snapshot_name = name or datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    snapshot_dir = _agent_snapshot_dir(agent_id) / snapshot_name
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    saved: dict[str, str] = {}
    absent: list[str] = []
    for target in targets:
        if target.exists():
            shutil.copy2(target, snapshot_dir / target.name)
            saved[target.name] = str(target)
        else:
            absent.append(str(target))
    meta = {
        "agent_id": agent_id,
        "reason": reason,
        "created_at": datetime.now().isoformat(),
        "files": saved,
        "absent": absent,
    }
    (snapshot_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if name != ORIGINAL_SNAPSHOT_NAME:
        _prune_config_snapshots(agent_id)
    if log:
        log(f"已创建 {agent_id} 配置快照：{snapshot_name}（{reason}）")
    return snapshot_dir


def ensure_original_config_snapshot(agent_id: str, log=None) -> Path:
    snapshot_dir = _agent_snapshot_dir(agent_id) / ORIGINAL_SNAPSHOT_NAME
    if (snapshot_dir / "meta.json").exists():
        return snapshot_dir
    return create_config_snapshot(agent_id, "接管前原始配置", log=log, name=ORIGINAL_SNAPSHOT_NAME)


def list_config_snapshots(agent_id: str) -> list[dict]:
    base = _agent_snapshot_dir(agent_id)
    if not base.exists():
        return []
    snapshots: list[dict] = []
    for item in sorted(base.iterdir(), key=lambda entry: entry.name, reverse=True):
        meta_path = item / "meta.json"
        if not item.is_dir() or not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        snapshots.append(
            {
                "name": item.name,
                "reason": str(meta.get("reason") or ""),
                "created_at": str(meta.get("created_at") or ""),
                "file_count": len(meta.get("files") or {}),
                "is_original": item.name == ORIGINAL_SNAPSHOT_NAME,
            }
        )
    return snapshots


def restore_config_snapshot(agent_id: str, snapshot_name: str, log) -> bool:
    snapshot_dir = _agent_snapshot_dir(agent_id) / snapshot_name
    meta_path = snapshot_dir / "meta.json"
    if not meta_path.exists():
        raise ValueError(f"快照不存在：{agent_id}/{snapshot_name}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    create_config_snapshot(agent_id, f"回滚到 {snapshot_name} 前自动快照", log=log)
    for file_name, original_path in (meta.get("files") or {}).items():
        source = snapshot_dir / file_name
        target = Path(original_path)
        if not source.exists():
            raise ValueError(f"快照文件缺失：{source}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        log(f"已恢复 {agent_id} 配置文件：{target}")
    for absent_path in meta.get("absent") or []:
        target = Path(absent_path)
        if target.exists():
            target.unlink()
            log(f"已移除快照时不存在的文件：{target}")
    log(f"{agent_id} 已回滚到快照 {snapshot_name}；请完全退出并重新打开对应 Agent 后生效。")
    return True


def restore_original_config(agent_id: str, log) -> bool:
    """一键恢复官方初始配置：回到本工具首次接管前的状态（交付回收/客户自修复场景）。"""
    return restore_config_snapshot(agent_id, ORIGINAL_SNAPSHOT_NAME, log)


# ---------------------------------------------------------------------------
# 配置漂移巡检（对标 cc-switch 漂移检测，2026-07-03 方案 P0）
# 比对各 Agent 当前配置与"胖虎最后一次写入的期望值"，分级：
#   red  = 网关地址被改（影响计费/把买家切走），需一键修复
#   yellow = 模型被改（影响体验/额度），提示
#   grey = 无关字段变化，忽略
# key 只比指纹（mask），不落明文。
# ---------------------------------------------------------------------------

DRIFT_RED = "red"
DRIFT_YELLOW = "yellow"
DRIFT_OK = "ok"


def _read_text_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8") if path.exists() else ""
    except OSError:
        return ""


def _load_json_safe(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def agent_expected_gateway(agent_id: str) -> str:
    if agent_id == "claude_code":
        return CLAUDE_CODE_BASE_URL
    if agent_id in {"codex", "openclaw", "hermes"}:
        return CODEX_BASE_URL
    if agent_id == "gemini_agy":
        return DEFAULT_BASE_URL
    raise ValueError(f"未知 Agent：{agent_id}")


def inspect_agent_config_drift(agent_id: str, expected_model: str = "") -> dict:
    """检查单个 Agent 的配置漂移。返回 {agent_id, level, findings[], repairable}。

    findings 每项 {field, severity, detail}。不返回任何明文 Key。
    """
    findings: list[dict] = []
    expected_gateway = agent_expected_gateway(agent_id)
    configured = False

    def add(field: str, severity: str, detail: str) -> None:
        findings.append({"field": field, "severity": severity, "detail": detail})

    if agent_id == "codex":
        config_text = _read_text_safe(codex_home() / "config.toml")
        auth = _load_json_safe(codex_auth_path())
        configured = bool(config_text) or bool(auth)
        if configured:
            if CODEX_BASE_URL not in config_text and "aitokenapi.cc" not in config_text:
                add("base_url", DRIFT_RED, "Codex config.toml 未指向胖虎AI网关")
            if expected_model and expected_model not in config_text:
                add("model", DRIFT_YELLOW, f"Codex 未使用推荐模型 {expected_model}")
            if not str(auth.get("OPENAI_API_KEY") or "").strip():
                add("api_key", DRIFT_RED, "Codex auth.json 缺少 API Key")
    elif agent_id == "claude_code":
        settings = _load_json_safe(claude_code_settings_path())
        env = settings.get("env") if isinstance(settings.get("env"), dict) else {}
        configured = bool(env)
        if configured:
            if str(env.get("ANTHROPIC_BASE_URL") or "") != CLAUDE_CODE_BASE_URL:
                add("base_url", DRIFT_RED, "ClaudeCode ANTHROPIC_BASE_URL 未指向胖虎AI网关")
            if not str(env.get("ANTHROPIC_AUTH_TOKEN") or env.get("ANTHROPIC_API_KEY") or "").strip():
                add("api_key", DRIFT_RED, "ClaudeCode 缺少 API Key")
            if expected_model and str(env.get("ANTHROPIC_MODEL") or "") != expected_model:
                add("model", DRIFT_YELLOW, f"ClaudeCode 未使用推荐模型 {expected_model}")
    elif agent_id == "openclaw":
        config = _load_json_safe(openclaw_config_path())
        providers = ((config.get("models") or {}).get("providers") or {})
        panghu = providers.get("panghuai") if isinstance(providers, dict) else None
        configured = bool(config)
        if configured:
            if not isinstance(panghu, dict) or str(panghu.get("baseUrl") or "") != CODEX_BASE_URL:
                add("base_url", DRIFT_RED, "OpenClaw panghuai 提供商未指向胖虎AI网关")
            elif not str(panghu.get("apiKey") or "").strip():
                add("api_key", DRIFT_RED, "OpenClaw panghuai 提供商缺少 API Key")
    elif agent_id == "hermes":
        config_text = _read_text_safe(hermes_config_path())
        env_text = _read_text_safe(hermes_env_path())
        configured = bool(config_text) or bool(env_text)
        if configured:
            if CODEX_BASE_URL not in config_text:
                add("base_url", DRIFT_RED, "Hermes custom_providers 未指向胖虎AI网关")
            if "PANGHUAI_API_KEY=" not in env_text:
                add("api_key", DRIFT_RED, "Hermes .env 缺少 PANGHUAI_API_KEY")
    elif agent_id == "gemini_agy":
        env_text = _read_text_safe(gemini_agy_env_path())
        configured = bool(env_text)
        if configured:
            if f"GOOGLE_GEMINI_BASE_URL={DEFAULT_BASE_URL}" not in env_text:
                add("base_url", DRIFT_RED, "Gemini/agy GOOGLE_GEMINI_BASE_URL 未指向胖虎AI网关")
            if "GEMINI_API_KEY=" not in env_text:
                add("api_key", DRIFT_RED, "Gemini/agy 缺少 GEMINI_API_KEY")
            if expected_model and f"GEMINI_MODEL={expected_model}" not in env_text:
                add("model", DRIFT_YELLOW, f"Gemini/agy 未使用推荐模型 {expected_model}")
    else:
        raise ValueError(f"未知 Agent：{agent_id}")

    if not configured:
        level = DRIFT_OK
    elif any(f["severity"] == DRIFT_RED for f in findings):
        level = DRIFT_RED
    elif any(f["severity"] == DRIFT_YELLOW for f in findings):
        level = DRIFT_YELLOW
    else:
        level = DRIFT_OK
    return {
        "agent_id": agent_id,
        "configured": configured,
        "level": level,
        "findings": findings,
        "repairable": level == DRIFT_RED,
        "expected_gateway": expected_gateway,
    }


def inspect_all_config_drift(agent_ids: list[str] | None = None, expected_models: dict[str, str] | None = None) -> dict:
    ids = agent_ids or [agent.id for agent in AGENTS]
    if isinstance(expected_models, str):
        _m = expected_models
        expected_models = {aid: (_m if key_format_for_agent(aid) == "openai" else "") for aid in ids}
    em = expected_models or {}
    reports = [inspect_agent_config_drift(agent_id, em.get(agent_id, "")) for agent_id in ids]
    risk_findings = detect_risk_plugins()
    worst = DRIFT_OK
    for report in reports:
        if report["level"] == DRIFT_RED:
            worst = DRIFT_RED
            break
        if report["level"] == DRIFT_YELLOW:
            worst = DRIFT_YELLOW
    if risk_findings and worst != DRIFT_RED:
        worst = DRIFT_RED  # 风险插件在场直接升红
    return {
        "overall_level": worst,
        "agents": reports,
        "risk_plugins": [
            {"name": finding.name, "source": finding.source, "detail": finding.detail}
            for finding in risk_findings
        ],
    }


def repair_agent_config_drift(agent_id: str, api_key: str, model: str, log) -> bool:
    """一键修复：用当前买家 Key/模型重新写入胖虎网关配置（内部走 apply_agent_config，含快照保护）。"""
    if not api_key.strip():
        raise ValueError("一键修复需要当前买家的胖虎AI API Key。")
    agent = next((item for item in AGENTS if item.id == agent_id), None)
    if agent is None:
        raise ValueError(f"未知 Agent：{agent_id}")
    log(f"开始一键修复 {agent.name} 配置漂移……")
    ok = apply_agent_config(agent, "cli", api_key, model or DEFAULT_MODEL, log)
    if ok:
        after = inspect_agent_config_drift(agent_id, model)
        if after["level"] == DRIFT_RED:
            log(f"警告：{agent.name} 修复后仍检测到红色漂移，请人工检查是否有第三方工具持续改写配置。")
            return False
        log(f"{agent.name} 配置漂移已修复；请完全退出并重新打开对应 Agent。")
    return ok


# ---------------------------------------------------------------------------
# 网关线路测速（对标 cc-switch 延迟测速，2026-07-03 方案 P1）
# 对胖虎网关候选线路做轻量探测，返回延迟，为多线路自动选优打基础。
# 线路清单默认只有主域名；服务端下发备用线路后可扩展 GATEWAY_ENDPOINT_CANDIDATES。
# ---------------------------------------------------------------------------

GATEWAY_ENDPOINT_CANDIDATES = (
    {"id": "primary", "label": "胖虎AI主线路", "url": DEFAULT_BASE_URL},
)


def _measure_endpoint_latency(url: str, timeout: int = 8) -> dict:
    import time as _time

    probe_url = url.rstrip("/") + "/"
    started = _time.monotonic()
    try:
        req = Request(probe_url, headers={"User-Agent": HTTP_USER_AGENT}, method="HEAD")
        with trusted_urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
        elapsed_ms = int((_time.monotonic() - started) * 1000)
        return {"reachable": True, "latency_ms": elapsed_ms, "status": status, "error": ""}
    except Exception as exc:  # HEAD 不被支持时退回 GET
        try:
            req = Request(probe_url, headers={"User-Agent": HTTP_USER_AGENT}, method="GET")
            with trusted_urlopen(req, timeout=timeout) as resp:
                status = getattr(resp, "status", 200)
            elapsed_ms = int((_time.monotonic() - started) * 1000)
            return {"reachable": True, "latency_ms": elapsed_ms, "status": status, "error": ""}
        except Exception as exc2:
            return {"reachable": False, "latency_ms": None, "status": None, "error": str(exc2 or exc)}


def measure_gateway_latency(candidates=None, timeout: int = 8) -> dict:
    """测各候选线路延迟，返回排序结果和推荐线路（延迟最低的可达线路）。"""
    endpoints = candidates if candidates is not None else GATEWAY_ENDPOINT_CANDIDATES
    results = []
    for endpoint in endpoints:
        measured = _measure_endpoint_latency(endpoint["url"], timeout=timeout)
        results.append({**endpoint, **measured})
    reachable = [item for item in results if item["reachable"]]
    reachable.sort(key=lambda item: item["latency_ms"])
    results.sort(key=lambda item: (not item["reachable"], item["latency_ms"] if item["latency_ms"] is not None else 10**9))
    return {
        "endpoints": results,
        "recommended_id": reachable[0]["id"] if reachable else None,
        "recommended_url": reachable[0]["url"] if reachable else None,
    }


def agent_dialogue_probe_command(agent_id: str, model: str) -> list[str]:
    prompt = AGENT_DIALOGUE_PROBE_PROMPT
    if agent_id == "claude_code":
        command = ["claude"]
        settings_path = os.environ.get("CLAUDE_CODE_SETTINGS_PATH")
        if settings_path:
            command.extend(["--settings", settings_path, "--bare"])
        command.extend(["--model", model, "-p", prompt])
        return command
    if agent_id == "openclaw":
        return ["openclaw", "infer", "model", "run", "--model", f"panghuai/{model}", "--prompt", prompt, "--json"]
    if agent_id == "hermes":
        return ["hermes", "--provider", "custom:panghuai", "--model", model, "-z", prompt]
    if agent_id == "gemini_agy":
        # agy CLI 只有 --model 长参（无 -m 短参，传 -m 会报 flags provided but not defined）
        return ["agy", "--model", model, "-p", prompt]
    raise ValueError(f"未知或不支持命令验收的 Agent：{agent_id}")


def recent_hermes_error_summary(home: Path | None = None) -> str:
    hermes_home = home or hermes_home_path()
    sessions_dir = hermes_home / "sessions"
    if not sessions_dir.exists():
        return ""
    dumps = sorted(sessions_dir.glob("request_dump_*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    for dump_path in dumps[:3]:
        try:
            payload = json.loads(dump_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        request = payload.get("request") if isinstance(payload, dict) else {}
        error = payload.get("error") if isinstance(payload, dict) else {}
        if not isinstance(request, dict) or not isinstance(error, dict):
            continue
        url = str(request.get("url") or "")
        status = error.get("status_code") or error.get("response_status") or ""
        body = error.get("body")
        message = ""
        if isinstance(body, dict):
            message = str(body.get("message") or body.get("error") or "")
        if not message:
            message = str(error.get("message") or error.get("response_text") or "")
        if re.search(r"invalid\s+token", message, flags=re.IGNORECASE):
            request_id_match = re.search(r"request id:\s*([A-Za-z0-9._-]+)", message, flags=re.IGNORECASE)
            message = "无效令牌"
            if request_id_match:
                message += f"（request id: {request_id_match.group(1)}）"
        parts = []
        if url:
            parts.append(f"请求地址：{url}")
        if status:
            parts.append(f"状态码：{status}")
        if message:
            parts.append(f"错误：{message}")
        if parts:
            return sanitize_log_text("；".join(parts))
    return ""


def run_agent_dialogue_probe(agent: AgentSpec, mode_id: str, model: str) -> tuple[bool, str]:
    if agent.id == "codex":
        return False, "Codex 使用胖虎AI网关真实任务验证，不走外部 CLI 对话命令。"
    try:
        command = agent_dialogue_probe_command(agent.id, model.strip())
    except ValueError as exc:
        return False, str(exc)
    ok, output = run_command(command, timeout=90)
    output = (output or "").strip()
    if not ok:
        if agent.id == "hermes":
            summary = recent_hermes_error_summary()
            if summary:
                return False, f"{output}\nHermes 最近请求诊断：{summary}".strip()
        return False, output or f"{agent.name}/{mode_id} 最小对话命令执行失败。"
    if not output:
        return False, f"{agent.name}/{mode_id} 最小对话命令没有返回内容。"
    return True, output[:1000]


def agent_mode_uses_cli_probe(mode_id: str) -> bool:
    return mode_id == "cli"


def agent_mode_requires_client_scope(mode_id: str) -> bool:
    return mode_id in {"client", "both"}


# 用户决策（2026-07-03 修正版）：官方提供客户端安装的 Agent（Codex、ClaudeCode/Claude Desktop、
# Gemini/agy/Antigravity）做真实客户端交付：检测/安装官方客户端并按验收矩阵单独验收；
# 官方没有客户端的（OpenClaw、Hermes）只销售 CLI 交付，不提供 client scope。
AGENTS_WITH_OFFICIAL_CLIENT = frozenset({"codex", "claude_code", "gemini_agy"})
CLI_ONLY_DELIVERY_AGENTS = frozenset({"openclaw", "hermes"})


def agent_offers_client_scope(agent_id: str) -> bool:
    return agent_id in AGENTS_WITH_OFFICIAL_CLIENT


def verify_agent_client_scope(agent: AgentSpec, mode_id: str) -> tuple[bool, str]:
    if agent.id in CLI_ONLY_DELIVERY_AGENTS:
        return (
            False,
            f"{agent.name} 官方未提供客户端安装，本产品对该 Agent 只销售 CLI 交付；client scope 不适用。",
        )
    client_ok, client_detail = agent_client_status(agent)
    if not client_ok:
        return (
            False,
            f"{agent.name}/{mode_id} client scope 需要官方客户端；当前未检测到：{client_detail}",
        )
    return (
        True,
        f"{agent.name}/{mode_id} 官方客户端已检测到（{client_detail}）；"
        "最终交付仍以客户端内最小中文任务和功能验收矩阵记录为准。",
    )


def agent_dialogue_probe_command_text(agent: AgentSpec, model: str) -> str:
    if agent.id == "codex":
        return "胖虎AI /v1/chat/completions 最小中文真实任务验证"
    try:
        return " ".join(shlex.quote(part) for part in agent_dialogue_probe_command(agent.id, model.strip()))
    except ValueError:
        return "暂未配置自动复验命令"


def _agent_mode_label(agent: AgentSpec, mode_id: str) -> str:
    mode_labels = {mode.id: mode.label for mode in agent.modes}
    # CLI-only Agent 已移除 client 模式，但矩阵仍可能渲染 client scope 行；
    # 客户可见文案回退到中文标签，不出现原始英文 mode id。
    fallback_labels = {"cli": "CLI", "client": "客户端"}
    return mode_labels.get(mode_id, fallback_labels.get(mode_id, mode_id))


def _customer_status_label(status: NodeStatus) -> str:
    labels = {
        NodeStatus.PASS: "通过",
        NodeStatus.FAILED: "失败",
        NodeStatus.NEEDS_MANUAL: "待人工确认",
        NodeStatus.WARNING: "警告",
        NodeStatus.BLOCKED: "被阻断",
        NodeStatus.SERVER_DISABLED: "服务端关闭",
        NodeStatus.RUNNING: "处理中",
        NodeStatus.NOT_STARTED: "未开始",
    }
    return labels.get(status, str(status))


def build_customer_agent_acceptance_matrix(
    selected: list[tuple[AgentSpec, str]],
    agent_progress: dict[tuple[str, str], DeploymentProgress],
    real_task_results: dict[tuple[str, str], RealTaskVerificationResult],
    diagnostic_code: str,
) -> str:
    lines = [
        "客户可见功能验收矩阵",
        f"诊断码：{diagnostic_code}",
        "",
        "说明：只有安装、配置写入、启动检测、最小对话全部通过，才算该 Agent 完整交付并允许扣次。",
    ]
    for agent, mode_id in selected:
        mode_key = commercial_mode_key_for_deployment(agent.id, mode_id)
        session_key = (agent.id, mode_key)
        progress = agent_progress.get(session_key, DeploymentProgress())
        result = real_task_results.get(session_key)
        delivered = progress.can_commit_success()
        lines.extend(
            [
                "",
                f"{agent.name}({_agent_mode_label(agent, mode_id)})：{'完整交付' if delivered else '未完整交付'}",
                f"- 官方入口：已纳入",
                f"- 配置写入：{_customer_status_label(progress.status_for(DeploymentNode.CONFIG_WRITE))}",
                f"- 启动检测：{_customer_status_label(progress.status_for(DeploymentNode.LAUNCH_VERIFY))}",
                f"- 最小对话：{_customer_status_label(progress.status_for(DeploymentNode.REAL_TASK_VERIFY))}",
                f"- 复验命令：{agent_dialogue_probe_command_text(agent, DEFAULT_MODEL)}",
                f"- 第三方通道：默认跳过",
                f"- 扣次状态：{'允许扣次' if delivered else '不扣次'}",
                f"- 响应摘要：{sanitize_worker_message(result.response_excerpt) if result else '无'}",
            ]
        )
    return "\n".join(lines) + "\n"


def write_customer_agent_acceptance_matrix(
    selected: list[tuple[AgentSpec, str]],
    agent_progress: dict[tuple[str, str], DeploymentProgress],
    real_task_results: dict[tuple[str, str], RealTaskVerificationResult],
    diagnostic_code: str,
    log,
) -> Path:
    report_path = customer_acceptance_matrix_path()
    content = build_customer_agent_acceptance_matrix(selected, agent_progress, real_task_results, diagnostic_code)
    write_text(report_path, content)
    log(f"已生成客户可见功能验收矩阵：{report_path}")
    return report_path


AGENT_KEY_FORMAT = {
    "codex": "openai",
    "openclaw": "openai",
    "hermes": "openai",
    "claude_code": "anthropic",
    "gemini_agy": "gemini",
}
KEY_FORMAT_IDS = ("openai", "anthropic", "gemini")
KEY_FORMAT_LABELS = {"openai": "OpenAI 兼容格式", "anthropic": "Anthropic 格式", "gemini": "Gemini 格式"}


def key_format_for_agent(agent_id: str) -> str:
    return AGENT_KEY_FORMAT.get(agent_id, "openai")


def apply_agent_config(agent: AgentSpec, mode_id: str, api_key: str, model: str, log) -> bool:
    # 统一快照层：首次接管前留存 original 初始快照；每次写配置前自动快照（保留最近 10 份）
    try:
        ensure_original_config_snapshot(agent.id, log)
        create_config_snapshot(agent.id, f"写入 {mode_id} 配置前自动快照", log=log)
    except Exception as exc:  # 快照失败不阻断配置，但必须让用户知道
        log(f"警告：{agent.name} 配置快照创建失败（{exc}）；本次写入仍有单文件备份保护。")
    if agent.id == "codex":
        log("Codex 配置由 Codex 主配置链路写入。")
        return True
    if agent.id == "claude_code":
        return install_claude_code_config(api_key, model, log)
    if agent.id == "openclaw":
        return install_openclaw_config(api_key, model, log)
    if agent.id == "hermes":
        return install_hermes_config(api_key, model, log)
    if agent.id == "gemini_agy":
        return install_gemini_agy_config(api_key, model, log)
    raise ValueError(f"未知 Agent：{agent.id}/{mode_id}")


def build_agent_setup_guide_content(selected: list[tuple[AgentSpec, str]], api_key: str) -> str:
    names = "、".join(f"{agent.name}({mode})" for agent, mode in selected)
    playbook_lines = []
    for agent, mode in selected:
        playbook = agent_delivery_playbook(agent.id)
        playbook_lines.append(
            f"- {agent.name}({mode})：{playbook.customer_goal}"
            f"第三方通道默认跳过；配置项包括 {('；'.join(playbook.config_commands))}；"
            f"验收：{playbook.minimal_dialogue_check}"
        )
    return f"""胖虎AI Agent 配置说明

已选择 Agent：{names}
胖虎AI接口地址：{DEFAULT_BASE_URL}
胖虎AI API Key：{mask_key(api_key)}

说明：
1. Codex 默认由本工具写入普通直接 API 配置。
2. 配置写完后，请先完全退出 Codex，再重新打开 Codex；只有完全退出后重新打开，新的配置才会生效。
3. 普通配置方式无需登录 ChatGPT 账号，也可以正常使用 Codex。
4. 只有点击“双态配置”时，才需要用户重新打开 Codex 后自行登录自己的 ChatGPT 账号。
5. 双态模式下，Codex 会保持用户自己的账号登录态，同时模型调用消耗胖虎AI API Key。本工具不代替登录、不保存 ChatGPT 账号密码。
6. ClaudeCode/CC、OpenClaw、Hermes 都按官方 CLI 与客户端入口做安装和配置；IDE 插件形态不处理。
7. Gemini / agy（Google Antigravity）按官方 CLI 与客户端入口安装，写入胖虎AI网关 Gemini 格式配置；未通过最小中文对话验收前不计完整交付。
8. OpenClaw、Hermes 等复杂第三方通道默认跳过，只走能让买家直接对话的最短可用链路。
9. 已接入配置链路的 Agent 必须完成配置写入、重启/启动检查和最小中文对话验证后，才算完整交付。
10. 本工具不会把 API Key 明文写入日志。

当前 Agent Playbook：
{chr(10).join(playbook_lines)}
"""


def login_help_text() -> str:
    return "\n".join(
        [
            "这里登录的是胖虎AI账号，不是 ChatGPT 账号。",
            "",
            "没有胖虎AI账号时，先点击“去胖虎AI注册账号”完成注册，再回到本工具登录。",
            "",
            "该配置方式无需登录 ChatGPT 账号，也可以正常使用 Codex。普通客户只需要胖虎AI账号和胖虎AI API Key。",
            "",
            "如果客户后续明确需要保留自己的 ChatGPT 登录态，再到第四步使用“双态配置”。",
        ]
    )


def key_creation_help_text() -> str:
    return "\n".join(
        [
            "API Key 是胖虎AI给 Codex 或其他 Agent 使用的调用令牌，不是登录密码。",
            "",
            "推荐流程：",
            "1. 先注册并登录胖虎AI账号。",
            "2. 新账号先充值或确认账户里有余额。",
            "3. 点击“打开 API Key 创建页面”。",
            "4. 在网站里新建 Key，复制完整的 sk- 开头内容。",
            "5. 粘贴到本工具的 API Key 输入框。",
            "6. 点击“保存并测试 Key”。",
            "",
            "常见错误：",
            "- 不要填写手机号、邮箱、登录密码或 ChatGPT 密码。",
            "- 测试不通过时，先检查 Key 是否复制完整、账户是否有余额、接口地址是否保持默认。",
            "- 刚注册但未充值的账号，即使创建了 Key，也可能因为余额不足而测试失败。",
        ]
    )


def environment_help_text() -> str:
    return "\n".join(
        [
            "环境检测会识别当前电脑系统、基础命令和已经安装的 Agent。",
            "",
            "如果检测到 ccswitch、codex++、CCR 等第三方配置工具，本工具会阻止继续安装。",
            "",
            "原因：这些工具可能改写 Codex 或 ClaudeCode 的配置，导致胖虎AI写入的接口、Key、模型被覆盖。",
            "",
            "处理方式：按提示先卸载或禁用风险工具，再重新点击“检测环境”。",
        ]
    )


def agent_choice_help_text() -> str:
    return "\n".join(
        [
            "本工具固定覆盖五个 Agent：Codex、Claude Code/CC、Hermes、OpenClaw、Gemini / agy。",
            "",
            "Agent 差异：",
            "- Codex：写入胖虎AI API Key、接口、模型和中文规则。",
            "- Claude Code/CC：覆盖官方 CLI 和客户端入口，写入胖虎AI网关配置。",
            "- OpenClaw：覆盖官方 CLI 和 Hub/客户端入口，第三方通道默认跳过，只保留直接对话链路。",
            "- Hermes：覆盖官方 CLI 和客户端入口，第三方通道默认跳过，只保留直接对话链路。",
            "- Gemini / agy：覆盖 Google Antigravity 官方 CLI 和客户端入口，写入胖虎AI网关 Gemini 格式配置。",
            "",
            "CLI 和客户端都要做进去；VS Code / IDE 插件形态不作为本轮交付对象。",
        ]
    )


def codex_action_help_text() -> str:
    return "\n".join(
        [
            "一键部署（普通）：安装所选 Agent，并写入胖虎AI直接 API 配置。",
            "双态配置：需要同时保留 ChatGPT 登录态并消耗胖虎AI API Key 时使用，不安装 Agent。",
            "仅修复 Codex 配置：Agent 已经装好、只是换 Key 或配置损坏时使用，不会重新安装 Agent。",
            "官方直登：切换为用户自己的 ChatGPT 账号额度，不写入胖虎AI中转站 Key；如未登录，需要重开 Codex 后登录 ChatGPT 账号。",
            "恢复最近备份：配置异常时退回写入前的最近备份。",
            "复制日志：出问题时把日志发给客服排查。",
            "打开工作区：查看本工具生成的配置说明和工作资料。",
            "打开配置目录：查看 Codex 的 config.toml、auth.json 和备份文件。",
            "重要：任何 Agent 配置写完后都必须重新打开对应 Agent；只有验证能直接对话后才算完整交付。",
        ]
    )


def codex_action_summary_text() -> str:
    return "\n".join(
        [
            "普通客户点“一键部署（普通）”。",
            "需要登录态共存时，才点“双态配置”。",
            "需要消耗 ChatGPT 账号额度时，点“官方直登”。",
            "只要修改过 Codex 配置，都要完全退出 Codex 后重新打开。",
        ]
    )


def write_agent_setup_guide(selected: list[tuple[AgentSpec, str]], api_key: str, log) -> None:
    guide = workspace_root() / "胖虎AI-Agent配置说明.txt"
    content = build_agent_setup_guide_content(selected, api_key)
    write_text(guide, content)
    log(f"已生成配置说明：{guide}")


def install_agent(agent: AgentSpec, mode_id: str, log) -> bool:
    log(f"开始处理 {agent.name} / {mode_id}。")
    if agent.id == "codex" and mode_id == "cli":
        ok = install_codex_cli(log)
    elif agent.id == "codex" and mode_id == "client":
        ok = install_codex_app(log)
    elif agent.id == "claude_code" and mode_id == "cli":
        ok = install_claude_code_cli(log)
    elif agent.id == "claude_code" and mode_id == "client":
        open_url(CLAUDE_CODE_DOCS_URL)
        log("已打开 Claude Code/CC 官方客户端入口；安装后继续按胖虎AI网关配置计划验收。")
        ok = True
    elif agent.id == "openclaw" and mode_id == "cli":
        ok = install_openclaw_cli(log)
    elif agent.id == "openclaw" and mode_id == "client":
        open_url(OPENCLAW_DOCS_URL)
        log("已打开 OpenClaw 官方客户端/Hub 入口；安装后继续按胖虎AI网关配置计划验收。")
        ok = True
    elif agent.id == "hermes" and mode_id == "cli":
        ok = install_hermes_cli(log)
    elif agent.id == "hermes" and mode_id == "client":
        open_url(HERMES_DOCS_URL)
        log("已打开 Hermes 官方客户端入口；安装后继续按胖虎AI网关配置计划验收。")
        ok = True
    elif agent.id == "gemini_agy" and mode_id == "cli":
        ok = install_gemini_agy_cli(log)
    elif agent.id == "gemini_agy" and mode_id == "client":
        open_url(GEMINI_AGY_DOCS_URL)
        log("已打开 Google Antigravity 官方入口；请按官方流程完成安装，随后本工具会写入胖虎AI网关配置（~/.gemini/.env）。")
        ok = True
    else:
        log("未知 Agent 或安装方式。")
        return False

    verified, version = version_for(agent.verify_command)
    if verified:
        log(f"{agent.name} 检测通过：{version or '已安装'}")
        return True
    if ok:
        log(f"{agent.name} 安装命令已执行，但当前 PATH 暂未检测到命令，可能需要重开终端或重启软件。")
        return True
    return False


def apply_agent_config_plan(agent: AgentSpec, mode_id: str, api_key: str, model: str, log) -> bool:
    configured = apply_agent_config(agent, mode_id, api_key, model, log)
    for line in build_agent_config_plan(agent.id, mode_id, api_key, model):
        log(line)
    return configured


def detect_environment() -> list[str]:
    system = current_system_id()
    lines = [
        f"系统：{platform.system()} {platform.release()}",
        f"架构：{platform.machine()}",
        f"识别结果：{'Windows' if system == 'windows' else 'Mac' if system == 'mac' else '其他系统'}",
    ]
    for command in ("powershell", "winget", "npm", "node"):
        exists, path = command_exists(command)
        lines.append(f"{command}: {'已找到 ' + path if exists else '未找到'}")
    system = current_system_id()
    lines = [
        f"系统：{platform.system()} {platform.release()}",
        f"架构：{platform.machine()}",
        f"识别结果：{'Windows' if system == 'windows' else 'Mac' if system == 'mac' else '其他系统'}",
    ]
    for command in ("powershell", "winget", "npm", "node"):
        exists, path = command_exists(command)
        lines.append(f"{command}: {'已找到 ' + path if exists else '未找到'}")
    lines.extend(agent_install_status_lines())
    lines.extend(risk_plugin_report_lines(detect_risk_plugins()))
    return lines


def enable_windows_dpi_awareness() -> None:
    if platform.system() != "Windows":
        return
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


class WebviewApi:
    def __init__(self, app: "InstallerApp") -> None:
        self.app = app

    @staticmethod
    def _accepted(message: str) -> dict:
        return {"success": True, "accepted": True, "message": message}

    def get_initial_state(self) -> dict:
        # 前端加载完成后的首次全量拉取；此后才允许 Python 侧 evaluate_js 推送。
        self.app.webview_ready = True
        is_logged = self.app.logged_in_user is not None and self.app.deployer_auth is not None
        metrics = self.app._commercial_metric_values()
        agent_center_state = self.app.current_agent_center_state()

        agent_enabled = {}
        for k, v in self.app.agent_enabled.items():
            agent_enabled[k] = v.get()

        agent_mode = {}
        for k, v in self.app.agent_mode.items():
            agent_mode[k] = v.get()

        agent_matrix_state = {}
        selected_ids = {agent.id for agent, _mode in self.app.selected_agents()}
        executable = self.app.can_access_step(4)
        for agent in AGENTS:
            selected = agent.id in selected_ids
            if self.app.worker_running and selected and executable:
                states = {
                    "install": RUNNING,
                    "launch": RUNNING,
                    "dialogue": NEUTRAL_DOT,
                    "acceptance": NEUTRAL_DOT,
                    "delivery": NEUTRAL_DOT,
                }
            elif selected and executable:
                states = {
                    "install": RUNNING,
                    "launch": NEUTRAL_DOT,
                    "dialogue": NEUTRAL_DOT,
                    "acceptance": NEUTRAL_DOT,
                    "delivery": NEUTRAL_DOT,
                }
            elif selected:
                states = {
                    "install": NEUTRAL_DOT,
                    "launch": NEUTRAL_DOT,
                    "dialogue": NEUTRAL_DOT,
                    "acceptance": NEUTRAL_DOT,
                    "delivery": NEUTRAL_DOT,
                }
            else:
                states = {
                    "install": NEUTRAL_DOT,
                    "launch": NEUTRAL_DOT,
                    "dialogue": NEUTRAL_DOT,
                    "acceptance": NEUTRAL_DOT,
                    "delivery": NEUTRAL_DOT,
                }
            agent_matrix_state[agent.id] = {
                dim: color_to_char(color) for dim, color in states.items()
            }

        if not hasattr(self.app, "webview_logs"):
            self.app.webview_logs = empty_flow_logs()

        login_state = load_login_account_public_state()
        login_username = self.app.login_username.get().strip() or str(login_state.get("last_username") or "")
        login_account = login_account_public_entry(login_username)

        return {
            "isLogged": is_logged,
            "loginUsername": login_username,
            "loginPassword": "",
            "loginPasswordSaved": bool(login_account.get("has_password")),
            "rememberPassword": bool(login_account.get("remember_password")),
            "autoLogin": bool(login_account.get("auto_login")),
            "restoringSession": False,
            "apiKeyValue": "",
            "apiKeyPresent": bool(self.app.api_key.get().strip()),
            "apiKeyMasked": mask_key(self.app.api_key.get().strip()) if self.app.api_key.get().strip() else "",
            "skipTest": self.app.skip_test.get(),
            "savedKeyOk": self.app.saved_key_ok,
            "environmentChecked": self.app.environment_checked,
            "environmentOk": self.app.environment_ok,
            "remainingUses": metrics["remaining"],
            "validUntil": metrics["valid_until"],
            "deviceLimit": metrics["device_limit"],
            "agentEnabled": agent_enabled,
            "agentMode": agent_mode,
            "agentMatrix": agent_matrix_state,
            "logs": self.app.webview_logs,
            "theme": getattr(self.app, "theme_name", "light"),
            "currentStep": self.app.step.get(),
            "activeSubnav": self.app.active_subnav.get(),
            "activeModule": self.app.active_module.get(),
            "loginAccounts": login_state.get("accounts") or [],
            "accounts": login_state.get("accounts") or [],
            "buyerPurchase": self.app.current_buyer_purchase_state(),
            "agentCenter": agent_center_state,
            "valueAddedServices": self.app.current_value_added_services_state(),
            "communicationSoftwareLink": self.app.current_communication_software_link_web_state(),
        }

    def login(self, username, password, remember_password=False, auto_login=False):
        # 登录含网络请求（最长 20s）。必须放后台线程：
        # 1) 网络请求不能堵 GUI 线程；
        # 2) 关键——绝不能在 js_api 回调里同步调 evaluate_js（pywebview 会重入死锁）。
        # 因此本方法只启线程后立刻返回，任何 log/evaluate_js 都由线程里做。
        threading.Thread(
            target=self._login_bridge_worker,
            args=(username, password, bool(remember_password), bool(auto_login)),
            daemon=True,
        ).start()
        return {"success": True, "message": "登录请求已提交", "pending": True}

    def _login_bridge_worker(self, username, password, remember_password, auto_login):
        try:
            self.app.login_username.set(username)
            self.app.login_password.set(password)
            self.app.push_webview_toast("正在登录胖虎AI，请稍候……", "running")
            ok, msg, data = login_panghuai(username, password, self.app.cookie_jar)
            self.app.log(msg)
            if not ok:
                self.app.status.set("状态：登录失败")
                self.app.push_webview_toast(f"登录失败：{msg}", "error")
                return

            auth_ok, auth_msg, auth_data = activate_deployer(data, self.app.cookie_jar)
            self.app.log(auth_msg)
            if not auth_ok:
                self.app.status.set("状态：部署授权失败")
                self.app.push_webview_toast(f"部署授权失败：{auth_msg}", "error")
                return

            self.app.logged_in_user = data
            self.app.deployer_auth = auth_data
            self.app.commercial_contexts = self.app.build_buyer_contexts(data)
            buyer_profile = create_commercial_web_profile(self.app.commercial_contexts, str(web_profile_root()))
            ensure_commercial_web_profile_dir(buyer_profile)
            display_name = str(data.get("username") or username)
            save_buyer_session_state(data, self.app.cookie_jar)
            save_profile_data({"username": display_name}, self.app.commercial_contexts)

            save_login_account_state(
                username=display_name,
                password=password,
                remember_password=bool(remember_password or auto_login),
                auto_login=bool(auto_login and (remember_password or auto_login)),
                user_id=str(data.get("id") or ""),
            )
            self.app.login_username.set(display_name)
            self.app.login_password.set("")

            self.app.step.set(1)
            self.app.status.set("状态：已登录，请按步骤部署")
            self.app.run_later(1200, self.app.start_auto_update_check)
            self.app.run_later(1600, self.app.start_refresh_commercial_manifest)
            self.app.sync_webview_state()
        except Exception as e:
            self.app.status.set("状态：登录错误")
            self.app.log(f"登录错误：{e}")
            self.app.push_webview_toast(f"登录错误：{e}", "error")

    def login_saved_account(self, username):
        target = login_account_private_entry(username)
        if not target:
            return {"success": False, "message": "未找到该账号的保存记录。"}
        password = target.get("password", "")
        if not password:
            return {"success": False, "message": "该账号没有可用的本机保存密码，请手动输入密码。"}
        remember_password = target.get("remember_password", False)
        auto_login = target.get("auto_login", False)
        return self.login(target.get("username", username), password, remember_password, auto_login)

    def select_login_account(self, username):
        account = login_account_public_entry(username)
        self.app.login_username.set(account.get("username", ""))
        self.app.login_password.set("")
        self.app.sync_webview_state()
        return {"success": True, "account": account}

    def remove_login_account(self, username):
        try:
            state = remove_login_account_state(username)
            if _normalize_login_username(self.app.login_username.get()) == _normalize_login_username(username):
                self.app.login_password.set("")
                clear_buyer_session_state(self.app.cookie_jar)
                self.app.cookie_jar = load_buyer_cookie_jar()
                self.app.logged_in_user = None
                self.app.deployer_auth = None
                self.app.commercial_contexts = None
                self.app.step.set(1)
                self.app.status.set("客服提示：请先登录胖虎AI账号")
            self.app.sync_webview_state()
            return {"success": True, "state": state}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def logout(self):
        last_user = self.app.login_username.get().strip()
        if last_user:
            disable_login_account_auto_login(last_user)
        clear_buyer_session_state(self.app.cookie_jar)
        self.app.cookie_jar = load_buyer_cookie_jar()
        self.app.logged_in_user = None
        self.app.deployer_auth = None
        self.app.commercial_contexts = None
        self.app.login_password.set("")
        self.app.step.set(1)
        self.app.status.set("客服提示：请先登录胖虎AI账号")
        self.app.sync_webview_state()
        return True

    def build_register_url(self, invite_code_or_url=""):
        return build_register_url(str(invite_code_or_url or ""))

    def save_key(self, payload, skip_test: bool = False):
        if isinstance(payload, dict):
            keys_in = payload.get("keys") or {}
            models_in = payload.get("models") or {}
            skip = bool(payload.get("skip_test"))
        else:
            keys_in = {"openai": str(payload or "")}
            models_in = {}
            skip = bool(skip_test)
        if not isinstance(getattr(self.app, "deploy_keys", None), dict):
            self.app.deploy_keys = {f: {"key": "", "model": ""} for f in KEY_FORMAT_IDS}
        for fmt in KEY_FORMAT_IDS:
            self.app.deploy_keys[fmt] = {
                "key": (keys_in.get(fmt) or "").strip(),
                "model": (models_in.get(fmt) or "").strip(),
            }
        self.app.api_key.set(self.app.deploy_keys["openai"]["key"])
        if self.app.deploy_keys["openai"]["model"]:
            self.app.model.set(self.app.deploy_keys["openai"]["model"])
        self.app.skip_test.set(skip)
        try:
            if not self.app.logged_in_user:
                return {"success": False, "message": "请先登录胖虎AI账号。"}
            if not self.app.deployer_auth:
                return {"success": False, "message": "请重新登录胖虎AI账号以重新获取部署授权。"}
            provided = [fmt for fmt in KEY_FORMAT_IDS if self.app.deploy_keys[fmt]["key"]]
            if not provided:
                return {"success": False, "message": "请至少填写一种格式的 API Key。"}

            self.app.status.set("状态：正在校验 API Key...")
            contexts = deployment_commercial_contexts(self.app.logged_in_user or {})
            for fmt in provided:
                verify_msg = execute_api_key_owner_verify(
                    self.app.deploy_keys[fmt]["key"], contexts, opener=trusted_urlopen, deployer_auth=self.app.deployer_auth
                )
                self.app.log(f"[{KEY_FORMAT_LABELS.get(fmt, fmt)}] {verify_msg}")

            if "openai" in provided and not skip:
                ok, msg = test_api(DEFAULT_BASE_URL, self.app.deploy_keys["openai"]["key"])
                self.app.log(f"[OpenAI 兼容格式] {msg}")
            else:
                ok, msg = True, "已保存 Key；Anthropic / Gemini 格式的连通性将在部署时按各自端点验证。"
                self.app.log(msg)

            self.app.saved_key_ok = ok
            if ok:
                self.app.saved_key_signature = self.app.current_key_signature()
                save_profile_data(
                    {
                        "api_key": self.app.deploy_keys["openai"]["key"],
                        "base_url": DEFAULT_BASE_URL,
                        "model": self.app.model.get().strip(),
                        "deploy_keys": self.app.deploy_keys,
                        "skip_test": skip,
                        "open_app": self.app.open_app.get(),
                    },
                    contexts,
                )
                self.app.status.set("状态：Key 已保存")
                self.app.step.set(2)
                self.app.sync_webview_state()
                fmt_names = "、".join(KEY_FORMAT_LABELS.get(f, f) for f in provided)
                return {"success": True, "message": f"已保存 {len(provided)} 种格式的 Key（{fmt_names}）"}
            else:
                self.app.status.set("状态：Key 测试失败")
                return {"success": False, "message": msg}
        except Exception as exc:
            self.app.status.set("状态：Key 保存失败")
            return {"success": False, "message": str(exc)}

    def run_env_check(self):
        try:
            self.app.run_environment_check()
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def start_deploy(self):
        try:
            self.app.start_deploy()
            return self._accepted("部署请求已受理，最终结果以状态和诊断日志为准。")
        except Exception as e:
            return {"success": False, "message": str(e)}

    def start_dual_state_config(self):
        try:
            self.app.start_dual_state_config()
            return self._accepted("双态配置请求已受理，最终结果以状态和诊断日志为准。")
        except Exception as e:
            return {"success": False, "message": str(e)}

    def start_official_chatgpt_config(self):
        try:
            self.app.start_official_chatgpt_config()
            return self._accepted("官方直登配置请求已受理，最终结果以状态和诊断日志为准。")
        except Exception as e:
            return {"success": False, "message": str(e)}

    def start_config_only(self):
        try:
            self.app.start_config_only()
            return self._accepted("配置任务已受理，最终结果以状态和诊断日志为准。")
        except Exception as e:
            return {"success": False, "message": str(e)}

    def restore_backups(self):
        try:
            self.app.restore_backups()
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # --- 配置健康：快照 / 一键恢复 / 漂移巡检 / 一键修复 ---

    def list_config_snapshots(self, agentId):
        try:
            return {"success": True, "snapshots": list_config_snapshots(str(agentId))}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def restore_config_snapshot(self, agentId, snapshotName):
        try:
            restore_config_snapshot(str(agentId), str(snapshotName), self.app.log)
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def restore_original_config(self, agentId):
        try:
            restore_original_config(str(agentId), self.app.log)
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def inspect_config_drift(self):
        try:
            expected_models = {agent.id: self.app.key_model_for_agent(agent.id)[1] for agent in AGENTS}
            return {"success": True, "report": inspect_all_config_drift(expected_models=expected_models)}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def repair_config_drift(self, agentId):
        try:
            api_key, model = self.app.key_model_for_agent(str(agentId))
            ok = repair_agent_config_drift(str(agentId), api_key, model, self.app.log)
            return {"success": bool(ok)}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def measure_gateway_latency(self):
        try:
            return {"success": True, "result": measure_gateway_latency()}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def get_codex_mode_status(self):
        """一键检测当前 Codex 模式，免手动翻配置文件。"""
        try:
            config_text = _read_text_safe(codex_home() / "config.toml")
            auth_text = _read_text_safe(codex_auth_path())
            mode = detect_codex_config_mode(config_text, auth_text)
            mode_labels = {
                CodexConfigMode.DIRECT_API: "普通模式（走胖虎额度）",
                CodexConfigMode.DUAL_STATE: "双态模式（保留 ChatGPT 登录态，走胖虎额度）",
                CodexConfigMode.OFFICIAL_CHATGPT: "官方直登（走你自己的 ChatGPT 账号额度）",
            }
            return {
                "success": True,
                "configured": bool(config_text or auth_text),
                "current_mode": mode.value if mode else None,
                "current_mode_label": mode_labels.get(mode, "未检测到胖虎配置" if not mode else mode.value),
                "has_chatgpt_login": has_chatgpt_auth_state(auth_text),
                "gateway_ok": ("aitokenapi.cc" in config_text) if mode in (CodexConfigMode.DIRECT_API, CodexConfigMode.DUAL_STATE) else None,
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    def open_workspace(self):
        try:
            self.app.open_workspace()
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def open_config_dir(self):
        try:
            self.app.open_config_dir()
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def copy_logs(self):
        try:
            self.app.copy_logs()
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def start_update_check(self):
        try:
            self.app.start_update_check()
            return self._accepted("更新检查已受理，最终结果以状态和诊断日志为准。")
        except Exception as e:
            return {"success": False, "message": str(e)}

    def buyer_create_order(self):
        try:
            self.app.start_buyer_create_order()
            return self._accepted("订单创建请求已受理，支付状态以服务端回填为准。")
        except Exception as e:
            return {"success": False, "message": str(e)}

    def buyer_poll_payment(self):
        try:
            self.app.start_buyer_poll_payment()
            return self._accepted("支付查询已受理，是否可交付以服务端权益回填为准。")
        except Exception as e:
            return {"success": False, "message": str(e)}

    def buyer_refresh_entitlements(self):
        try:
            self.app.start_buyer_refresh_entitlements()
            return self._accepted("权益刷新已受理，最终权益以服务端返回为准。")
        except Exception as e:
            return {"success": False, "message": str(e)}

    def buyer_create_payment_order(self):
        try:
            return self.app.create_buyer_payment_order()
        except Exception as e:
            return {"success": False, "message": str(e)}

    def buyer_query_payment_status(self, order_id=None):
        try:
            return self.app.query_buyer_payment_status(str(order_id or ""))
        except Exception as e:
            return {"success": False, "message": str(e)}

    def refresh_agent_center(self):
        try:
            self.app.start_refresh_agent_center()
            return self._accepted("代理中心刷新已受理，最终快照以服务端返回为准。")
        except Exception as e:
            return {"success": False, "message": str(e)}

    def refresh_agent_center_detail(self):
        try:
            self.app.start_refresh_agent_center_detail()
            return self._accepted("代理中心明细刷新已受理，最终明细以服务端返回为准。")
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _apply_communication_software_link_payload(self, payload=None):
        if not isinstance(payload, dict):
            return
        state_payload = payload.get("state")
        flattened = dict(payload)
        if isinstance(state_payload, dict):
            flattened.update(state_payload)
        aliases = {
            "serviceProductId": "service_product_id",
            "orderId": "order_id",
            "sessionId": "session_id",
            "agentId": "agent_id",
            "agentSource": "agent_source",
            "platformAccountId": "platform_account_id",
            "platformChatId": "platform_chat_id",
            "gatewayMode": "gateway_mode",
            "testPrompt": "test_prompt",
            "sourceEventId": "source_event_id",
            "inboundPlatformMessageId": "inbound_platform_message_id",
            "outboundPlatformMessageId": "outbound_platform_message_id",
            "agentResponseDigest": "agent_response_digest",
            "evidenceUrl": "evidence_url",
        }
        for camel_key, snake_key in aliases.items():
            if camel_key in flattened and snake_key not in flattened:
                flattened[snake_key] = flattened[camel_key]
        mapping = {
            "service_product_id": self.app.communication_software_link_service_product_id,
            "order_id": self.app.communication_software_link_order_id,
            "session_id": self.app.communication_software_link_session_id,
            "agent_id": self.app.communication_software_link_agent_id,
            "channel": self.app.communication_software_link_channel,
            "agent_source": self.app.communication_software_link_agent_source,
            "platform_account_id": self.app.communication_software_link_platform_account_id,
            "platform_chat_id": self.app.communication_software_link_platform_chat_id,
            "gateway_mode": self.app.communication_software_link_gateway_mode,
            "test_prompt": self.app.communication_software_link_test_prompt,
            "source_event_id": self.app.communication_software_link_source_event_id,
            "inbound_platform_message_id": self.app.communication_software_link_inbound_message_id,
            "outbound_platform_message_id": self.app.communication_software_link_outbound_message_id,
            "agent_response_digest": self.app.communication_software_link_response_digest,
            "evidence_url": self.app.communication_software_link_evidence_url,
        }
        for key, var in mapping.items():
            if key in flattened:
                var.set(str(flattened.get(key) or ""))

    def communication_software_link_refresh_offering(self, payload=None):
        try:
            self._apply_communication_software_link_payload(payload)
            self.app.start_communication_software_link_refresh_offering()
            return self._accepted("连接通讯软件服务商品刷新已受理，价格和上架状态以服务端返回为准。")
        except Exception as e:
            return {"success": False, "message": str(e)}

    def communication_software_link_create_order(self, payload=None):
        try:
            self._apply_communication_software_link_payload(payload)
            self.app.start_communication_software_link_create_order()
            return self._accepted("连接通讯软件订单创建已受理，支付/人工确认状态以服务端返回为准。")
        except Exception as e:
            return {"success": False, "message": str(e)}

    def communication_software_link_get_order(self, payload=None):
        try:
            self._apply_communication_software_link_payload(payload)
            self.app.start_communication_software_link_get_order()
            return self._accepted("连接通讯软件订单查询已受理，终态以服务端返回为准。")
        except Exception as e:
            return {"success": False, "message": str(e)}

    def communication_software_link_create_session(self, payload=None):
        try:
            self._apply_communication_software_link_payload(payload)
            self.app.start_communication_software_link_create_session()
            return self._accepted("连接通讯软件配置会话创建已受理，最终会话状态以服务端返回为准。")
        except Exception as e:
            return {"success": False, "message": str(e)}

    def communication_software_link_get_session(self, payload=None):
        try:
            self._apply_communication_software_link_payload(payload)
            self.app.start_communication_software_link_get_session()
            return self._accepted("连接通讯软件会话查询已受理，终态以服务端返回为准。")
        except Exception as e:
            return {"success": False, "message": str(e)}

    def communication_software_link_test(self, payload=None):
        try:
            self._apply_communication_software_link_payload(payload)
            self.app.start_communication_software_link_test()
            return self._accepted("连接通讯软件测试请求已受理，测试结果以服务端回填为准。")
        except Exception as e:
            return {"success": False, "message": str(e)}

    def communication_software_link_run_local_runtime_test(self, payload=None):
        try:
            self._apply_communication_software_link_payload(payload)
            self.app.start_communication_software_link_local_runtime_test()
            return self._accepted("连接通讯软件本地 Runtime 测试已受理，完成后只生成本地预检字段，不能替代通讯软件平台回调。")
        except Exception as e:
            return {"success": False, "message": str(e)}

    def communication_software_link_one_click_connect(self, payload=None):
        try:
            self._apply_communication_software_link_payload(payload)
            self.app.start_communication_software_link_one_click_connect()
            return self._accepted("连接通讯软件一键连接已受理：将完成订单、配置会话、测试和本地预检；不会自动提交真实验收。")
        except Exception as e:
            return {"success": False, "message": str(e)}

    def communication_software_link_acceptance(self, payload=None):
        try:
            self._apply_communication_software_link_payload(payload)
            self.app.start_communication_software_link_acceptance()
            return self._accepted("连接通讯软件验收证据提交请求已受理，最终交付以服务端真实验收记录为准。")
        except Exception as e:
            return {"success": False, "message": str(e)}

    def communication_software_link_disable(self, payload=None):
        try:
            self._apply_communication_software_link_payload(payload)
            self.app.start_communication_software_link_disable()
            return self._accepted("连接通讯软件停用请求已受理，停用终态以服务端返回为准。")
        except Exception as e:
            return {"success": False, "message": str(e)}

    def open_url(self, url):
        try:
            open_url(
                url,
                cookie_jar=self.app.cookie_jar,
                log=self.app.log,
                storage_path=self.app.current_buyer_web_profile_path(),
            )
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def go_to_step(self, idx):
        try:
            self.app.go_to_step(int(idx))
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def switch_module(self, moduleId):
        try:
            self.app.active_module.set(str(moduleId))
            self.app.sync_webview_state()
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def switch_subnav(self, itemId):
        try:
            self.app.active_subnav.set(str(itemId))
            self.app.sync_webview_state()
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def toggle_agent(self, agentId, checked):
        try:
            if agentId in self.app.agent_enabled:
                self.app.agent_enabled[agentId].set(bool(checked))
                self.app.sync_webview_state()
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def set_agent_mode(self, agentId, mode):
        try:
            if agentId in self.app.agent_mode:
                self.app.agent_mode[agentId].set(str(mode))
                self.app.sync_webview_state()
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def set_buyer_product(self, val):
        try:
            self.app.buyer_product_id.set(str(val))
            self.app.sync_webview_state()
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def set_theme(self, themeName):
        try:
            save_theme_preference(str(themeName))
            self.app.theme_name = str(themeName)
            self.app.sync_webview_state()
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}


class WebviewVar:
    """webview 模式下替代 tk.StringVar/BooleanVar/IntVar 的线程安全变量。

    真机根因（2026-07-04 登录"无反应"）：webview 模式主线程阻塞在
    webview.start()，Tk mainloop 永远不运行；此时任何 pywebview bridge
    线程或后台线程访问 Tk 变量都会抛 RuntimeError: main thread is not
    in main loop，导致 js_api 调用与登录后台线程集体无声失败。
    业务界面只允许 WebView，这些变量只承担纯数据存取与 trace 回调，
    因此改用普通线程安全对象，任何线程可读写。
    """

    def __init__(self, value=None):
        self._lock = threading.Lock()
        self._value = value
        self._traces: list = []

    def get(self):
        with self._lock:
            return self._value

    def set(self, value) -> None:
        with self._lock:
            self._value = value
            traces = list(self._traces)
        for callback in traces:
            try:
                callback("", "", "write")
            except Exception:
                pass

    def trace_add(self, mode: str, callback) -> str:
        with self._lock:
            self._traces.append(callback)
            return f"webviewtrace{len(self._traces)}"


class WebviewStringVar(WebviewVar):
    def __init__(self, value: str = ""):
        super().__init__("" if value is None else str(value))

    def get(self) -> str:
        value = super().get()
        return "" if value is None else str(value)


class WebviewBooleanVar(WebviewVar):
    def __init__(self, value: bool = False):
        super().__init__(bool(value))

    def set(self, value) -> None:
        super().set(bool(value))


class WebviewIntVar(WebviewVar):
    def __init__(self, value: int = 0):
        super().__init__(int(value))

    def set(self, value) -> None:
        super().set(int(value))


class InstallerApp:
    def __init__(self, root: tk.Tk, webview_mode: bool = False) -> None:
        if not webview_mode:
            raise RuntimeError("胖虎AI客户端正式业务界面只允许 WebView UI；旧 Tkinter 业务界面已禁止启动。")
        self.webview_mode = webview_mode
        self.root = root
        self.theme_name = load_theme_preference()
        self.webview_logs = empty_flow_logs()
        self.webview_window = None
        # 前端就绪门闩：页面加载完成并首次拉取 get_initial_state 前，禁止任何
        # evaluate_js 推送。evaluate_js 无超时；若与页面加载竞态（如启动时的
        # 会话恢复线程），会永久锁死 bridge 导致窗口"未响应"。就绪前的状态与
        # 日志都会在首次拉取时整体带给前端，不会丢失。
        self.webview_ready = False
        # 异步 JS 推送队列：所有 evaluate_js 一律经专用线程执行。
        # 直接在 pywebview js_api 回调里同步 evaluate_js 会重入死锁（save_key/
        # run_env_check 等同步 bridge 曾整窗卡死）；队列化后调用方立即返回。
        self._js_push_queue: queue.Queue = queue.Queue()
        threading.Thread(target=self._js_push_worker, daemon=True).start()

        if not getattr(self, 'webview_mode', False):
            root.title(APP_NAME)
            root.geometry("1400x900")
            root.minsize(1180, 760)
            root.configure(bg=APP_BG)
        self.ui_images: list[tk.PhotoImage] = []
        if not getattr(self, 'webview_mode', False):
            self.set_window_icon()

        self.cookie_jar = load_buyer_cookie_jar()
        self.logged_in_user: dict | None = None
        self.deployer_auth: dict | None = None
        self.deployer_manifest: dict | None = None
        self.commercial_contexts = None
        self.commercial_capabilities = {}
        self.commercial_products = []
        self.value_added_services = []
        self.commercial_entitlements: list[EntitlementContract] = []
        self.agent_center_live_data: dict = {}
        self.agent_downstreams_live_data: dict = {}
        self.agent_commissions_live_data: dict[str, dict] = {}
        self.communication_software_link_offering_data: dict = {}
        self.communication_software_link_order_statuses: dict[str, dict] = {}
        self.commercial_api = CommercialApiContract(DEFAULT_BASE_URL)
        self.last_diagnostic_code = ""
        self.saved_key_ok = False
        self.saved_key_signature: tuple[str, str, str, bool] | None = None
        self.environment_checked = False
        self.environment_ok = False
        self.worker_running = False
        self.auto_update_checked = False
        self.app_closed = False
        self.after_handles: set[str] = set()
        if not getattr(self, 'webview_mode', False):
            self.root.protocol("WM_DELETE_WINDOW", self.close_app)

        self.login_username = WebviewStringVar()
        self.login_password = WebviewStringVar()
        self.registration_invite_code = WebviewStringVar()
        self.remember_password = WebviewBooleanVar(value=True)
        self.auto_login = WebviewBooleanVar(value=False)
        self.buyer_product_id = WebviewStringVar()
        self.buyer_order_id = WebviewStringVar()
        self.communication_software_link_service_product_id = WebviewStringVar()
        self.communication_software_link_order_id = WebviewStringVar()
        self.communication_software_link_session_id = WebviewStringVar()
        self.communication_software_link_agent_id = WebviewStringVar(value="codex")
        self.communication_software_link_channel = WebviewStringVar(value="feishu")
        self.communication_software_link_agent_source = WebviewStringVar(value="existing_local_agent")
        self.communication_software_link_platform_account_id = WebviewStringVar()
        self.communication_software_link_platform_chat_id = WebviewStringVar()
        self.communication_software_link_gateway_mode = WebviewStringVar(value="official_bot")
        self.communication_software_link_test_prompt = WebviewStringVar(value=COMMUNICATION_SOFTWARE_LINK_DEFAULT_PROMPT)
        self.communication_software_link_source_event_id = WebviewStringVar()
        self.communication_software_link_inbound_message_id = WebviewStringVar()
        self.communication_software_link_outbound_message_id = WebviewStringVar()
        self.communication_software_link_response_digest = WebviewStringVar()
        self.communication_software_link_evidence_url = WebviewStringVar()
        self.login_entry_mode = WebviewStringVar(value="buyer")
        self.buyer_purchase_statuses: dict[BuyerSelfServiceNode, NodeStatus] = {}
        self.api_key = WebviewStringVar()
        self.base_url = WebviewStringVar(value=DEFAULT_BASE_URL)
        self.model = WebviewStringVar(value=DEFAULT_MODEL)
        self.deploy_keys = {fmt: {"key": "", "model": ""} for fmt in KEY_FORMAT_IDS}
        self.show_key = WebviewBooleanVar(value=False)
        self.skip_test = WebviewBooleanVar(value=False)
        self.open_app = WebviewBooleanVar(value=True)
        self.selected_system = WebviewStringVar(value=current_system_id())
        self.status = WebviewStringVar(value="客服提示：请先登录胖虎AI账号")
        self.step = WebviewIntVar(value=1)
        self.active_module = WebviewStringVar(value=MODULE_AGENT)
        self.active_subnav = WebviewStringVar(value="2")
        self.agent_enabled: dict[str, tk.BooleanVar] = {}
        self.agent_mode: dict[str, tk.StringVar] = {}
        self.agent_rows: dict[str, tk.Frame] = {}
        self.agent_checkbuttons: dict[str, tk.Checkbutton] = {}
        self.agent_badge_labels: dict[str, tk.Label] = {}
        self.agent_note_labels: dict[str, tk.Label] = {}
        for variable in (self.api_key, self.model, self.skip_test):
            variable.trace_add("write", self.mark_key_dirty)
        self.selected_system.trace_add("write", self.mark_environment_dirty)

        if getattr(self, 'webview_mode', False):
            for agent in AGENTS:
                enabled = WebviewBooleanVar(value=agent.id == "codex")
                mode = WebviewStringVar(value="cli")
                enabled.trace_add("write", self.mark_agent_selection_changed)
                mode.trace_add("write", self.mark_agent_selection_changed)
                self.agent_enabled[agent.id] = enabled
                self.agent_mode[agent.id] = mode

            def on_state_change(*_args):
                self.sync_webview_state()

            for var in (
                self.login_username, self.api_key, self.model, self.skip_test,
                self.selected_system, self.status, self.step,
                self.active_module, self.active_subnav
            ):
                var.trace_add("write", on_state_change)

        self.load_profile_into_ui()
        if not getattr(self, 'webview_mode', False):
            self._build_ui()
            self.apply_restored_login_state()
            self.start_restore_saved_session()
        else:
            self.start_restore_saved_session()
        self.log("系统提示：请先登录胖虎AI账号。登录后再填写 Key、检测环境并安装 Agent。", replace=True)

    def set_window_icon(self) -> None:
        ico = asset_path("panghu-avatar.ico")
        png = asset_path("panghu-avatar-64.png")
        try:
            if ico.exists() and platform.system() == "Windows":
                self.root.iconbitmap(str(ico))
            if png.exists():
                self.window_icon = tk.PhotoImage(file=str(png))
                self.root.iconphoto(True, self.window_icon)
        except Exception:
            self.window_icon = None

    def load_ui_image(self, name: str) -> tk.PhotoImage | None:
        path = asset_path(name)
        if not path.exists():
            return None
        try:
            image = tk.PhotoImage(file=str(path))
            self.ui_images.append(image)
            return image
        except Exception:
            return None

    def load_scaled_ui_image(self, name: str, subsample: int = 1) -> tk.PhotoImage | None:
        image = self.load_ui_image(name)
        if image is None or subsample <= 1:
            return image
        try:
            scaled = image.subsample(subsample, subsample)
            self.ui_images.append(scaled)
            return scaled
        except Exception:
            return image

    def load_profile_into_ui(self) -> None:
        profile = load_saved_profile()
        if not profile:
            return
        self.api_key.set(str(profile.get("api_key") or ""))
        self.base_url.set(DEFAULT_BASE_URL)
        self.model.set(str(profile.get("model") or DEFAULT_MODEL))
        if not isinstance(getattr(self, "deploy_keys", None), dict):
            self.deploy_keys = {fmt: {"key": "", "model": ""} for fmt in KEY_FORMAT_IDS}
        _dk = profile.get("deploy_keys")
        if isinstance(_dk, dict):
            for fmt in KEY_FORMAT_IDS:
                _e = _dk.get(fmt) or {}
                self.deploy_keys[fmt] = {"key": str(_e.get("key") or ""), "model": str(_e.get("model") or "")}
        else:
            self.deploy_keys["openai"] = {"key": str(profile.get("api_key") or ""), "model": str(profile.get("model") or "")}
        self.skip_test.set(bool(profile.get("skip_test")))
        self.open_app.set(bool(profile.get("open_app", True)))
        # Hide stale proxy/agent identities from older polluted profiles.
        user = profile.get("user")
        deployer_auth = profile.get("deployer_auth")
        if isinstance(user, dict) and (
            str(user.get("role") or "").lower() == "agent"
            or str((deployer_auth or {}).get("role") or "").lower() == "agent"
        ):
            self.login_username.set("")
            return
        self.login_username.set(str(profile.get("username") or ""))

    def sync_webview_state(self) -> None:
        if (
            not getattr(self, 'webview_mode', False)
            or not getattr(self, "webview_window", None)
            or not getattr(self, "webview_ready", False)
        ):
            return

        is_logged = self.logged_in_user is not None and self.deployer_auth is not None
        metrics = self._commercial_metric_values()
        agent_center_state = self.current_agent_center_state()

        agent_enabled = {}
        for k, v in self.agent_enabled.items():
            agent_enabled[k] = v.get()

        agent_mode = {}
        for k, v in self.agent_mode.items():
            agent_mode[k] = v.get()

        agent_matrix_state = {}
        selected_ids = {agent.id for agent, _mode in self.selected_agents()}
        executable = self.can_access_step(4)
        for agent in AGENTS:
            selected = agent.id in selected_ids
            if self.worker_running and selected and executable:
                states = {
                    "install": RUNNING,
                    "launch": RUNNING,
                    "dialogue": NEUTRAL_DOT,
                    "acceptance": NEUTRAL_DOT,
                    "delivery": NEUTRAL_DOT,
                }
            elif selected and executable:
                states = {
                    "install": RUNNING,
                    "launch": NEUTRAL_DOT,
                    "dialogue": NEUTRAL_DOT,
                    "acceptance": NEUTRAL_DOT,
                    "delivery": NEUTRAL_DOT,
                }
            elif selected:
                states = {
                    "install": NEUTRAL_DOT,
                    "launch": NEUTRAL_DOT,
                    "dialogue": NEUTRAL_DOT,
                    "acceptance": NEUTRAL_DOT,
                    "delivery": NEUTRAL_DOT,
                }
            else:
                states = {
                    "install": NEUTRAL_DOT,
                    "launch": NEUTRAL_DOT,
                    "dialogue": NEUTRAL_DOT,
                    "acceptance": NEUTRAL_DOT,
                    "delivery": NEUTRAL_DOT,
                }
            agent_matrix_state[agent.id] = {
                dim: color_to_char(color) for dim, color in states.items()
            }

        if not hasattr(self, "webview_logs"):
            self.webview_logs = empty_flow_logs()

        state_dict = {
            "isLogged": is_logged,
            "loginUsername": self.login_username.get(),
            "loginPassword": "",
            "loginPasswordSaved": bool(login_account_public_entry(self.login_username.get()).get("has_password")),
            "rememberPassword": bool(login_account_public_entry(self.login_username.get()).get("remember_password")),
            "autoLogin": bool(login_account_public_entry(self.login_username.get()).get("auto_login")),
            "restoringSession": False,
            "apiKeyValue": "",
            "apiKeyPresent": bool(self.api_key.get().strip()),
            "apiKeyMasked": mask_key(self.api_key.get().strip()) if self.api_key.get().strip() else "",
            "skipTest": self.skip_test.get(),
            "savedKeyOk": self.saved_key_ok,
            "environmentChecked": self.environment_checked,
            "environmentOk": self.environment_ok,
            "remainingUses": metrics["remaining"],
            "validUntil": metrics["valid_until"],
            "deviceLimit": metrics["device_limit"],
            "agentEnabled": agent_enabled,
            "agentMode": agent_mode,
            "agentMatrix": agent_matrix_state,
            "logs": self.webview_logs,
            "theme": getattr(self, "theme_name", "light"),
            "currentStep": self.step.get(),
            "activeSubnav": self.active_subnav.get(),
            "activeModule": self.active_module.get(),
            "loginAccounts": load_login_account_public_state().get("accounts") or [],
            "accounts": load_login_account_public_state().get("accounts") or [],
            "buyerPurchase": self.current_buyer_purchase_state(),
            "agentCenter": agent_center_state,
            "valueAddedServices": self.current_value_added_services_state(),
            "communicationSoftwareLink": self.current_communication_software_link_web_state(),
        }

        self._push_js(f"updatePythonState({json.dumps(state_dict)})")

    def apply_restored_login_state(self) -> None:
        username = self.login_username.get().strip()
        if username:
            display_username = username if len(username) <= 20 else f"{username[:17]}..."
            self.user_label.configure(text=f"上次账号：{display_username}")
            self.status.set("状态：已恢复上次账号提示，正在尝试恢复胖虎AI登录态")
        else:
            self.user_label.configure(text="账号：未登录")

    def start_restore_saved_session(self) -> None:
        if self.logged_in_user or self.deployer_auth:
            return

        saved_user = load_buyer_session_user()
        if saved_user:
            username = str(saved_user.get("username") or saved_user.get("display_name") or "").strip()
            if username:
                self.login_username.set(username)
            self.log("正在恢复保存的胖虎AI登录态，并向服务端重新申请本次部署授权")
            self.set_busy(True)
            self.status.set("状态：正在恢复保存的胖虎AI登录态...")
            threading.Thread(target=self._restore_saved_session_worker, args=(saved_user,), daemon=True).start()
            return
        
        state = load_login_account_state()
        last_username = state.get("last_username", "")
        auto_account = None
        for acc in state.get("accounts", []):
            if acc["username"] == last_username and acc.get("auto_login") and acc.get("remember_password") and acc.get("password"):
                auto_account = acc
                break
                
        if auto_account:
            username = auto_account["username"]
            password = auto_account["password"]
            self.login_username.set(username)
            self.login_password.set(password)
            self.remember_password.set(True)
            self.auto_login.set(True)
            self.log("已启用自动登录，正在通过本机加密密码记录登录胖虎AI账号")
            self.set_busy(True)
            self.status.set("状态：正在自动登录胖虎AI...")
            threading.Thread(target=self._login_worker, args=(username, password), daemon=True).start()
        else:
            clear_buyer_session_state(self.cookie_jar)
            self.cookie_jar = load_buyer_cookie_jar()

    def _restore_saved_session_worker(self, user: dict) -> None:
        # 注意：本 worker 必须在 finally 里 set_busy(False)。
        # 历史 bug：恢复成功后 worker_running 永远为 True，导致检查更新/保存 Key/
        # 部署等所有带 `if self.worker_running: return` 守卫的动作静默失效。
        try:
            auth_ok, auth_msg, auth_data = activate_deployer(user, self.cookie_jar)
            self.log_from_worker(f"恢复胖虎AI登录态：{auth_msg}")
            if not auth_ok:
                if "HTTP 401" in auth_msg or "HTTP 403" in auth_msg:
                    clear_buyer_session_state(self.cookie_jar)
                    self.cookie_jar = load_buyer_cookie_jar()
                    self.set_status_from_worker("状态：保存的胖虎AI登录态已失效，请重新登录")
                else:
                    self.set_status_from_worker("状态：暂时无法验证上次登录态，请检查网络后重试")
                return
            save_buyer_session_state(user, self.cookie_jar)
            self.logged_in_user = user
            self.deployer_auth = auth_data
            self.commercial_contexts = self.build_buyer_contexts(user)
            buyer_profile = create_commercial_web_profile(self.commercial_contexts, str(web_profile_root()))
            ensure_commercial_web_profile_dir(buyer_profile)
            display_name = str(user.get("username") or user.get("display_name") or self.login_username.get())
            save_profile_data({"username": display_name}, self.commercial_contexts)
            display_username = display_name if len(display_name) <= 20 else f"{display_name[:17]}..."

            def finish_restore() -> None:
                if hasattr(self, "user_label"):
                    self.user_label.configure(text=f"已登录：{display_username}")
                self.step.set(max(1, int(self.step.get() or 1)))
                self.status.set("状态：已恢复上次胖虎AI登录态，可继续使用")
                self.show_wizard()

            self.run_on_ui(finish_restore)
            self.run_later(1200, self.start_auto_update_check)
            self.run_later(1600, self.start_refresh_commercial_manifest)
        except Exception as exc:
            self.set_status_from_worker(f"状态：恢复登录态失败：{exc}")
        finally:
            self.run_on_ui(lambda: self.set_busy(False))

    def current_buyer_web_profile_path(self) -> Path:
        if self.commercial_contexts is not None:
            return ensure_commercial_web_profile_dir(
                create_commercial_web_profile(self.commercial_contexts, str(web_profile_root()))
            )
        return web_profile_root() / "buyer-site"

    def build_buyer_contexts(self, user: dict):
        user_id = str(user.get("id") or "").strip()
        display_name = str(user.get("username") or user.get("display_name") or user_id or "买家")
        buyer = UserContext(user_id=user_id, display_name=display_name, role="buyer")
        return create_buyer_contexts(buyer)

    def _build_ui(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        self.root.option_add("*Font", ("Microsoft YaHei UI", 10))
        style.configure(
            "TEntry",
            fieldbackground=INPUT_BG,
            foreground=INK,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            insertcolor=INK,
        )
        style.configure("TCombobox", fieldbackground=INPUT_BG, foreground=INK, bordercolor=BORDER)
        style.configure("TCheckbutton", background=CARD_BG, foreground=INK)
        style.configure("TRadiobutton", background=CARD_BG, foreground=INK)

        self.container = tk.Frame(self.root, bg=APP_BG, padx=20, pady=20)
        self.container.pack(fill="both", expand=True)
        self.container.bind("<Configure>", self._sync_surface_layouts, add="+")
        self.app_frame = tk.Frame(
            self.container,
            bg=APP_FRAME_BG,
            highlightthickness=1,
            highlightbackground=APP_FRAME_BORDER,
            bd=0,
        )
        self.app_frame.pack(fill="both", expand=True)
        self.topbar_outer = tk.Frame(self.app_frame, bg=APP_FRAME_BG)
        self.topbar_outer.pack(fill="x")
        self._build_topbar()
        self.gate_shell = tk.Frame(self.app_frame, bg=APP_FRAME_BG)
        self.gate_shell.pack(fill="both", expand=True, pady=(0, 0))
        self.gate_shell.grid_columnconfigure(0, weight=1)
        self.gate_shell.grid_rowconfigure(0, weight=1)
        self.login_gate_host = tk.Frame(self.gate_shell, bg=APP_FRAME_BG)
        self.login_gate_host.grid(row=0, column=0, sticky="nsew")
        self.gate_shell.bind("<Configure>", self._sync_gate_layout, add="+")

        self.console_outer = tk.Frame(self.app_frame, bg=APP_FRAME_BG)
        self.console_outer.pack_propagate(False)
        self.console_shell = tk.Frame(self.console_outer, bg=SURFACE_BG)
        self.console_shell.grid_columnconfigure(0, minsize=LEFT_PANEL_WIDTH)
        self.console_shell.grid_columnconfigure(1, weight=1)
        self.console_shell.grid_columnconfigure(2, minsize=RIGHT_PANEL_WIDTH)
        self.console_shell.grid_rowconfigure(0, weight=1)

        self._build_sidebar(self.console_shell)

        center_shell = tk.Frame(self.console_shell, bg=SURFACE_BG, padx=24, pady=22)
        center_shell.grid(row=0, column=1, sticky="nsew")
        center_shell.grid_rowconfigure(0, weight=1)
        center_shell.grid_columnconfigure(0, weight=1)
        self.center_shell = center_shell
        self.steps_host = tk.Frame(center_shell, bg=SURFACE_BG)
        self.steps_host.grid(row=0, column=0, sticky="nsew")
        self.module_content_host = tk.Frame(center_shell, bg=SURFACE_BG)
        self.module_content_host.grid(row=0, column=0, sticky="nsew")
        self.module_content_frames: dict[str, tk.Frame] = {}
        self._build_non_agent_module_frame(MODULE_SITE)
        self._build_non_agent_module_frame(MODULE_VALUE_ADDED)
        self._build_non_agent_module_frame(MODULE_COURSES)

        self.step_frames: dict[int, tk.Frame] = {}
        self.step_canvases: dict[int, tk.Canvas] = {}
        self.step_hint_labels: dict[int, tk.Label] = {}
        self.step_next_buttons: dict[int, tk.Button] = {}
        self._build_login_gate_frame()
        self._build_step_1()
        self._build_step_2()
        self._build_step_3()
        self._build_step_4()
        self._build_status_step(
            5,
            "第五步：写入配置",
            "检查所选 Agent 是否已写入胖虎AI网关、Key、模型和本机配置文件。",
            "配置写入由部署按钮触发。未通过功能验收矩阵前，不扣次、不算完整交付。",
        )
        self._build_status_step(
            6,
            "第六步：启动检测",
            "确认 CLI 或客户端入口可以启动，并且命令在当前系统 PATH 中可用。",
            "如果提示需要重开终端或重启客户端，请按提示处理后再复验。",
        )
        self._build_status_step(
            7,
            "第七步：最小中文对话验收",
            "对每个 Agent 执行一句中文最小对话，确认能通过胖虎AI网关返回内容。",
            "OpenClaw、Hermes 的 QQ、微信、TG 等第三方通道默认跳过，只验收直接对话链路。",
        )
        self._build_status_step(
            8,
            "第八步：功能验收矩阵",
            "打开客户可见验收矩阵，逐项确认安装、启动、对话、验收、交付状态。",
            "矩阵未全部通过时，系统必须记录失败，不扣次，不包装成完整交付。",
            button_text="打开功能验收矩阵",
            command=self.open_acceptance_matrix,
        )
        self._build_status_step(
            9,
            "第九步：基础交付验收",
            "当选定 Agent 的目标链路全部达标后，才进入客户交付收口；五个 Agent 都按同一验收矩阵门控。",
            "正式发客户前还要重新打包并完成三端包、公钥、Release、下载页授权流程。",
        )
        self._build_communication_software_link_step()
        self._build_communication_software_link_acceptance_step()
        for canvas in self.step_canvases.values():
            canvas.place(in_=self.steps_host, x=0, y=0, relwidth=1, relheight=1)

        self._build_right_panel(self.console_shell)
        self._build_execution_log()
        self.refresh_steps()
        self.show_login_gate()

    def _button(self, parent: tk.Widget, text: str, command, kind: str = "secondary") -> tk.Button:
        if kind == "primary":
            bg, fg, active = PRIMARY, "#ffffff", PRIMARY_DARK
            border_thickness = 0
        elif kind == "success":
            bg, fg, active = ACCENT, "#ffffff", "#08745b"
            border_thickness = 0
        else:
            bg, fg, active = PANEL_BG, INK, "#e0e6ed"
            border_thickness = 1
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=active,
            activeforeground=fg,
            relief="flat",
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
            font=("Microsoft YaHei UI", 9, "bold"),
            highlightthickness=border_thickness,
            highlightbackground=BORDER,
        )

    def _masked_account_label(self) -> str:
        if not self.logged_in_user:
            raw = self.login_username.get().strip()
            if not raw:
                return "未登录"
        else:
            raw = str(self.logged_in_user.get("username") or self.logged_in_user.get("display_name") or self.login_username.get() or "")
        if "@" in raw:
            left, right = raw.split("@", 1)
            safe_left = left[:2] + "***" if len(left) > 2 else "***"
            return f"{safe_left}@{right}"
        if len(raw) <= 4:
            return f"{raw[:1]}***" if raw else "未登录"
        return f"{raw[:2]}***{raw[-2:]}"

    def _agent_display_name(self, agent: AgentSpec) -> str:
        if agent.id == "claude_code":
            return "ClaudeCode（CC）"
        return agent.name

    def _commercial_metric_values(self) -> dict[str, str]:
        active = [item for item in self.commercial_entitlements if item.status == "active"]
        if active:
            total_remaining = sum(item.remaining_uses for item in active if not item.is_unlimited)
            remaining = "不限次" if any(item.is_unlimited for item in active) else f"{total_remaining}次"
            expiry_text = active[0].valid_until or "以服务端为准"
            device_count_text = str(max(item.device_limit for item in active))
        else:
            # 清单已从服务端刷新但没有活跃权益时，如实显示"无可用权益"；
            # "待刷新"只用于还没拉到服务端清单的阶段，避免误导买家一直等刷新。
            remaining = "无可用权益" if getattr(self, "deployer_manifest", None) else "待刷新"
            expiry_text = "以服务端为准"
            device_count_text = "以服务端为准"
        return {
            "account": self._masked_account_label(),
            "remaining": remaining,
            "valid_until": expiry_text,
            "device_limit": device_count_text,
            "edition": "商业版",
            "domain": DEFAULT_BASE_URL,
        }

    def _build_topbar(self) -> None:
        self.topbar_outer.pack_propagate(False)
        self.topbar_outer.configure(height=TOPBAR_HEIGHT)
        self.topbar = tk.Frame(self.topbar_outer, bg=APP_FRAME_BG, padx=16, pady=0, highlightthickness=0)
        self.topbar.pack(fill="both", expand=True)
        self.topbar.grid_columnconfigure(0, minsize=250)
        self.topbar.grid_columnconfigure(1, weight=1)
        self.topbar.grid_columnconfigure(2, minsize=340)
        self.topbar.grid_rowconfigure(0, weight=1)
        brand = tk.Frame(self.topbar, bg=APP_FRAME_BG)
        brand.grid(row=0, column=0, sticky="w")
        avatar_shell = tk.Frame(brand, bg=APP_FRAME_BG, width=28, height=28, highlightthickness=0, bd=0)
        avatar_shell.pack(side="left", padx=(0, 8), pady=(0, 0))
        avatar_shell.pack_propagate(False)
        avatar = self.load_scaled_ui_image("panghu-avatar-64.png", subsample=2)
        if avatar is not None:
            tk.Label(avatar_shell, image=avatar, bg=APP_FRAME_BG, bd=0, highlightthickness=0).pack(fill="both", expand=True)
        else:
            tk.Label(
                avatar_shell,
                text="PH",
                bg=PRIMARY,
                fg="#ffffff",
                font=("Microsoft YaHei UI", 10, "bold"),
            ).pack(fill="both", expand=True)

        title_block = tk.Frame(brand, bg=APP_FRAME_BG)
        title_block.pack(side="left")
        tk.Label(
            title_block,
            text=APP_NAME,
            bg=APP_FRAME_BG,
            fg=INK,
            font=("Microsoft YaHei UI", 10, "bold"),
            anchor="w"
        ).pack(anchor="w", pady=(0, 1))
        tk.Label(
            title_block,
            text="胖虎AI客户端商业交付平台",
            bg=APP_FRAME_BG,
            fg=MUTED,
            font=("Microsoft YaHei UI", 7),
            anchor="w"
        ).pack(anchor="w", pady=(1, 0))

        self._build_module_nav(self.topbar)

        actions = tk.Frame(self.topbar, bg=APP_FRAME_BG)
        actions.grid(row=0, column=2, sticky="e")
        actions.grid_columnconfigure(0, weight=0)
        actions.grid_columnconfigure(1, weight=0)
        actions.grid_columnconfigure(2, weight=0)
        actions.grid_columnconfigure(3, weight=0)
        self.topbar_domain_label = tk.Label(
            actions,
            text="商业交付版",
            bg=SUCCESS_BG,
            fg="#116047",
            padx=9,
            pady=2,
            font=("Microsoft YaHei UI", 8, "bold"),
        )
        self.topbar_domain_label.grid(row=0, column=0, padx=(0, 12), sticky="w")
        self.topbar_account_label = tk.Label(actions, text="账号：未登录", bg=APP_FRAME_BG, fg=INK, font=("Microsoft YaHei UI", 8, "bold"))
        self.topbar_account_label.grid(row=0, column=1, padx=(0, 14), sticky="w")
        self.topbar_remaining_label = tk.Label(actions, text="剩余次数：待刷新", bg=APP_FRAME_BG, fg=SECONDARY, font=("Microsoft YaHei UI", 8))
        self.topbar_remaining_label.grid(row=0, column=2, padx=(0, 12), sticky="w")
        self.update_button = self._button(actions, "检查更新", self.start_update_check, "secondary")
        self.update_button.grid(row=0, column=3, sticky="w")
        self.user_label = self.topbar_account_label

    def _build_module_nav(self, parent: tk.Frame) -> None:
        self.module_nav = tk.Frame(parent, bg=SEGMENTED_BG, padx=4, pady=4, width=560, height=36, highlightthickness=0)
        self.module_nav.grid(row=0, column=1, sticky="", padx=(16, 16))
        self.module_nav.grid_propagate(False)
        self.module_buttons: dict[str, tk.Frame] = {}
        self.module_button_labels: dict[str, tuple[tk.Label, tk.Label]] = {}
        for col, (module_id, title, subtitle) in enumerate(TOP_MODULES):
            self.module_nav.grid_columnconfigure(col, weight=1, uniform="top_modules")
            item = tk.Frame(
                self.module_nav,
                bg=SEGMENTED_BG,
                padx=10,
                pady=5,
                highlightthickness=0,
                cursor="hand2",
            )
            item.grid(row=0, column=col, sticky="ew")
            title_label = tk.Label(
                item,
                text=title,
                bg=SEGMENTED_BG,
                fg=SECONDARY,
                anchor="center",
                font=("Microsoft YaHei UI", 8, "bold"),
                cursor="hand2",
            )
            title_label.pack(fill="both", expand=True)
            subtitle_label = tk.Label(
                item,
                text=subtitle,
                bg=SEGMENTED_BG,
                fg=MUTED,
                anchor="center",
                font=("Microsoft YaHei UI", 7),
                cursor="hand2",
            )
            for widget in (item, title_label, subtitle_label):
                widget.bind("<Button-1>", lambda _event, value=module_id: self.switch_module(value))
            self.module_buttons[module_id] = item
            self.module_button_labels[module_id] = (title_label, subtitle_label)

    def _build_sidebar(self, parent: tk.Frame) -> None:
        sidebar = tk.Frame(parent, bg=SIDEBAR_BG, width=LEFT_PANEL_WIDTH, padx=16, pady=18, highlightthickness=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        self.sidebar = sidebar
        self.sidebar_title_label = tk.Label(sidebar, text="", bg=SIDEBAR_BG, fg=SECONDARY, font=("Microsoft YaHei UI", 9, "bold"))
        self.sidebar_title_label.pack(anchor="w")
        self.sidebar_subtitle_label = tk.Label(
            sidebar,
            text="",
            bg=SIDEBAR_BG,
            fg=MUTED,
            wraplength=184,
            justify="left",
            font=("Microsoft YaHei UI", 8),
        )
        self.sidebar_subtitle_label.pack(anchor="w", pady=(6, 14))
        self.sidebar_body = tk.Frame(sidebar, bg=SIDEBAR_BG)
        self.sidebar_body.pack(fill="both", expand=True)
        self.step_buttons: dict[int, tk.Button] = {}
        self.step_status_dots: dict[int, tk.Label] = {}
        self.module_subnav_buttons: dict[str, tk.Button] = {}
        self._render_sidebar_nav()

    def _render_sidebar_nav(self) -> None:
        body = getattr(self, "sidebar_body", None)
        if body is None:
            return
        for child in body.winfo_children():
            child.destroy()
        module_id = self.active_module.get() if hasattr(self, "active_module") else MODULE_AGENT
        module_titles = {key: title for key, title, _subtitle in TOP_MODULES}
        self.sidebar_title_label.configure(text=module_titles.get(module_id, "配置Agent"))
        self.sidebar_subtitle_label.configure(
            text="按顺序完成，一次只处理当前一步。" if module_id == MODULE_AGENT else "当前模块内导航，具体规则以服务端为准。"
        )
        self.step_buttons = {}
        self.step_status_dots = {}
        self.module_subnav_buttons = {}
        if module_id == MODULE_AGENT:
            self._render_agent_step_nav(body)
        else:
            self._render_module_subnav(body, module_id)

    def _render_agent_step_nav(self, body: tk.Frame) -> None:
        for idx, title, subtitle in FLOW_STEPS:
            row = tk.Frame(body, bg=SIDEBAR_BG)
            row.pack(fill="x", pady=(0, 5))
            dot = tk.Canvas(
                row,
                bg=WAIT_BG if "WAIT_BG" in globals() else LOCKED_BG,
                width=24,
                height=24,
                highlightthickness=0,
                bd=0,
            )
            dot.create_oval(2, 2, 22, 22, fill=WAIT_BG, outline=WAIT_BORDER, tags=("circle",))
            dot.create_text(12, 12, text=str(idx), fill=MUTED, font=("Microsoft YaHei UI", 8, "bold"), tags=("label",))
            dot.pack(side="left", padx=(0, 8), pady=(6, 0))
            btn = self._step_button(row, idx, title, subtitle)
            btn.pack(side="left", fill="x", expand=True)
            self.step_buttons[idx] = btn
            self.step_status_dots[idx] = dot
        tk.Frame(body, bg=LIGHT_BORDER, height=1).pack(fill="x", pady=(8, 12))
        self.flow_status_label = tk.Label(
            body,
            text="客服提示：请先登录胖虎AI账号。",
            bg=PRIMARY_LIGHT,
            fg=PRIMARY,
            padx=12,
            pady=10,
            wraplength=168,
            justify="left",
            anchor="nw",
            font=("Microsoft YaHei UI", 9),
            highlightthickness=1,
            highlightbackground="#d8eaff",
        )
        self.flow_status_label.pack(fill="x", anchor="w")

    def _render_module_subnav(self, body: tk.Frame, module_id: str) -> None:
        for item_id, title, subtitle in MODULE_SIDE_NAV_ITEMS.get(module_id, ()):
            btn = tk.Button(
                body,
                text=f"{title}\n{subtitle}",
                command=lambda value=item_id: self.switch_subnav(value),
                bg=SIDEBAR_BG,
                fg=SECONDARY,
                activebackground=PRIMARY_LIGHT,
                activeforeground=PRIMARY,
                relief="flat",
                bd=0,
                padx=12,
                pady=8,
                justify="left",
                anchor="w",
                cursor="hand2",
                font=("Microsoft YaHei UI", 8, "bold"),
            )
            btn.pack(fill="x", pady=(0, 5))
            self.module_subnav_buttons[item_id] = btn
        tk.Frame(body, bg=LIGHT_BORDER, height=1).pack(fill="x", pady=(8, 12))
        self.flow_status_label = tk.Label(
            body,
            text="客服提示：该模块内容以胖虎AI网站和服务端为准。",
            bg=PRIMARY_LIGHT,
            fg=PRIMARY,
            padx=12,
            pady=10,
            wraplength=168,
            justify="left",
            anchor="nw",
            font=("Microsoft YaHei UI", 9),
            highlightthickness=1,
            highlightbackground="#d5e7ff",
        )
        self.flow_status_label.pack(fill="x", anchor="w")

    def switch_module(self, module_id: str) -> None:
        if module_id not in MODULE_SIDE_NAV_ITEMS:
            return
        self.active_module.set(module_id)
        if module_id == MODULE_AGENT:
            self.active_subnav.set(str(self.step.get()))
        else:
            self.active_subnav.set(MODULE_SIDE_NAV_ITEMS[module_id][0][0])
        self._render_sidebar_nav()
        self.refresh_steps()

    def switch_subnav(self, item_id: str) -> None:
        module_id = self.active_module.get()
        if module_id == MODULE_AGENT:
            try:
                self.go_to_step(int(item_id))
            except ValueError:
                return
            return
        self.active_subnav.set(item_id)
        self.refresh_steps()

    def _build_non_agent_module_frame(self, module_id: str) -> None:
        host = self.module_content_host
        host.grid_rowconfigure(0, weight=1)
        host.grid_columnconfigure(0, weight=1)
        frame = tk.Frame(host, bg=SURFACE_BG)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        card = tk.Frame(frame, bg=CARD_BG, padx=30, pady=20, highlightthickness=1, highlightbackground=BORDER)
        card.grid(row=0, column=0, sticky="nsew")
        self.module_content_frames[module_id] = frame
        head = tk.Frame(card, bg=CARD_BG)
        head.pack(fill="x", pady=(0, 12))
        head.grid_columnconfigure(0, weight=1)
        title = tk.Label(head, text="", bg=CARD_BG, fg=INK, font=("Microsoft YaHei UI", 16, "bold"))
        title.grid(row=0, column=0, sticky="w")
        badge = tk.Label(head, text="", bg=PRIMARY_LIGHT, fg=PRIMARY, padx=9, pady=4, font=("Microsoft YaHei UI", 9, "bold"))
        badge.grid(row=0, column=1, sticky="e")
        note = tk.Label(head, text="", bg=CARD_BG, fg=MUTED, wraplength=720, justify="left", font=("Microsoft YaHei UI", 9))
        note.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        guide_box = tk.Frame(card, bg=PRIMARY_LIGHT, padx=14, pady=8, highlightthickness=1, highlightbackground="#d5e7ff")
        guide_box.pack(fill="x", pady=(0, 12))
        guide_title = tk.Label(guide_box, text="客服指引", bg=PRIMARY_LIGHT, fg=PRIMARY, font=("Microsoft YaHei UI", 10, "bold"))
        guide_title.pack(anchor="w")
        guide_lines: list[tk.Label] = []
        for _ in range(3):
            line = tk.Label(guide_box, text="", bg=PRIMARY_LIGHT, fg="#2f5e89", wraplength=720, justify="left", anchor="w", font=("Microsoft YaHei UI", 8))
            line.pack(anchor="w", fill="x", pady=(4 if not guide_lines else 2, 0))
            guide_lines.append(line)

        service_grid = tk.Frame(card, bg=CARD_BG)
        service_grid.pack(fill="x", pady=(0, 10))
        for col in range(2):
            service_grid.grid_columnconfigure(col, weight=1, uniform=f"module_{module_id}_actions")
        action_card_labels: list[tuple[tk.Label, tk.Label]] = []
        for index in range(4):
            item = tk.Frame(service_grid, bg=CARD_BG, padx=12, pady=8, highlightthickness=1, highlightbackground=BORDER)
            item.grid(row=index // 2, column=index % 2, sticky="nsew", padx=(0 if index % 2 == 0 else 14, 0), pady=(0, 10))
            item.grid_columnconfigure(0, weight=1)
            item_title = tk.Label(item, text="", bg=CARD_BG, fg=INK, anchor="w", font=("Microsoft YaHei UI", 10, "bold"))
            item_title.grid(row=0, column=0, sticky="ew")
            item_note = tk.Label(item, text="", bg=CARD_BG, fg=MUTED, wraplength=280, justify="left", anchor="w", font=("Microsoft YaHei UI", 8))
            item_note.grid(row=1, column=0, sticky="ew", pady=(3, 0))
            action_card_labels.append((item_title, item_note))

        browser_box = tk.Frame(card, bg="#f6f7f9", padx=14, pady=10, highlightthickness=1, highlightbackground=BORDER)
        browser_box.pack(fill="x", pady=(0, 10))
        browser_header = tk.Frame(browser_box, bg="#f6f7f9")
        browser_header.pack(fill="x")
        tk.Label(browser_header, text="内置网站服务区", bg="#f6f7f9", fg=INK, font=("Microsoft YaHei UI", 11, "bold")).pack(side="left")
        self._button(browser_header, "打开当前网站页面 ->", lambda: self.open_current_module_url(), "primary").pack(side="right", padx=(8, 0))
        refresh_button = self._button(browser_header, "刷新服务端数据", lambda: self.start_refresh_agent_center_detail(), "secondary")
        refresh_button.pack(side="right", padx=(8, 0))
        tk.Label(
            browser_header,
            text="服务端页面",
            bg=SUCCESS_BG,
            fg="#116047",
            padx=7,
            pady=2,
            font=("Microsoft YaHei UI", 8, "bold"),
        ).pack(side="right")
        url_label = tk.Label(browser_box, text="", bg="#f6f7f9", fg=PRIMARY, font=("Cascadia Mono", 9, "bold"))
        url_label.pack(anchor="w", pady=(6, 0))
        browser_preview = tk.Frame(browser_box, bg="#ffffff", padx=12, pady=8, highlightthickness=1, highlightbackground=LIGHT_BORDER)
        browser_preview.pack(fill="x", pady=(8, 0))
        preview_title = tk.Label(browser_preview, text="网站页面入口", bg="#ffffff", fg=INK, font=("Microsoft YaHei UI", 9, "bold"))
        preview_title.pack(anchor="w")
        preview_body = tk.Label(
            browser_preview,
            text="点击下方按钮后，优先在软件内 WebView 打开；不支持时阻断并提示内置浏览器未完成，不自动打开系统浏览器。",
            bg="#ffffff",
            fg=MUTED,
            wraplength=680,
            justify="left",
            anchor="w",
            font=("Microsoft YaHei UI", 8),
        )
        preview_body.pack(anchor="w", fill="x", pady=(4, 0))
        action_row = tk.Frame(card, bg=CARD_BG)
        action_row.pack(fill="x")
        self._button(action_row, "复制给客服的追踪记录", self.copy_logs, "secondary").pack(side="left", padx=(10, 0))
        tk.Label(
            card,
            text="打开页面时优先使用软件内 WebView；环境不支持时必须阻断并提示内置浏览器未完成，不自动打开系统浏览器。",
            bg=WARNING_BG,
            fg=PRIMARY_DARK,
            padx=10,
            pady=5,
            wraplength=620,
            justify="left",
            font=("Microsoft YaHei UI", 8),
        ).pack(fill="x", pady=(10, 0))
        frame._module_badge_label = badge  # type: ignore[attr-defined]
        frame._module_title_label = title  # type: ignore[attr-defined]
        frame._module_note_label = note  # type: ignore[attr-defined]
        frame._module_guide_lines = guide_lines  # type: ignore[attr-defined]
        frame._module_url_label = url_label  # type: ignore[attr-defined]
        frame._module_preview_title_label = preview_title  # type: ignore[attr-defined]
        frame._module_preview_body_label = preview_body  # type: ignore[attr-defined]
        frame._module_action_card_labels = action_card_labels  # type: ignore[attr-defined]
        frame._module_refresh_button = refresh_button  # type: ignore[attr-defined]
        self._sync_wraplength(note, 96, 900)

    def current_module_page_meta(self) -> tuple[str, str, str]:
        module_id = self.active_module.get()
        item_id = self.active_subnav.get()
        module_meta = MODULE_PAGE_META.get(module_id, {})
        if item_id not in module_meta and module_id in MODULE_SIDE_NAV_ITEMS:
            item_id = MODULE_SIDE_NAV_ITEMS[module_id][0][0]
            self.active_subnav.set(item_id)
        return module_meta.get(item_id, ("模块入口", DEFAULT_BASE_URL, "该模块内容以胖虎AI网站和服务端为准。"))

    def open_current_module_url(self) -> None:
        _title, url, _note = self.current_module_page_meta()
        result = open_customer_page(
            url,
            cookie_jar=self.cookie_jar,
            log=self.log,
            storage_path=self.current_buyer_web_profile_path(),
        )
        self.status.set(f"状态：{result.message}")
        self.log(f"网站页面打开结果：{result.message} URL={result.url}")

    def _show_active_module_content(self) -> None:
        if getattr(self, 'webview_mode', False):
            return
        module_id = self.active_module.get() if hasattr(self, "active_module") else MODULE_AGENT
        if module_id == MODULE_AGENT:
            self.steps_host.lift()
            return
        title, url, note = self.current_module_page_meta()
        frame = self.module_content_frames.get(module_id)
        if frame is None:
            return
        module_titles = {key: label for key, label, _subtitle in TOP_MODULES}
        getattr(frame, "_module_badge_label").configure(text=module_titles.get(module_id, "模块入口"))
        getattr(frame, "_module_title_label").configure(text=title)
        getattr(frame, "_module_note_label").configure(text=note)
        getattr(frame, "_module_url_label").configure(text=f"当前页面：{url}")
        guide_map = {
            MODULE_SITE: (
                f"现在要做什么：先在“{title}”里完成当前网站动作。",
                "做完看哪里：完成后回到左侧步骤或当前模块继续下一项。",
                "客服确认点：页面里的账号、购买、返佣和权限结果都以服务端页面为准。",
            ),
            MODULE_VALUE_ADDED: (
                f"现在要做什么：在“{title}”里确认当前增值服务是否已开放。",
                "做完看哪里：需要继续购买或咨询时，把底部日志复制给客服。",
                "客服确认点：增值业务价格、上架状态和服务范围都不在本地写死。",
            ),
            MODULE_COURSES: (
                f"现在要做什么：在“{title}”里核对代理身份、规则或代理后端入口。",
                "做完看哪里：代理相关问题统一回到右侧状态面板和网站结果一起确认。",
                "客服确认点：代理身份属于登录后权益，不再使用旧的本地代理协助入口。",
            ),
        }
        guide_lines = getattr(frame, "_module_guide_lines", [])
        for label, text in zip(guide_lines, guide_map.get(module_id, ())):
            label.configure(text=text)
        getattr(frame, "_module_preview_title_label").configure(text=f"{title} 页面入口")
        refresh_button = getattr(frame, "_module_refresh_button", None)
        if refresh_button is not None:
            refresh_button.configure(state="normal" if module_id == MODULE_COURSES and not self.worker_running else "disabled")
        preview_text = (
            f"当前主界面对应的网站目标页：{url}\n"
            "点击“打开当前网站页面”后，优先用软件内 WebView 打开；当前技术若无法内嵌，会阻断并提示内置网页闭环未完成。"
        )
        if module_id == MODULE_COURSES:
            preview_text += "\n\n" + self.agent_center_current_summary_text()
        getattr(frame, "_module_preview_body_label").configure(
            text=preview_text
        )
        action_cards = getattr(frame, "_module_action_card_labels", [])
        subnav_id = self.active_subnav.get() if hasattr(self, "active_subnav") else ""
        subnav_cards = MODULE_ACTION_CARDS.get(module_id, {}).get(subnav_id, ())
        for labels, copy in zip(action_cards, subnav_cards):
            title_label, note_label = labels
            card_title, card_note = copy
            title_label.configure(text=card_title)
            note_label.configure(text=card_note)
        self.module_content_host.lift()
        frame.lift()

    def refresh_module_nav(self) -> None:
        if getattr(self, 'webview_mode', False):
            self.sync_webview_state()
            return
        active_module = self.active_module.get() if hasattr(self, "active_module") else MODULE_AGENT
        for module_id, button in getattr(self, "module_buttons", {}).items():
            active = module_id == active_module
            bg = SEGMENTED_ACTIVE if active else SEGMENTED_BG
            fg = INK if active else SECONDARY
            sub_fg = SECONDARY if active else MUTED
            button.configure(bg=bg)
            for index, label in enumerate(getattr(self, "module_button_labels", {}).get(module_id, ())):
                label.configure(bg=bg, fg=fg if index == 0 else sub_fg)
        for item_id, button in getattr(self, "module_subnav_buttons", {}).items():
            active = item_id == self.active_subnav.get()
            button.configure(
                bg=PRIMARY_LIGHT if active else SIDEBAR_BG,
                fg=PRIMARY if active else INK,
                activebackground=PRIMARY_LIGHT,
                activeforeground=PRIMARY,
            )

    def _panel_card(self, parent: tk.Widget, title: str) -> tk.Frame:
        card = tk.Frame(parent, bg=SIDEBAR_BG, padx=18, pady=13, highlightthickness=0)
        card.pack(fill="x")
        tk.Label(card, text=title, bg=SIDEBAR_BG, fg=SECONDARY, font=("Microsoft YaHei UI", 8, "bold")).pack(anchor="w")
        return card

    def _build_right_panel(self, parent: tk.Frame) -> None:
        self.right_panel = tk.Frame(parent, bg=SIDEBAR_BG, width=RIGHT_PANEL_WIDTH, highlightthickness=0)
        self.right_panel.grid(row=0, column=2, sticky="nsew")
        self.right_panel.grid_propagate(False)

        delivery_card = self._panel_card(self.right_panel, "当前交付结论")
        self.delivery_readiness_label = tk.Label(
            delivery_card,
            text="当前状态：等待登录与权益确认",
            bg=WARNING_BG,
            fg=GOLD,
            padx=10,
            pady=6,
            font=("Microsoft YaHei UI", 8, "bold"),
            anchor="w",
            justify="left",
            wraplength=244,
            highlightthickness=1,
            highlightbackground="#feebc8",
        )
        self.delivery_readiness_label.pack(fill="x", pady=(10, 0))
        self.delivery_next_label = tk.Label(
            delivery_card,
            text="客服动作：先让客户登录，再确认账号权益。",
            bg=SIDEBAR_BG,
            fg=SECONDARY,
            font=("Microsoft YaHei UI", 8),
            justify="left",
            anchor="w",
            wraplength=244,
        )
        self.delivery_next_label.pack(fill="x", pady=(8, 0))

        commercial_card = self._panel_card(self.right_panel, "商业确认")
        self.commercial_info_labels: dict[str, tk.Label] = {}
        for label, key in (
            ("当前账号", "account"),
            ("版本标识", "edition"),
            ("剩余次数", "remaining"),
            ("有效期", "valid_until"),
            ("设备数", "device_limit"),
            ("当前公共域名", "domain"),
        ):
            row = tk.Frame(commercial_card, bg=SIDEBAR_BG)
            row.pack(fill="x", pady=(7, 0))
            tk.Label(row, text=label, bg=SIDEBAR_BG, fg=MUTED, font=("Microsoft YaHei UI", 8)).pack(side="left")
            value = tk.Label(row, text="待刷新", bg=SIDEBAR_BG, fg=INK, font=("Microsoft YaHei UI", 8, "bold"), anchor="e")
            value.pack(side="right")
            self.commercial_info_labels[key] = value

        agent_card = self._panel_card(self.right_panel, "五 Agent 五维状态")
        self.agent_matrix_labels: dict[tuple[str, str], tk.Label] = {}
        self.agent_summary_labels: dict[str, tk.Label] = {}
        header = tk.Frame(agent_card, bg=SIDEBAR_BG)
        header.pack(fill="x", pady=(10, 0))
        header.grid_columnconfigure(0, minsize=92)
        for col, label_text in enumerate(("安装", "启动", "对话", "验收", "交付"), start=1):
            header.grid_columnconfigure(col, weight=1, uniform="agent_status")
            tk.Label(header, text=label_text, bg=SIDEBAR_BG, fg=MUTED, font=("Microsoft YaHei UI", 7, "bold")).grid(
                row=0, column=col, sticky="ew"
            )
        for row_idx, agent in enumerate(AGENTS, start=1):
            row = tk.Frame(agent_card, bg=SIDEBAR_BG)
            row.pack(fill="x", pady=(7, 0))
            row.grid_columnconfigure(0, minsize=92)
            tk.Label(row, text=self._agent_display_name(agent), bg=SIDEBAR_BG, fg=INK, font=("Microsoft YaHei UI", 8, "bold")).grid(
                row=0, column=0, sticky="w"
            )
            for col, key in enumerate(("install", "launch", "dialogue", "acceptance", "delivery"), start=1):
                row.grid_columnconfigure(col, weight=1, uniform="agent_status")
                value = tk.Label(
                    row,
                    text="-",
                    bg=LOCKED_BG,
                    fg=MUTED,
                    font=("Microsoft YaHei UI", 7, "bold"),
                    anchor="center",
                    padx=2,
                    pady=3,
                    highlightthickness=1,
                    highlightbackground=WAIT_BORDER,
                )
                value.grid(row=0, column=col, sticky="ew", padx=(1, 0))
                self.agent_matrix_labels[(agent.id, key)] = value
            summary = tk.Label(row, text="", bg=SIDEBAR_BG)
            self.agent_summary_labels[agent.id] = summary

        rules_card = self._panel_card(self.right_panel, "安全审计与交付守则")
        self.rules_card = rules_card
        audit_rules = [
            "API Key 不输出到日志",
            "保留买家会话，不保存密码或部署授权 token",
            "代理中心只走登录后服务端权益",
            "所有请求走公共域名 https://aitokenapi.cc",
            "未通过功能验收矩阵不得包装成完整交付",
        ]
        for rule in audit_rules:
            r_row = tk.Frame(rules_card, bg=SIDEBAR_BG)
            r_row.pack(fill="x", pady=(6, 0))
            tk.Label(r_row, text="•", bg=SIDEBAR_BG, fg=SUCCESS, font=("Microsoft YaHei UI", 8, "bold")).pack(side="left")
            tk.Label(
                r_row,
                text=rule,
                bg=SIDEBAR_BG,
                fg=SECONDARY,
                font=("Microsoft YaHei UI", 8),
                anchor="w",
                justify="left",
                wraplength=245,
            ).pack(side="left", padx=(5, 0))

    def _build_execution_log(self) -> None:
        self.log_shell = tk.Frame(self.app_frame, bg=LOG_BG, padx=16, pady=5, highlightthickness=1, highlightbackground="#2f2f32")
        top = tk.Frame(self.log_shell, bg=LOG_BG)
        top.pack(fill="x")
        tk.Label(top, text=">_  Execution Trace Log", bg=LOG_BG, fg="#ffffff", font=("Microsoft YaHei UI", 9, "bold")).pack(side="left")
        tk.Label(top, text="● ACTIVE TRACE", bg=LOG_BG, fg="#ff4d4d", font=("Microsoft YaHei UI", 7, "bold")).pack(side="left", padx=(10, 0))
        tk.Label(top, textvariable=self.status, bg=LOG_BG, fg="#b9c0cc", font=("Microsoft YaHei UI", 8)).pack(side="right")
        self.log_box = tk.Text(
            self.log_shell,
            height=1,
            bg=LOG_BG,
            fg=LOG_FG,
            insertbackground=LOG_FG,
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=3,
            wrap="word",
            font=("Cascadia Mono", 8),
        )
        self.log_box.pack(fill="x", expand=False, pady=(3, 0))
        self.log_box.tag_configure("success", foreground="#8fd19e")
        self.log_box.tag_configure("running", foreground="#f2c66d")
        self.log_box.tag_configure("failed", foreground="#ff8a80")
        self.log_box.tag_configure("muted", foreground="#d8dee9")
        self.log_box.configure(state="disabled")

    def refresh_topbar(self) -> None:
        if getattr(self, 'webview_mode', False):
            self.sync_webview_state()
            return
        metrics = self._commercial_metric_values()
        if hasattr(self, "topbar_account_label"):
            self.topbar_account_label.configure(text=f"账号：{metrics['account']}")
        if hasattr(self, "topbar_remaining_label"):
            self.topbar_remaining_label.configure(text=f"剩余次数：{metrics['remaining']}")

    def show_login_gate(self) -> None:
        self._show_login_gate_shell()
        if hasattr(self, "step"):
            self.refresh_steps()

    def _show_login_gate_shell(self) -> None:
        if hasattr(self, "console_outer"):
            self.console_outer.pack_forget()
        if hasattr(self, "console_shell"):
            self.console_shell.pack_forget()
        if hasattr(self, "log_shell"):
            self.log_shell.pack_forget()
        if hasattr(self, "gate_shell"):
            self.gate_shell.pack(fill="both", expand=True, padx=0, pady=0)
            self._sync_gate_layout()
        self._sync_surface_layouts()
        if hasattr(self, "topbar_remaining_label"):
            self._hide_managed_widget(self.topbar_remaining_label)
        if hasattr(self, "update_button"):
            self._hide_managed_widget(self.update_button)
        if hasattr(self, "topbar_domain_label"):
            self._hide_managed_widget(self.topbar_domain_label)
        if hasattr(self, "module_nav"):
            self._hide_managed_widget(self.module_nav)
        if hasattr(self, "topbar_account_label") and not self.logged_in_user:
            self.topbar_account_label.configure(text="账号：未登录")

    def show_wizard(self) -> None:
        if hasattr(self, "step") and getattr(self, "logged_in_user", None) and getattr(self, "deployer_auth", None):
            try:
                self.step.set(max(1, int(self.step.get())))
            except Exception:
                self.step.set(1)
        self._show_wizard_shell()
        if hasattr(self, "step"):
            self.refresh_steps()

    def _show_wizard_shell(self) -> None:
        if hasattr(self, "gate_shell"):
            self.gate_shell.pack_forget()
        if hasattr(self, "log_shell"):
            self.log_shell.pack(side="bottom", fill="x", padx=0, pady=0)
        if hasattr(self, "console_outer"):
            self.console_outer.pack(fill="both", expand=True, padx=0, pady=0)
        if hasattr(self, "console_shell") and hasattr(self.console_shell, "pack"):
            self.console_shell.pack(fill="both", expand=True)
        if hasattr(self, "topbar_domain_label") and not self.topbar_domain_label.winfo_ismapped():
            self._show_topbar_action_widget(self.topbar_domain_label)
        if hasattr(self, "topbar_remaining_label") and not self.topbar_remaining_label.winfo_ismapped():
            self._show_topbar_action_widget(self.topbar_remaining_label)
        if hasattr(self, "update_button") and not self.update_button.winfo_ismapped():
            self._show_topbar_action_widget(self.update_button)
        if hasattr(self, "module_nav") and not self.module_nav.winfo_ismapped():
            self.module_nav.grid(row=0, column=1, sticky="", padx=(16, 16))
        self._sync_surface_layouts()

    def _hide_managed_widget(self, widget: tk.Widget) -> None:
        if hasattr(widget, "grid_remove"):
            widget.grid_remove()
        elif hasattr(widget, "pack_forget"):
            widget.pack_forget()

    def _show_topbar_action_widget(self, widget: tk.Widget) -> None:
        if hasattr(widget, "grid"):
            widget.grid()
        elif hasattr(widget, "pack"):
            widget.pack(side="left")

    def _sync_gate_layout(self, _event=None) -> None:
        return

    def _surface_target_width(self, available_width: int) -> int:
        if available_width >= 1440:
            return 1400
        return max(available_width, 1180)

    def _sync_surface_layouts(self, _event=None) -> None:
        if not hasattr(self, "container") or not hasattr(self.container, "winfo_width"):
            return
        available_width = self.container.winfo_width()
        if available_width <= 1:
            return
        target_width = min(available_width, self._surface_target_width(available_width))
        side_pad = max(0, (available_width - target_width) // 2)
        app_frame = getattr(self, "app_frame", None)
        if app_frame is not None and hasattr(app_frame, "pack_configure"):
            app_frame.pack_configure(padx=side_pad)

    def _sync_console_outer_layout(self, _event=None) -> None:
        if not hasattr(self, "console_outer") or not hasattr(self, "console_shell"):
            return
        return

    def refresh_commercial_info_panel(self) -> None:
        if getattr(self, 'webview_mode', False):
            self.sync_webview_state()
            return
        metrics = self._commercial_metric_values()
        for key, value in metrics.items():
            label = getattr(self, "commercial_info_labels", {}).get(key)
            if label:
                label.configure(text=value)
        readiness_label = getattr(self, "delivery_readiness_label", None)
        if readiness_label:
            if not self.logged_in_user or not self.deployer_auth:
                text, bg, fg, next_text = "当前状态：等待登录", INFO_BG, PRIMARY_DARK, "客服动作：先让客户登录，再确认账号权益。"
            elif not self.has_valid_key():
                text, bg, fg, next_text = "当前状态：待填写并测试 Key", WARNING_BG, PRIMARY_DARK, "客服动作：指导客户创建或粘贴 Key，然后点击保存并测试。"
            elif not self.environment_ok:
                text, bg, fg, next_text = "当前状态：待检测环境", WARNING_BG, PRIMARY_DARK, "客服动作：先跑环境检测，排除风险工具和命令缺失。"
            elif not self.agents_ready():
                text, bg, fg, next_text = "当前状态：待选择交付 Agent", WARNING_BG, PRIMARY_DARK, "客服动作：确认本次要交付的 Agent，再进入安装。"
            else:
                text, bg, fg, next_text = "当前状态：可继续安装与验收", SUCCESS_BG, "#116047", "客服动作：继续执行安装、启动检查和最小中文对话验收。"
            readiness_label.configure(text=text, bg=bg, fg=fg)
            next_label = getattr(self, "delivery_next_label", None)
            if next_label:
                next_label.configure(text=next_text, bg=GOLD_SOFT if bg != SUCCESS_BG else SUCCESS_BG, fg="#34594d" if bg == SUCCESS_BG else MUTED)

    def _matrix_badge(self, text: str, color: str) -> tuple[str, str]:
        return text, color

    def refresh_agent_matrix_panel(self) -> None:
        if getattr(self, 'webview_mode', False):
            self.sync_webview_state()
            return
        selected_ids = {agent.id for agent, _mode in self.selected_agents()}
        executable = self.can_access_step(4)
        for agent in AGENTS:
            selected = agent.id in selected_ids
            if self.worker_running and selected and executable:
                states = {
                    "install": self._matrix_badge("进行中", RUNNING),
                    "launch": self._matrix_badge("进行中", RUNNING),
                    "dialogue": self._matrix_badge("待验收", NEUTRAL_DOT),
                    "acceptance": self._matrix_badge("待矩阵", NEUTRAL_DOT),
                    "delivery": self._matrix_badge("未交付", NEUTRAL_DOT),
                }
            elif selected and executable:
                states = {
                    "install": self._matrix_badge("待执行", RUNNING),
                    "launch": self._matrix_badge("待检测", NEUTRAL_DOT),
                    "dialogue": self._matrix_badge("待验收", NEUTRAL_DOT),
                    "acceptance": self._matrix_badge("待矩阵", NEUTRAL_DOT),
                    "delivery": self._matrix_badge("未交付", NEUTRAL_DOT),
                }
            elif selected:
                states = {
                    "install": self._matrix_badge("已选择", NEUTRAL_DOT),
                    "launch": self._matrix_badge("未开始", NEUTRAL_DOT),
                    "dialogue": self._matrix_badge("未开始", NEUTRAL_DOT),
                    "acceptance": self._matrix_badge("未开始", NEUTRAL_DOT),
                    "delivery": self._matrix_badge("未交付", NEUTRAL_DOT),
                }
            else:
                states = {
                    "install": self._matrix_badge("未开始", NEUTRAL_DOT),
                    "launch": self._matrix_badge("未开始", NEUTRAL_DOT),
                    "dialogue": self._matrix_badge("未开始", NEUTRAL_DOT),
                    "acceptance": self._matrix_badge("未开始", NEUTRAL_DOT),
                    "delivery": self._matrix_badge("未交付", NEUTRAL_DOT),
                }
            for key, (text, color) in states.items():
                label = getattr(self, "agent_matrix_labels", {}).get((agent.id, key))
                if label:
                    if color == SUCCESS:
                        bg = SUCCESS_BG
                    elif color == RUNNING:
                        bg = GOLD_SOFT
                    elif color == FAIL:
                        bg = FAIL_BG
                    else:
                        bg = "#eef2f7"
                    label.configure(text=text, fg=color, bg=bg)
            summary_label = getattr(self, "agent_summary_labels", {}).get(agent.id)
            if summary_label:
                compact = {
                    "安装": states["install"][0].replace("● ", ""),
                    "启动": states["launch"][0].replace("● ", ""),
                    "对话": states["dialogue"][0].replace("● ", ""),
                    "验收": states["acceptance"][0].replace("● ", ""),
                    "交付": states["delivery"][0].replace("● ", ""),
                }
                summary_label.configure(
                    text=" / ".join(f"{key}:{value}" for key, value in compact.items()),
                    fg=states["install"][1] if selected else MUTED,
                )

    def _log_tag_for_message(self, message: str) -> str:
        failed_words = ("失败", "错误", "异常", "未通过", "阻止", "风险", "FAIL", "ERROR")
        success_words = ("成功", "通过", "已完成", "已保存", "PASS", "OK")
        running_words = ("正在", "开始", "检测", "部署", "写入", "初始化", "刷新", "验证")
        upper_message = message.upper()
        if any(word in message or word in upper_message for word in failed_words):
            return "failed"
        if any(word in message or word in upper_message for word in success_words):
            return "success"
        if any(word in message for word in running_words):
            return "running"
        return "muted"

    def _show_help(self, title: str, message: str) -> None:
        self.notify_info(title, message)

    def _grid_button(
        self,
        parent: tk.Widget,
        text: str,
        command,
        kind: str,
        row: int,
        column: int,
        columnspan: int = 1,
    ) -> tk.Button:
        button = self._button(parent, text, command, kind)
        button.grid(row=row, column=column, columnspan=columnspan, sticky="ew", padx=(0, 8), pady=(0, 10))
        return button

    def _text_button(self, parent: tk.Widget, text: str, command) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=CARD_BG,
            fg=PRIMARY,
            activebackground=INFO_BG,
            activeforeground=PRIMARY_DARK,
            relief="flat",
            bd=0,
            padx=8,
            pady=2,
            cursor="hand2",
            font=("Microsoft YaHei UI", 9, "bold"),
        )

    def _notice_strip(
        self,
        parent: tk.Widget,
        title: str,
        body: str,
        tone: str = "info",
        button_text: str | None = None,
        command=None,
        compact: bool = False,
    ) -> tk.Frame:
        palette = {
            "info": (INFO_BG, PRIMARY_DARK, MUTED, BORDER),
            "success": (SUCCESS_BG, "#1f6b55", "#34594d", "#c6e8d3"),
            "warning": (WARNING_BG, "#9a4b18", "#71411c", "#f1c995"),
        }
        bg, title_fg, body_fg, border = palette.get(tone, palette["info"])
        box = tk.Frame(parent, bg=bg, padx=10 if compact else 12, pady=6 if compact else 9, highlightthickness=1, highlightbackground=border)
        box.pack(fill="x")
        header = tk.Frame(box, bg=bg)
        header.pack(fill="x")
        header.grid_columnconfigure(0, weight=1)
        tk.Label(
            header,
            text=title,
            bg=bg,
            fg=title_fg,
            font=("Microsoft YaHei UI", 9 if compact else 10, "bold"),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            header,
            text=body,
            bg=bg,
            fg=body_fg,
            wraplength=420 if compact else 520,
            justify="left",
            anchor="w",
            font=("Microsoft YaHei UI", 9 if compact else 10),
        ).grid(row=1 if compact else 0, column=0 if compact else 1, sticky="ew", padx=(0 if compact else 10, 8), pady=(2 if compact else 0, 0))
        if button_text and command:
            tk.Button(
                header,
                text=button_text,
                command=command,
                bg=bg,
                fg=PRIMARY,
                activebackground=bg,
                activeforeground=PRIMARY_DARK,
                relief="flat",
                bd=0,
                padx=6 if compact else 8,
                pady=0,
                cursor="hand2",
                font=("Microsoft YaHei UI", 9, "bold"),
            ).grid(row=0, column=1 if compact else 2, sticky="ne")
        return box

    def _sync_wraplength(self, label: tk.Label, padding: int = 60, max_width: int = 360) -> None:
        def update(event) -> None:
            label.configure(wraplength=min(max_width, max(260, event.width - padding)))

        label.master.bind("<Configure>", update, add="+")

    def _build_commercial_entry_cards(self, parent: tk.Frame) -> None:
        self.login_mode_summary_label = tk.Label(
            parent,
            text="所有客户先统一登录胖虎AI账号。代理身份、邀请码、充值购买和 API Key 创建，登录后在胖虎AI网站模块处理。",
            bg=CARD_BG,
            fg=MUTED,
            font=("Microsoft YaHei UI", 9),
            justify="left",
            anchor="w",
            wraplength=620,
        )
        self.login_mode_summary_label.pack(fill="x", pady=(0, 10))

    def refresh_login_entry_mode(self) -> None:
        if getattr(self, 'webview_mode', False):
            self.sync_webview_state()
            return
        if hasattr(self, "login_entry_mode"):
            self.login_entry_mode.set("buyer")
        if hasattr(self, "login_mode_summary_label"):
            self.login_mode_summary_label.configure(
                text="所有客户先统一登录胖虎AI账号。代理身份、邀请码、充值购买和 API Key 创建，登录后在胖虎AI网站模块处理。"
            )
        if hasattr(self, "buyer_login_panel"):
            self.buyer_login_panel.pack(fill="x")

    def focus_buyer_login(self) -> None:
        if hasattr(self, "login_entry_mode"):
            self.login_entry_mode.set("buyer")
        self.refresh_login_entry_mode()
        if hasattr(self, "base_url"):
            self.base_url.set(DEFAULT_BASE_URL)
        if hasattr(self, "status"):
            self.status.set("状态：买家路径已就绪，请先登录胖虎AI账号。")
        self.login_username_entry.focus_set()

    def show_agent_center_placeholder(self) -> None:
        self.notify_info(
            "代理中心",
            self.agent_center_current_summary_text(),
        )

    def agent_center_current_summary_text(self) -> str:
        current = self.current_agent_center_state()
        if current:
            return agent_center_summary_text({"agent_center": current})
        return agent_center_summary_text(self.deployer_manifest)

    def current_agent_center_state(self) -> dict:
        live_data = getattr(self, "agent_center_live_data", {})
        if isinstance(live_data, dict) and live_data:
            return parse_agent_center_snapshot_data(live_data)
        manifest = getattr(self, "deployer_manifest", {})
        if isinstance(manifest, dict):
            center = manifest.get("agent_center") or manifest.get("center")
            if isinstance(center, dict):
                return parse_agent_center_snapshot_data(center)
        return {}

    def current_value_added_services_state(self) -> list[dict]:
        services = getattr(self, "value_added_services", []) or []
        result: list[dict] = []
        for service in services:
            result.append(
                {
                    "service_id": service.service_id,
                    "title": service.title,
                    "target_project": service.target_project,
                    "status": service.status,
                    "entry_url": service.entry_url,
                    "purchase_url": service.purchase_url,
                    "entitlement_status": service.entitlement_status,
                    "requires_webview_session": service.requires_webview_session,
                    "summary_url": service.summary_url,
                    "unverified_reason": service.unverified_reason,
                    "is_available": service.is_available,
                }
            )
        return result

    def current_buyer_purchase_state(self) -> dict:
        statuses = getattr(self, "buyer_purchase_statuses", {})
        entitlements = getattr(self, "commercial_entitlements", [])
        return {
            "productId": self._safe_var_value("buyer_product_id"),
            "orderId": self._safe_var_value("buyer_order_id"),
            "nodes": {node.value: status.value for node, status in statuses.items()},
            "entitlementCount": len(entitlements),
            "activeEntitlementCount": len([item for item in entitlements if item.status == "active"]),
        }

    def _safe_var_value(self, attr: str) -> str:
        value = getattr(self, attr, None)
        if value is None:
            return ""
        getter = getattr(value, "get", None)
        if callable(getter):
            return str(getter() or "")
        return str(value or "")

    def current_communication_software_link_web_state(self) -> dict:
        return {
            "offering": getattr(self, "communication_software_link_offering_data", {}) or {},
            "serviceProductId": self._safe_var_value("communication_software_link_service_product_id"),
            "orderId": self._safe_var_value("communication_software_link_order_id"),
            "sessionId": self._safe_var_value("communication_software_link_session_id"),
            "agentId": self._safe_var_value("communication_software_link_agent_id"),
            "channel": self._safe_var_value("communication_software_link_channel"),
            "agentSource": self._safe_var_value("communication_software_link_agent_source"),
            "platformAccountId": self._safe_var_value("communication_software_link_platform_account_id"),
            "platformChatId": self._safe_var_value("communication_software_link_platform_chat_id"),
            "gatewayMode": self._safe_var_value("communication_software_link_gateway_mode"),
            "testPrompt": self._safe_var_value("communication_software_link_test_prompt"),
            "state": self.current_communication_software_link_state(),
        }

    def current_communication_software_link_state(self) -> dict:
        order_id = self._safe_var_value("communication_software_link_order_id").strip()
        session_id = self._safe_var_value("communication_software_link_session_id").strip()
        statuses = getattr(self, "communication_software_link_order_statuses", {})
        order_status = statuses.get(order_id, {}) if order_id else {}
        delivery_boundary = (
            "连接通讯软件最终交付必须以服务端真实验收记录为准；"
            "本地字段或离线/mock 守卫不能单独证明真实平台回调、Agent Runtime Adapter、支付和账本闭环。"
        )
        return {
            "order": order_status,
            "sessionId": session_id,
            "sourceEventId": self._safe_var_value("communication_software_link_source_event_id"),
            "inboundPlatformMessageId": self._safe_var_value("communication_software_link_inbound_message_id"),
            "outboundPlatformMessageId": self._safe_var_value("communication_software_link_outbound_message_id"),
            "agentResponseDigest": self._safe_var_value("communication_software_link_response_digest"),
            "evidenceUrl": self._safe_var_value("communication_software_link_evidence_url"),
            "realServiceStatus": str(order_status.get("real_service_status") or "server_required"),
            "platformCallbackStatus": str(order_status.get("platform_callback_status") or ""),
            "runtimeAdapterStatus": str(order_status.get("runtime_adapter_status") or ""),
            "acceptanceStatus": str(order_status.get("acceptance_status") or ""),
            "charged": order_status.get("charged") is True,
            "clientMayClaimDeliveryComplete": order_status.get("client_may_claim_delivery_complete") is True,
            "deliveryBoundary": delivery_boundary,
        }

    def _ensure_commercial_contexts(self) -> bool:
        if self.commercial_contexts is None or self.deployer_auth is None:
            self.notify_warning("请先登录", "请先登录胖虎AI买家账号，并获取本次运行的服务端授权。")
            return False
        return True

    def start_refresh_agent_center(self) -> None:
        if self.worker_running:
            return
        if not self._ensure_commercial_contexts():
            return
        request = commercial_api_request_with_auth(
            "agent_center",
            self.commercial_contexts,
            deployer_auth=self.deployer_auth,
        )
        self.set_busy(True)
        threading.Thread(target=self._agent_center_request_worker, args=("agent_home", request), daemon=True).start()

    def start_refresh_agent_center_detail(self) -> None:
        if self.worker_running:
            return
        if not self._ensure_commercial_contexts():
            return
        item_id = self.active_subnav.get()
        commission_types = {
            "agent_token_comm": "token_usage_settled",
            "agent_activation_comm": "activation_paid",
            "agent_install_comm": "agent_install_delivered",
        }
        if item_id == "agent_customers":
            request = commercial_api_request_with_auth(
                "agent_downstreams",
                self.commercial_contexts,
                deployer_auth=self.deployer_auth,
            )
        elif item_id in commission_types:
            request = commercial_api_request_with_auth(
                "agent_commissions",
                self.commercial_contexts,
                deployer_auth=self.deployer_auth,
                event_type=commission_types[item_id],
            )
        else:
            request = commercial_api_request_with_auth(
                "agent_center",
                self.commercial_contexts,
                deployer_auth=self.deployer_auth,
            )
        self.set_busy(True)
        threading.Thread(target=self._agent_center_request_worker, args=(item_id, request), daemon=True).start()

    def _agent_center_request_worker(self, item_id: str, request) -> None:
        try:
            data, summary = execute_commercial_api_with_trusted_certs(request)
            self.log_from_worker(summary)
            if item_id == "agent_customers":
                self.agent_downstreams_live_data = data
                count = len(data.get("items") or data.get("downstreams") or data.get("customers") or [])
                self.set_status_from_worker(f"状态：下游客户数据已刷新，服务端返回 {count} 条")
            elif item_id in {"agent_token_comm", "agent_activation_comm", "agent_install_comm"}:
                self.agent_commissions_live_data[item_id] = data
                count = len(data.get("items") or data.get("commissions") or data.get("ledger") or [])
                self.set_status_from_worker(f"状态：代理佣金数据已刷新，服务端返回 {count} 条")
            else:
                center = data.get("agent_center") or data.get("center") or data
                self.agent_center_live_data = parse_agent_center_snapshot_data(center) if isinstance(center, dict) else {}
                self.set_status_from_worker("状态：代理中心服务端数据已刷新")
            self.run_on_ui(self.refresh_steps)
        except Exception as exc:
            self.log_from_worker(f"代理中心服务端刷新失败：{exc}")
            self.show_error_from_worker("代理中心刷新失败", str(exc))
        finally:
            self.run_on_ui(lambda: self.set_busy(False))

    def _find_communication_software_link_service_product_id(self, data: dict) -> str:
        candidates = []
        for key in ("products", "items", "offerings"):
            values = data.get(key)
            if isinstance(values, list):
                candidates.extend(values)
        for item in candidates:
            if not isinstance(item, dict):
                continue
            service_type = str(item.get("service_type") or item.get("type") or "")
            status = str(item.get("status") or "").lower()
            if service_type == "communication_software_link" and status in {"listed", "active", "available", ""}:
                return str(item.get("product_id") or item.get("id") or "")
        return str(data.get("service_product_id") or data.get("product_id") or "")

    def start_communication_software_link_refresh_offering(self) -> None:
        if self.worker_running:
            return
        if not self._ensure_commercial_contexts():
            return
        request = commercial_api_request_with_auth(
            "communication_software_link_offering",
            self.commercial_contexts,
            deployer_auth=self.deployer_auth,
        )
        self.set_busy(True)
        threading.Thread(target=self._communication_software_link_offering_worker, args=(request,), daemon=True).start()

    def _communication_software_link_offering_worker(self, request) -> None:
        try:
            data, summary = execute_commercial_api_with_trusted_certs(request)
            self.log_from_worker(summary)
            self.communication_software_link_offering_data = data
            product_id = self._find_communication_software_link_service_product_id(data)
            if product_id and not self.communication_software_link_service_product_id.get().strip():
                self.run_on_ui(lambda: self.communication_software_link_service_product_id.set(product_id))
            self.set_status_from_worker("状态：连接通讯软件服务商品已从服务端刷新")
            self.run_on_ui(self.refresh_steps)
            self.run_on_ui(self.sync_webview_state)
        except Exception as exc:
            self.log_from_worker(f"连接通讯软件服务商品刷新失败：{exc}")
            self.show_error_from_worker("连接通讯软件刷新失败", str(exc))
        finally:
            self.run_on_ui(lambda: self.set_busy(False))

    def current_communication_software_link_offering_text(self) -> str:
        data = self.communication_software_link_offering_data or {}
        if not data:
            return "登录并刷新服务端后，这里会显示连接通讯软件服务商品。价格、通道和上架状态以服务端返回为准。"
        product_id = self._find_communication_software_link_service_product_id(data)
        list_count = 0
        for key in ("products", "items", "offerings"):
            values = data.get(key)
            if isinstance(values, list):
                list_count += len(values)
        parts = ["服务端已返回连接通讯软件商品信息。"]
        if product_id:
            parts.append(f"当前服务商品 ID：{mask_key(product_id)}")
        if list_count:
            parts.append(f"候选商品条数：{list_count}")
        parts.append("具体价格、次数、有效期、上架状态和通道范围不在本地硬编码。")
        return " ".join(parts)

    def refresh_communication_software_link_panel(self) -> None:
        label = getattr(self, "communication_software_link_service_summary_label", None)
        if label:
            label.configure(text=self.current_communication_software_link_offering_text())

    def _communication_software_link_common_kwargs(self) -> dict[str, str]:
        return {
            "agent_id": self.communication_software_link_agent_id.get().strip(),
            "channel": self.communication_software_link_channel.get().strip(),
            "agent_source": self.communication_software_link_agent_source.get().strip(),
        }

    def start_communication_software_link_create_order(self) -> None:
        if self.worker_running:
            return
        if not self._ensure_commercial_contexts():
            return
        service_product_id = self.communication_software_link_service_product_id.get().strip()
        if not service_product_id:
            self.notify_warning("缺少商品", "请先刷新或填写服务端返回的连接通讯软件服务商品 ID。")
            return
        request = commercial_api_request_with_auth(
            "communication_software_link_order_create",
            self.commercial_contexts,
            deployer_auth=self.deployer_auth,
            service_product_id=service_product_id,
            **self._communication_software_link_common_kwargs(),
        )
        self.set_busy(True)
        threading.Thread(target=self._communication_software_link_create_order_worker, args=(request,), daemon=True).start()

    def _communication_software_link_create_order_worker(self, request) -> None:
        try:
            data, summary = execute_commercial_api_with_trusted_certs(request)
            self.log_from_worker(summary)
            order_id = str(data.get("order_id") or data.get("service_order_id") or data.get("id") or "").strip()
            if not order_id:
                raise ValueError("创建连接通讯软件订单返回缺少订单 ID。")
            order_status = parse_communication_software_link_order_status_data(data)
            self.communication_software_link_order_statuses[order_id] = order_status
            self.run_on_ui(lambda: self.communication_software_link_order_id.set(order_id))
            self.set_status_from_worker("状态：连接通讯软件订单创建请求已受理，支付/人工确认状态以服务端返回为准")
            self.run_on_ui(self.sync_webview_state)
            self.show_info_from_worker("连接通讯软件订单创建请求已受理", build_customer_payment_instruction(data))
        except Exception as exc:
            self.log_from_worker(f"连接通讯软件订单创建失败：{exc}")
            self.show_error_from_worker("连接通讯软件订单创建失败", str(exc))
        finally:
            self.run_on_ui(lambda: self.set_busy(False))

    def start_communication_software_link_get_order(self) -> None:
        if self.worker_running:
            return
        if not self._ensure_commercial_contexts():
            return
        order_id = self.communication_software_link_order_id.get().strip()
        if not order_id:
            self.notify_warning("缺少订单", "请先创建或填写连接通讯软件订单 ID。")
            return
        request = commercial_api_request_with_auth(
            "communication_software_link_order_get",
            self.commercial_contexts,
            deployer_auth=self.deployer_auth,
            order_id=order_id,
        )
        self.set_busy(True)
        threading.Thread(target=self._communication_software_link_get_order_worker, args=(request,), daemon=True).start()

    def _communication_software_link_get_order_worker(self, request) -> None:
        try:
            data, summary = execute_commercial_api_with_trusted_certs(request)
            self.log_from_worker(summary)
            order_status = parse_communication_software_link_order_status_data(data)
            self.communication_software_link_order_statuses[order_status["order_id"]] = order_status
            self.set_status_from_worker("状态：连接通讯软件订单状态已刷新")
            self.run_on_ui(self.refresh_steps)
        except Exception as exc:
            self.log_from_worker(f"连接通讯软件订单查询失败：{exc}")
            self.show_error_from_worker("连接通讯软件订单查询失败", str(exc))
        finally:
            self.run_on_ui(lambda: self.set_busy(False))

    def start_communication_software_link_create_session(self) -> None:
        if self.worker_running:
            return
        if not self._ensure_commercial_contexts():
            return
        order_id = self.communication_software_link_order_id.get().strip()
        if not order_id:
            self.notify_warning("缺少订单", "请先创建或填写连接通讯软件订单 ID。")
            return
        order_status = self.communication_software_link_order_statuses.get(order_id)
        if not order_status or not order_status.get("session_allowed"):
            self.notify_warning(
                "订单未确认",
                "请先查询连接通讯软件订单状态；订单必须已支付，或服务端明确进入人工预售/人工复核后，才能创建配置会话。",
            )
            return
        request = commercial_api_request_with_auth(
            "communication_software_link_session_create",
            self.commercial_contexts,
            deployer_auth=self.deployer_auth,
            order_id=order_id,
            platform_account_id=self.communication_software_link_platform_account_id.get().strip(),
            platform_chat_id=self.communication_software_link_platform_chat_id.get().strip(),
            gateway_mode=self.communication_software_link_gateway_mode.get().strip(),
            **self._communication_software_link_common_kwargs(),
        )
        self.set_busy(True)
        threading.Thread(target=self._communication_software_link_create_session_worker, args=(request,), daemon=True).start()

    def _apply_communication_software_link_state_fields(self, fields: dict[str, str]) -> None:
        order_id = str(fields.get("order_id") or "").strip()
        session_id = str(fields.get("session_id") or "").strip()
        status = str(fields.get("status") or "").strip()
        var_updates = {
            "communication_software_link_order_id": order_id,
            "communication_software_link_session_id": session_id,
            "communication_software_link_source_event_id": str(fields.get("source_event_id") or "").strip(),
            "communication_software_link_inbound_message_id": str(fields.get("inbound_platform_message_id") or "").strip(),
            "communication_software_link_outbound_message_id": str(fields.get("outbound_platform_message_id") or "").strip(),
            "communication_software_link_response_digest": str(fields.get("agent_response_digest") or "").strip(),
            "communication_software_link_evidence_url": str(fields.get("evidence_url") or "").strip(),
        }
        for attr, value in var_updates.items():
            if value:
                getattr(self, attr).set(value)
        if order_id:
            order_status = dict(self.communication_software_link_order_statuses.get(order_id, {}))
            order_status["order_id"] = order_id
            if session_id:
                order_status["session_id"] = session_id
            if status:
                order_status["communication_software_link_status"] = status
            for key in (
                "real_service_status",
                "platform_callback_status",
                "runtime_adapter_status",
                "acceptance_status",
            ):
                value = str(fields.get(key) or "").strip()
                if value:
                    order_status[key] = value
            if "client_may_claim_delivery_complete" in fields:
                order_status["client_may_claim_delivery_complete"] = fields.get("client_may_claim_delivery_complete") is True
            # charged 一旦为真保持为真（幂等），避免后续刷新未带该字段时被清回 false。
            if fields.get("charged") is True:
                order_status["charged"] = True
            self.communication_software_link_order_statuses[order_id] = order_status

    def _communication_software_link_create_session_worker(self, request) -> None:
        try:
            data, summary = execute_commercial_api_with_trusted_certs(request)
            self.log_from_worker(summary)
            fields = parse_communication_software_link_state_fields(data)
            if not fields["session_id"]:
                raise ValueError("创建连接通讯软件配置会话返回缺少会话 ID。")
            self.run_on_ui(lambda: self._apply_communication_software_link_state_fields(fields))
            self.set_status_from_worker("状态：连接通讯软件配置会话创建请求已受理，最终会话状态以服务端返回为准")
            self.run_on_ui(self.refresh_steps)
            self.run_on_ui(self.sync_webview_state)
        except Exception as exc:
            self.log_from_worker(f"连接通讯软件会话创建失败：{exc}")
            self.show_error_from_worker("连接通讯软件会话创建失败", str(exc))
        finally:
            self.run_on_ui(lambda: self.set_busy(False))

    def start_communication_software_link_get_session(self) -> None:
        if self.worker_running:
            return
        if not self._ensure_commercial_contexts():
            return
        session_id = self.communication_software_link_session_id.get().strip()
        if not session_id:
            self.notify_warning("缺少会话", "请先创建或填写连接通讯软件配置会话 ID。")
            return
        request = commercial_api_request_with_auth(
            "communication_software_link_session_get",
            self.commercial_contexts,
            deployer_auth=self.deployer_auth,
            session_id=session_id,
        )
        self.set_busy(True)
        threading.Thread(target=self._communication_software_link_generic_worker, args=("会话状态已刷新", request), daemon=True).start()

    def start_communication_software_link_test(self) -> None:
        if self.worker_running:
            return
        if not self._ensure_commercial_contexts():
            return
        session_id = self.communication_software_link_session_id.get().strip()
        test_prompt = self.communication_software_link_test_prompt.get().strip() or COMMUNICATION_SOFTWARE_LINK_DEFAULT_PROMPT
        if not session_id:
            self.notify_warning("缺少会话", "请先创建或填写连接通讯软件配置会话 ID。")
            return
        request = commercial_api_request_with_auth(
            "communication_software_link_session_test",
            self.commercial_contexts,
            deployer_auth=self.deployer_auth,
            session_id=session_id,
            test_prompt=test_prompt,
        )
        self.set_busy(True)
        threading.Thread(target=self._communication_software_link_generic_worker, args=("测试请求已提交", request), daemon=True).start()

    def start_communication_software_link_local_runtime_test(self) -> None:
        if self.worker_running:
            return
        if not self._ensure_commercial_contexts():
            return
        session_id = self.communication_software_link_session_id.get().strip()
        order_id = self.communication_software_link_order_id.get().strip()
        agent_id = self.communication_software_link_agent_id.get().strip()
        if not session_id:
            self.notify_warning("缺少会话", "请先创建或填写连接通讯软件配置会话 ID。")
            return
        if not order_id:
            self.notify_warning("缺少订单", "请先创建或填写连接通讯软件订单 ID。")
            return
        if not agent_id:
            self.notify_warning("缺少 Agent", "请选择要接入通讯软件的 Agent。")
            return
        self.set_busy(True)
        threading.Thread(target=self._communication_software_link_local_runtime_worker, daemon=True).start()

    def _run_local_communication_software_link_runtime_probe(self, agent_id: str) -> str:
        agent = next((item for item in AGENTS if item.id == agent_id), None)
        if agent is None:
            raise ValueError(f"未知 Agent：{agent_id}")
        mode_var = getattr(self, "agent_mode", {}).get(agent_id)
        mode_id = mode_var.get() if mode_var is not None else "cli"
        if not agent_mode_uses_cli_probe(mode_id):
            ok, output = verify_agent_client_scope(agent, mode_id)
        else:
            model_var = getattr(self, "model", None)
            model = model_var.get().strip() if model_var is not None else DEFAULT_MODEL
            ok, output = run_agent_dialogue_probe(agent, mode_id, model or DEFAULT_MODEL)
        if not ok:
            raise RuntimeError(output or f"{agent.name} 本地 Runtime 测试未通过。")
        return output

    def _communication_software_link_local_runtime_worker(self) -> None:
        try:
            agent_id = self.communication_software_link_agent_id.get().strip()
            output = self._run_local_communication_software_link_runtime_probe(agent_id)
            evidence = build_local_communication_software_link_acceptance_evidence(
                session_id=self.communication_software_link_session_id.get().strip(),
                order_id=self.communication_software_link_order_id.get().strip(),
                agent_id=agent_id,
                channel=self.communication_software_link_channel.get().strip(),
                platform_chat_id=self.communication_software_link_platform_chat_id.get().strip(),
                test_prompt=self.communication_software_link_test_prompt.get().strip() or COMMUNICATION_SOFTWARE_LINK_DEFAULT_PROMPT,
                agent_response=output,
            )
            self.run_on_ui(lambda: self._apply_communication_software_link_state_fields(evidence))
            self.log_from_worker("连接通讯软件本地 Runtime 测试通过；已生成入站、Agent 响应摘要、出站和 source_event_id 验收字段。")
            self.set_status_from_worker("状态：连接通讯软件本地 Runtime 测试通过，等待真实平台回调与服务端验收记录")
            self.run_on_ui(self.refresh_steps)
            self.run_on_ui(self.sync_webview_state)
        except Exception as exc:
            self.log_from_worker(f"连接通讯软件本地 Runtime 测试失败：{exc}")
            self.show_error_from_worker("连接通讯软件本地 Runtime 测试失败", str(exc))
        finally:
            self.run_on_ui(lambda: self.set_busy(False))

    def start_communication_software_link_one_click_connect(self) -> None:
        if self.worker_running:
            return
        if not self._ensure_commercial_contexts():
            return
        self.set_busy(True)
        threading.Thread(target=self._communication_software_link_one_click_connect_worker, daemon=True).start()

    def _communication_software_link_one_click_connect_worker(self) -> None:
        try:
            result = self.run_communication_software_link_one_click_connect()
            self.log_from_worker(
                "连接通讯软件一键连接已完成本地预检；"
                f"订单={result.get('order_id') or '-'}，会话={result.get('session_id') or '-'}，"
                "本地预检不能替代通讯软件平台回调，最终交付仍以服务端真实验收记录为准。"
            )
            self.set_status_from_worker("状态：连接通讯软件本地预检通过，等待真实平台消息与服务端验收")
            self.run_on_ui(self.refresh_steps)
            self.run_on_ui(self.sync_webview_state)
        except Exception as exc:
            self.log_from_worker(f"连接通讯软件一键连接失败：{exc}")
            self.show_error_from_worker("连接通讯软件一键连接失败", str(exc))
        finally:
            self.run_on_ui(lambda: self.set_busy(False))

    def run_communication_software_link_one_click_connect(self) -> dict[str, str]:
        if self.commercial_contexts is None or self.deployer_auth is None:
            raise RuntimeError("请先登录胖虎AI买家账号，并获取本次运行的服务端授权。")
        service_product_id = self.communication_software_link_service_product_id.get().strip()
        order_id = self.communication_software_link_order_id.get().strip()
        session_id = self.communication_software_link_session_id.get().strip()
        agent_id = self.communication_software_link_agent_id.get().strip()
        channel = self.communication_software_link_channel.get().strip()
        agent_source = self.communication_software_link_agent_source.get().strip()
        platform_account_id = self.communication_software_link_platform_account_id.get().strip()
        platform_chat_id = self.communication_software_link_platform_chat_id.get().strip()
        gateway_mode = self.communication_software_link_gateway_mode.get().strip()
        test_prompt = self.communication_software_link_test_prompt.get().strip() or COMMUNICATION_SOFTWARE_LINK_DEFAULT_PROMPT

        missing = []
        if not agent_id:
            missing.append("Agent")
        if not channel:
            missing.append("通讯通道")
        if not agent_source:
            missing.append("Agent 来源")
        if not gateway_mode:
            missing.append("网关模式")
        if not order_id and not service_product_id:
            missing.append("服务商品 ID 或订单 ID")
        if missing:
            raise ValueError("连接通讯软件一键连接缺少：" + "、".join(missing))

        if not order_id:
            order_request = commercial_api_request_with_auth(
                "communication_software_link_order_create",
                self.commercial_contexts,
                deployer_auth=self.deployer_auth,
                service_product_id=service_product_id,
                agent_id=agent_id,
                channel=channel,
                agent_source=agent_source,
            )
            order_data, summary = execute_commercial_api_with_trusted_certs(order_request)
            self.log_from_worker(summary)
            order_id = str(order_data.get("order_id") or order_data.get("service_order_id") or order_data.get("id") or "").strip()
            if not order_id:
                raise ValueError("创建连接通讯软件订单返回缺少订单 ID。")
            order_status = parse_communication_software_link_order_status_data(order_data)
            self.communication_software_link_order_statuses[order_id] = order_status
            self.run_on_ui(lambda: self.communication_software_link_order_id.set(order_id))
        else:
            status = self.communication_software_link_order_statuses.get(order_id)
            if status is None:
                order_request = commercial_api_request_with_auth(
                    "communication_software_link_order_get",
                    self.commercial_contexts,
                    deployer_auth=self.deployer_auth,
                    order_id=order_id,
                )
                order_data, summary = execute_commercial_api_with_trusted_certs(order_request)
                self.log_from_worker(summary)
                status = parse_communication_software_link_order_status_data(order_data)
                self.communication_software_link_order_statuses[order_id] = status
            order_status = status

        if not order_status.get("session_allowed"):
            raise RuntimeError("连接通讯软件订单尚未支付或未进入服务端人工复核，不能创建配置会话。")

        if not platform_account_id or not platform_chat_id:
            platform_fields = self.resolve_communication_software_link_platform_authorization(
                order_id=order_id,
                agent_id=agent_id,
                channel=channel,
                gateway_mode=gateway_mode,
                platform_chat_hint=platform_chat_id,
            )
            platform_account_id = platform_fields["platform_account_id"]
            platform_chat_id = platform_fields["platform_chat_id"]
            gateway_mode = platform_fields.get("gateway_mode") or gateway_mode

        if not session_id:
            session_request = commercial_api_request_with_auth(
                "communication_software_link_session_create",
                self.commercial_contexts,
                deployer_auth=self.deployer_auth,
                order_id=order_id,
                agent_id=agent_id,
                channel=channel,
                platform_account_id=platform_account_id,
                platform_chat_id=platform_chat_id,
                gateway_mode=gateway_mode,
                agent_source=agent_source,
            )
            session_data, summary = execute_commercial_api_with_trusted_certs(session_request)
            self.log_from_worker(summary)
            fields = parse_communication_software_link_state_fields(session_data)
            session_id = fields["session_id"]
            if not session_id:
                raise ValueError("创建连接通讯软件配置会话返回缺少会话 ID。")
            self.run_on_ui(lambda: self._apply_communication_software_link_state_fields(fields))
        else:
            self.run_on_ui(lambda: self.communication_software_link_session_id.set(session_id))

        test_request = commercial_api_request_with_auth(
            "communication_software_link_session_test",
            self.commercial_contexts,
            deployer_auth=self.deployer_auth,
            session_id=session_id,
            test_prompt=test_prompt,
        )
        test_data, summary = execute_commercial_api_with_trusted_certs(test_request)
        self.log_from_worker(summary)
        self.run_on_ui(lambda: self._apply_communication_software_link_state_fields(parse_communication_software_link_state_fields(test_data)))

        agent_response = self._run_local_communication_software_link_runtime_probe(agent_id)
        evidence = build_local_communication_software_link_acceptance_evidence(
            session_id=session_id,
            order_id=order_id,
            agent_id=agent_id,
            channel=channel,
            platform_chat_id=platform_chat_id,
            test_prompt=test_prompt,
            agent_response=agent_response,
        )
        self.run_on_ui(lambda: self._apply_communication_software_link_state_fields(evidence))

        return {
            "status": "local_runtime_precheck_passed",
            "order_id": order_id,
            "session_id": session_id,
            "source_event_id": evidence["source_event_id"],
            "evidence_url": evidence["evidence_url"],
            "client_may_claim_delivery_complete": False,
        }

    def open_communication_software_link_platform_auth_url(self, url: str) -> None:
        open_url(
            url,
            cookie_jar=getattr(self, "cookie_jar", None),
            log=getattr(self, "log", None),
            storage_path=self.current_buyer_web_profile_path() if hasattr(self, "current_buyer_web_profile_path") else None,
        )

    def resolve_communication_software_link_platform_authorization(
        self,
        order_id: str,
        agent_id: str,
        channel: str,
        gateway_mode: str,
        platform_chat_hint: str = "",
    ) -> dict[str, str]:
        create_request = commercial_api_request_with_auth(
            "communication_software_link_platform_auth_create",
            self.commercial_contexts,
            deployer_auth=self.deployer_auth,
            order_id=order_id,
            agent_id=agent_id,
            channel=channel,
            gateway_mode=gateway_mode,
            platform_chat_hint=platform_chat_hint,
        )
        data, summary = execute_commercial_api_with_trusted_certs(create_request)
        self.log_from_worker(summary)
        auth_session_id = str(data.get("auth_session_id") or data.get("platform_auth_session_id") or data.get("id") or "").strip()
        authorization_url = str(data.get("authorization_url") or data.get("qr_code_url") or data.get("url") or "").strip()
        if not auth_session_id:
            raise ValueError("连接通讯软件平台授权返回缺少授权会话 ID。")
        if authorization_url:
            self.run_on_ui(lambda: self.open_communication_software_link_platform_auth_url(authorization_url))
            self.log_from_worker("已打开连接通讯软件平台授权页，请买家在手机或通讯软件中完成扫码/确认。")
        max_polls = max(1, int(COMMUNICATION_SOFTWARE_LINK_PLATFORM_AUTH_MAX_POLLS))
        poll_seconds = max(0, int(COMMUNICATION_SOFTWARE_LINK_PLATFORM_AUTH_POLL_SECONDS))
        for attempt in range(max_polls):
            get_request = commercial_api_request_with_auth(
                "communication_software_link_platform_auth_get",
                self.commercial_contexts,
                deployer_auth=self.deployer_auth,
                auth_session_id=auth_session_id,
            )
            status_data, summary = execute_commercial_api_with_trusted_certs(get_request)
            self.log_from_worker(summary)
            status = str(status_data.get("status") or "").strip().lower()
            platform_account_id = str(status_data.get("platform_account_id") or "").strip()
            platform_chat_id = str(status_data.get("platform_chat_id") or "").strip()
            resolved_gateway_mode = str(status_data.get("gateway_mode") or gateway_mode or "").strip()
            if status in {"authorized", "connected", "completed", "success"} and platform_account_id and platform_chat_id:
                self.run_on_ui(lambda: self.communication_software_link_platform_account_id.set(platform_account_id))
                self.run_on_ui(lambda: self.communication_software_link_platform_chat_id.set(platform_chat_id))
                if resolved_gateway_mode:
                    self.run_on_ui(lambda: self.communication_software_link_gateway_mode.set(resolved_gateway_mode))
                return {
                    "platform_account_id": platform_account_id,
                    "platform_chat_id": platform_chat_id,
                    "gateway_mode": resolved_gateway_mode,
                }
            if status in {"failed", "cancelled", "canceled", "expired", "rejected"}:
                raise RuntimeError(f"连接通讯软件平台授权未完成：{status}")
            if attempt < max_polls - 1 and poll_seconds:
                self.log_from_worker(f"平台授权等待中（{attempt + 1}/{max_polls}）：请在手机或通讯软件中完成扫码/授权。")
                time.sleep(poll_seconds)
        raise RuntimeError("连接通讯软件平台授权超时，请确认手机或通讯软件已完成扫码/授权后重试。")

    def start_communication_software_link_acceptance(self) -> None:
        if self.worker_running:
            return
        if not self._ensure_commercial_contexts():
            return
        required = {
            "配置会话 ID": self.communication_software_link_session_id.get().strip(),
            "源事件 ID": self.communication_software_link_source_event_id.get().strip(),
            "入站消息 ID": self.communication_software_link_inbound_message_id.get().strip(),
            "出站消息 ID": self.communication_software_link_outbound_message_id.get().strip(),
            "响应摘要": self.communication_software_link_response_digest.get().strip(),
            "证据 URL": self.communication_software_link_evidence_url.get().strip(),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            self.notify_warning(
                "缺少验收证据",
                "这些字段由服务端在真实平台消息回调后自动回填，通常无需手填。"
                "请先点“从服务端刷新验收字段”拉取；若仍缺少：" + "、".join(missing),
            )
            return
        request = commercial_api_request_with_auth(
            "communication_software_link_session_acceptance",
            self.commercial_contexts,
            deployer_auth=self.deployer_auth,
            session_id=required["配置会话 ID"],
            source_event_id=required["源事件 ID"],
            inbound_platform_message_id=required["入站消息 ID"],
            outbound_platform_message_id=required["出站消息 ID"],
            test_prompt=self.communication_software_link_test_prompt.get().strip() or COMMUNICATION_SOFTWARE_LINK_DEFAULT_PROMPT,
            agent_response_digest=required["响应摘要"],
            evidence_url=required["证据 URL"],
        )
        self.set_busy(True)
        threading.Thread(
            target=self._communication_software_link_generic_worker,
            args=("验收证据提交请求已受理，等待服务端真实验收", request),
            daemon=True,
        ).start()

    def start_communication_software_link_disable(self) -> None:
        if self.worker_running:
            return
        if not self._ensure_commercial_contexts():
            return
        session_id = self.communication_software_link_session_id.get().strip()
        if not session_id:
            self.notify_warning("缺少会话", "请先填写要停用的连接通讯软件配置会话 ID。")
            return
        request = commercial_api_request_with_auth(
            "communication_software_link_session_disable",
            self.commercial_contexts,
            deployer_auth=self.deployer_auth,
            session_id=session_id,
        )
        self.set_busy(True)
        threading.Thread(target=self._communication_software_link_generic_worker, args=("会话停用请求已提交", request), daemon=True).start()

    def _communication_software_link_generic_worker(self, success_status: str, request) -> None:
        try:
            data, summary = execute_commercial_api_with_trusted_certs(request)
            self.log_from_worker(summary)
            keys = sorted(str(key) for key in data.keys()) if isinstance(data, dict) else []
            key_text = "、".join(keys[:8]) if keys else "无结构化字段"
            self.log_from_worker(f"连接通讯软件服务端返回字段：{key_text}")
            fields = parse_communication_software_link_state_fields(data)
            self.run_on_ui(lambda: self._apply_communication_software_link_state_fields(fields))
            if success_status == "验收证据已提交":
                success_status = "验收证据提交请求已受理，等待服务端真实验收"
            self.set_status_from_worker(f"状态：连接通讯软件{success_status}")
            self.run_on_ui(self.refresh_steps)
            self.run_on_ui(self.sync_webview_state)
        except Exception as exc:
            self.log_from_worker(f"连接通讯软件请求失败：{exc}")
            self.show_error_from_worker("连接通讯软件请求失败", str(exc))
        finally:
            self.run_on_ui(lambda: self.set_busy(False))

    def create_buyer_payment_order(self) -> dict:
        """WebView 同步下单：创建订单并把支付宝支付链接生成二维码返回给前端。

        与线程版 start_buyer_create_order 走同一套服务端约定（order_create），
        但同步返回 payment_url + 本地生成的二维码 data URL，供前端弹窗扫码付款。
        """
        if self.worker_running:
            return {"success": False, "message": "有任务正在执行，请稍候再试。"}
        if self.commercial_contexts is None:
            return {"success": False, "message": "请先登录胖虎AI买家账号，再在软件内购买权益。"}
        product_id = self.buyer_product_id.get().strip()
        if not product_id:
            return {"success": False, "message": "请先选择或填写服务端返回的商品 ID。"}
        product_snapshot = next(
            (p for p in self.commercial_products if p.product_id == product_id),
            None,
        )
        if product_snapshot is None:
            return {"success": False, "message": "该商品未在服务端商品清单中上架。请刷新授权清单后重试。"}
        product = find_orderable_product(
            self.commercial_products,
            product_id=product_id,
            agent_id=product_snapshot.agent_id,
            mode_key=product_snapshot.mode_key,
            app_version=APP_VERSION,
            buyer_user_id=self.commercial_contexts.target_buyer.user_id,
        )
        if product is None:
            return {"success": False, "message": "该商品未在服务端商品清单中上架，或不满足当前交付条件（版本/权限/上架状态）。请刷新授权清单后重试。"}
        request = commercial_api_request_with_auth(
            "order_create",
            self.commercial_contexts,
            product_id=product_id,
        )
        data, summary = execute_commercial_api_with_trusted_certs(request)
        self.log_from_worker(summary)
        order_id = str(data.get("order_id") or data.get("id") or "").strip()
        if not order_id:
            return {"success": False, "message": "创建订单返回缺少订单 ID。"}
        payment_url = str(data.get("payment_url") or data.get("pay_url") or data.get("checkout_url") or "").strip()
        if not payment_url:
            return {"success": False, "message": "服务端未返回支付链接，无法生成支付二维码。请联系后台确认订单支付入口。"}
        try:
            qr_data_url = build_payment_qr_data_url(payment_url)
        except Exception as exc:
            self.log_from_worker(f"支付二维码生成失败：{exc}")
            qr_data_url = ""
        self.buyer_order_id.set(order_id)
        self.buyer_purchase_statuses[BuyerSelfServiceNode.ORDER_PAYMENT] = NodeStatus.NEEDS_MANUAL
        self.run_on_ui(self.refresh_buyer_purchase_status)
        self.run_on_ui(self.sync_webview_state)
        return {
            "success": True,
            "order_id": order_id,
            "payment_url": payment_url,
            "qr_data_url": qr_data_url,
            "message": "订单已创建，请用手机支付宝扫码付款，付款后点“查询支付结果”。",
        }

    def query_buyer_payment_status(self, order_id: str = "") -> dict:
        """WebView 同步查询支付状态；可交付判定沿用 parse_payment_status_data。"""
        if self.commercial_contexts is None:
            return {"success": False, "message": "请先登录胖虎AI买家账号。"}
        order_id = str(order_id or "").strip() or self.buyer_order_id.get().strip()
        if not order_id:
            return {"success": False, "message": "缺少订单 ID，请先创建订单。"}
        request = commercial_api_request_with_auth("payment_poll", self.commercial_contexts, order_id=order_id)
        data, summary = execute_commercial_api_with_trusted_certs(request)
        self.log_from_worker(summary)
        payment = parse_payment_status_data(data)
        ready = bool(payment["ready_for_delivery"])
        needs_review = bool(payment["requires_manual_review"])
        if ready:
            self.buyer_purchase_statuses[BuyerSelfServiceNode.ORDER_PAYMENT] = NodeStatus.PASS
            self.buyer_purchase_statuses[BuyerSelfServiceNode.ENTITLEMENT_REFRESH] = NodeStatus.NEEDS_MANUAL
        self.run_on_ui(self.refresh_buyer_purchase_status)
        self.run_on_ui(self.sync_webview_state)
        return {
            "success": True,
            "order_id": payment["order_id"],
            "payment_status": payment["payment_status"],
            "entitlement_id": payment["entitlement_id"],
            "entitlement_status": payment["entitlement_status"],
            "ready_for_delivery": ready,
            "requires_manual_review": needs_review,
            "message": (
                "支付已确认，权益已到账。" if ready
                else ("支付已确认但权益尚未生效，请稍候再查询。" if needs_review else "支付尚未完成，请扫码付款后再查询。")
            ),
        }

    def start_buyer_create_order(self) -> None:
        if self.worker_running:
            return
        if self.commercial_contexts is None:
            self.notify_warning("请先登录", "请先登录胖虎AI买家账号，再在软件内购买权益。")
            return
        product_id = self.buyer_product_id.get().strip()
        if not product_id:
            self.notify_warning("缺少商品", "请选择或填写服务端返回的商品 ID。")
            return
        product_snapshot = next(
            (p for p in self.commercial_products if p.product_id == product_id),
            None,
        )
        if product_snapshot is None:
            self.notify_warning("商品不匹配", "该商品未在服务端商品清单中上架。请刷新授权清单后重试。")
            return
        product = find_orderable_product(
            self.commercial_products,
            product_id=product_id,
            agent_id=product_snapshot.agent_id,
            mode_key=product_snapshot.mode_key,
            app_version=APP_VERSION,
            buyer_user_id=self.commercial_contexts.target_buyer.user_id,
        )
        if product is None:
            self.notify_warning("商品不匹配", "该商品未在服务端商品清单中上架，或不满足当前交付条件（版本/权限/上架状态）。请刷新授权清单后重试。")
            return
        request = commercial_api_request_with_auth(
            "order_create",
            self.commercial_contexts,
            product_id=product_id,
        )
        self.buyer_purchase_statuses[BuyerSelfServiceNode.ORDER_PAYMENT] = NodeStatus.RUNNING
        self.refresh_buyer_purchase_status()
        self.set_busy(True)
        threading.Thread(target=self._buyer_create_order_worker, args=(request,), daemon=True).start()

    def _buyer_create_order_worker(self, request) -> None:
        try:
            data, summary = execute_commercial_api_with_trusted_certs(request)
            self.log_from_worker(summary)
            order_id = str(data.get("order_id") or data.get("id") or "").strip()
            if not order_id:
                raise ValueError("创建订单返回缺少订单 ID。")
            self.run_on_ui(lambda: self.buyer_order_id.set(order_id))
            self.buyer_purchase_statuses[BuyerSelfServiceNode.ORDER_PAYMENT] = NodeStatus.NEEDS_MANUAL
            self.set_status_from_worker("状态：订单已创建，请完成支付后查询支付状态")
            self.run_on_ui(self.refresh_buyer_purchase_status)
            self.run_on_ui(self.sync_webview_state)
            self.show_info_from_worker("订单已创建", build_customer_payment_instruction(data))
        except Exception as exc:
            self.buyer_purchase_statuses[BuyerSelfServiceNode.ORDER_PAYMENT] = NodeStatus.FAILED
            self.run_on_ui(self.refresh_buyer_purchase_status)
            self.log_from_worker(f"买家创建订单失败：{exc}")
            self.show_error_from_worker("创建订单失败", str(exc))
        finally:
            self.run_on_ui(lambda: self.set_busy(False))

    def start_buyer_poll_payment(self) -> None:
        if self.worker_running:
            return
        if self.commercial_contexts is None:
            self.notify_warning("请先登录", "请先登录胖虎AI买家账号。")
            return
        order_id = self.buyer_order_id.get().strip()
        if not order_id:
            self.notify_warning("缺少订单", "请先创建订单或填写订单 ID。")
            return
        request = commercial_api_request_with_auth("payment_poll", self.commercial_contexts, order_id=order_id)
        self.set_busy(True)
        threading.Thread(target=self._buyer_poll_payment_worker, args=(request,), daemon=True).start()

    def _buyer_poll_payment_worker(self, request) -> None:
        try:
            data, summary = execute_commercial_api_with_trusted_certs(request)
            self.log_from_worker(summary)
            payment = parse_payment_status_data(data)
            status = str(payment["payment_status"]).lower()
            if payment["ready_for_delivery"]:
                self.buyer_purchase_statuses[BuyerSelfServiceNode.ORDER_PAYMENT] = NodeStatus.PASS
                self.buyer_purchase_statuses[BuyerSelfServiceNode.ENTITLEMENT_REFRESH] = NodeStatus.NEEDS_MANUAL
                self.set_status_from_worker("状态：支付已确认，请刷新权益")
            elif payment["requires_manual_review"]:
                self.buyer_purchase_statuses[BuyerSelfServiceNode.ORDER_PAYMENT] = NodeStatus.NEEDS_MANUAL
                self.set_status_from_worker("状态：支付已确认但权益尚未生效，请等待后台处理后再刷新权益")
            elif status in {"success", "completed"}:
                self.buyer_purchase_statuses[BuyerSelfServiceNode.ORDER_PAYMENT] = NodeStatus.NEEDS_MANUAL
                self.set_status_from_worker("状态：支付状态已返回，但服务端未返回可用权益，请刷新权益或联系后台确认")
            else:
                self.buyer_purchase_statuses[BuyerSelfServiceNode.ORDER_PAYMENT] = NodeStatus.NEEDS_MANUAL
                self.set_status_from_worker("状态：支付尚未完成或需人工确认")
            self.run_on_ui(self.refresh_buyer_purchase_status)
            self.run_on_ui(self.sync_webview_state)
        except Exception as exc:
            self.buyer_purchase_statuses[BuyerSelfServiceNode.ORDER_PAYMENT] = NodeStatus.FAILED
            self.run_on_ui(self.refresh_buyer_purchase_status)
            self.log_from_worker(f"买家查询支付状态失败：{exc}")
            self.show_error_from_worker("查询支付状态失败", str(exc))
        finally:
            self.run_on_ui(lambda: self.set_busy(False))

    def start_buyer_refresh_entitlements(self) -> None:
        if self.worker_running:
            return
        if self.commercial_contexts is None:
            self.notify_warning("请先登录", "请先登录胖虎AI买家账号。")
            return
        request = commercial_api_request_with_auth("entitlement_query", self.commercial_contexts)
        self.buyer_purchase_statuses[BuyerSelfServiceNode.ENTITLEMENT_REFRESH] = NodeStatus.RUNNING
        self.refresh_buyer_purchase_status()
        self.set_busy(True)
        threading.Thread(target=self._buyer_refresh_entitlements_worker, args=(request,), daemon=True).start()

    def _buyer_refresh_entitlements_worker(self, request) -> None:
        try:
            data, summary = execute_commercial_api_with_trusted_certs(request)
            self.log_from_worker(summary)
            manifest = {"entitlements": data.get("entitlements") or []}
            self.commercial_entitlements = manifest_commercial_entitlements(manifest)
            self.buyer_purchase_statuses[BuyerSelfServiceNode.ENTITLEMENT_REFRESH] = NodeStatus.PASS
            self.set_status_from_worker("状态：权益已刷新，可以继续创建 Key 或安装配置")
            self.run_on_ui(self.refresh_steps)
            self.run_on_ui(self.refresh_buyer_purchase_status)
            self.run_on_ui(self.sync_webview_state)
        except Exception as exc:
            self.buyer_purchase_statuses[BuyerSelfServiceNode.ENTITLEMENT_REFRESH] = NodeStatus.FAILED
            self.run_on_ui(self.refresh_buyer_purchase_status)
            self.log_from_worker(f"买家刷新权益失败：{exc}")
            self.show_error_from_worker("刷新权益失败", str(exc))
        finally:
            self.run_on_ui(lambda: self.set_busy(False))

    def refresh_customer_purchase_products(self) -> None:
        if getattr(self, 'webview_mode', False):
            self.sync_webview_state()
            return
        label = getattr(self, "agent_product_summary_label", None)
        if not label:
            return
        lines = build_customer_purchase_product_lines(self.commercial_products)
        if not lines:
            text = "服务端暂未返回可购买商品；不能在本工具内创建订单。"
        else:
            text = "可购买商品：\n" + "\n".join(f"- {line}" for line in lines[:5])
        label.configure(text=text)

    def refresh_buyer_purchase_status(self) -> None:
        if getattr(self, 'webview_mode', False):
            self.sync_webview_state()
            return
        product_label = getattr(self, "buyer_product_summary_label", None)
        if product_label:
            lines = build_customer_purchase_product_lines(self.commercial_products)
            if lines:
                product_label.configure(text="可购买商品：\n" + "\n".join(f"- {line}" for line in lines[:5]))
            else:
                product_label.configure(text="服务端暂未返回可购买商品；不能在本工具内创建订单。")
        status_label = getattr(self, "buyer_purchase_status_label", None)
        if status_label:
            lines = [row.customer_message for row in build_buyer_self_service_status_rows(self.buyer_purchase_statuses)]
            if lines and any(status != NodeStatus.NOT_STARTED for status in self.buyer_purchase_statuses.values()):
                text = "\n".join(lines)
            else:
                text = (
                    "当前还没开始买家自助购买。\n"
                    "先打开 API Key 创建页面；如果新账号余额不足，请先充值后再回来保存并测试 Key。\n"
                    "当前桌面版还不能直接在这里完成 API Key 创建或余额充值。"
                )
            status_label.configure(text=text)

    def next_diagnostic_code(self, prefix: str = "PH-CFG") -> str:
        self.last_diagnostic_code = f"{prefix}-{time.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
        return self.last_diagnostic_code

    def _build_login_frame(self, parent: tk.Frame) -> None:
        parent.configure(padx=0, pady=0)
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        login_shell = tk.Frame(parent, bg=APP_BG)
        login_shell.pack(fill="both", expand=True)
        login_card = tk.Frame(login_shell, bg=CARD_BG, padx=40, pady=35, highlightthickness=1, highlightbackground=BORDER)
        login_card.pack(fill="none", expand=True, padx=20, pady=20)
        self.login_card = login_card

        # Circular Avatar & Brand Row
        brand_row = tk.Frame(login_card, bg=CARD_BG)
        brand_row.pack(fill="x", pady=(0, 20))
        avatar_shell = tk.Frame(brand_row, bg=CARD_BG, width=64, height=64, highlightthickness=0, bd=0)
        avatar_shell.pack(side="left", padx=(0, 15), pady=(0, 0))
        avatar_shell.pack_propagate(False)
        avatar = self.load_ui_image("panghu-avatar-64.png")
        if avatar is not None:
            tk.Label(avatar_shell, image=avatar, bg=CARD_BG, bd=0, highlightthickness=0).pack(fill="both", expand=True)
        else:
            tk.Label(
                avatar_shell,
                text="PH",
                bg=PRIMARY,
                fg="#ffffff",
                font=("Microsoft YaHei UI", 12, "bold"),
            ).pack(fill="both", expand=True)

        title_block = tk.Frame(brand_row, bg=CARD_BG)
        title_block.pack(side="left")
        tk.Label(
            title_block,
            text=APP_NAME,
            bg=CARD_BG,
            fg=INK,
            font=("Microsoft YaHei UI", 15, "bold"),
            anchor="w"
        ).pack(anchor="w", pady=(0, 1))
        tk.Label(
            title_block,
            text="胖虎AI客户端商业交付平台",
            bg=CARD_BG,
            fg=PRIMARY_DARK,
            font=("Microsoft YaHei UI", 9, "bold"),
            anchor="w"
        ).pack(anchor="w", pady=(1, 0))

        # Divider line
        tk.Frame(login_card, bg=BORDER, height=1).pack(fill="x", pady=(0, 20))

        tk.Label(
            login_card,
            text="登录胖虎AI账号",
            font=("Microsoft YaHei UI", 18, "bold"),
            bg=CARD_BG,
            fg=INK,
        ).pack(anchor="w", pady=(0, 8))
        tk.Label(
            login_card,
            text="先完成身份确认和登录。登录成功后，才会解锁完整部署向导和交付状态。",
            bg=CARD_BG,
            fg=MUTED,
            wraplength=480,
            justify="left",
            font=("Microsoft YaHei UI", 9),
        ).pack(anchor="w", pady=(0, 15))

        info_row = tk.Frame(login_card, bg=CARD_BG)
        info_row.pack(fill="x", pady=(0, 15))
        tk.Label(
            info_row,
            text="所有客户先用胖虎AI账号登录；代理权益等登录后在网站模块处理。",
            bg=CARD_BG,
            fg=MUTED,
            font=("Microsoft YaHei UI", 9),
            justify="left",
            anchor="w",
        ).pack(side="left")
        self._text_button(info_row, "查看说明", lambda: self._show_help("账号说明", login_help_text())).pack(side="right")

        self.buyer_login_panel = tk.Frame(login_card, bg=CARD_BG)
        self.buyer_login_panel.pack(fill="x")
        account = tk.Frame(self.buyer_login_panel, bg=CARD_BG)
        account.pack(fill="x")
        tk.Label(account, text="用户名或邮箱", bg=CARD_BG, fg=INK, font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w")
        self.login_username_entry = ttk.Entry(account, textvariable=self.login_username, font=("Microsoft YaHei UI", 11), width=45)
        self.login_username_entry.pack(fill="x", ipady=7, pady=(6, 12))

        password = tk.Frame(self.buyer_login_panel, bg=CARD_BG)
        password.pack(fill="x")
        tk.Label(password, text="密码", bg=CARD_BG, fg=INK, font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w")
        pwd_entry = ttk.Entry(password, textvariable=self.login_password, show="*", font=("Microsoft YaHei UI", 11), width=45)
        pwd_entry.pack(fill="x", ipady=7, pady=(6, 16))

        invite = tk.Frame(self.buyer_login_panel, bg=CARD_BG)
        invite.pack(fill="x")
        tk.Label(invite, text="邀请码 / 代理邀请链接（新账号注册时填写）", bg=CARD_BG, fg=INK, font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w")
        ttk.Entry(invite, textvariable=self.registration_invite_code, font=("Microsoft YaHei UI", 11), width=45).pack(fill="x", ipady=7, pady=(6, 8))
        tk.Label(
            invite,
            text="没有账号时先填代理给的邀请码或邀请链接，再点注册；绑定和返佣仍以胖虎AI网站服务端为准。",
            bg=CARD_BG,
            fg=MUTED,
            wraplength=480,
            justify="left",
            font=("Microsoft YaHei UI", 8),
        ).pack(anchor="w", pady=(0, 12))

        buttons = tk.Frame(self.buyer_login_panel, bg=CARD_BG)
        buttons.pack(fill="x", pady=(5, 0))
        self.login_button = self._button(buttons, "登录并激活工具", self.start_login, "primary")
        self.login_button.pack(side="left")
        self._text_button(
            buttons,
            "没有账号？先去注册",
            lambda: open_url(
                self.current_registration_url(),
                storage_path=self.current_buyer_web_profile_path(),
            ),
        ).pack(side="left", padx=(18, 0), pady=(4, 0))

        tk.Frame(login_card, bg=BORDER, height=1).pack(fill="x", pady=(20, 15))
        tk.Label(
            login_card,
            text="安全说明：密码仅用于登录验证；API Key 只写入本机 Agent 配置，日志会自动隐藏明文 Key。",
            bg=CARD_BG,
            fg=MUTED,
            wraplength=480,
            justify="left",
            font=("Microsoft YaHei UI", 9),
        ).pack(anchor="w")

    def current_registration_url(self) -> str:
        return build_register_url(self.registration_invite_code.get())

    def _build_buyer_purchase_panel(self, parent: tk.Frame) -> None:
        panel = tk.Frame(parent, bg=INFO_BG, padx=12, pady=9, highlightthickness=1, highlightbackground=BORDER)
        self.buyer_purchase_panel = panel
        panel.pack(fill="x", pady=(0, 14))
        tk.Label(
            panel,
            text="买家自助购买与权益刷新",
            bg=INFO_BG,
            fg=PRIMARY_DARK,
            font=("Microsoft YaHei UI", 10, "bold"),
        ).pack(anchor="w")
        tk.Label(
            panel,
            text="显示服务端返回的可购买商品。价格、次数、有效期和设备数以服务端为准，支付成功并刷新权益后再继续交付。",
            bg=INFO_BG,
            fg=MUTED,
            wraplength=760,
            justify="left",
            font=("Microsoft YaHei UI", 8),
        ).pack(anchor="w", pady=(4, 7))
        buyer_product = tk.Frame(panel, bg=INFO_BG)
        buyer_product.pack(fill="x")
        buyer_product.grid_columnconfigure(0, weight=1)
        buyer_product.grid_columnconfigure(1, weight=1)
        product_left = tk.Frame(buyer_product, bg=INFO_BG)
        product_left.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        product_right = tk.Frame(buyer_product, bg=INFO_BG)
        product_right.grid(row=0, column=1, sticky="ew")
        tk.Label(product_left, text="商品 ID", bg=INFO_BG, fg=INK, font=("Microsoft YaHei UI", 9, "bold")).pack(anchor="w")
        ttk.Entry(product_left, textvariable=self.buyer_product_id, show="*", font=("Microsoft YaHei UI", 10)).pack(fill="x", ipady=5, pady=(4, 0))
        tk.Label(product_right, text="订单 ID", bg=INFO_BG, fg=INK, font=("Microsoft YaHei UI", 9, "bold")).pack(anchor="w")
        ttk.Entry(product_right, textvariable=self.buyer_order_id, show="*", font=("Microsoft YaHei UI", 10)).pack(fill="x", ipady=5, pady=(4, 0))
        self.buyer_product_summary_label = tk.Label(
            panel,
            text="登录并刷新授权后，这里会显示可购买商品。",
            bg=INFO_BG,
            fg="#71411c",
            wraplength=760,
            justify="left",
            anchor="w",
            font=("Microsoft YaHei UI", 9),
        )
        self.buyer_product_summary_label.pack(fill="x", pady=(6, 0))
        actions = tk.Frame(panel, bg=INFO_BG)
        actions.pack(fill="x", pady=(8, 0))
        self._button(actions, "创建订单", self.start_buyer_create_order, "primary").pack(side="left")
        self._button(actions, "查询支付", self.start_buyer_poll_payment, "secondary").pack(side="left", padx=(10, 0))
        self._button(actions, "刷新权益", self.start_buyer_refresh_entitlements, "secondary").pack(side="left", padx=(10, 0))
        self._button(
            actions,
            "打开 API Key 创建页面",
            lambda: open_url(
                KEY_CREATE_URL,
                cookie_jar=self.cookie_jar,
                log=self.log,
                storage_path=self.current_buyer_web_profile_path(),
            ),
            "secondary",
        ).pack(side="left", padx=(10, 0))
        self._button(actions, "查看创建说明", lambda: self._show_help("API Key 创建说明", key_creation_help_text()), "secondary").pack(side="left", padx=(10, 0))
        self.buyer_purchase_status_label = tk.Label(
            panel,
            text="买家购买：未开始。",
            bg=INFO_BG,
            fg="#71411c",
            wraplength=760,
            justify="left",
            anchor="w",
            font=("Microsoft YaHei UI", 9),
        )
        self.buyer_purchase_status_label.pack(fill="x", pady=(6, 0))

    def _build_wizard_frame(self, parent: tk.Frame) -> None:
        # Legacy hook kept for old call sites. The current UI is built by _build_ui.
        return

    def _create_step_frame(self, idx: int, parent: tk.Widget | None = None) -> tk.Frame:
        host = parent or self.steps_host
        viewport_bg = APP_BG if parent is self.login_gate_host else SURFACE_BG
        viewport = tk.Frame(host, bg=viewport_bg)
        canvas = tk.Canvas(viewport, bg=viewport_bg, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(viewport, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas, bg=CARD_BG, padx=24, pady=20, highlightthickness=1, highlightbackground=BORDER)
        window_id = canvas.create_window((0, 0), window=content, anchor="nw")
        scrollbar_visible = {"value": False}

        def sync_scrollbar_visibility() -> None:
            viewport_height = max(0, viewport.winfo_height())
            content_height = max(0, content.winfo_reqheight())
            should_show = content_height > max(0, viewport_height - 8)
            if should_show and not scrollbar_visible["value"]:
                scrollbar.pack(side="right", fill="y")
                scrollbar_visible["value"] = True
            elif not should_show and scrollbar_visible["value"]:
                scrollbar.pack_forget()
                scrollbar_visible["value"] = False

        def sync_scroll_region(_event=None) -> None:
            canvas.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox("all"))
            sync_scrollbar_visibility()

        def sync_content_width(event) -> None:
            available_width = max(360, event.width - 24)
            if event.width >= 2400:
                max_width = 1280
            elif event.width >= 1800:
                max_width = 1120
            elif event.width >= 1400:
                max_width = 920
            elif event.width >= 1100:
                max_width = 760
            else:
                max_width = available_width
            target_width = max(360, min(max_width, available_width))
            canvas.itemconfigure(window_id, width=target_width)
            left_pad = max(0, (event.width - target_width) // 2)
            canvas.coords(window_id, left_pad, 0)
            sync_scrollbar_visibility()

        content.bind("<Configure>", sync_scroll_region)
        canvas.bind("<Configure>", sync_content_width)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        self.step_canvases[idx] = viewport
        self.step_frames[idx] = content
        return content

    def _step_button(self, parent: tk.Frame, idx: int, title: str, subtitle: str) -> tk.Button:
        def activate() -> None:
            self.go_to_step(idx)

        return tk.Button(
            parent,
            text=f"{title}\n未开始",
            command=activate,
            anchor="w",
            justify="left",
            bg=SIDEBAR_BG,
            fg=INK,
            activebackground=PRIMARY_LIGHT,
            activeforeground=INK,
            relief="flat",
            bd=0,
            padx=8,
            pady=7,
            cursor="hand2",
            font=("Microsoft YaHei UI", 8),
        )

    def _build_status_step(
        self,
        idx: int,
        title: str,
        desc: str,
        hint: str,
        button_text: str | None = None,
        command=None,
    ) -> None:
        frame = self._create_step_frame(idx)
        self._step_title(frame, title, desc)
        self._step_hint(frame, idx)
        result = tk.Frame(frame, bg=PANEL_BG, padx=14, pady=12, highlightthickness=1, highlightbackground=BORDER)
        result.pack(fill="x", pady=(0, 12))
        tk.Label(result, text="当前要确认什么", bg=PANEL_BG, fg=INK, font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w")
        tk.Label(
            result,
            text=desc,
            bg=PANEL_BG,
            fg=MUTED,
            wraplength=520,
            justify="left",
            font=("Microsoft YaHei UI", 9),
        ).pack(anchor="w", fill="x", pady=(4, 0))
        tip = tk.Frame(frame, bg=INFO_BG, padx=14, pady=12, highlightthickness=1, highlightbackground=BORDER)
        tip.pack(fill="x")
        tk.Label(tip, text="完成后看哪里", bg=INFO_BG, fg=PRIMARY_DARK, font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w")
        tk.Label(
            tip,
            text=hint,
            bg=INFO_BG,
            fg=INK,
            wraplength=520,
            justify="left",
            font=("Microsoft YaHei UI", 9),
        ).pack(anchor="w", fill="x", pady=(4, 0))
        if button_text and command:
            self._button(tip, button_text, command, "secondary").pack(anchor="w", pady=(12, 0))

    def _step_title(
        self,
        parent: tk.Frame,
        title: str,
        desc: str,
        help_title: str | None = None,
        help_text: str | None = None,
    ) -> None:
        row = tk.Frame(parent, bg=CARD_BG)
        row.pack(fill="x")
        tk.Label(row, text=title, font=("Microsoft YaHei UI", 14, "bold"), bg=CARD_BG, fg=INK).pack(side="left", anchor="w")
        if help_title and help_text:
            self._text_button(row, "查看详细说明", lambda: self._show_help(help_title, help_text)).pack(side="right")
        desc_label = tk.Label(parent, text=desc, bg=CARD_BG, fg=MUTED, wraplength=520, justify="left", font=("Microsoft YaHei UI", 8))
        desc_label.pack(anchor="w", fill="x", pady=(5, 10))
        self._sync_wraplength(desc_label, 20, 360)

    def _step_hint(self, parent: tk.Frame, idx: int) -> None:
        label = tk.Label(
            parent,
            text="",
            bg=INFO_BG,
            fg=PRIMARY_DARK,
            padx=10,
            pady=5,
            wraplength=500,
            justify="left",
            anchor="w",
            font=("Microsoft YaHei UI", 8, "bold"),
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        label.pack(fill="x", pady=(0, 8))
        self._sync_wraplength(label, 28, 360)
        self.step_hint_labels[idx] = label

    def _field_label(self, parent: tk.Frame, text: str, bg: str = CARD_BG) -> None:
        tk.Label(parent, text=text, bg=bg, fg=INK, font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w")

    def _form_entry(
        self,
        parent: tk.Widget,
        label: str,
        variable: tk.StringVar,
        *,
        row: int,
        column: int,
        show: str | None = None,
        bg: str = CARD_BG,
    ) -> ttk.Entry:
        box = tk.Frame(parent, bg=bg)
        box.grid(row=row, column=column, sticky="ew", padx=(0 if column == 0 else 10, 0), pady=(0, 10))
        tk.Label(box, text=label, bg=bg, fg=INK, font=("Microsoft YaHei UI", 9, "bold")).pack(anchor="w")
        entry = ttk.Entry(box, textvariable=variable, show=show or "", font=("Microsoft YaHei UI", 10))
        entry.pack(fill="x", ipady=5, pady=(4, 0))
        return entry

    def _form_combo(
        self,
        parent: tk.Widget,
        label: str,
        variable: tk.StringVar,
        values: tuple[str, ...],
        *,
        row: int,
        column: int,
        bg: str = CARD_BG,
        state: str = "readonly",
    ) -> ttk.Combobox:
        box = tk.Frame(parent, bg=bg)
        box.grid(row=row, column=column, sticky="ew", padx=(0 if column == 0 else 10, 0), pady=(0, 10))
        tk.Label(box, text=label, bg=bg, fg=INK, font=("Microsoft YaHei UI", 9, "bold")).pack(anchor="w")
        combo = ttk.Combobox(box, textvariable=variable, values=list(values), state=state, font=("Microsoft YaHei UI", 10))
        combo.pack(fill="x", ipady=4, pady=(4, 0))
        return combo

    def _build_login_gate_frame(self) -> None:
        frame = tk.Frame(self.login_gate_host, bg=APP_BG)
        frame.place(x=0, y=0, relwidth=1, relheight=1)
        self._build_login_frame(frame)

    def _build_step_1(self) -> None:
        frame = self._create_step_frame(1)
        self._step_title(
            frame,
            "第一步：创建或填写胖虎AI API Key",
            "把客户自己的胖虎AI API Key 填进来。它是 Agent 调用令牌，不是登录密码，日志里只显示脱敏结果。",
            "API Key 创建说明",
            key_creation_help_text(),
        )
        self._step_hint(frame, 1)

        self._build_buyer_purchase_panel(frame)

        key_row = tk.Frame(frame, bg=CARD_BG)
        key_row.pack(fill="x", pady=(18, 0))
        self._field_label(key_row, "胖虎AI API Key")
        entry_row = tk.Frame(key_row, bg=CARD_BG)
        entry_row.pack(fill="x", pady=(6, 0))
        self.key_entry = ttk.Entry(entry_row, textvariable=self.api_key, show="*", font=("Microsoft YaHei UI", 11))
        self.key_entry.pack(side="left", fill="x", expand=True, ipady=7)
        ttk.Checkbutton(entry_row, text="显示", variable=self.show_key, command=self.toggle_key).pack(
            side="left", padx=(10, 0)
        )

        form = tk.Frame(frame, bg=CARD_BG)
        form.pack(fill="x", pady=(14, 0))
        form.grid_columnconfigure(0, weight=1)
        form.grid_columnconfigure(1, weight=1)
        base_frame = tk.Frame(form, bg=CARD_BG)
        base_frame.grid(row=0, column=0, sticky="ew", padx=(0, 14))
        self._field_label(base_frame, "接口地址")
        self.base_url_entry = ttk.Entry(
            base_frame,
            textvariable=self.base_url,
            font=("Microsoft YaHei UI", 11),
            state="readonly",
        )
        self.base_url_entry.pack(fill="x", ipady=7, pady=(6, 0))
        model_frame = tk.Frame(form, bg=CARD_BG)
        model_frame.grid(row=0, column=1, sticky="ew")
        self._field_label(model_frame, "默认模型")
        ttk.Combobox(model_frame, textvariable=self.model, values=["gpt-5.5", "gpt-4.1"]).pack(
            fill="x", ipady=5, pady=(6, 0)
        )

        options = tk.Frame(frame, bg=CARD_BG)
        options.pack(fill="x", pady=(18, 0))
        ttk.Checkbutton(options, text="跳过接口测试", variable=self.skip_test).pack(side="right", padx=(0, 12))
        self._button(options, "保存并测试 Key", self.start_save_key, "primary").pack(side="right", padx=(12, 0))
        self.step_next_buttons[1] = self._button(options, "下一步：检测系统", lambda: self.go_to_step(2), "secondary")
        self.step_next_buttons[1].pack(side="right")

    def _build_step_2(self) -> None:
        frame = self._create_step_frame(2)
        self._step_title(
            frame,
            "第二步：选择系统并检测环境",
            "先帮客户检查电脑环境。这里会识别系统、基础命令和会改写配置的风险工具。",
            "环境检测说明",
            environment_help_text(),
        )
        self._step_hint(frame, 2)
        self._notice_strip(
            frame,
            "检测说明",
            "如果提示存在 ccswitch、codex++、CCR 等工具，请先按提示处理，再继续安装配置。",
            "info",
            compact=True,
        ).pack_configure(pady=(0, 12))
        choices = tk.Frame(frame, bg=PANEL_BG, padx=14, pady=12, highlightthickness=1, highlightbackground=BORDER)
        choices.pack(fill="x")
        ttk.Radiobutton(choices, text="自动识别", value=current_system_id(), variable=self.selected_system).pack(
            side="left", padx=(0, 16)
        )
        ttk.Radiobutton(choices, text="Windows", value="windows", variable=self.selected_system).pack(
            side="left", padx=(0, 16)
        )
        ttk.Radiobutton(choices, text="Mac", value="mac", variable=self.selected_system).pack(side="left")
        self._button(choices, "检测环境", self.run_environment_check, "primary").pack(side="right")
        self.env_text = tk.Text(
            frame,
            height=15,
            bg=LOG_BG,
            fg=LOG_FG,
            insertbackground=LOG_FG,
            relief="flat",
            borderwidth=0,
            padx=14,
            pady=12,
            wrap="word",
            font=("Cascadia Mono", 9),
        )
        self.env_text.pack(fill="both", expand=True, pady=(14, 0))
        self.env_text.configure(state="disabled")
        nav = tk.Frame(frame, bg=CARD_BG)
        nav.pack(fill="x", pady=(12, 0))
        self.step_next_buttons[2] = self._button(nav, "下一步：选择 Agent", lambda: self.go_to_step(3), "secondary")
        self.step_next_buttons[2].pack(side="right")

    def _agent_card_copy(self, agent: AgentSpec) -> tuple[str, str]:
        copies = {
            "codex": ("官方 Codex Agent，可应用胖虎AI配置。", "可写入 Key、接口、模型和中文规则。"),
            "claude_code": ("Claude Code/CC，官方 CLI 与客户端入口。", "写入胖虎AI网关配置，目标是直接对话。"),
            "openclaw": ("OpenClaw，官方 CLI 与 Hub/客户端入口。", "跳过 QQ/微信/TG 等第三方通道，只保留直接对话链路。"),
            "hermes": ("Hermes，官方 CLI 与客户端入口。", "跳过 QQ/微信/TG 等第三方通道，只保留直接对话链路。"),
        }
        return copies.get(agent.id, (agent.description, agent.config_note))

    def _build_step_3(self) -> None:
        frame = self._create_step_frame(3)
        self._step_title(
            frame,
            "第三步：选择 Agent 和安装方式",
            "按客户实际需要选择要交付的 Agent。五个 Agent 都按官方 CLI 与客户端入口覆盖，IDE 插件形态不处理。",
            "Agent 选择说明",
            agent_choice_help_text(),
        )
        self._step_hint(frame, 3)
        self._notice_strip(
            frame,
            "配置范围",
            "五个 Agent 都必须按五维状态验收；Gemini / agy 走胖虎AI网关 Gemini 格式配置链路。",
            "info",
            compact=True,
        ).pack_configure(pady=(0, 10))

        top_nav = tk.Frame(frame, bg=CARD_BG)
        top_nav.pack(fill="x", pady=(0, 8))
        self.step_next_buttons[3] = self._button(top_nav, "下一步：执行安装", lambda: self.go_to_step(4), "secondary")
        self.step_next_buttons[3].pack(side="right")

        list_frame = tk.Frame(frame, bg=CARD_BG)
        list_frame.pack(fill="both", expand=True)
        list_frame.grid_columnconfigure(0, weight=1)
        commercial_manifest_present = bool(self.deployer_manifest and manifest_has_commercial_controls(self.deployer_manifest))
        for index, agent in enumerate(AGENTS):
            state = build_agent_customer_state(
                agent.id,
                self.commercial_capabilities,
                commercial_manifest_present=commercial_manifest_present,
            )
            row = tk.Frame(list_frame, bg=PANEL_BG, padx=9, pady=4, highlightthickness=1, highlightbackground=BORDER)
            row.grid(row=index, column=0, sticky="ew", pady=(0, 4))
            row.grid_columnconfigure(0, minsize=148)
            row.grid_columnconfigure(1, weight=1)
            row.grid_columnconfigure(2, minsize=112)
            enabled = WebviewBooleanVar(value=agent.id == "codex")
            mode = WebviewStringVar(value="cli")
            enabled.trace_add("write", self.mark_agent_selection_changed)
            mode.trace_add("write", self.mark_agent_selection_changed)
            self.agent_enabled[agent.id] = enabled
            self.agent_mode[agent.id] = mode
            card_description, _card_note = self._agent_card_copy(agent)
            header = tk.Frame(row, bg=PANEL_BG)
            header.grid(row=0, column=0, sticky="nw", padx=(0, 12))
            checkbutton = tk.Checkbutton(
                header,
                text=f"选择 {agent.name}",
                variable=enabled,
                indicatoron=False,
                bg=LOCKED_BG,
                fg=INK,
                activebackground=INFO_BG,
                activeforeground=INK,
                selectcolor=SUCCESS_BG,
                relief="flat",
                bd=0,
                padx=8,
                pady=2,
                cursor="hand2",
                font=("Microsoft YaHei UI", 9, "bold"),
                state="normal" if state.selectable else "disabled",
            )
            checkbutton.pack(anchor="w")
            badge_label = tk.Label(
                header,
                text=state.badge,
                bg=GOLD_SOFT if state.selectable else LOCKED_BG,
                fg=PRIMARY_DARK if state.selectable else MUTED,
                padx=7,
                pady=2,
                font=("Microsoft YaHei UI", 8, "bold"),
            )
            badge_label.pack(anchor="w", pady=(3, 0))
            text_area = tk.Frame(row, bg=PANEL_BG)
            text_area.grid(row=0, column=1, sticky="ew", padx=(0, 12))
            tk.Label(
                text_area,
                text=card_description,
                bg=PANEL_BG,
                fg=INK,
                font=("Microsoft YaHei UI", 8, "bold"),
                wraplength=260,
                justify="left",
            ).pack(anchor="w")
            note_label = tk.Label(
                text_area,
                text=state.note,
                bg=PANEL_BG,
                fg=MUTED,
                wraplength=260,
                justify="left",
                font=("Microsoft YaHei UI", 8),
            )
            note_label.pack(anchor="w", pady=(2, 0))
            mode_area = tk.Frame(row, bg=PANEL_BG)
            mode_area.grid(row=0, column=2, sticky="e")
            tk.Label(mode_area, text="安装方式", bg=PANEL_BG, fg=MUTED, font=("Microsoft YaHei UI", 7, "bold")).pack(anchor="e")
            modes_row = tk.Frame(mode_area, bg=PANEL_BG)
            modes_row.pack(anchor="e", pady=(3, 0))
            for item in agent.modes:
                tk.Radiobutton(
                    modes_row,
                    text=item.label,
                    value=item.id,
                    variable=mode,
                    indicatoron=False,
                    bg=CARD_BG,
                    fg=INK,
                    activebackground=LOCKED_BG,
                    activeforeground=INK,
                    selectcolor=SUCCESS_BG,
                    relief="flat",
                    bd=0,
                    padx=6,
                    pady=2,
                    cursor="hand2",
                    font=("Microsoft YaHei UI", 7, "bold"),
                ).pack(side="left", padx=(0, 5))
            self.agent_rows[agent.id] = row
            self.agent_checkbuttons[agent.id] = checkbutton
            self.agent_badge_labels[agent.id] = badge_label
            self.agent_note_labels[agent.id] = note_label
            if not state.visible:
                row.grid_remove()
        nav = tk.Frame(frame, bg=CARD_BG)
        nav.pack(fill="x", pady=(6, 0))
        self._button(nav, "下一步：执行安装", lambda: self.go_to_step(4), "secondary").pack(side="right")

    def _build_step_4(self) -> None:
        frame = self._create_step_frame(4)
        self._step_title(
            frame,
            "第四步：执行安装",
            "客服确认登录、Key、环境和 Agent 选择无误后，再开始安装。工具会写入胖虎AI配置，并按最短可用链路验证能直接对话。",
            "按钮功能说明",
            codex_action_help_text(),
        )
        self._step_hint(frame, 4)
        commercial_box = tk.Frame(frame, bg=SUCCESS_BG, padx=10, pady=7, highlightthickness=1, highlightbackground=BORDER)
        commercial_box.pack(fill="x", pady=(0, 10))
        tk.Label(
            commercial_box,
            text="商业权益状态",
            bg=SUCCESS_BG,
            fg="#116047",
            font=("Microsoft YaHei UI", 10, "bold"),
        ).pack(anchor="w")
        self.commercial_summary_label = tk.Label(
            commercial_box,
            text=self.current_commercial_summary_text(),
            bg=SUCCESS_BG,
            fg="#315c4b",
            wraplength=760,
            justify="left",
            anchor="w",
            font=("Microsoft YaHei UI", 9),
        )
        self.commercial_summary_label.pack(fill="x", pady=(3, 0))
        confirm_row = tk.Frame(frame, bg=CARD_BG)
        confirm_row.pack(fill="x")
        confirm_row.grid_columnconfigure(0, weight=1, uniform="confirm")
        confirm_row.grid_columnconfigure(1, weight=1, uniform="confirm")
        summary = tk.Frame(confirm_row, bg=PANEL_BG, padx=10, pady=7, highlightthickness=1, highlightbackground=BORDER)
        summary.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        tk.Label(summary, text="客服执行前确认", bg=PANEL_BG, fg=INK, font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w")
        summary_body = tk.Label(
            summary,
            text="确认账号、Key、系统检测和 Agent 选择都完成后再执行；开始前会再查风险工具。",
            bg=PANEL_BG,
            fg=MUTED,
            wraplength=240,
            justify="left",
            anchor="w",
            font=("Microsoft YaHei UI", 9),
        )
        summary_body.pack(fill="x", pady=(3, 0))
        restart = tk.Frame(confirm_row, bg=WARNING_BG, padx=10, pady=7, highlightthickness=1, highlightbackground="#f1c995")
        restart.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        tk.Label(restart, text="客户要知道", bg=WARNING_BG, fg=PRIMARY_DARK, font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w")
        restart_body = tk.Label(
            restart,
            text="配置写完后必须重新打开对应 Agent，并完成最小对话验证。",
            bg=WARNING_BG,
            fg="#71411c",
            wraplength=240,
            justify="left",
            anchor="w",
            font=("Microsoft YaHei UI", 9),
        )
        restart_body.pack(fill="x", pady=(3, 0))
        ttk.Checkbutton(frame, text="完成后打开对应 Agent，并临时打开必要的官方访问窗口", variable=self.open_app).pack(
            anchor="w", pady=(8, 0)
        )

        actions = tk.Frame(frame, bg=CARD_BG)
        actions.pack(fill="x", pady=(10, 0))
        for col in range(2):
            actions.grid_columnconfigure(col, weight=1, uniform="actions")
        self.deploy_button = self._grid_button(actions, "一键部署（普通）", self.start_deploy, "success", 0, 0)
        self.dual_state_button = self._grid_button(actions, "双态配置", self.start_dual_state_config, "primary", 0, 1)
        self.config_button = self._grid_button(actions, "仅修复 Codex 配置", self.start_config_only, "primary", 1, 0)
        self.official_chatgpt_button = self._grid_button(
            actions,
            "官方直登",
            self.start_official_chatgpt_config,
            "secondary",
            1,
            1,
        )
        aux_actions = tk.Frame(frame, bg=CARD_BG)
        aux_actions.pack(fill="x", pady=(0, 0))
        for col in range(2):
            aux_actions.grid_columnconfigure(col, weight=1, uniform="actions2")
        self.restore_button = self._grid_button(aux_actions, "恢复最近备份", self.restore_backups, "secondary", 0, 0)
        self._grid_button(aux_actions, "复制日志", self.copy_logs, "secondary", 0, 1)
        self._grid_button(aux_actions, "打开工作区", self.open_workspace, "secondary", 1, 0)
        self._grid_button(aux_actions, "打开配置目录", self.open_config_dir, "secondary", 1, 1)
        self._grid_button(aux_actions, "打开功能验收矩阵", self.open_acceptance_matrix, "secondary", 2, 0, 2)

        help_box = tk.Frame(frame, bg=INFO_BG, padx=10, pady=7, highlightthickness=1, highlightbackground=BORDER)
        help_box.pack(fill="x", pady=(10, 0))
        help_box.grid_columnconfigure(0, weight=1)
        tk.Label(
            help_box,
            text="按钮功能",
            bg=INFO_BG,
            fg=PRIMARY_DARK,
            font=("Microsoft YaHei UI", 9, "bold"),
        ).grid(row=0, column=0, sticky="w")
        help_body = tk.Label(
            help_box,
            text="普通/双态都走胖虎AI中转站；官方直登走用户自己的 ChatGPT 账号额度。交付是否完成，以“功能验收矩阵”里的最小对话结果为准。",
            bg=INFO_BG,
            fg=MUTED,
            wraplength=420,
            justify="left",
            anchor="w",
            font=("Microsoft YaHei UI", 9),
        )
        help_body.grid(row=1, column=0, sticky="ew", pady=(3, 0))
        self._sync_wraplength(help_body, 130, 330)
        self._text_button(help_box, "查看全部按钮说明", lambda: self._show_help("按钮功能说明", codex_action_help_text())).grid(
            row=0, column=1, rowspan=2, sticky="ne", padx=(12, 0)
        )

    def _build_communication_software_link_step(self) -> None:
        frame = self._create_step_frame(10)
        self._step_title(
            frame,
            "第十步：连接通讯软件",
            "连接通讯软件是独立增值服务。它可以绑定本次交付、历史交付、已有本机 Agent 或人工复核通过的 Agent，不强制绑定基础安装流程。",
        )
        self._step_hint(frame, 10)
        self._notice_strip(
            frame,
            "服务端定价与订单",
            "商品、价格、通道、上架状态和配置会话都必须由服务端返回。本地只负责发起订单、创建配置会话和记录验收证据。",
            "warning",
        ).pack(fill="x", pady=(0, 12))

        form = tk.Frame(frame, bg=CARD_BG)
        form.pack(fill="x")
        for col in range(2):
            form.grid_columnconfigure(col, weight=1, uniform="communication_software_link")
        self._form_entry(form, "连接通讯软件服务商品 ID", self.communication_software_link_service_product_id, row=0, column=0)
        self._form_entry(form, "连接通讯软件订单 ID", self.communication_software_link_order_id, row=0, column=1)
        self._form_combo(form, "目标 Agent", self.communication_software_link_agent_id, COMMUNICATION_SOFTWARE_LINK_AGENT_OPTIONS, row=1, column=0)
        self._form_combo(form, "通讯软件通道", self.communication_software_link_channel, COMMUNICATION_SOFTWARE_LINK_CHANNEL_OPTIONS, row=1, column=1)
        self._form_combo(form, "Agent 来源", self.communication_software_link_agent_source, COMMUNICATION_SOFTWARE_LINK_AGENT_SOURCE_OPTIONS, row=2, column=0)
        self._form_combo(form, "网关模式", self.communication_software_link_gateway_mode, COMMUNICATION_SOFTWARE_LINK_GATEWAY_MODE_OPTIONS, row=2, column=1)
        self._form_entry(form, "平台账号 ID", self.communication_software_link_platform_account_id, row=3, column=0)
        self._form_entry(form, "平台会话 / 群聊 ID", self.communication_software_link_platform_chat_id, row=3, column=1)

        service_summary = tk.Label(
            frame,
            text="登录并刷新服务端后，这里会按服务端返回的连接通讯软件商品继续创建订单。",
            bg=INFO_BG,
            fg=PRIMARY_DARK,
            padx=12,
            pady=8,
            wraplength=760,
            justify="left",
            anchor="w",
            font=("Microsoft YaHei UI", 9),
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        service_summary.pack(fill="x", pady=(4, 12))
        self.communication_software_link_service_summary_label = service_summary

        actions = tk.Frame(frame, bg=CARD_BG)
        actions.pack(fill="x")
        for col in range(3):
            actions.grid_columnconfigure(col, weight=1, uniform="communication_software_link_actions")
        self._grid_button(actions, "刷新服务商品", self.start_communication_software_link_refresh_offering, "secondary", 0, 0)
        self._grid_button(actions, "创建连接通讯软件订单", self.start_communication_software_link_create_order, "primary", 0, 1)
        self._grid_button(actions, "查询订单", self.start_communication_software_link_get_order, "secondary", 0, 2)
        self._grid_button(actions, "创建配置会话", self.start_communication_software_link_create_session, "primary", 1, 0)
        self._grid_button(actions, "查询会话", self.start_communication_software_link_get_session, "secondary", 1, 1)
        self._grid_button(actions, "下一步：连接通讯软件验收", lambda: self.go_to_step(11), "secondary", 1, 2)

    def _build_communication_software_link_acceptance_step(self) -> None:
        frame = self._create_step_frame(11)
        self._step_title(
            frame,
            "第十一步：连接通讯软件交付验收",
            "只有服务端确认入站消息、Agent 调用、出站回复和证据 URL 后，连接通讯软件才算交付。未验收不能扣次或包装成完整交付。",
        )
        self._step_hint(frame, 11)

        form = tk.Frame(frame, bg=CARD_BG)
        form.pack(fill="x")
        for col in range(2):
            form.grid_columnconfigure(col, weight=1, uniform="communication_software_link_acceptance")
        self._form_entry(form, "配置会话 ID", self.communication_software_link_session_id, row=0, column=0)
        self._form_entry(form, "测试提示词", self.communication_software_link_test_prompt, row=0, column=1)
        self._form_entry(form, "源事件 ID", self.communication_software_link_source_event_id, row=1, column=0)
        self._form_entry(form, "入站消息 ID", self.communication_software_link_inbound_message_id, row=1, column=1)
        self._form_entry(form, "出站消息 ID", self.communication_software_link_outbound_message_id, row=2, column=0)
        self._form_entry(form, "Agent 响应摘要", self.communication_software_link_response_digest, row=2, column=1)
        self._form_entry(form, "证据 URL", self.communication_software_link_evidence_url, row=3, column=0)

        self._notice_strip(
            frame,
            "验收边界",
            "连接通讯软件暂不保存第三方平台账号密码，不保存部署授权 token，不把订单、权益、配置会话写入 profile.json。验收状态以服务端返回为准。",
            "info",
        ).pack(fill="x", pady=(4, 12))

        actions = tk.Frame(frame, bg=CARD_BG)
        actions.pack(fill="x")
        for col in range(3):
            actions.grid_columnconfigure(col, weight=1, uniform="communication_software_link_acceptance_actions")
        self._grid_button(actions, "发送测试请求", self.start_communication_software_link_test, "secondary", 0, 0)
        self._grid_button(actions, "提交验收证据", self.start_communication_software_link_acceptance, "primary", 0, 1)
        self._grid_button(actions, "停用配置会话", self.start_communication_software_link_disable, "secondary", 0, 2)

    def has_valid_key(self) -> bool:
        return self.saved_key_ok and self.saved_key_signature == self.current_key_signature()

    def agents_ready(self) -> bool:
        return bool(self.selected_agents())

    def first_missing_step(self) -> tuple[int, str] | None:
        if not self.logged_in_user or not self.deployer_auth:
            return 1, "请登录胖虎AI账号并获取商业部署授权。"
        if not self.has_valid_key():
            return 1, "第一步还没完成：请填写胖虎AI API Key，并点击“保存并测试 Key”。"
        if not self.environment_ok:
            return 2, "第二步还没完成：请点击“检测环境”，并处理所有风险提示。"
        if not self.agents_ready():
            return 3, "第三步还没完成：请至少选择一个 Agent。"
        return None

    def can_access_step(self, idx: int) -> bool:
        if not self.logged_in_user or not self.deployer_auth:
            return False
        if idx == 1:
            return True
        if idx == 2:
            return self.has_valid_key()
        if idx == 3:
            return self.has_valid_key() and self.environment_ok
        if 4 <= idx <= 9:
            return self.first_missing_step() is None
        if idx in (10, 11):
            return True
        return False

    def go_to_step(self, idx: int) -> None:
        if self.can_access_step(idx):
            self.step.set(idx)
            self.refresh_steps()
            return
        missing = self.first_missing_step()
        if missing:
            target_step, message = missing
            self.step.set(target_step)
            self.refresh_steps()
            self.notify_warning("暂时不能进入下一步", message)

    def step_button_copy(self, idx: int) -> tuple[str, str, str]:
        copies = {step_idx: (title, subtitle) for step_idx, title, subtitle in FLOW_STEPS}
        title, subtitle = copies[idx]
        if idx == 1:
            status = "已完成" if self.has_valid_key() else "进行中"
        elif idx == 2:
            status = "已完成" if self.environment_ok else "进行中" if self.step.get() == 2 and self.can_access_step(2) else "未开始"
        elif idx == 3:
            status = "已完成" if self.agents_ready() and self.can_access_step(3) else "进行中" if self.step.get() == 3 and self.can_access_step(3) else "未开始"
        elif idx == 4:
            status = "进行中" if self.worker_running and self.step.get() == 4 else "可执行" if self.can_access_step(4) else "未开始"
        elif idx == 10:
            status = "可配置" if self.can_access_step(10) else "未开始"
        elif idx == 11:
            status = "待验收" if self.can_access_step(11) else "未开始"
        else:
            status = "进行中" if self.step.get() == idx else "待验收" if self.can_access_step(idx) else "未开始"
        return title, subtitle, status

    def current_flow_message(self) -> str:
        missing = self.first_missing_step()
        if not missing:
            return "客服提示：前 3 步已完成，进入安装与验收阶段。"
        return f"客服提示：{missing[1]}"

    def current_commercial_summary_text(self) -> str:
        if self.deployer_manifest and manifest_has_commercial_controls(self.deployer_manifest):
            lines = build_customer_commercial_summary_lines(self.commercial_products, self.commercial_entitlements)
            return "\n".join(lines[:6])
        if self.logged_in_user:
            return "已登录。商业商品、权益次数和有效期会在部署前从服务端清单刷新。"
        return "请先登录买家账号；商品、权益、次数、有效期和设备数均以服务端返回为准。"

    def refresh_commercial_summary(self) -> None:
        if getattr(self, 'webview_mode', False):
            self.sync_webview_state()
            return
        label = getattr(self, "commercial_summary_label", None)
        if label:
            label.configure(text=self.current_commercial_summary_text())

    def refresh_agent_commercial_states(self) -> None:
        if getattr(self, 'webview_mode', False):
            self.sync_webview_state()
            return
        commercial_manifest_present = bool(self.deployer_manifest and manifest_has_commercial_controls(self.deployer_manifest))
        for agent in AGENTS:
            state = build_agent_customer_state(
                agent.id,
                self.commercial_capabilities,
                commercial_manifest_present=commercial_manifest_present,
            )
            row = self.agent_rows.get(agent.id)
            if row:
                if state.visible:
                    row.grid()
                else:
                    row.grid_remove()
            enabled = self.agent_enabled.get(agent.id)
            if enabled is not None and not state.selectable:
                enabled.set(False)
            button = self.agent_checkbuttons.get(agent.id)
            if button:
                button.configure(state="normal" if state.selectable else "disabled")
            badge = self.agent_badge_labels.get(agent.id)
            if badge:
                badge.configure(
                    text=state.badge,
                    bg=GOLD_SOFT if state.selectable else LOCKED_BG,
                    fg=PRIMARY_DARK if state.selectable else MUTED,
                )
            note = self.agent_note_labels.get(agent.id)
            if note:
                note.configure(text=state.note)

    def refresh_recommended_agent_product(self) -> None:
        if not hasattr(self, "buyer_product_id"):
            return
        product = find_listed_product(
            self.commercial_products,
            agent_id="codex",
            mode_key=CodexConfigMode.DIRECT_API.value,
        )
        if product and not self.buyer_product_id.get().strip():
            self.buyer_product_id.set(product.product_id)
        if getattr(self, 'webview_mode', False):
            self.sync_webview_state()
        product = find_listed_product(
            self.commercial_products,
            agent_id="codex",
            mode_key=CodexConfigMode.DIRECT_API.value,
        )
        if product and not self.buyer_product_id.get().strip():
            self.buyer_product_id.set(product.product_id)

    def update_step_hints(self) -> None:
        hint_data = {
            1: (
                "已完成：Key 已保存并通过当前配置校验，可以进入第二步。"
                if self.has_valid_key()
                else "待完成：请创建或填写胖虎AI API Key，并点击“保存并测试 Key”。Key 不写入日志，默认使用公共域名。"
            ),
            2: (
                "已完成：环境检测通过，可以进入第三步。"
                if self.environment_ok
                else "待完成：点击“检测环境”，先处理所有风险提示。"
            ),
            3: (
                f"已完成：已选择 {len(self.selected_agents())} 个 Agent，可以进入第四步。"
                if self.agents_ready()
                else "待完成：至少选择一个 Agent。普通客户建议保留 Codex；ClaudeCode、OpenClaw、Hermes 只按已打通链路验收。"
            ),
            4: (
                "可执行：前三项前置检查已完成。普通客户点“一键部署（普通）”；需要登录态共存才点“双态配置”。"
                if self.can_access_step(4)
                else "未解锁：请先完成登录、Key 保存、环境检测和 Agent 选择。"
            ),
            5: (
                "待验收：部署执行后检查配置写入结果。买家密码只有用户勾选记住密码时才进入本机加密保存；部署授权 token 不落 profile.json，Key 不输出到日志。"
                if self.can_access_step(5)
                else "未解锁：请先完成前置检查并执行安装。"
            ),
            6: (
                "待验收：确认 CLI 或客户端入口可启动。需要重开终端时按提示处理后复验。"
                if self.can_access_step(6)
                else "未解锁：请先完成前置检查并执行安装。"
            ),
            7: (
                "待验收：对每个目标 Agent 执行最小中文对话。QQ、微信、TG 等第三方通道默认跳过。"
                if self.can_access_step(7)
                else "未解锁：请先完成前置检查并执行安装。"
            ),
            8: (
                "待验收：打开功能验收矩阵，逐项确认安装、启动、对话、验收、交付状态。"
                if self.can_access_step(8)
                else "未解锁：请先完成前置检查并执行安装。"
            ),
            9: (
                "待交付：矩阵全部达标后才算客户可交付；正式发客户前还要确认安装包和下载页。"
                if self.can_access_step(9)
                else "未解锁：请先完成前置检查并执行安装。"
            ),
            10: (
                "可配置：连接通讯软件是独立增值服务，可绑定本次、历史或已有本机 Agent；订单、通道和价格以服务端返回为准。"
                if self.can_access_step(10)
                else "未解锁：请先登录胖虎AI账号。"
            ),
            11: (
                "待验收：必须提交入站消息、Agent 调用、出站回复和证据 URL，服务端确认后才算连接通讯软件交付。"
                if self.can_access_step(11)
                else "未解锁：请先登录胖虎AI账号。"
            ),
        }
        for idx, label in getattr(self, "step_hint_labels", {}).items():
            ready = (
                idx == 1 and self.has_valid_key()
                or idx == 2 and self.environment_ok
                or idx == 3 and self.agents_ready()
            )
            unlocked = self.can_access_step(idx)
            label.configure(
                text=hint_data.get(idx, ""),
                bg=SUCCESS_BG if ready else INFO_BG,
                fg="#116047" if ready else PRIMARY_DARK if unlocked else MUTED,
            )

    def refresh_steps(self) -> None:
        if getattr(self, 'webview_mode', False):
            if not self.logged_in_user or not self.deployer_auth:
                self.step.set(1)
                self.active_module.set(MODULE_AGENT)
                self.active_subnav.set("1")
            elif self.active_module.get() == MODULE_AGENT:
                self.active_subnav.set(str(self.step.get()))
            self.sync_webview_state()
            return
        if not self.logged_in_user or not self.deployer_auth:
            self.step.set(1)
            if hasattr(self, "active_module"):
                self.active_module.set(MODULE_AGENT)
                self.active_subnav.set("1")
        elif hasattr(self, "active_module") and self.active_module.get() == MODULE_AGENT:
            self.active_subnav.set(str(self.step.get()))
        for idx, frame in self.step_canvases.items():
            if idx == self.step.get():
                frame.lift()
                canvas = frame.winfo_children()[0] if frame.winfo_children() else None
                if isinstance(canvas, tk.Canvas):
                    canvas.yview_moveto(0)
        for idx, button in getattr(self, "step_buttons", {}).items():
            active = idx == self.step.get()
            title, subtitle, status = self.step_button_copy(idx)
            locked = not self.can_access_step(idx)
            if "已完成" in status:
                dot_color = SUCCESS
            elif active or "进行中" in status:
                dot_color = RUNNING
            elif "失败" in status:
                dot_color = FAIL
            else:
                dot_color = NEUTRAL_DOT
            button.configure(
                text=f"{title}\n{status}",
                bg=PRIMARY_LIGHT if active else SIDEBAR_BG,
                fg=PRIMARY if active else MUTED if locked else INK,
                activebackground=PRIMARY_LIGHT,
                activeforeground=PRIMARY,
                state="normal" if not self.worker_running else "disabled",
            )
            dot = getattr(self, "step_status_dots", {}).get(idx)
            if dot:
                fill = PRIMARY if active else SUCCESS if dot_color == SUCCESS else WAIT_BG
                outline = PRIMARY if active else SUCCESS if dot_color == SUCCESS else WAIT_BORDER
                text_color = "#ffffff" if active or dot_color == SUCCESS else MUTED if locked else SECONDARY
                if isinstance(dot, tk.Canvas):
                    dot.configure(bg=SIDEBAR_BG)
                    dot.itemconfigure("circle", fill=fill, outline=outline)
                    dot.itemconfigure("label", fill=text_color, text=str(idx))
                else:
                    dot.configure(
                        fg=text_color,
                        bg=fill,
                        highlightbackground=outline,
                    )
        if hasattr(self, "flow_status_label"):
            if getattr(self, "active_module", WebviewStringVar(value=MODULE_AGENT)).get() == MODULE_AGENT:
                self.flow_status_label.configure(text=self.current_flow_message())
            else:
                _title, _url, note = self.current_module_page_meta()
                self.flow_status_label.configure(text=f"客服提示：{note}")
        self.refresh_commercial_summary()
        self.refresh_agent_commercial_states()
        self.refresh_recommended_agent_product()
        self.refresh_buyer_purchase_status()
        self.refresh_communication_software_link_panel()
        self.refresh_topbar()
        self.refresh_commercial_info_panel()
        self.refresh_agent_matrix_panel()
        self.update_step_hints()
        for idx, button in getattr(self, "step_next_buttons", {}).items():
            button.configure(state="normal" if self.can_access_step(idx + 1) and not self.worker_running else "disabled")
        ready_for_step_5 = self.can_access_step(4) and not self.worker_running
        for button in (getattr(self, "deploy_button", None), getattr(self, "dual_state_button", None), getattr(self, "config_button", None)):
            if button:
                button.configure(state="normal" if ready_for_step_5 else "disabled")
        official_ready = bool(self.logged_in_user and self.deployer_auth and self.environment_ok and not self.worker_running)
        official_button = getattr(self, "official_chatgpt_button", None)
        if official_button:
            official_button.configure(state="normal" if official_ready else "disabled")
        for button in (getattr(self, "restore_button", None), getattr(self, "update_button", None), getattr(self, "login_button", None)):
            if button:
                button.configure(state="disabled" if self.worker_running else "normal")
        self.refresh_module_nav()
        self._show_active_module_content()
        if self.logged_in_user and self.deployer_auth:
            self._show_wizard_shell()
        else:
            self._show_login_gate_shell()

    def toggle_key(self) -> None:
        self.key_entry.configure(show="" if self.show_key.get() else "*")

    def _js_push_worker(self) -> None:
        """专用 evaluate_js 执行线程。所有前端推送经 _push_js 入队后在此执行，
        保证任何线程（含 js_api 回调）调用推送都不会重入死锁。
        注意用 getattr 读 app_closed：本线程在 __init__ 早期启动，属性可能尚未赋值。"""
        while not getattr(self, "app_closed", False):
            try:
                script = self._js_push_queue.get(timeout=1.0)
            except queue.Empty:
                continue
            window = getattr(self, "webview_window", None)
            if window is None or not getattr(self, "webview_ready", False):
                continue  # 未就绪：丢弃，内容会随首次全量拉取带给前端
            try:
                window.evaluate_js(script)
            except Exception:
                pass

    def _push_js(self, script: str) -> None:
        if not getattr(self, "webview_mode", False):
            return
        try:
            self._js_push_queue.put_nowait(script)
        except Exception:
            pass

    def push_webview_toast(self, message: str, level: str = "info") -> None:
        """向 WebView 前端弹一条提示（异步入队，任何线程可安全调用）。"""
        if not getattr(self, "webview_mode", False):
            return
        safe = sanitize_log_text(message, *self._all_deploy_keys())
        self._push_js(
            f"(window.showToast||window.appendPythonLog)({json.dumps(safe)}, {json.dumps(level)})"
        )

    def log(self, message: str, replace: bool = False) -> None:
        safe = sanitize_log_text(message, *self._all_deploy_keys())
        tag = self._log_tag_for_message(safe)
        if getattr(self, 'webview_mode', False):
            current_step = self.step.get()
            if not hasattr(self, "webview_logs"):
                self.webview_logs = empty_flow_logs()
            now = time.strftime("%H:%M:%S")
            log_line = {"t": now, "c": tag_to_css(tag), "m": safe}
            if replace:
                self.webview_logs[current_step] = [log_line]
            else:
                self.webview_logs[current_step].append(log_line)
            if replace:
                self._push_js(f"logsData[{current_step}] = []; renderLogs();")
            self._push_js(f"appendPythonLog({json.dumps(log_line)})")
        else:
            self.log_box.configure(state="normal")
            if replace:
                self.log_box.delete("1.0", "end")
                self.log_box.insert("end", safe, tag)
            else:
                now = time.strftime("%H:%M:%S")
                self.log_box.insert("end", f"[{now}] {safe}\n", tag)
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
            self.root.update_idletasks()

    def close_app(self) -> None:
        self.app_closed = True
        cleanup_legacy_ephemeral_web_profiles()
        for handle in list(getattr(self, "after_handles", set())):
            try:
                self.root.after_cancel(handle)
            except (tk.TclError, AttributeError):
                pass
        self.after_handles.clear()
        try:
            self.root.destroy()
        except (tk.TclError, AttributeError):
            pass
        if getattr(self, "webview_window", None):
            try:
                self.webview_window.destroy()
            except Exception:
                pass

    def run_on_ui(self, callback) -> None:
        if self.app_closed:
            return
        if getattr(self, 'webview_mode', False):
            try:
                callback()
            except Exception as e:
                self.log(f"Error in run_on_ui: {e}")
        else:
            try:
                self.root.after(0, callback)
            except RuntimeError:
                self.app_closed = True

    def run_later(self, delay_ms: int, callback) -> None:
        if self.app_closed:
            return
        if getattr(self, 'webview_mode', False):
            def wrapped() -> None:
                if self.app_closed:
                    return
                try:
                    callback()
                except Exception as e:
                    self.log(f"Error in run_later callback: {e}")
            t = threading.Timer(delay_ms / 1000.0, wrapped)
            t.daemon = True
            t.start()
        else:
            def wrapped() -> None:
                if self.app_closed:
                    return
                self.after_handles.discard(handle)
                callback()

            try:
                handle = self.root.after(delay_ms, wrapped)
                self.after_handles.add(handle)
            except RuntimeError:
                self.app_closed = True

    def log_from_worker(self, message: str) -> None:
        self.run_on_ui(lambda: self.log(sanitize_worker_message(message)))

    def set_status_from_worker(self, message: str) -> None:
        self.run_on_ui(lambda: self.status.set(sanitize_worker_message(message)))

    def notify_user(self, title: str, message: str, level: str = "info") -> None:
        """统一用户提示出口（webview 安全）。

        webview 模式下 Tk messagebox 不可用：主线程阻塞在 webview.start()，
        Tk mainloop 永远不运行，bridge/后台线程调 messagebox 直接抛
        RuntimeError 并被上层 try/except 吞掉，表现为"点了无反应"。
        因此 webview 模式统一改为：写入运行日志 + 前端全局 toast。
        """
        safe = sanitize_worker_message(str(message))
        text = f"{title}：{safe}" if title else safe
        if getattr(self, 'webview_mode', False):
            self.log(text)
            self.push_webview_toast(text, level)
            return
        shows = {"info": messagebox.showinfo, "error": messagebox.showerror}
        shows.get(level, messagebox.showwarning)(title, safe)

    def notify_info(self, title: str, message: str) -> None:
        self.notify_user(title, message, "info")

    def notify_warning(self, title: str, message: str) -> None:
        self.notify_user(title, message, "warning")

    def notify_error(self, title: str, message: str) -> None:
        self.notify_user(title, message, "error")

    def show_info_from_worker(self, title: str, message: str) -> None:
        self.run_on_ui(lambda: self.notify_info(title, message))

    def show_warning_from_worker(self, title: str, message: str) -> None:
        self.run_on_ui(lambda: self.notify_warning(title, message))

    def show_error_from_worker(self, title: str, message: str) -> None:
        self.run_on_ui(lambda: self.notify_error(title, message))

    def set_busy(self, busy: bool) -> None:
        self.worker_running = busy
        self.refresh_steps()

    def key_model_for_agent(self, agent_id: str, fallback_key: str = "", fallback_model: str = "") -> tuple[str, str]:
        fmt = key_format_for_agent(agent_id)
        entry = (getattr(self, "deploy_keys", None) or {}).get(fmt) or {}
        key = (entry.get("key") or "").strip()
        model = (entry.get("model") or "").strip()
        if fmt == "openai":
            if not key:
                key = (fallback_key or "").strip() or (self.api_key.get().strip() if hasattr(self, "api_key") else "")
            if not model:
                model = (fallback_model or "").strip() or (self.model.get().strip() if hasattr(self, "model") else "") or DEFAULT_MODEL
        return key, model

    def _primary_deploy_key(self) -> str:
        dk = getattr(self, "deploy_keys", None) or {}
        for fmt in KEY_FORMAT_IDS:
            k = (dk.get(fmt, {}).get("key") or "").strip()
            if k:
                return k
        return self.api_key.get().strip()

    def _all_deploy_keys(self) -> list[str]:
        dk = getattr(self, "deploy_keys", None) or {}
        keys = [(dk.get(fmt, {}).get("key") or "").strip() for fmt in KEY_FORMAT_IDS]
        if hasattr(self, "api_key"):
            keys.append(self.api_key.get().strip())
        return [k for k in keys if k]

    def current_key_signature(self) -> tuple[str, str, str, bool]:
        return (
            self._primary_deploy_key(),
            DEFAULT_BASE_URL,
            self.model.get().strip(),
            self.skip_test.get(),
        )

    def mark_key_dirty(self, *_args) -> None:
        if self.saved_key_ok or self.saved_key_signature:
            self.saved_key_ok = False
            self.saved_key_signature = None
            self.status.set("状态：Key 已修改，请重新保存")
            self.refresh_steps()

    def mark_environment_dirty(self, *_args) -> None:
        if self.environment_checked or self.environment_ok:
            self.environment_checked = False
            self.environment_ok = False
            self.status.set("状态：系统选择已修改，请重新检测环境")
            self.refresh_steps()

    def mark_agent_selection_changed(self, *_args) -> None:
        self.refresh_steps()

    def start_login(self) -> None:
        if self.worker_running:
            return
        username = self.login_username.get()
        password = self.login_password.get()
        self.set_busy(True)
        self.status.set("状态：正在登录胖虎AI...")
        threading.Thread(target=self._login_worker, args=(username, password), daemon=True).start()

    def _login_worker(self, username: str, password: str) -> None:
        try:
            ok, msg, data = login_panghuai(username, password, self.cookie_jar)
            self.log_from_worker(msg)
            if not ok:
                self.set_status_from_worker("状态：登录失败")
                self.show_error_from_worker("登录失败", msg)
                return
            auth_ok, auth_msg, auth_data = activate_deployer(data, self.cookie_jar)
            self.log_from_worker(auth_msg)
            if not auth_ok:
                self.set_status_from_worker("状态：部署授权失败")
                self.show_error_from_worker("部署授权失败", auth_msg)
                return
            self.logged_in_user = data
            self.deployer_auth = auth_data
            self.commercial_contexts = self.build_buyer_contexts(data)
            buyer_profile = create_commercial_web_profile(self.commercial_contexts, str(web_profile_root()))
            ensure_commercial_web_profile_dir(buyer_profile)
            display_name = str(data.get("username") or username)
            save_buyer_session_state(data, self.cookie_jar)
            save_profile_data({"username": display_name}, self.commercial_contexts)
            
            # Save account state to login_accounts.json
            save_login_account_state(
                username=username,
                password=password,
                remember_password=self.remember_password.get(),
                auto_login=self.auto_login.get(),
                user_id=str(data.get("id") or ""),
            )

            display_username = display_name if len(display_name) <= 20 else f"{display_name[:17]}..."
            if hasattr(self, "user_label"):
                self.run_on_ui(lambda: self.user_label.configure(text=f"已登录：{display_username}"))
            self.run_on_ui(self.show_wizard)
            self.run_later(1200, self.start_auto_update_check)
            self.run_later(1600, self.start_refresh_commercial_manifest)
            self.set_status_from_worker("状态：已登录，请按步骤部署")
        finally:
            self.run_on_ui(lambda: self.set_busy(False))

    def start_auto_update_check(self) -> None:
        if self.worker_running or self.auto_update_checked:
            return
        self.auto_update_checked = True
        threading.Thread(target=lambda: self._update_worker(auto=True), daemon=True).start()

    def start_update_check(self) -> None:
        if self.worker_running:
            return
        self.set_busy(True)
        self.status.set("状态：正在检查更新...")
        threading.Thread(target=lambda: self._update_worker(auto=False), daemon=True).start()

    def _update_worker(self, auto: bool = False) -> None:
        try:
            update, msg, release_url = find_available_update()
            self.log_from_worker(msg)
            if update:
                self.set_status_from_worker(f"状态：发现新版本 {update.latest_tag}")
                self.run_on_ui(lambda: self.prompt_online_update(update, auto))
            elif release_url and "未找到" in msg and "更新包" in msg:
                self.set_status_from_worker("状态：发现新版本，请到发布页下载")
                self.run_on_ui(lambda: open_url(release_url))
                if not auto:
                    self.show_warning_from_worker("发现新版本", msg)
            elif "当前已是最新版本" in msg:
                self.set_status_from_worker("状态：当前已是最新版本")
                if not auto:
                    self.show_info_from_worker("检查更新", msg)
            else:
                self.set_status_from_worker("状态：检查更新失败")
                if not auto:
                    self.show_warning_from_worker("检查更新", msg)
        finally:
            if not auto:
                self.run_on_ui(lambda: self.set_busy(False))

    def prompt_online_update(self, update: UpdateInfo, auto: bool) -> None:
        if self.worker_running and auto:
            return
        message = (
            f"发现新版本 {update.latest_tag}（当前 {APP_VERSION}）。\n\n"
            "是否现在在线更新？\n\n"
            "工具会下载对应系统安装包，自动覆盖当前程序并重新打开。"
            "你的登录状态、API Key、Codex 配置和工作区资料都会保留。"
        )
        if getattr(self, 'webview_mode', False):
            # webview 模式无法用 Tk askyesno 阻塞等待用户确认；打包发布当前叫停中，
            # 先只提示不自动更新（后续接前端确认对话框后再放开自动更新链路）。
            self.notify_info(
                "发现新版本",
                f"检测到新版本 {update.latest_tag}（当前 {APP_VERSION}）。当前版本可继续使用，暂不自动更新。",
            )
            self.set_busy(False)
            return
        if not messagebox.askyesno("发现新版本", message):
            if auto:
                self.status.set("状态：已跳过本次自动更新")
            else:
                self.set_busy(False)
            return
        self.set_busy(True)
        self.status.set("状态：正在下载在线更新包...")
        threading.Thread(target=self._download_and_apply_update_worker, args=(update,), daemon=True).start()

    def _download_and_apply_update_worker(self, update: UpdateInfo) -> None:
        try:
            path = download_update_package(update, self.log_from_worker)
            self.log_from_worker(f"更新包已下载：{path}")
            self.set_status_from_worker("状态：准备在线更新")
            self.run_on_ui(lambda: self.confirm_and_start_online_update(path))
        except Exception as exc:
            self.set_status_from_worker("状态：在线更新失败")
            self.show_warning_from_worker("在线更新失败", str(exc))
            self.run_on_ui(lambda: self.set_busy(False))

    def confirm_and_start_online_update(self, path: Path) -> None:
        try:
            start_online_update(path, self.log)
            self.notify_info("开始在线更新", "更新程序已启动。本工具将退出，更新完成后会自动重新打开。")
            self.run_later(200, self.close_app)
        except Exception as exc:
            self.set_busy(False)
            self.notify_error("在线更新失败", sanitize_worker_message(str(exc)))

    def start_save_key(self) -> None:
        if self.worker_running:
            return
        if not self.logged_in_user:
            self.notify_warning("请先登录", "请先登录胖虎AI账号。")
            return
        if not self.deployer_auth:
            self.notify_warning("缺少部署授权", "请重新登录胖虎AI账号获取部署授权。")
            return
        api_key = self.api_key.get()
        self.base_url.set(DEFAULT_BASE_URL)
        base_url = DEFAULT_BASE_URL
        model = self.model.get()
        skip_test = self.skip_test.get()
        open_app = self.open_app.get()
        self.set_busy(True)
        self.status.set("状态：正在测试 API Key...")
        threading.Thread(target=self._save_key_worker, args=(api_key, base_url, model, skip_test, open_app), daemon=True).start()

    def _save_key_worker(self, api_key: str, base_url: str, model: str, skip_test: bool, open_app: bool) -> None:
        try:
            base_url = DEFAULT_BASE_URL
            if not api_key.strip():
                raise ValueError("请先填写胖虎AI API Key。")
            contexts = deployment_commercial_contexts(self.logged_in_user or {})
            self.log_from_worker(execute_api_key_owner_verify(api_key, contexts, opener=trusted_urlopen, deployer_auth=self.deployer_auth))
            if skip_test:
                ok, msg = True, "已保存 Key，接口测试被跳过。"
            else:
                base_url = DEFAULT_BASE_URL
                ok, msg = test_api(base_url, api_key)
            self.log_from_worker(msg)
            self.saved_key_ok = ok
            if ok:
                self.saved_key_signature = (api_key.strip(), DEFAULT_BASE_URL, model.strip(), skip_test)
                save_profile_data(
                    {
                        "api_key": api_key.strip(),
                        "base_url": DEFAULT_BASE_URL,
                        "model": model.strip(),
                        "skip_test": skip_test,
                        "open_app": open_app,
                    },
                    contexts,
                )
                self.set_status_from_worker("状态：Key 已保存")
                self.run_on_ui(lambda: self.step.set(2))
                self.run_on_ui(self.refresh_steps)
            else:
                self.set_status_from_worker("状态：Key 测试失败")
                self.show_warning_from_worker("Key 测试失败", msg)
        except Exception as exc:
            self.set_status_from_worker("状态：Key 保存失败")
            self.show_error_from_worker("Key 保存失败", str(exc))
        finally:
            self.run_on_ui(lambda: self.set_busy(False))

    def run_environment_check(self) -> None:
        if not self.has_valid_key():
            self.notify_warning("请先完成第一步", "请先保存并测试胖虎AI API Key，再检测环境。")
            self.step.set(1)
            self.refresh_steps()
            return
        lines = detect_environment()
        if not getattr(self, 'webview_mode', False):
            # env_text 是旧 Tk 界面控件，webview 模式不存在；结果统一走日志。
            self.env_text.configure(state="normal")
            self.env_text.delete("1.0", "end")
            self.env_text.insert("end", "\n".join(lines))
            self.env_text.configure(state="disabled")
        for line in lines:
            self.log(line)
        self.environment_checked = True
        risk_findings = detect_risk_plugins()
        self.environment_ok = not risk_findings
        if self.environment_ok:
            self.status.set("状态：环境检测通过")
            self.step.set(3)
        else:
            self.status.set("状态：发现第三方配置插件，请先处理")
            self.notify_warning("环境检测未通过", format_risk_plugin_block_message(risk_findings))
        self.refresh_steps()

    def selected_agents(self) -> list[tuple[AgentSpec, str]]:
        selected = []
        for agent in AGENTS:
            if self.agent_enabled[agent.id].get():
                selected.append((agent, self.agent_mode[agent.id].get()))
        return selected

    def validate_config_ready(self, mode: CodexConfigMode = CodexConfigMode.DIRECT_API) -> tuple[bool, tuple[str, str, str, bool] | None]:
        if self.worker_running:
            return False, None
        if not self.logged_in_user:
            self.notify_warning("请先登录", "请先登录胖虎AI账号。")
            return False, None
        if not self.deployer_auth:
            self.notify_warning("缺少部署授权", "请重新登录胖虎AI账号获取部署授权。")
            return False, None
        if not codex_config_mode_requires_panghu_key(mode):
            return True, self.current_key_signature()
        current_key_signature = self.current_key_signature()
        if not current_key_signature[0]:
            self.notify_warning("请先填写 Key", "请先在第一步填写胖虎AI API Key。")
            self.step.set(1)
            self.refresh_steps()
            return False, None
        if not self.saved_key_ok or self.saved_key_signature != current_key_signature:
            self.notify_warning("请先保存 Key", "请先在第一步保存当前胖虎AI API Key，然后再开始部署。")
            self.step.set(1)
            self.refresh_steps()
            return False, None
        return True, current_key_signature

    def validate_system_and_risk_plugins(self) -> bool:
        actual_system = current_system_id()
        if self.selected_system.get() != actual_system:
            readable = {"windows": "Windows", "mac": "Mac", "other": "其他系统"}
            self.notify_warning(
                "系统选择不一致",
                f"当前电脑识别为 {readable.get(actual_system, actual_system)}，"
                f"但你选择的是 {readable.get(self.selected_system.get(), self.selected_system.get())}。请回到第二步选择当前电脑系统。",
            )
            self.step.set(2)
            self.refresh_steps()
            return False
        risk_findings = detect_risk_plugins()
        if risk_findings:
            for line in risk_plugin_report_lines(risk_findings):
                self.log(line)
            self.notify_warning("请先卸载第三方插件", format_risk_plugin_block_message(risk_findings))
            self.status.set("状态：发现第三方配置插件，请先卸载后再部署")
            self.step.set(2)
            self.refresh_steps()
            return False
        return True

    def start_deploy(self) -> None:
        ok, _current_key_signature = self.validate_config_ready()
        if not ok:
            return
        if not self.can_access_step(4):
            self.go_to_step(4)
            return
        selected = self.selected_agents()
        if not selected:
            self.notify_warning("请选择 Agent", "请至少选择一个 Agent。")
            return
        if not self.validate_system_and_risk_plugins():
            return
        user = dict(self.logged_in_user or {})
        contexts = deployment_commercial_contexts(user)
        self.commercial_contexts = contexts
        deployer_auth = dict(self.deployer_auth or {})
        api_key = self.api_key.get()
        self.base_url.set(DEFAULT_BASE_URL)
        base_url = DEFAULT_BASE_URL
        model = self.model.get()
        skip_test = self.skip_test.get()
        open_app = self.open_app.get()
        self.set_busy(True)
        self.status.set("状态：正在部署 Agent...")
        threading.Thread(
            target=self._deploy_worker,
            args=(selected, user, deployer_auth, contexts, api_key, base_url, model, skip_test, open_app),
            daemon=True,
        ).start()

    def start_config_only(self) -> None:
        self.start_config_for_mode(CodexConfigMode.DIRECT_API)

    def start_dual_state_config(self) -> None:
        self.start_config_for_mode(CodexConfigMode.DUAL_STATE)

    def start_official_chatgpt_config(self) -> None:
        self.start_config_for_mode(CodexConfigMode.OFFICIAL_CHATGPT)

    def start_config_for_mode(self, mode: CodexConfigMode) -> None:
        ok, _current_key_signature = self.validate_config_ready(mode)
        if not ok:
            return
        if not codex_config_mode_requires_panghu_key(mode) and not self.environment_ok:
            self.step.set(2)
            self.refresh_steps()
            self.notify_warning("请先检测环境", "请先完成第二步环境检测，再切换官方直登模式。")
            return
        if not self.can_access_step(4) and codex_config_mode_requires_panghu_key(mode):
            self.go_to_step(4)
            return
        if not self.validate_system_and_risk_plugins():
            return
        user = dict(self.logged_in_user or {})
        contexts = deployment_commercial_contexts(user)
        self.commercial_contexts = contexts
        deployer_auth = dict(self.deployer_auth or {})
        api_key = self.api_key.get()
        self.base_url.set(DEFAULT_BASE_URL)
        base_url = DEFAULT_BASE_URL
        model = self.model.get()
        skip_test = self.skip_test.get()
        open_app = self.open_app.get()
        if mode == CodexConfigMode.DUAL_STATE:
            status = "状态：正在写入 Codex 双态模式配置..."
            target = self._config_only_worker
        elif mode == CodexConfigMode.OFFICIAL_CHATGPT:
            status = "状态：正在切换 Codex 官方直登模式..."
            target = self._config_only_worker
        else:
            status = "状态：正在修复 Codex 普通配置..."
            target = self._config_only_worker
        self.set_busy(True)
        self.status.set(status)
        threading.Thread(
            target=target,
            args=(user, deployer_auth, contexts, api_key, base_url, model, skip_test, open_app, mode),
            daemon=True,
        ).start()

    def _config_only_worker(
        self,
        user: dict,
        deployer_auth: dict,
        contexts,
        api_key: str,
        base_url: str,
        model: str,
        skip_test: bool,
        open_app: bool,
        mode: CodexConfigMode,
    ) -> None:
        config_session_ids: dict[tuple[str, str], str] = {}
        completed_session_keys: set[tuple[str, str]] = set()
        diagnostic_code = ""
        try:
            diagnostic_code = self.next_diagnostic_code()
            self.log_from_worker(f"商业版诊断码：{diagnostic_code}")
            token = str(deployer_auth.get("token") or "")
            ok_manifest, msg, manifest = fetch_deployer_manifest(user, self.cookie_jar, token)
            self.log_from_worker(msg)
            if not ok_manifest:
                raise RuntimeError(msg)
            ensure_commercial_manifest_trusted(manifest)
            self.deployer_manifest = manifest
            self.apply_commercial_manifest_snapshot(manifest)
            config_session_id, reserve_summary = codex_config_session_reserve_from_manifest(
                manifest=manifest,
                mode=mode,
                contexts=contexts,
                diagnostic_code=diagnostic_code,
                opener=trusted_urlopen,
                deployer_auth=deployer_auth,
            )
            if config_session_id:
                config_session_ids[("codex", commercial_mode_key_for_config_mode(mode))] = config_session_id
                self.log_from_worker(f"配置会话已预占：{mask_business_identifier(config_session_id)}；{reserve_summary}")
            temporary_access = None if mode == CodexConfigMode.OFFICIAL_CHATGPT else parse_temporary_openai_access_config(manifest)
            ok = install_codex_config(
                api_key,
                base_url,
                model,
                skip_test,
                open_app,
                self.log_from_worker,
                temporary_access,
                mode,
            )
            if ok:
                self.set_status_from_worker("状态：Codex 配置修复完成")
                progress = DeploymentProgress()
                progress.mark(DeploymentNode.CONFIG_WRITE, NodeStatus.PASS)
                mode_key = commercial_mode_key_for_config_mode(mode)
                if mode == CodexConfigMode.OFFICIAL_CHATGPT:
                    probe_ok = True
                    probe_excerpt = "官方直登模式已写入；需重开 Codex 后用用户自己的 ChatGPT 账号完成对话验收。"
                else:
                    probe_ok, probe_excerpt = run_real_task_probe(base_url, api_key, model)
                real_task = verify_real_task_evidence(
                    diagnostic_code=diagnostic_code,
                    agent_id="codex",
                    mode_key=mode_key,
                    request_ok=True,
                    response_ok=probe_ok,
                    response_excerpt=probe_excerpt,
                )
                progress.mark(DeploymentNode.REAL_TASK_VERIFY, real_task.status)
                self.log_from_worker(build_real_task_diagnostic_summary(real_task, api_key))
                if mode == CodexConfigMode.DUAL_STATE:
                    message = (
                        "Codex 双态模式配置已写入，不会重新安装 Agent。\n\n"
                        "请先完全退出 Codex，再重新打开 Codex；新的配置只有重开后才会生效。\n\n"
                        "双态模式需要用户重新打开后自行登录自己的 ChatGPT 账号。登录态来自用户账号，模型消耗走胖虎AI API Key。"
                    )
                elif mode == CodexConfigMode.OFFICIAL_CHATGPT:
                    message = (
                        "Codex 官方直登模式已写入，不会重新安装 Agent。\n\n"
                        "请先完全退出 Codex，再重新打开 Codex；新的配置只有重开后才会生效。\n\n"
                        "官方直登模式消耗用户自己的 ChatGPT 账号额度；如 Codex 未登录，请在重开后登录自己的 ChatGPT 账号。"
                    )
                else:
                    message = (
                        "Codex 普通直接 API 配置已重新写入，不会重新安装 Agent。\n\n"
                        "请先完全退出 Codex，再重新打开 Codex；新的配置只有重开后才会生效。"
                    )
                if config_session_id and real_task.passed:
                    _data, summary = execute_config_session_complete(
                        config_session_id,
                        diagnostic_code,
                        opener=trusted_urlopen,
                        contexts=contexts,
                        deployer_auth=deployer_auth,
                    )
                    completed_session_keys.add(("codex", commercial_mode_key_for_config_mode(mode)))
                    self.log_from_worker(f"真实任务已通过；商业交付成功已提交：{summary}")
                elif config_session_id:
                    _data, summary = execute_config_session_fail(
                        config_session_id,
                        diagnostic_code,
                        real_task.customer_message,
                        opener=trusted_urlopen,
                        contexts=contexts,
                        deployer_auth=deployer_auth,
                    )
                    completed_session_keys.add(("codex", commercial_mode_key_for_config_mode(mode)))
                    self.log_from_worker(f"真实任务未通过；已提交失败且不扣次：{summary}")
                else:
                    self.log_from_worker("配置写入成功；当前未获得服务端配置会话 ID，本次不提交成功、不扣次。")
                delivery_report = build_customer_delivery_report(
                    diagnostic_code=diagnostic_code,
                    progress=progress,
                    reserved=bool(config_session_id),
                    agent_id="codex",
                    mode_key=commercial_mode_key_for_config_mode(mode),
                    api_key=api_key,
                    commercial_ids=[config_session_id],
                )
                self.log_from_worker(delivery_report.customer_message)
                self.show_info_from_worker("配置完成", message + "\n\n" + delivery_report.customer_message)
            else:
                progress = DeploymentProgress()
                progress.mark(DeploymentNode.CONFIG_WRITE, NodeStatus.FAILED)
                if config_session_id:
                    _data, summary = execute_config_session_fail(
                        config_session_id,
                        diagnostic_code,
                        "Codex 配置测试失败，已恢复备份。",
                        opener=trusted_urlopen,
                        contexts=contexts,
                        deployer_auth=deployer_auth,
                    )
                    completed_session_keys.add(("codex", commercial_mode_key_for_config_mode(mode)))
                    self.log_from_worker(f"配置写入失败；已提交失败且不扣次：{summary}")
                delivery_report = build_customer_delivery_report(
                    diagnostic_code=diagnostic_code,
                    progress=progress,
                    reserved=bool(config_session_id),
                    agent_id="codex",
                    mode_key=commercial_mode_key_for_config_mode(mode),
                    api_key=api_key,
                    commercial_ids=[config_session_id],
                )
                self.log_from_worker(delivery_report.support_packet)
                self.set_status_from_worker("状态：Codex 配置测试失败，已恢复备份")
                self.log_from_worker(delivery_report.customer_message)
                self.show_warning_from_worker("配置测试失败", "配置写入后接口测试失败，已自动恢复备份。\n\n" + delivery_report.customer_message)
        except Exception as exc:
            for summary in fail_unfinished_config_sessions(
                config_session_ids,
                completed_session_keys,
                diagnostic_code,
                "配置流程异常中断，未形成完整交付。",
                opener=trusted_urlopen,
                contexts=contexts,
                deployer_auth=deployer_auth,
            ):
                self.log_from_worker(f"异常兜底：已提交失败且不扣次：{summary}")
            self.set_status_from_worker("状态：Codex 配置修复失败")
            self.log_from_worker(f"Codex 配置修复失败：{exc}")
            self.show_error_from_worker("配置修复失败", customer_error_with_diagnostic(exc, diagnostic_code))
        finally:
            self.run_on_ui(lambda: self.set_busy(False))

    def _deploy_worker(
        self,
        selected: list[tuple[AgentSpec, str]],
        user: dict,
        deployer_auth: dict,
        contexts,
        api_key: str,
        base_url: str,
        model: str,
        skip_test: bool,
        open_app: bool,
    ) -> None:
        config_session_ids: dict[tuple[str, str], str] = {}
        completed_session_keys: set[tuple[str, str]] = set()
        diagnostic_code = ""
        try:
            buyer_user_id = contexts.target_buyer.user_id
            operator_user_id = contexts.operator.user_id
            diagnostic_code = self.next_diagnostic_code()
            self.log_from_worker(f"商业版诊断码：{diagnostic_code}")
            token = str(deployer_auth.get("token") or "")
            ok, msg, manifest = fetch_deployer_manifest(user, self.cookie_jar, token)
            self.log_from_worker(msg)
            if not ok:
                raise RuntimeError(msg)
            ensure_commercial_manifest_trusted(manifest)
            self.deployer_manifest = manifest
            self.commercial_capabilities = manifest_commercial_capabilities(manifest)
            self.commercial_products = manifest_commercial_products(manifest)
            self.value_added_services = manifest_value_added_services(manifest)
            self.commercial_entitlements = manifest_commercial_entitlements(manifest)
            self.run_on_ui(self.refresh_commercial_summary)
            commercial_manifest_present = manifest_has_commercial_controls(manifest)
            allowed_agents = set(manifest_allowed_agents(manifest))
            blocked = [agent.name for agent, _ in selected if agent.id not in allowed_agents]
            if blocked:
                raise RuntimeError("当前账号未授权安装：" + "、".join(blocked))
            commercial_blockers = commercial_deployment_blockers(
                [agent.id for agent, _ in selected],
                self.commercial_capabilities,
            )
            if commercial_blockers:
                raise RuntimeError("服务端商业策略已阻止部署：" + "；".join(commercial_blockers))
            if commercial_manifest_present:
                for line in build_customer_commercial_summary_lines(self.commercial_products, self.commercial_entitlements):
                    self.log_from_worker(line)
            for agent, mode in selected:
                commercial_mode_key = commercial_mode_key_for_deployment(agent.id, mode)
                gate = commercial_config_gate(
                    agent_id=agent.id,
                    mode_key=commercial_mode_key,
                    capabilities=self.commercial_capabilities,
                    entitlements=self.commercial_entitlements,
                    commercial_manifest_present=commercial_manifest_present,
                )
                if not gate.allowed:
                    raise RuntimeError(gate.message)
                if gate.entitlement_id:
                    config_session_id, reserve_summary = execute_config_session_reserve(
                        entitlement_id=gate.entitlement_id,
                        buyer_user_id=buyer_user_id,
                        operator_user_id=operator_user_id,
                        agent_id=agent.id,
                        mode_key=commercial_mode_key,
                        diagnostic_code=diagnostic_code,
                        opener=trusted_urlopen,
                        contexts=contexts,
                        deployer_auth=deployer_auth,
                    )
                    config_session_ids[(agent.id, commercial_mode_key)] = config_session_id
                    self.log_from_worker(f"商业门禁通过：{agent.name}/{commercial_mode_key} 已匹配可用权益。")
                    self.log_from_worker(f"配置会话已预占：{mask_business_identifier(config_session_id)}；{reserve_summary}")
            temporary_access = parse_temporary_openai_access_config(manifest)
            self.log_from_worker("开始普通一键部署：" + "、".join(f"{a.name}/{m}" for a, m in selected))
            agent_progress: dict[tuple[str, str], DeploymentProgress] = {}
            real_task_results: dict[tuple[str, str], object] = {}
            success_count = 0
            for agent, mode in selected:
                commercial_mode_key = commercial_mode_key_for_deployment(agent.id, mode)
                session_key = (agent.id, commercial_mode_key)
                progress = DeploymentProgress()
                agent_progress[session_key] = progress
                if install_agent(agent, mode, self.log_from_worker):
                    progress.mark(DeploymentNode.INSTALL, NodeStatus.PASS)
                    try:
                        a_key, a_model = self.key_model_for_agent(agent.id, api_key, model)
                        if not a_key:
                            self.log_from_worker(f"{agent.name}/{mode} 未填写「{KEY_FORMAT_LABELS.get(key_format_for_agent(agent.id), '')}」的 API Key，跳过配置写入。")
                            progress.mark(DeploymentNode.CONFIG_WRITE, NodeStatus.NEEDS_MANUAL)
                        else:
                            configured = apply_agent_config_plan(agent, mode, a_key, a_model, self.log_from_worker)
                            progress.mark(DeploymentNode.CONFIG_WRITE, NodeStatus.PASS if configured else NodeStatus.NEEDS_MANUAL)
                    except Exception as exc:
                        progress.mark(DeploymentNode.CONFIG_WRITE, NodeStatus.FAILED)
                        self.log_from_worker(f"{agent.name}/{mode} 配置写入失败：{exc}")
                    success_count += 1
                else:
                    progress.mark(DeploymentNode.INSTALL, NodeStatus.FAILED)
                    progress.mark(DeploymentNode.CONFIG_WRITE, NodeStatus.FAILED)
            if any(agent.id == "codex" for agent, _ in selected):
                codex_key, codex_model = self.key_model_for_agent("codex", api_key, model)
                ok = install_codex_config(
                    codex_key,
                    base_url,
                    codex_model,
                    skip_test,
                    open_app,
                    self.log_from_worker,
                    temporary_access,
                )
                codex_progress = agent_progress.setdefault(("codex", CodexConfigMode.DIRECT_API.value), DeploymentProgress())
                if ok:
                    codex_progress.mark(DeploymentNode.INSTALL, NodeStatus.PASS)
                    codex_progress.mark(DeploymentNode.CONFIG_WRITE, NodeStatus.PASS)
                    codex_progress.mark(DeploymentNode.LAUNCH_VERIFY, NodeStatus.NEEDS_MANUAL)
                    self.log_from_worker("Codex 胖虎AI配置已应用。")
                    probe_ok, probe_excerpt = run_real_task_probe(base_url, codex_key, codex_model)
                    real_task = verify_real_task_evidence(
                        diagnostic_code=diagnostic_code,
                        agent_id="codex",
                        mode_key=CodexConfigMode.DIRECT_API.value,
                        request_ok=True,
                        response_ok=probe_ok,
                        response_excerpt=probe_excerpt,
                    )
                    real_task_results[("codex", CodexConfigMode.DIRECT_API.value)] = real_task
                    codex_progress.mark(DeploymentNode.REAL_TASK_VERIFY, real_task.status)
                    self.log_from_worker(build_real_task_diagnostic_summary(real_task, api_key))
                    config_session_id = config_session_ids.get(("codex", CodexConfigMode.DIRECT_API.value), "")
                    if real_task.passed:
                        if config_session_id:
                            _data, summary = execute_config_session_complete(
                                config_session_id,
                                diagnostic_code,
                                opener=trusted_urlopen,
                                contexts=contexts,
                                deployer_auth=deployer_auth,
                            )
                            completed_session_keys.add(("codex", CodexConfigMode.DIRECT_API.value))
                            self.log_from_worker(f"真实任务已通过；商业交付成功已提交：{summary}")
                        else:
                            self.log_from_worker("真实任务已通过；当前未获得服务端配置会话 ID，本次不提交成功、不扣次。")
                    else:
                        if config_session_id:
                            _data, summary = execute_config_session_fail(
                                config_session_id,
                                diagnostic_code,
                                real_task.customer_message,
                                opener=trusted_urlopen,
                                contexts=contexts,
                                deployer_auth=deployer_auth,
                            )
                            completed_session_keys.add(("codex", CodexConfigMode.DIRECT_API.value))
                            self.log_from_worker(f"真实任务未通过；已提交失败且不扣次：{summary}")
                        else:
                            self.log_from_worker("真实任务未通过；本次不提交成功、不扣次。")
                else:
                    codex_progress.mark(DeploymentNode.CONFIG_WRITE, NodeStatus.FAILED)
                    config_session_id = config_session_ids.get(("codex", CodexConfigMode.DIRECT_API.value), "")
                    if config_session_terminal_action(codex_progress, reserved=bool(config_session_id)) == "fail":
                        _data, summary = execute_config_session_fail(
                            config_session_id,
                            diagnostic_code,
                            "Codex 配置写入或接口测试失败，已恢复备份。",
                            opener=trusted_urlopen,
                            contexts=contexts,
                            deployer_auth=deployer_auth,
                        )
                        completed_session_keys.add(("codex", CodexConfigMode.DIRECT_API.value))
                        self.log_from_worker(f"配置写入失败；已提交失败且不扣次：{summary}")
            for agent, mode in selected:
                if agent.id == "codex":
                    continue
                commercial_mode_key = commercial_mode_key_for_deployment(agent.id, mode)
                session_key = (agent.id, commercial_mode_key)
                progress = agent_progress.setdefault(session_key, DeploymentProgress())
                if progress.status_for(DeploymentNode.CONFIG_WRITE) != NodeStatus.PASS:
                    continue
                if agent_mode_requires_client_scope(mode):
                    client_ok, client_excerpt = verify_agent_client_scope(agent, mode)
                    config_written = progress.status_for(DeploymentNode.CONFIG_WRITE) == NodeStatus.PASS
                    progress.mark(DeploymentNode.LAUNCH_VERIFY, NodeStatus.PASS if client_ok else NodeStatus.FAILED)
                    self.log_from_worker(client_excerpt)
                    # 产品决策：桌面客户端无法自动做联网对话验收，退而求其次——
                    # 官方客户端已安装 + 配置已写入即视为客户端交付合格并扣次。
                    # CLI-only Agent 在 verify_agent_client_scope 处已 client_ok=False，仍会判失败。
                    real_task = verify_client_scope_delivery_evidence(
                        diagnostic_code=diagnostic_code,
                        agent_id=agent.id,
                        mode_key=commercial_mode_key,
                        client_installed=client_ok,
                        config_written=config_written,
                        detail=client_excerpt,
                    )
                    progress.mark(DeploymentNode.REAL_TASK_VERIFY, real_task.status)
                    real_task_results[session_key] = real_task
                    self.log_from_worker(build_real_task_diagnostic_summary(real_task, api_key))
                    config_session_id = config_session_ids.get(session_key, "")
                    if real_task.passed:
                        if config_session_id:
                            _data, summary = execute_config_session_complete(
                                config_session_id,
                                diagnostic_code,
                                opener=trusted_urlopen,
                                contexts=contexts,
                                deployer_auth=deployer_auth,
                            )
                            completed_session_keys.add(session_key)
                            self.log_from_worker(f"{agent.name}/{commercial_mode_key} 客户端交付已完成（安装+配置）；已提交成功并扣次：{summary}")
                        else:
                            self.log_from_worker(f"{agent.name}/{commercial_mode_key} 客户端交付已完成（安装+配置）；当前未获得服务端配置会话 ID，本次不提交成功、不扣次。")
                    else:
                        if config_session_id:
                            _data, summary = execute_config_session_fail(
                                config_session_id,
                                diagnostic_code,
                                real_task.customer_message,
                                opener=trusted_urlopen,
                                contexts=contexts,
                                deployer_auth=deployer_auth,
                            )
                            completed_session_keys.add(session_key)
                            self.log_from_worker(f"{agent.name}/{commercial_mode_key} 客户端未形成完整交付；已提交失败且不扣次：{summary}")
                    continue
                verified, version = version_for(agent.verify_command)
                progress.mark(DeploymentNode.LAUNCH_VERIFY, NodeStatus.PASS if verified else NodeStatus.NEEDS_MANUAL)
                if not verified:
                    self.log_from_worker(f"{agent.name}/{mode} 命令暂未在 PATH 中可用，无法执行最小对话验收；可能需要重开终端或重启客户端。")
                    progress.mark(DeploymentNode.REAL_TASK_VERIFY, NodeStatus.FAILED)
                    continue
                self.log_from_worker(f"{agent.name}/{mode} 启动检测通过：{version or '已安装'}")
                probe_ok, probe_excerpt = run_agent_dialogue_probe(agent, mode, self.key_model_for_agent(agent.id, api_key, model)[1])
                real_task = verify_real_task_evidence(
                    diagnostic_code=diagnostic_code,
                    agent_id=agent.id,
                    mode_key=commercial_mode_key,
                    request_ok=True,
                    response_ok=probe_ok,
                    response_excerpt=probe_excerpt,
                )
                real_task_results[session_key] = real_task
                progress.mark(DeploymentNode.REAL_TASK_VERIFY, real_task.status)
                self.log_from_worker(build_real_task_diagnostic_summary(real_task, api_key))
                config_session_id = config_session_ids.get(session_key, "")
                if real_task.passed and config_session_id:
                    _data, summary = execute_config_session_complete(
                        config_session_id,
                        diagnostic_code,
                        opener=trusted_urlopen,
                        contexts=contexts,
                        deployer_auth=deployer_auth,
                    )
                    completed_session_keys.add(session_key)
                    self.log_from_worker(f"{agent.name}/{commercial_mode_key} 最小对话已通过；商业交付成功已提交：{summary}")
                elif config_session_id:
                    _data, summary = execute_config_session_fail(
                        config_session_id,
                        diagnostic_code,
                        real_task.customer_message,
                        opener=trusted_urlopen,
                        contexts=contexts,
                        deployer_auth=deployer_auth,
                    )
                    completed_session_keys.add(session_key)
                    self.log_from_worker(f"{agent.name}/{commercial_mode_key} 最小对话未通过；已提交失败且不扣次：{summary}")
            for session_key, session_id in list(config_session_ids.items()):
                if session_key in completed_session_keys:
                    continue
                progress = agent_progress.get(session_key, DeploymentProgress())
                if config_session_terminal_action(progress, reserved=bool(session_id)) == "fail":
                    _data, summary = execute_config_session_fail(
                        session_id,
                        diagnostic_code,
                        "该 Agent 当前未完成自动配置和真实任务验证。",
                        opener=trusted_urlopen,
                        contexts=contexts,
                        deployer_auth=deployer_auth,
                    )
                    self.log_from_worker(f"{session_key[0]}/{session_key[1]} 未形成完整交付；已提交失败且不扣次：{summary}")
            write_agent_setup_guide(selected, api_key, self.log_from_worker)
            acceptance_matrix = build_customer_agent_acceptance_matrix(selected, agent_progress, real_task_results, diagnostic_code)
            write_customer_agent_acceptance_matrix(selected, agent_progress, real_task_results, diagnostic_code, self.log_from_worker)
            self.log_from_worker(acceptance_matrix)
            combined_progress = DeploymentProgress()
            for node in DeploymentNode:
                statuses = [progress.status_for(node) for progress in agent_progress.values()]
                if any(status == NodeStatus.FAILED for status in statuses):
                    combined_progress.mark(node, NodeStatus.FAILED)
                elif statuses and all(status == NodeStatus.PASS for status in statuses):
                    combined_progress.mark(node, NodeStatus.PASS)
                elif any(status == NodeStatus.NEEDS_MANUAL for status in statuses):
                    combined_progress.mark(node, NodeStatus.NEEDS_MANUAL)
            delivery_report = build_customer_delivery_report(
                diagnostic_code=diagnostic_code,
                progress=combined_progress,
                reserved=bool(config_session_ids),
                agent_id="codex" if any(agent.id == "codex" for agent, _ in selected) else selected[0][0].id,
                mode_key=CodexConfigMode.DIRECT_API.value if any(agent.id == "codex" for agent, _ in selected) else selected[0][1],
                api_key=api_key,
                commercial_ids=list(config_session_ids.values()),
            )
            result_note = delivery_report.customer_message
            self.log_from_worker(result_note)
            self.log_from_worker(delivery_report.support_packet)
            self.set_status_from_worker(f"状态：部署动作完成，成功处理 {success_count}/{len(selected)} 个 Agent")
            self.show_info_from_worker("部署动作完成", result_note + "\n\n请查看日志确认每个 Agent 的状态。")
        except Exception as exc:
            for summary in fail_unfinished_config_sessions(
                config_session_ids,
                completed_session_keys,
                diagnostic_code,
                "部署流程异常中断，未形成完整交付。",
                opener=trusted_urlopen,
                contexts=contexts,
                deployer_auth=deployer_auth,
            ):
                self.log_from_worker(f"异常兜底：已提交失败且不扣次：{summary}")
            self.set_status_from_worker("状态：部署失败")
            self.log_from_worker(f"部署失败：{exc}")
            self.show_error_from_worker("部署失败", customer_error_with_diagnostic(exc, diagnostic_code))
        finally:
            self.run_on_ui(lambda: self.set_busy(False))

    def start_refresh_commercial_manifest(self) -> None:
        if not self.logged_in_user or not self.deployer_auth:
            return
        user = dict(self.logged_in_user)
        deployer_auth = dict(self.deployer_auth)
        threading.Thread(target=self._refresh_commercial_manifest_worker, args=(user, deployer_auth), daemon=True).start()

    def _refresh_commercial_manifest_worker(self, user: dict, deployer_auth: dict) -> None:
        token = str(deployer_auth.get("token") or "")
        ok, msg, manifest = fetch_deployer_manifest(user, self.cookie_jar, token)
        self.log_from_worker(msg)
        if not ok:
            self.log_from_worker("商业权益状态暂未刷新；部署前会再次校验。")
            return
        try:
            ensure_commercial_manifest_trusted(manifest)
        except RuntimeError as exc:
            self.log_from_worker(str(exc))
            self.log_from_worker("商业权益状态暂未刷新；部署前会再次校验。")
            return
        self.deployer_manifest = manifest
        self.apply_commercial_manifest_snapshot(manifest)
        if manifest_has_commercial_controls(manifest):
            for line in build_customer_commercial_summary_lines(self.commercial_products, self.commercial_entitlements):
                self.log_from_worker(line)

    def fetch_temporary_openai_access(
        self,
        user: dict,
        deployer_auth: dict,
        mode: CodexConfigMode = CodexConfigMode.DIRECT_API,
    ) -> TemporaryOpenAIAccessConfig | None:
        token = str(deployer_auth.get("token") or "")
        ok, msg, manifest = fetch_deployer_manifest(user, self.cookie_jar, token)
        self.log_from_worker(msg)
        if not ok:
            self.log_from_worker("未能刷新部署清单，本次只修复 Codex 配置，不开启 OpenAI 官网临时访问窗口。")
            return None
        ensure_commercial_manifest_trusted(manifest)
        self.deployer_manifest = manifest
        self.apply_commercial_manifest_snapshot(manifest)
        mode_key = commercial_mode_key_for_config_mode(mode)
        commercial_manifest_present = manifest_has_commercial_controls(manifest)
        gate = commercial_config_gate(
            agent_id="codex",
            mode_key=mode_key,
            capabilities=self.commercial_capabilities,
            entitlements=self.commercial_entitlements,
            commercial_manifest_present=commercial_manifest_present,
        )
        if not gate.allowed:
            raise RuntimeError(gate.message)
        return parse_temporary_openai_access_config(manifest)

    def apply_commercial_manifest_snapshot(self, manifest: dict) -> None:
        self.commercial_capabilities = manifest_commercial_capabilities(manifest)
        self.commercial_products = manifest_commercial_products(manifest)
        self.value_added_services = manifest_value_added_services(manifest)
        self.commercial_entitlements = manifest_commercial_entitlements(manifest)
        center = manifest.get("agent_center") if isinstance(manifest, dict) else None
        if isinstance(center, dict):
            self.agent_center_live_data = parse_agent_center_snapshot_data(center)
        self.run_on_ui(self.refresh_steps)
        self.run_on_ui(self.sync_webview_state)

    def open_workspace(self) -> None:
        path = workspace_root()
        path.mkdir(parents=True, exist_ok=True)
        open_path(path)

    def open_config_dir(self) -> None:
        path = codex_home()
        path.mkdir(parents=True, exist_ok=True)
        open_path(path)

    def open_acceptance_matrix(self) -> None:
        path = customer_acceptance_matrix_path()
        if not path.exists():
            self.notify_warning("功能验收矩阵", "还没有生成验收矩阵。请先执行一次部署或配置验收。")
            return
        open_path(path)

    def restore_backups(self) -> None:
        if self.worker_running:
            return
        ok = restore_latest_backups(self.log)
        if ok:
            self.status.set("状态：已恢复最近备份")
            self.notify_info("恢复备份", "已恢复找到的最近备份。")
        else:
            self.status.set("状态：未找到可恢复备份")
            self.notify_warning("恢复备份", "未找到可恢复的配置备份。")

    def copy_logs(self) -> None:
        text = sanitize_worker_message(self.log_box.get("1.0", "end").strip())
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status.set("状态：日志已复制")


def self_test() -> None:
    assert APP_VERSION == "1.0.16"
    assert any(agent.id == "codex" for agent in AGENTS)
    assert any(agent.id == "claude_code" for agent in AGENTS)
    assert [agent.id for agent in AGENTS] == ["codex", "claude_code", "openclaw", "hermes", "gemini_agy"]
    gemini = next(agent for agent in AGENTS if agent.id == "gemini_agy")
    assert all(mode.supports_config for mode in gemini.modes)
    assert "agy" in agent_dialogue_probe_command_text(gemini, DEFAULT_MODEL)
    assert "GEMINI_API_KEY=sk-test" in build_gemini_agy_env("", "sk-test", DEFAULT_MODEL)
    assert any(spec.id == "ccswitch" for spec in RISK_PLUGIN_SPECS)
    assert any(spec.id == "codex_plus_plus" for spec in RISK_PLUGIN_SPECS)
    assert LOGIN_URL.endswith("/api/user/login?turnstile=")
    assert DEPLOYER_ACTIVATE_URL.endswith("/api/deployer/activate")
    assert manifest_allowed_agents({"agents": [{"id": "codex"}, {"id": "hermes"}]}) == ["codex", "hermes"]
    api_contract = CommercialApiContract(DEFAULT_BASE_URL)
    key_owner_request = build_api_key_owner_verify_request(
        api_contract,
        api_key="sk-selftest",
        target_buyer_user_id="buyer-1",
        operator_user_id="buyer-1",
    )
    assert key_owner_request.url.endswith("/api/deployer/api-keys/verify-owner")
    paid_without_entitlement = parse_payment_status_data({"order_id": "ord-selftest", "payment_status": "paid"})
    assert not paid_without_entitlement["ready_for_delivery"]
    assert paid_without_entitlement["requires_manual_review"]
    completed_with_entitlement = parse_payment_status_data(
        {
            "order_id": "ord-selftest",
            "status": "completed",
            "entitlement_id": "ent-selftest",
            "entitlement_status": "active",
        }
    )
    assert completed_with_entitlement["ready_for_delivery"]
    owner_gate = api_key_owner_gate(create_buyer_contexts(UserContext(user_id="buyer-1", display_name="买家", role="buyer")), verified_owner_user_id="buyer-1")
    assert owner_gate.allowed
    reserve_request = build_config_session_reserve_request(
        api_contract,
        "ent",
        "buyer",
        "buyer",
        "codex",
        "direct_api",
        "device",
        "PH-CFG-1",
        "idem",
    )
    assert reserve_request.body["diagnostic_code"] == "PH-CFG-1"
    complete_request = build_config_session_complete_request(api_contract, "cfg", "PH-CFG-1", True, "idem-complete")
    fail_request = build_config_session_fail_request(api_contract, "cfg", "PH-CFG-1", "真实任务失败", "idem-fail")
    assert complete_request.body["real_task_verified"]
    assert fail_request.body["deduct_entitlement"] is False
    probe_url, probe_payload = build_real_task_probe_payload(DEFAULT_BASE_URL, DEFAULT_MODEL)
    assert probe_url == "https://aitokenapi.cc/v1/chat/completions"
    assert probe_payload["max_tokens"] == 16
    entry_titles = [entry.title for entry in build_commercial_entry_cards()]
    assert entry_titles == ["账号自助配置", "代理中心"]
    node_rows = build_node_status_rows(DeploymentProgress())
    assert node_rows[0].title == "登录身份"
    assert node_rows[-1].title == "客服诊断"
    assert manifest_has_commercial_controls({"products": []})
    assert manifest_has_commercial_controls({"value_added_services": []})
    assert not manifest_has_commercial_controls({"agents": []})
    assert validate_commercial_manifest_trust({"agents": []}).trusted
    assert not validate_commercial_manifest_trust({"products": []}).trusted
    commercial_entitlements = manifest_commercial_entitlements({"entitlements": []})
    assert build_entitlement_summary_rows(commercial_entitlements) == []
    customer_summary = "\n".join(build_customer_commercial_summary_lines([], commercial_entitlements))
    assert "服务端商品" in customer_summary
    assert "可用权益：未返回。" in customer_summary
    center_summary = agent_center_summary_text(
        {
            "agent_center": {
                "enabled": True,
                "current_level": "L1",
                "upgrade_label": "申请升级",
                "invite_url": "https://aitokenapi.cc/invite/selftest",
                "benefits": ["可绑定买家"],
                "boundaries": ["以后台结算为准"],
            }
        }
    )
    assert "当前等级：L1" in center_summary
    assert "邀请入口：已开放" in center_summary
    value_added_summary = value_added_services_summary_text(
        {
            "value_added_services": [
                {
                    "service_id": "sms_code",
                    "title": "接码控制台",
                    "target_project": "手机号接码控制中心",
                    "status": "pending_production",
                    "entry_url": "https://sim.aitokenapi.cc",
                    "entitlement_status": "unknown",
                    "requires_webview_session": True,
                    "unverified_reason": "生产验收待完成",
                }
            ]
        }
    )
    assert "待生产验收" in value_added_summary
    assert "已交付" not in value_added_summary
    assert "请先登录买家账号" in InstallerApp.current_commercial_summary_text(
        type(
            "SummaryProbe",
            (),
            {
                "deployer_manifest": None,
                "commercial_products": [],
                "commercial_entitlements": [],
                "logged_in_user": None,
            },
        )()
    )
    assert commercial_mode_key_for_deployment("codex", "cli") == "direct_api"
    assert commercial_mode_key_for_config_mode(CodexConfigMode.DUAL_STATE) == "dual_state"
    commercial_capabilities = manifest_commercial_capabilities(
        {"agents": [{"id": "codex", "delivery_scope": "full_config", "full_config_allowed": True}]}
    )
    assert commercial_capabilities["codex"].can_sell_full_config
    assert build_agent_customer_state("codex", commercial_capabilities).selectable
    assert not commercial_config_gate("codex", "direct_api", commercial_capabilities, [], True).allowed
    assert not commercial_config_gate("codex", "dual_state", commercial_capabilities, [], True).allowed
    assert commercial_deployment_blockers(["codex"], commercial_capabilities) == []
    hidden_capabilities = manifest_commercial_capabilities({"agents": [{"id": "openclaw", "delivery_scope": "hidden"}]})
    hidden_state = build_agent_customer_state("openclaw", hidden_capabilities)
    assert not hidden_state.visible
    assert commercial_deployment_blockers(["openclaw"], hidden_capabilities)
    buyer_contexts = create_buyer_contexts(UserContext(user_id="buyer-1", display_name="买家", role="buyer"))
    assert buyer_contexts.effective_buyer_user_id == "buyer-1"
    progress = DeploymentProgress()
    progress.mark(DeploymentNode.CONFIG_WRITE, NodeStatus.PASS)
    assert not progress.can_commit_success()
    progress.mark(DeploymentNode.REAL_TASK_VERIFY, NodeStatus.PASS)
    assert progress.can_commit_success()
    delivery_report = build_customer_delivery_report(
        diagnostic_code="PH-CFG-SELFTEST",
        progress=progress,
        reserved=True,
        agent_id="codex",
        mode_key=CodexConfigMode.DIRECT_API.value,
    )
    assert delivery_report.deduct_entitlement
    assert delivery_report.terminal_action == "complete"
    assert "PH-CFG-SELFTEST" in delivery_report.customer_message
    no_session_report = build_customer_delivery_report(
        diagnostic_code="PH-CFG-NOSESSION",
        progress=progress,
        reserved=False,
        agent_id="codex",
        mode_key=CodexConfigMode.DIRECT_API.value,
    )
    assert not no_session_report.deduct_entitlement
    assert no_session_report.terminal_action == "none"
    assert "未获得服务端配置会话" in no_session_report.customer_message
    assert process_text_contains_alias("node ccr start", "ccr")
    assert not process_text_contains_alias("screenrecorder.exe", "ccr")
    assert "sk-test-secret-123456" not in sanitize_log_text("Key sk-test-secret-123456", "sk-test-secret-123456")
    assert "已接入配置链路的 Agent 必须完成配置写入、重启/启动检查和最小中文对话验证后，才算完整交付" in build_agent_setup_guide_content([], "sk-test-secret-123456")
    assert "无需登录 ChatGPT 账号" in login_help_text()
    assert "新账号先充值或确认账户里有余额" in key_creation_help_text()
    action_help = codex_action_help_text()
    assert "一键部署（普通）：安装所选 Agent，并写入胖虎AI直接 API 配置" in action_help
    assert "双态配置：需要同时保留 ChatGPT 登录态并消耗胖虎AI API Key" in action_help
    assert "仅修复 Codex 配置：Agent 已经装好" in action_help
    assert "官方直登：切换为用户自己的 ChatGPT 账号额度" in action_help
    assert "恢复最近备份：配置异常时退回" in action_help
    assert "任何 Agent 配置写完后都必须重新打开对应 Agent" in action_help
    assert "需要消耗 ChatGPT 账号额度时，点“官方直登”" in codex_action_summary_text()
    assert "只要修改过 Codex 配置，都要完全退出 Codex 后重新打开" in codex_action_summary_text()
    assert "已禁止继续安装" in "\n".join(risk_plugin_report_lines([RiskPluginFinding("CCSwitch", "命令", "ccswitch", "")]))
    config = build_config("sk-test", DEFAULT_BASE_URL, DEFAULT_MODEL)
    expected_config = '''model_provider = "panghuAI"
model = "gpt-5.5"
review_model = "gpt-5.5"
model_reasoning_effort = "xhigh"
disable_response_storage = true
network_access = "enabled"
windows_wsl_setup_acknowledged = true
model_context_window = 1000000
model_auto_compact_token_limit =600000

[model_providers.panghuAI]
name = "panghuAI"
base_url = "https://aitokenapi.cc/v1"
wire_api = "responses"
requires_openai_auth = true
'''
    assert config == expected_config
    assert merge_config("old = true\n[desktop]\nappearanceTheme = \"light\"\n", "sk-test", "bad", "bad") == expected_config
    assert build_config("sk-test", "https://bad.example", DEFAULT_MODEL) == expected_config
    bad_url_dual_config = build_dual_state_config("sk-test", "https://bad.example", DEFAULT_MODEL)
    assert "https://bad.example" not in bad_url_dual_config
    assert 'base_url = "https://aitokenapi.cc/v1"' in bad_url_dual_config
    assert "experimental_bearer_token" not in config
    dual_config = build_dual_state_config("sk-test", DEFAULT_BASE_URL, DEFAULT_MODEL)
    assert 'experimental_bearer_token = "sk-test"' in dual_config
    direct_auth = json.loads(build_direct_api_auth_json("", "sk-test"))
    assert direct_auth == {"OPENAI_API_KEY": "sk-test"}
    existing_auth = json.dumps(
        {
            "auth_mode": "apikey",
            "OPENAI_API_KEY": "old-key",
            "tokens": {"access_token": "keep-access", "refresh_token": "keep-refresh"},
            "last_refresh": "2026-06-18T00:00:00Z",
        }
    )
    auth = json.loads(build_dual_state_auth_json(existing_auth, "sk-test"))
    assert auth["auth_mode"] == "chatgpt"
    assert auth["OPENAI_API_KEY"] is None
    assert auth["tokens"]["access_token"] == "keep-access"
    assert auth["tokens"]["refresh_token"] == "keep-refresh"
    assert auth["last_refresh"] == "2026-06-18T00:00:00Z"
    official_config = build_official_chatgpt_config(dual_config, DEFAULT_MODEL)
    assert 'model_provider = "openai"' in official_config
    assert "panghuAI" not in official_config
    assert "experimental_bearer_token" not in official_config
    official_auth = json.loads(build_official_chatgpt_auth_json(existing_auth))
    assert official_auth["auth_mode"] == "chatgpt"
    assert official_auth["OPENAI_API_KEY"] is None
    assert official_auth["tokens"]["access_token"] == "keep-access"
    assert detect_codex_config_mode(config, json.dumps(direct_auth)) == CodexConfigMode.DIRECT_API
    assert detect_codex_config_mode(dual_config, existing_auth) == CodexConfigMode.DUAL_STATE
    assert detect_codex_config_mode(official_config, json.dumps(official_auth)) == CodexConfigMode.OFFICIAL_CHATGPT
    assert codex_config_mode_requires_panghu_key(CodexConfigMode.DIRECT_API)
    assert codex_config_mode_requires_panghu_key(CodexConfigMode.DUAL_STATE)
    assert not codex_config_mode_requires_panghu_key(CodexConfigMode.OFFICIAL_CHATGPT)
    stale_dual_snapshot_config = build_dual_state_config("sk-old", DEFAULT_BASE_URL, DEFAULT_MODEL)
    refreshed_dual_config = build_dual_state_config("sk-new", DEFAULT_BASE_URL, DEFAULT_MODEL)
    assert 'experimental_bearer_token = "sk-old"' in stale_dual_snapshot_config
    assert 'experimental_bearer_token = "sk-new"' in refreshed_dual_config
    assert "sk-old" not in refreshed_dual_config
    assert [title for _module_id, title, _subtitle in TOP_MODULES] == ["配置Agent", "胖虎AI网站", "增值业务", "代理中心"]
    assert "delivery" not in VALUE_ADDED_URLS
    assert not any(item_id == "delivery" for item_id, _title, _subtitle in MODULE_SIDE_NAV_ITEMS[MODULE_VALUE_ADDED])
    assert [title for _item_id, title, _subtitle in MODULE_SIDE_NAV_ITEMS[MODULE_AGENT]] == [
        title for _idx, title, _subtitle in FLOW_STEPS
    ]
    assert [title for _item_id, title, _subtitle in MODULE_SIDE_NAV_ITEMS[MODULE_SITE]] != [
        title for _idx, title, _subtitle in FLOW_STEPS
    ]
    assert MODULE_PAGE_META[MODULE_SITE]["key"][1] == KEY_CREATE_URL
    assert DEFAULT_BASE_URL == (PANGHU_DEV_BASE_URL_OVERRIDE or "https://aitokenapi.cc")
    assert normalize_version("v1.2.3") > normalize_version("1.0.9")
    merged = merge_agents_rules("# old")
    assert PANGHU_AGENTS_START in merged and PANGHU_AGENTS_END in merged
    temporary_config = parse_temporary_openai_access_config(
        {"temporary_openai_access": {"enabled": True, "proxy": "aitokenapi.cc:80", "duration_seconds": 999}}
    )
    assert temporary_config is not None
    assert temporary_config.proxy == "aitokenapi.cc:80"
    assert temporary_config.duration_seconds == 600
    assert parse_temporary_openai_access_config({"temporary_openai_access": {"enabled": True, "proxy": "bad/proxy"}}) is None
    pac = build_openai_access_pac("aitokenapi.cc:80", "DIRECT")
    assert 'shExpMatch(host, "*.openai.com")' in pac
    assert 'shExpMatch(host, "*.chatgpt.com")' in pac
    assert "return \"PROXY aitokenapi.cc:80; DIRECT\";" in pac
    update = UpdateInfo("v9.9.9", "https://example.com/update.zip", "https://example.com/release", "胖虎AI客户端-Windows.zip", "Windows")
    assert update.asset_name == "胖虎AI客户端-Windows.zip"
    win_update_script = build_windows_update_script(Path("C:/tmp/update.zip"), Path("C:/App"), Path("C:/App/app.exe"), 1234)
    assert "Wait-Process -Id $pidToWait" in win_update_script
    assert "Expand-Archive" in win_update_script
    assert "Copy-Item -Path" in win_update_script
    assert "Start-Process -FilePath $launchTarget" in win_update_script
    mac_update_script = build_macos_update_script(Path("/tmp/update.zip"), Path("/Applications/App.app"), Path("/Applications/App.app"), 1234)
    assert "while kill -0" in mac_update_script
    assert "ditto -x -k" in mac_update_script
    assert 'rm -rf "$APP_DIR"' in mac_update_script
    assert "cp -R" in mac_update_script
    assert "open \"$LAUNCH_TARGET\"" in mac_update_script
    restore_script = build_windows_temp_openai_access_script()
    assert "Start-Sleep -Seconds $Seconds" in restore_script
    assert "Restore-InternetProxyState" in restore_script
    assert "AutoConfigURL" in restore_script
    assert "Register-ScheduledTask" in restore_script
    assert "-RestoreOnly" in restore_script
    assert "if ($RestoreOnly)" in restore_script
    assert "InternetSetOption" in restore_script
    mac_restore_script = build_macos_temp_openai_access_script()
    assert "networksetup" in mac_restore_script
    assert "setautoproxyurl" in mac_restore_script
    assert "LaunchDaemons" in mac_restore_script
    assert "restore_state" in mac_restore_script
    assert "SECONDS_VALUE" in mac_restore_script
    original_system = platform.system
    original_machine = platform.machine
    try:
        platform.system = lambda: "Darwin"  # type: ignore[method-assign]
        platform.machine = lambda: "arm64"  # type: ignore[method-assign]
        assert current_mac_package_suffix() == "AppleSilicon"
        assert release_asset_name_for_current_system().endswith("-Mac-AppleSilicon.zip")
        assert public_manifest_asset_url({"mac_apple_silicon_zip_url": "arm", "mac_intel_zip_url": "intel"}) == "arm"
        platform.machine = lambda: "x86_64"  # type: ignore[method-assign]
        assert current_mac_package_suffix() == "Intel"
        assert release_asset_name_for_current_system().endswith("-Mac-Intel.zip")
        assert public_manifest_asset_url({"mac_apple_silicon_zip_url": "arm", "mac_intel_zip_url": "intel"}) == "intel"
        assert public_manifest_asset_url({"mac_zip_url": "legacy"}) == ""
    finally:
        platform.system = original_system  # type: ignore[method-assign]
        platform.machine = original_machine  # type: ignore[method-assign]
    print("UI self-test OK")


def main() -> int:
    if "--self-test" in sys.argv:
        self_test()
        return 0
    enable_windows_dpi_awareness()

    try:
        webview_runtime, bundled_webview_shell = require_webview_runtime_and_ui()
        root = tk.Tk()
        root.withdraw()

        app = InstallerApp(root, webview_mode=True)

        window_title = APP_NAME
        if PANGHU_DEV_BASE_URL_OVERRIDE:
            # 联调覆盖生效时窗口标题醒目提示，防止误当生产环境使用。
            window_title = f"{APP_NAME}【本地联调 {PANGHU_DEV_BASE_URL_OVERRIDE}】"
            print(f"[联调] 服务端地址已覆盖为 {PANGHU_DEV_BASE_URL_OVERRIDE}", flush=True)
        window = webview_runtime.create_window(
            title=window_title,
            url=str(bundled_webview_shell.absolute()),
            js_api=WebviewApi(app),
            width=1400,
            height=900,
            min_size=(1180, 760),
            resizable=True
        )
        app.webview_window = window

        app_shell_storage = web_profile_root() / "app-shell"
        app_shell_storage.mkdir(parents=True, exist_ok=True)
        webview_runtime.start(debug=False, private_mode=False, storage_path=str(app_shell_storage))
        app.close_app()
        return 0
    except Exception as e:
        print(f"胖虎AI客户端启动失败：{e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
