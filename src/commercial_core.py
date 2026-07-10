from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hashlib
import json
import re
from typing import Any


class WebProfileScope(str, Enum):
    BUYER = "buyer"


class DeliveryScope(str, Enum):
    FULL_CONFIG = "full_config"
    ASSISTED_FULL_CONFIG = "assisted_full_config"
    GUIDED_FULL_CONFIG = "guided_full_config"
    PARTIAL_CONFIG = "partial_config"
    INSTALL_GUIDED = "install_guided"
    GUIDE_ONLY = "guide_only"
    OFFICIAL_ENTRY_ONLY = "official_entry_only"
    PAUSED = "paused"
    HIDDEN = "hidden"


class NodeStatus(str, Enum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    PASS = "pass"
    WARNING = "warning"
    BLOCKED = "blocked"
    FAILED = "failed"
    NEEDS_MANUAL = "needs_manual"
    SERVER_DISABLED = "server_disabled"


class DeploymentNode(str, Enum):
    LOGIN = "login"
    ENTITLEMENT = "entitlement"
    API_KEY = "api_key"
    ENVIRONMENT = "environment"
    RISK_PLUGIN = "risk_plugin"
    DOWNLOAD = "download"
    INSTALL = "install"
    CONFIG_WRITE = "config_write"
    LAUNCH_VERIFY = "launch_verify"
    REAL_TASK_VERIFY = "real_task_verify"
    SUPPORT_DIAGNOSIS = "support_diagnosis"


class CommercialEntryId(str, Enum):
    BUYER_SELF_SERVICE = "buyer_self_service"
    AGENT_CENTER = "agent_center"


class BuyerSelfServiceNode(str, Enum):
    ORDER_PAYMENT = "order_payment"
    ENTITLEMENT_REFRESH = "entitlement_refresh"


SENSITIVE_TEXT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+\b"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b1[3-9]\d{9}\b"),
    re.compile(r"\bsk[-_][A-Za-z0-9][A-Za-z0-9._-]{8,}\b"),
    re.compile(r"(?i)\b(token|access_token|refresh_token|api_key|order_id|invite_code|config_session_id|entitlement_id)\s*[:= ]\s*[A-Za-z0-9._@%+-]{3,}"),
    re.compile(r"\bINVITE-[A-Za-z0-9._-]+\b", re.IGNORECASE),
)


def sanitize_customer_diagnostic_text(text: str) -> str:
    safe = str(text or "")
    for pattern in SENSITIVE_TEXT_PATTERNS:
        safe = pattern.sub(_mask_sensitive_match, safe)
    return safe


def _mask_sensitive_match(match: re.Match[str]) -> str:
    value = match.group(0)
    for separator in ("=", ":"):
        if separator in value:
            return value.split(separator, 1)[0] + "=***"
    if " " in value:
        return value.split(" ", 1)[0] + "=***"
    return "***"


@dataclass(frozen=True)
class UserContext:
    user_id: str
    display_name: str
    role: str
    token: str = ""


@dataclass(frozen=True)
class CommercialEntry:
    entry_id: CommercialEntryId
    title: str
    subtitle: str
    action_label: str


@dataclass(frozen=True)
class NodeStatusRow:
    node: DeploymentNode
    title: str
    status: NodeStatus
    customer_message: str


@dataclass(frozen=True)
class CustomerDeliveryVerdict:
    status: NodeStatus
    deduct_entitlement: bool
    customer_message: str


@dataclass(frozen=True)
class CustomerDeliveryReport:
    diagnostic_code: str
    status: NodeStatus
    deduct_entitlement: bool
    terminal_action: str
    customer_message: str
    node_rows: list[NodeStatusRow]
    support_packet: str


@dataclass(frozen=True)
class CustomerServiceStatusRow:
    node: BuyerSelfServiceNode
    title: str
    status: NodeStatus
    customer_message: str


@dataclass(frozen=True)
class AgentCustomerState:
    agent_id: str
    visible: bool
    selectable: bool
    badge: str
    note: str


@dataclass(frozen=True)
class CommercialProduct:
    product_id: str
    title: str
    agent_id: str
    mode_key: str
    delivery_scope: DeliveryScope
    price_cents: int
    currency: str
    remaining_uses: int
    valid_until: str
    includes_dual_state: bool
    device_limit: int
    is_listed: bool
    is_unlimited: bool = False
    min_client_version: str = ""
    allowed_buyer_user_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ValueAddedServiceEntry:
    service_id: str
    title: str
    target_project: str
    status: str
    entry_url: str
    purchase_url: str
    entitlement_status: str
    requires_webview_session: bool
    summary_url: str = ""
    unverified_reason: str = ""

    @property
    def is_available(self) -> bool:
        return self.status == "available" and not self.unverified_reason


@dataclass(frozen=True)
class EntitlementContract:
    entitlement_id: str
    buyer_user_id: str
    agent_id: str
    mode_key: str
    remaining_uses: int
    valid_until: str
    delivery_scope: DeliveryScope
    includes_dual_state: bool
    device_limit: int
    status: str
    source: str = "paid"
    is_unlimited: bool = False


@dataclass(frozen=True)
class CommercialConfigGateDecision:
    allowed: bool
    message: str
    entitlement_id: str = ""


@dataclass(frozen=True)
class ApiKeyOwnerGateDecision:
    allowed: bool
    message: str


@dataclass(frozen=True)
class RealTaskVerificationResult:
    diagnostic_code: str
    agent_id: str
    mode_key: str
    passed: bool
    status: NodeStatus
    customer_message: str
    response_excerpt: str = ""


@dataclass
class ConfigSessionContract:
    config_session_id: str
    buyer_user_id: str
    operator_user_id: str
    entitlement_id: str
    agent_id: str
    mode_key: str
    diagnostic_code: str
    progress: DeploymentProgress

    def can_commit_success(self) -> bool:
        return self.progress.can_commit_success()


@dataclass(frozen=True)
class CommercialSessionContexts:
    operator: UserContext
    target_buyer: UserContext
    web_profile_scope: WebProfileScope

    @property
    def effective_buyer_user_id(self) -> str:
        return self.target_buyer.user_id


@dataclass(frozen=True)
class CommercialWebProfile:
    profile_key: str
    scope: WebProfileScope
    root_dir: str
    ephemeral: bool

    @property
    def path(self) -> str:
        separator = "" if self.root_dir.endswith(("/", "\\")) else "/"
        return f"{self.root_dir}{separator}{self.profile_key}"


@dataclass(frozen=True)
class CommercialManifestTrustDecision:
    trusted: bool
    requires_signature: bool
    message: str


@dataclass(frozen=True)
class AgentCommercialCapability:
    agent_id: str
    delivery_scope: DeliveryScope
    full_config_allowed: bool = False
    min_client_version: str = ""
    playbook_version: str = ""

    @property
    def can_sell_full_config(self) -> bool:
        return self.delivery_scope == DeliveryScope.FULL_CONFIG and self.full_config_allowed

    @property
    def is_visible(self) -> bool:
        return self.delivery_scope != DeliveryScope.HIDDEN


@dataclass
class DeploymentProgress:
    node_statuses: dict[DeploymentNode, NodeStatus] = field(default_factory=dict)

    def mark(self, node: DeploymentNode, status: NodeStatus) -> None:
        self.node_statuses[node] = status

    def status_for(self, node: DeploymentNode) -> NodeStatus:
        return self.node_statuses.get(node, NodeStatus.NOT_STARTED)

    def can_commit_success(self) -> bool:
        return self.status_for(DeploymentNode.REAL_TASK_VERIFY) == NodeStatus.PASS


def config_session_terminal_action(progress: DeploymentProgress, reserved: bool) -> str:
    if not reserved:
        return "none"
    if progress.can_commit_success():
        return "complete"
    return "fail"


def build_customer_delivery_verdict(
    progress: DeploymentProgress,
    reserved: bool,
    diagnostic_code: str,
) -> CustomerDeliveryVerdict:
    if not reserved:
        return CustomerDeliveryVerdict(
            status=NodeStatus.WARNING,
            deduct_entitlement=False,
            customer_message=(
                f"诊断码 {diagnostic_code}：本次未获得服务端配置会话，"
                "不会提交商业交付成功，也不会扣次。"
            ),
        )
    if progress.can_commit_success():
        return CustomerDeliveryVerdict(
            status=NodeStatus.PASS,
            deduct_entitlement=True,
            customer_message=(
                f"诊断码 {diagnostic_code}：真实任务验证已通过，可以扣次并标记商业交付成功。"
            ),
        )
    failed_rows = [
        row for row in build_node_status_rows(progress)
        if row.status in (NodeStatus.FAILED, NodeStatus.BLOCKED, NodeStatus.SERVER_DISABLED)
    ]
    if failed_rows:
        failed_titles = "、".join(row.title for row in failed_rows)
        detail = f"失败节点：{failed_titles}。"
    else:
        detail = "当前尚未形成完整真实任务验证。"
    return CustomerDeliveryVerdict(
        status=NodeStatus.FAILED,
        deduct_entitlement=False,
        customer_message=(
            f"诊断码 {diagnostic_code}：{detail}本次不扣次，请把诊断码交给客服排查。"
        ),
    )


def build_customer_delivery_report(
    diagnostic_code: str,
    progress: DeploymentProgress,
    reserved: bool,
    agent_id: str,
    mode_key: str,
    api_key: str = "",
    commercial_ids: list[str] | None = None,
) -> CustomerDeliveryReport:
    verdict = build_customer_delivery_verdict(
        progress=progress,
        reserved=reserved,
        diagnostic_code=diagnostic_code,
    )
    return CustomerDeliveryReport(
        diagnostic_code=diagnostic_code,
        status=verdict.status,
        deduct_entitlement=verdict.deduct_entitlement,
        terminal_action=config_session_terminal_action(progress, reserved=reserved),
        customer_message=verdict.customer_message,
        node_rows=build_node_status_rows(progress),
        support_packet=build_support_diagnostic_packet(
            diagnostic_code=diagnostic_code,
            progress=progress,
            agent_id=agent_id,
            mode_key=mode_key,
            customer_message=verdict.customer_message,
            api_key=api_key,
            commercial_ids=commercial_ids,
        ),
    )


def create_commercial_web_profile(contexts: CommercialSessionContexts, root_dir: str) -> CommercialWebProfile:
    seed = f"buyer:{contexts.target_buyer.user_id}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return CommercialWebProfile(
        profile_key=f"buyer-{digest}",
        scope=contexts.web_profile_scope,
        root_dir=root_dir,
        ephemeral=False,
    )


NODE_TITLES: dict[DeploymentNode, str] = {
    DeploymentNode.LOGIN: "登录身份",
    DeploymentNode.ENTITLEMENT: "权益和次数",
    DeploymentNode.API_KEY: "API Key",
    DeploymentNode.ENVIRONMENT: "系统环境",
    DeploymentNode.RISK_PLUGIN: "风险插件",
    DeploymentNode.DOWNLOAD: "下载组件",
    DeploymentNode.INSTALL: "安装 Agent",
    DeploymentNode.CONFIG_WRITE: "配置写入",
    DeploymentNode.LAUNCH_VERIFY: "重启验证",
    DeploymentNode.REAL_TASK_VERIFY: "真实任务验证",
    DeploymentNode.SUPPORT_DIAGNOSIS: "客服诊断",
}

NODE_ORDER: tuple[DeploymentNode, ...] = (
    DeploymentNode.LOGIN,
    DeploymentNode.ENTITLEMENT,
    DeploymentNode.API_KEY,
    DeploymentNode.ENVIRONMENT,
    DeploymentNode.RISK_PLUGIN,
    DeploymentNode.DOWNLOAD,
    DeploymentNode.INSTALL,
    DeploymentNode.CONFIG_WRITE,
    DeploymentNode.LAUNCH_VERIFY,
    DeploymentNode.REAL_TASK_VERIFY,
    DeploymentNode.SUPPORT_DIAGNOSIS,
)

STATUS_MESSAGES: dict[NodeStatus, str] = {
    NodeStatus.NOT_STARTED: "等待开始。",
    NodeStatus.RUNNING: "正在处理。",
    NodeStatus.PASS: "已通过。",
    NodeStatus.WARNING: "可继续，但需要留意提示。",
    NodeStatus.BLOCKED: "当前节点被阻断，请先处理。",
    NodeStatus.FAILED: "当前节点失败，暂不扣次数。",
    NodeStatus.NEEDS_MANUAL: "需要人工确认或客服协助。",
    NodeStatus.SERVER_DISABLED: "服务端已暂停或关闭。",
}

MODE_LABELS: dict[str, str] = {
    "direct_api": "普通模式",
    "dual_state": "双态模式",
    "official_chatgpt": "官方直登",
    "cli": "CLI",
    "client": "客户端",
}

AGENT_LABELS: dict[str, str] = {
    "codex": "Codex",
    "claude_code": "ClaudeCode",
    "openclaw": "OpenClaw",
    "hermes": "Hermes",
    "gemini_agy": "Google 反重力（agy）",
}

ENTITLEMENT_STATUS_LABELS: dict[str, str] = {
    "active": "可用",
    "pending": "待生效",
    "expired": "已过期",
    "revoked": "已撤销",
    "used_up": "次数已用完",
}

ENTITLEMENT_SOURCE_LABELS: dict[str, str] = {
    "paid": "付费权益",
    "trial": "试用权益",
}

def build_commercial_entry_cards() -> list[CommercialEntry]:
    return [
        CommercialEntry(
            entry_id=CommercialEntryId.BUYER_SELF_SERVICE,
            title="账号自助配置",
            subtitle="统一登录胖虎AI账号，查看权益、创建 Key，并配置自己的 Agent。",
            action_label="账号登录",
        ),
        CommercialEntry(
            entry_id=CommercialEntryId.AGENT_CENTER,
            title="代理中心",
            subtitle="登录后通过胖虎AI网站查看代理身份、邀请入口和收益边界。",
            action_label="查看代理中心",
        ),
    ]


BUYER_SELF_SERVICE_NODE_TITLES: dict[BuyerSelfServiceNode, str] = {
    BuyerSelfServiceNode.ORDER_PAYMENT: "订单支付",
    BuyerSelfServiceNode.ENTITLEMENT_REFRESH: "刷新权益",
}

BUYER_SELF_SERVICE_NODE_ORDER: tuple[BuyerSelfServiceNode, ...] = (
    BuyerSelfServiceNode.ORDER_PAYMENT,
    BuyerSelfServiceNode.ENTITLEMENT_REFRESH,
)


def build_buyer_self_service_status_rows(
    statuses: dict[BuyerSelfServiceNode, NodeStatus],
) -> list[CustomerServiceStatusRow]:
    rows: list[CustomerServiceStatusRow] = []
    for node in BUYER_SELF_SERVICE_NODE_ORDER:
        title = BUYER_SELF_SERVICE_NODE_TITLES[node]
        status = statuses.get(node, NodeStatus.NOT_STARTED)
        rows.append(
            CustomerServiceStatusRow(
                node=node,
                title=title,
                status=status,
                customer_message=f"{title}：{STATUS_MESSAGES[status]}",
            )
        )
    return rows


def build_agent_customer_state(
    agent_id: str,
    capabilities: dict[str, AgentCommercialCapability],
    commercial_manifest_present: bool = False,
) -> AgentCustomerState:
    capability = capabilities.get(agent_id)
    if capability is None:
        if commercial_manifest_present:
            return AgentCustomerState(agent_id, True, False, "未开放", "服务端未明确开放该 Agent 的商业交付。")
        return AgentCustomerState(agent_id, True, True, "兼容模式", "当前清单未启用商业控制，按旧版安装引导兼容。")
    if capability.delivery_scope == DeliveryScope.HIDDEN:
        return AgentCustomerState(agent_id, False, False, "已隐藏", "服务端未开放该 Agent。")
    if capability.delivery_scope == DeliveryScope.PAUSED:
        return AgentCustomerState(agent_id, True, False, "已暂停", "服务端已暂停该 Agent 的商业交付。")
    if capability.can_sell_full_config:
        return AgentCustomerState(agent_id, True, True, "完整配置", "服务端允许作为完整配置交付。")
    return AgentCustomerState(
        agent_id,
        True,
        False,
        _delivery_scope_label(capability.delivery_scope),
        "未通过功能验收矩阵前不扣次、不算完整交付。",
    )


def build_node_status_rows(progress: DeploymentProgress) -> list[NodeStatusRow]:
    rows: list[NodeStatusRow] = []
    for node in NODE_ORDER:
        status = progress.status_for(node)
        title = NODE_TITLES[node]
        rows.append(
            NodeStatusRow(
                node=node,
                title=title,
                status=status,
                customer_message=f"{title}：{STATUS_MESSAGES[status]}",
            )
        )
    return rows


def build_commercial_product_catalog(manifest: dict[str, Any]) -> list[CommercialProduct]:
    catalog: list[CommercialProduct] = []
    products = manifest.get("products") or []
    if not isinstance(products, list):
        return catalog
    for item in products:
        if not isinstance(item, dict) or not item.get("product_id"):
            continue
        title = str(item.get("title") or "")
        agent_id = str(item.get("agent_id") or "")
        mode_key = str(item.get("mode_key") or "")
        delivery_scope_value = str(item.get("delivery_scope") or "")
        currency = str(item.get("currency") or "")
        valid_until = str(item.get("valid_until") or "")
        if not all((title, agent_id, mode_key, delivery_scope_value, currency, valid_until)):
            continue
        if not isinstance(item.get("is_listed"), bool):
            continue
        try:
            delivery_scope = DeliveryScope(delivery_scope_value)
            price_cents = int(item["price_cents"])
            remaining_uses = int(item["remaining_uses"])
            device_limit = int(item["device_limit"])
        except (KeyError, TypeError, ValueError):
            continue
        is_unlimited = bool(item.get("is_unlimited"))
        if price_cents < 0 or remaining_uses < 0 or (remaining_uses < 1 and not is_unlimited) or device_limit < 1:
            continue
        allowed_buyer_user_ids_value = item.get("allowed_buyer_user_ids") or item.get("gray_buyer_user_ids") or []
        if isinstance(allowed_buyer_user_ids_value, list):
            allowed_buyer_user_ids = tuple(str(value).strip() for value in allowed_buyer_user_ids_value if str(value).strip())
        else:
            allowed_buyer_user_ids = ()
        catalog.append(
            CommercialProduct(
                product_id=str(item["product_id"]),
                title=title,
                agent_id=agent_id,
                mode_key=mode_key,
                delivery_scope=delivery_scope,
                price_cents=price_cents,
                currency=currency,
                remaining_uses=remaining_uses,
                valid_until=valid_until,
                includes_dual_state=bool(item.get("includes_dual_state")),
                device_limit=device_limit,
                is_listed=item["is_listed"],
                is_unlimited=is_unlimited,
                min_client_version=str(item.get("min_client_version") or ""),
                allowed_buyer_user_ids=allowed_buyer_user_ids,
            )
        )
    return catalog


def build_entitlement_summary_rows(entitlements: list[EntitlementContract]) -> list[tuple[str, str, str, str, str]]:
    rows: list[tuple[str, str, str, str, str]] = []
    for entitlement in entitlements:
        agent_label = AGENT_LABELS.get(entitlement.agent_id, entitlement.agent_id)
        mode_label = MODE_LABELS.get(entitlement.mode_key, entitlement.mode_key)
        status_label = _entitlement_customer_status(entitlement)
        remaining_uses = max(0, entitlement.remaining_uses)
        uses_label = "不限次" if entitlement.is_unlimited else f"{remaining_uses}次"
        scope_label = _delivery_scope_label(entitlement.delivery_scope)
        valid_until = entitlement.valid_until or "以服务端为准"
        source_label = ENTITLEMENT_SOURCE_LABELS.get(entitlement.source, "服务端权益")
        rows.append((agent_label, mode_label, status_label, uses_label, f"{source_label}，{scope_label}，有效期 {valid_until}"))
    return rows


def build_customer_commercial_summary_lines(
    products: list[CommercialProduct],
    entitlements: list[EntitlementContract],
) -> list[str]:
    lines: list[str] = []
    if products:
        lines.append(f"服务端商品：{len(products)} 个")
        for product in products:
            agent_label = AGENT_LABELS.get(product.agent_id, product.agent_id)
            mode_label = MODE_LABELS.get(product.mode_key, product.mode_key)
            listed_label = "已上架" if product.is_listed else "未上架"
            lines.append(f"- {product.title} / {agent_label} / {mode_label} / {listed_label}")
    else:
        lines.append("服务端商品：未返回。")

    rows = build_entitlement_summary_rows(entitlements)
    if rows:
        lines.append(f"可用权益：{len(rows)} 条")
        for agent_label, mode_label, status_label, uses_label, detail in rows:
            lines.append(f"- {agent_label} / {mode_label} / {status_label} / {uses_label} / {detail}")
    else:
        lines.append("可用权益：未返回。")
    return lines


def format_customer_price(price_cents: int, currency: str) -> str:
    amount = max(0, int(price_cents)) / 100
    currency_text = str(currency or "").strip().upper()
    if currency_text == "CNY":
        return f"¥{amount:.2f}"
    if currency_text:
        return f"{currency_text} {amount:.2f}"
    return f"{amount:.2f}"


def build_customer_purchase_product_lines(
    products: list[CommercialProduct],
    app_version: str = "",
    buyer_user_id: str = "",
) -> list[str]:
    lines: list[str] = []
    for product in products:
        if not product.is_listed:
            continue
        if not _valid_until_is_active(product.valid_until):
            continue
        # 与 find_orderable_product 同口径过滤：展示的"可购买商品"必须真能下单，否则会展示
        # 交付范围不符/版本门槛未达/买家白名单外的商品，买家一点"创建订单"就是死单(B-CAT-CONSIST)。
        if product.delivery_scope not in (
            DeliveryScope.FULL_CONFIG,
            DeliveryScope.ASSISTED_FULL_CONFIG,
            DeliveryScope.GUIDED_FULL_CONFIG,
        ):
            continue
        if not _client_version_allowed(app_version, product.min_client_version):
            continue
        if not _buyer_allowed(buyer_user_id, product.allowed_buyer_user_ids):
            continue
        uses_label = "不限次" if product.is_unlimited else f"{max(0, product.remaining_uses)}次"
        device_label = f"{max(1, product.device_limit)}台设备"
        dual_state_label = "，含双态模式" if product.includes_dual_state else ""
        valid_until = product.valid_until[:10] if product.valid_until else "以服务端为准"
        lines.append(
            f"{product.title}：{format_customer_price(product.price_cents, product.currency)} / "
            f"{uses_label} / {device_label} / 有效期 {valid_until}{dual_state_label}"
        )
    return lines


VALUE_ADDED_SERVICE_STATUS_LABELS: dict[str, str] = {
    "available": "已开放",
    "paused": "已暂停",
    "pending_production": "待生产验收",
    "manual_review": "人工复核",
}

VALUE_ADDED_ENTITLEMENT_STATUS_LABELS: dict[str, str] = {
    "not_purchased": "未购买",
    "active": "已开通",
    "pending_activation": "待激活",
    "manual_review": "人工复核",
    "unknown": "待服务端确认",
}

VALUE_ADDED_FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "activation_service_token",
        "agent_token",
        "session_token",
        "plus_session_token",
        "sms_text",
        "sms_code",
        "phone_number",
        "device_token",
        "payment_secret",
        "private_key",
    }
)


def build_value_added_service_catalog(manifest: dict[str, Any]) -> list[ValueAddedServiceEntry]:
    services = manifest.get("value_added_services") or []
    if not isinstance(services, list):
        return []

    catalog: list[ValueAddedServiceEntry] = []
    for item in services:
        if not isinstance(item, dict):
            continue
        if any(key in item and item.get(key) for key in VALUE_ADDED_FORBIDDEN_KEYS):
            continue
        service_id = str(item.get("service_id") or "").strip()
        title = str(item.get("title") or "").strip()
        target_project = str(item.get("target_project") or "").strip()
        status = str(item.get("status") or "").strip()
        entry_url = str(item.get("entry_url") or "").strip()
        entitlement_status = str(item.get("entitlement_status") or "").strip()
        if not all((service_id, title, target_project, status, entry_url, entitlement_status)):
            continue
        if status not in VALUE_ADDED_SERVICE_STATUS_LABELS:
            continue
        purchase_url = str(item.get("purchase_url") or entry_url).strip()
        requires_webview_session = item.get("requires_webview_session")
        if not isinstance(requires_webview_session, bool):
            continue
        catalog.append(
            ValueAddedServiceEntry(
                service_id=service_id,
                title=title,
                target_project=target_project,
                status=status,
                entry_url=entry_url,
                purchase_url=purchase_url,
                entitlement_status=entitlement_status,
                requires_webview_session=requires_webview_session,
                summary_url=str(item.get("summary_url") or "").strip(),
                unverified_reason=str(item.get("unverified_reason") or "").strip(),
            )
        )
    return catalog


def build_value_added_service_summary_lines(services: list[ValueAddedServiceEntry]) -> list[str]:
    if not services:
        return ["增值业务：服务端暂未下发目录，请以网站后台开关为准。"]

    lines = ["增值业务：服务端目录已同步"]
    for service in services:
        status_label = VALUE_ADDED_SERVICE_STATUS_LABELS.get(service.status, service.status)
        entitlement_label = VALUE_ADDED_ENTITLEMENT_STATUS_LABELS.get(
            service.entitlement_status,
            service.entitlement_status or "待服务端确认",
        )
        bridge_label = "需要客户端登录会话" if service.requires_webview_session else "普通服务端入口"
        line = f"{service.title}：{status_label} / {entitlement_label} / {bridge_label}"
        if service.unverified_reason:
            line += f" / {service.unverified_reason}"
        lines.append(line)
    return lines


def build_agent_center_summary_lines(manifest: dict[str, Any]) -> list[str]:
    center = manifest.get("agent_center")
    if not isinstance(center, dict) or not center.get("enabled"):
        return ["代理中心：服务端暂未开放，请以后台开关为准。"]

    lines = ["代理中心：服务端已开放"]
    status = str(center.get("status") or "").strip()
    if status:
        lines.append(f"代理状态：{status}")
    current_level = str(center.get("current_level") or "").strip()
    if current_level:
        lines.append(f"当前等级：{current_level}")
    upgrade_label = str(center.get("upgrade_label") or "").strip()
    if upgrade_label:
        lines.append(f"升级入口：{upgrade_label}")
    invite_url = str(center.get("invite_url") or "").strip()
    if invite_url:
        lines.append("邀请入口：已开放")
    join_page_url = str(center.get("join_page_url") or "").strip()
    if join_page_url:
        lines.append("招商介绍：已开放")
    backend_url = str(center.get("backend_url") or "").strip()
    if backend_url:
        lines.append("工具代理后端：已开放")
    rules_url = str(center.get("rules_url") or "").strip()
    if rules_url:
        lines.append("代理规则：已开放")

    summary = center.get("summary")
    if isinstance(summary, dict):
        downstream_count = _nonnegative_int(summary.get("downstream_count"))
        if downstream_count is not None:
            lines.append(f"下游客户：{downstream_count} 人")
        for key, label in (
            # token_commission_cents（token 消耗返佣）已废弃、服务端恒 0，不再进摘要展示；字段暂保留兼容。
            ("activation_commission_cents", "激活返佣"),
            ("agent_install_commission_cents", "安装返佣"),
            ("available_settlement_cents", "可结算"),
            ("pending_settlement_cents", "待结算"),
            ("frozen_cents", "冻结金额"),
        ):
            cents = _nonnegative_int(summary.get(key))
            if cents is not None:
                lines.append(f"{label}：{format_customer_price(cents, 'CNY')}")

    benefits = center.get("benefits")
    if isinstance(benefits, list):
        for item in benefits[:5]:
            text = str(item or "").strip()
            if text:
                lines.append(f"等级权益：{text}")

    boundaries = center.get("boundaries")
    if isinstance(boundaries, list):
        for item in boundaries[:5]:
            text = str(item or "").strip()
            if text:
                lines.append(f"收益边界：{text}")
    return lines


def _nonnegative_int(value: Any) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return max(0, number)


def _valid_until_is_active(valid_until: str) -> bool:
    text = str(valid_until or "").strip()
    if not text:
        return False
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        expires_at = datetime.fromisoformat(normalized)
    except ValueError:
        return False
    if expires_at.tzinfo is None:
        now = datetime.now()
    else:
        now = datetime.now(expires_at.tzinfo)
    return expires_at > now


def _version_tuple(value: str) -> tuple[int, ...]:
    parts = re.findall(r"\d+", str(value or ""))
    return tuple(int(part) for part in parts) if parts else tuple()


def _client_version_allowed(app_version: str, min_client_version: str) -> bool:
    required = _version_tuple(min_client_version)
    if not required:
        return True
    current = _version_tuple(app_version)
    if not current:
        return False
    max_len = max(len(current), len(required))
    padded_current = current + (0,) * (max_len - len(current))
    padded_required = required + (0,) * (max_len - len(required))
    return padded_current >= padded_required


def _buyer_allowed(buyer_user_id: str, allowed_buyer_user_ids: tuple[str, ...]) -> bool:
    if not allowed_buyer_user_ids:
        return True
    return str(buyer_user_id or "").strip() in allowed_buyer_user_ids


def find_usable_entitlement(
    entitlements: list[EntitlementContract],
    agent_id: str,
    mode_key: str,
) -> EntitlementContract | None:
    for entitlement in entitlements:
        if entitlement.agent_id != agent_id or entitlement.mode_key != mode_key:
            continue
        if entitlement.status != "active":
            continue
        if entitlement.remaining_uses < 1 and not entitlement.is_unlimited:
            continue
        if not _valid_until_is_active(entitlement.valid_until):
            continue
        if entitlement.delivery_scope not in (
            DeliveryScope.FULL_CONFIG,
            DeliveryScope.ASSISTED_FULL_CONFIG,
            DeliveryScope.GUIDED_FULL_CONFIG,
        ):
            continue
        return entitlement
    return None


def find_listed_product(
    products: list[CommercialProduct],
    agent_id: str,
    mode_key: str,
) -> CommercialProduct | None:
    for product in products:
        if product.agent_id != agent_id or product.mode_key != mode_key:
            continue
        if not product.is_listed:
            continue
        if not _valid_until_is_active(product.valid_until):
            continue
        if product.delivery_scope not in (
            DeliveryScope.FULL_CONFIG,
            DeliveryScope.ASSISTED_FULL_CONFIG,
            DeliveryScope.GUIDED_FULL_CONFIG,
        ):
            continue
        return product
    return None


def find_orderable_product(
    products: list[CommercialProduct],
    product_id: str,
    agent_id: str,
    mode_key: str,
    app_version: str = "",
    buyer_user_id: str = "",
) -> CommercialProduct | None:
    target_product_id = str(product_id or "").strip()
    if not target_product_id:
        return None
    for product in products:
        if product.product_id != target_product_id:
            continue
        if product.agent_id != agent_id or product.mode_key != mode_key:
            return None
        if not product.is_listed:
            return None
        if not _valid_until_is_active(product.valid_until):
            return None
        if product.delivery_scope not in (
            DeliveryScope.FULL_CONFIG,
            DeliveryScope.ASSISTED_FULL_CONFIG,
            DeliveryScope.GUIDED_FULL_CONFIG,
        ):
            return None
        if not _client_version_allowed(app_version, product.min_client_version):
            return None
        if not _buyer_allowed(buyer_user_id, product.allowed_buyer_user_ids):
            return None
        return product
    return None


def canonical_commercial_manifest_payload(manifest: dict[str, Any]) -> bytes:
    payload = {
        key: value
        for key, value in manifest.items()
        if key != "manifest_signature"
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _verify_ed25519_manifest_signature(manifest: dict[str, Any], public_key_pem: str) -> tuple[bool, str]:
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except Exception:
        return False, "商业部署清单验签依赖不可用，已停止商业配置。"

    signature = str(manifest.get("manifest_signature") or "").strip()
    if not signature.startswith("ed25519:"):
        return False, "商业部署清单签名算法不受支持，已停止商业配置。"
    try:
        raw_signature = base64.b64decode(signature.split(":", 1)[1], validate=True)
        public_key = serialization.load_pem_public_key(public_key_pem.encode("ascii"))
    except Exception:
        return False, "商业部署清单签名格式或公钥格式无效，已停止商业配置。"
    if not isinstance(public_key, Ed25519PublicKey):
        return False, "商业部署清单公钥不是 Ed25519 公钥，已停止商业配置。"
    try:
        public_key.verify(raw_signature, canonical_commercial_manifest_payload(manifest))
    except InvalidSignature:
        return False, "商业部署清单验签失败，已停止商业配置，避免本地篡改解锁权益。"
    except Exception:
        return False, "商业部署清单验签异常，已停止商业配置。"
    return True, "商业部署清单验签通过。"


def validate_commercial_manifest_trust(
    manifest: dict[str, Any],
    public_key_pem: str = "",
) -> CommercialManifestTrustDecision:
    has_commercial_controls = any(
        key in manifest
        for key in ("products", "entitlements", "commercial", "commercial_enabled", "agent_center", "value_added_services")
    )
    if not has_commercial_controls:
        return CommercialManifestTrustDecision(
            trusted=True,
            requires_signature=False,
            message="兼容旧版清单，未启用商业控制。",
        )

    signature = str(manifest.get("manifest_signature") or "").strip()
    issued_at = str(manifest.get("manifest_issued_at") or "").strip()
    algorithm = str(manifest.get("manifest_signature_algorithm") or "").strip().lower()
    key_id = str(manifest.get("manifest_key_id") or "").strip()
    if not signature or not issued_at or not algorithm or not key_id:
        return CommercialManifestTrustDecision(
            trusted=False,
            requires_signature=True,
            message="商业部署清单缺少服务端签名、签发时间、算法或密钥 ID，已停止商业配置，避免本地篡改解锁权益。",
        )
    if not public_key_pem:
        return CommercialManifestTrustDecision(
            trusted=False,
            requires_signature=True,
            message="商业部署清单缺少客户端验签公钥，已停止商业配置。",
        )
    if algorithm != "ed25519":
        return CommercialManifestTrustDecision(
            trusted=False,
            requires_signature=True,
            message="商业部署清单签名算法不受支持，已停止商业配置。",
        )

    verified, message = _verify_ed25519_manifest_signature(manifest, public_key_pem)
    if not verified:
        return CommercialManifestTrustDecision(False, True, message)

    return CommercialManifestTrustDecision(
        trusted=True,
        requires_signature=True,
        message=message,
    )


def commercial_config_gate(
    agent_id: str,
    mode_key: str,
    capabilities: dict[str, AgentCommercialCapability],
    entitlements: list[EntitlementContract],
    commercial_manifest_present: bool,
) -> CommercialConfigGateDecision:
    capability = capabilities.get(agent_id)
    if capability is None and commercial_manifest_present:
        return CommercialConfigGateDecision(False, f"{agent_id} 服务端未开放完整配置交付。")
    if capability:
        if capability.delivery_scope == DeliveryScope.HIDDEN:
            return CommercialConfigGateDecision(False, f"{agent_id} 当前已隐藏，不能作为付费配置交付。")
        if capability.delivery_scope == DeliveryScope.PAUSED:
            return CommercialConfigGateDecision(False, f"{agent_id} 当前已暂停，不能作为付费配置交付。")
        if not capability.can_sell_full_config:
            return CommercialConfigGateDecision(False, f"{agent_id} 当前未开放完整配置交付。")

    if commercial_manifest_present:
        entitlement = find_usable_entitlement(entitlements, agent_id=agent_id, mode_key=mode_key)
        if entitlement is None:
            return CommercialConfigGateDecision(False, "当前账号没有可用权益，不能启动付费配置。")
        return CommercialConfigGateDecision(True, "权益可用，可以启动配置。", entitlement.entitlement_id)

    return CommercialConfigGateDecision(True, "兼容旧版清单，允许继续。")


def verify_real_task_evidence(
    diagnostic_code: str,
    agent_id: str,
    mode_key: str,
    request_ok: bool,
    response_ok: bool,
    response_excerpt: str,
) -> RealTaskVerificationResult:
    if request_ok and response_ok and response_excerpt.strip():
        return RealTaskVerificationResult(
            diagnostic_code=diagnostic_code,
            agent_id=agent_id,
            mode_key=mode_key,
            passed=True,
            status=NodeStatus.PASS,
            customer_message="真实任务验证已通过，可以提交商业交付成功。",
            response_excerpt=response_excerpt.strip()[:200],
        )
    return RealTaskVerificationResult(
        diagnostic_code=diagnostic_code,
        agent_id=agent_id,
        mode_key=mode_key,
        passed=False,
        status=NodeStatus.FAILED,
        customer_message="真实任务验证失败，暂不扣次；请按诊断码交给客服排查。",
        response_excerpt=response_excerpt.strip()[:200],
    )


def verify_client_scope_delivery_evidence(
    diagnostic_code: str,
    agent_id: str,
    mode_key: str,
    client_installed: bool,
    config_written: bool,
    detail: str,
) -> RealTaskVerificationResult:
    """客户端（桌面 App）形态的验收判定。

    产品决策：桌面客户端无法自动驱动图形界面做联网对话验收，因此退而求其次——
    只要官方客户端已安装（检测到）且胖虎AI网关配置已写入，即视为客户端交付合格并扣次。
    这条规则只用于官方提供客户端的 Agent（Codex/ClaudeCode/Antigravity）；CLI-only
    的 Agent 在 verify_agent_client_scope 处就已判定 client_installed=False，不会走到通过分支。
    """
    if client_installed and config_written:
        return RealTaskVerificationResult(
            diagnostic_code=diagnostic_code,
            agent_id=agent_id,
            mode_key=mode_key,
            passed=True,
            status=NodeStatus.PASS,
            customer_message="官方客户端已安装并写入胖虎AI网关配置，客户端交付已完成（客户端形态不做联网对话验收）。",
            response_excerpt=detail.strip()[:200],
        )
    return RealTaskVerificationResult(
        diagnostic_code=diagnostic_code,
        agent_id=agent_id,
        mode_key=mode_key,
        passed=False,
        status=NodeStatus.FAILED,
        customer_message="官方客户端未确认或配置未写入，暂不扣次；请按诊断码交给客服排查。",
        response_excerpt=detail.strip()[:200],
    )


def build_real_task_diagnostic_summary(result: RealTaskVerificationResult, api_key: str) -> str:
    agent_label = AGENT_LABELS.get(result.agent_id, result.agent_id)
    mode_label = MODE_LABELS.get(result.mode_key, result.mode_key)
    excerpt = result.response_excerpt.replace(api_key, "***") if api_key else result.response_excerpt
    return (
        f"诊断码：{result.diagnostic_code}\n"
        f"Agent：{agent_label}\n"
        f"模式：{mode_label}\n"
        f"状态：{STATUS_MESSAGES[result.status]}\n"
        f"说明：{result.customer_message}\n"
        f"响应摘要：{excerpt or '无'}"
    )


def build_support_diagnostic_packet(
    diagnostic_code: str,
    progress: DeploymentProgress,
    agent_id: str,
    mode_key: str,
    customer_message: str,
    api_key: str = "",
    commercial_ids: list[str] | None = None,
) -> str:
    agent_label = AGENT_LABELS.get(agent_id, agent_id)
    mode_label = MODE_LABELS.get(mode_key, mode_key)
    lines = [
        "客服诊断包",
        f"诊断码：{diagnostic_code}",
        f"Agent：{agent_label}",
        f"模式：{mode_label}",
        f"说明：{customer_message}",
        "节点状态：",
    ]
    for row in build_node_status_rows(progress):
        lines.append(f"- {row.title}：{STATUS_MESSAGES[row.status]}")
    packet = "\n".join(lines)
    if api_key:
        packet = packet.replace(api_key, "***")
    for item in commercial_ids or []:
        if item:
            packet = packet.replace(str(item), "***")
    return sanitize_customer_diagnostic_text(packet)


def create_buyer_contexts(buyer: UserContext) -> CommercialSessionContexts:
    return CommercialSessionContexts(
        operator=buyer,
        target_buyer=buyer,
        web_profile_scope=WebProfileScope.BUYER,
    )


def _parse_delivery_scope(value: Any) -> DeliveryScope:
    try:
        return DeliveryScope(str(value or DeliveryScope.INSTALL_GUIDED.value))
    except ValueError:
        return DeliveryScope.INSTALL_GUIDED


def _entitlement_customer_status(entitlement: EntitlementContract) -> str:
    if entitlement.status == "active" and entitlement.remaining_uses < 1 and not entitlement.is_unlimited:
        return ENTITLEMENT_STATUS_LABELS["used_up"]
    return ENTITLEMENT_STATUS_LABELS.get(entitlement.status, entitlement.status or "未知")


def _delivery_scope_label(scope: DeliveryScope) -> str:
    labels = {
        DeliveryScope.FULL_CONFIG: "完整配置",
        DeliveryScope.ASSISTED_FULL_CONFIG: "协助完整配置",
        DeliveryScope.GUIDED_FULL_CONFIG: "引导完整配置",
        DeliveryScope.PARTIAL_CONFIG: "部分配置",
        DeliveryScope.INSTALL_GUIDED: "安装引导",
        DeliveryScope.GUIDE_ONLY: "说明引导",
        DeliveryScope.OFFICIAL_ENTRY_ONLY: "官方入口",
        DeliveryScope.PAUSED: "已暂停",
        DeliveryScope.HIDDEN: "已隐藏",
    }
    return labels[scope]


def build_commercial_agent_capabilities(manifest: dict[str, Any]) -> dict[str, AgentCommercialCapability]:
    capabilities: dict[str, AgentCommercialCapability] = {}
    agents = manifest.get("agents") or []
    if not isinstance(agents, list):
        return capabilities
    for item in agents:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        agent_id = str(item["id"])
        delivery_scope = _parse_delivery_scope(item.get("delivery_scope"))
        capabilities[agent_id] = AgentCommercialCapability(
            agent_id=agent_id,
            delivery_scope=delivery_scope,
            full_config_allowed=bool(item.get("full_config_allowed")),
            min_client_version=str(item.get("min_client_version") or ""),
            playbook_version=str(item.get("playbook_version") or ""),
        )
    return capabilities


def commercial_deployment_blockers(
    selected_agent_ids: list[str],
    capabilities: dict[str, AgentCommercialCapability],
) -> list[str]:
    blockers: list[str] = []
    for agent_id in selected_agent_ids:
        capability = capabilities.get(agent_id)
        if not capability:
            continue
        if capability.delivery_scope == DeliveryScope.HIDDEN:
            blockers.append(f"{agent_id} 当前已隐藏，不能部署。")
        elif capability.delivery_scope == DeliveryScope.PAUSED:
            blockers.append(f"{agent_id} 当前已暂停，不能部署。")
        elif not capability.can_sell_full_config:
            blockers.append(f"{agent_id} 当前未开放完整配置交付，不能作为付费部署。")
    return blockers


def api_key_owner_gate(
    contexts: CommercialSessionContexts,
    verified_owner_user_id: str,
) -> ApiKeyOwnerGateDecision:
    owner_id = str(verified_owner_user_id or "").strip()
    target_buyer_id = contexts.target_buyer.user_id.strip()
    if not owner_id:
        return ApiKeyOwnerGateDecision(
            allowed=False,
            message="服务端未确认 API Key 归属，不能作为商业配置交付。",
        )
    if owner_id != target_buyer_id:
        return ApiKeyOwnerGateDecision(
            allowed=False,
            message="API Key 归属与目标买家不一致，请让目标买家创建自己的 Key 后再配置。",
        )
    return ApiKeyOwnerGateDecision(
        allowed=True,
        message="API Key 归属已确认，属于目标买家。",
    )


def build_persistent_profile_payload(
    current_profile: dict[str, Any],
    updates: dict[str, Any],
    contexts: CommercialSessionContexts | None,
    default_base_url: str,
    default_model: str,
) -> dict[str, Any]:
    current = dict(current_profile)
    current.update(updates)
    user = current.get("user")
    deployer_auth = current.get("deployer_auth")
    if isinstance(user, dict) and str(user.get("role") or "").lower() == "agent":
        current["username"] = ""
    if isinstance(deployer_auth, dict) and str(deployer_auth.get("role") or "").lower() == "agent":
        current["username"] = ""

    return {
        "username": str(current.get("username") or ""),
        "user": {},
        "deployer_auth": {},
        "api_key": str(current.get("api_key") or ""),
        "base_url": default_base_url,
        "model": str(current.get("model") or default_model),
        "skip_test": bool(current.get("skip_test")),
        "open_app": bool(current.get("open_app", True)),
    }
