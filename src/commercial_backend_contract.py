from __future__ import annotations

from dataclasses import dataclass
import hashlib

from commercial_api import sanitize_agent_center_summary


@dataclass
class ContractOrder:
    # Service-side commercial model. The current desktop client should not
    # interpret agent_chain as a local proxy workflow contract.
    order_id: str
    idempotency_key: str
    product_id: str
    buyer_user_id: str
    operator_user_id: str
    agent_chain: list[str]
    diagnostic_code: str
    delivery_scope: str = "codex_agent_config"
    status: str = "created"
    entitlement_id: str = ""


@dataclass
class ContractEntitlement:
    entitlement_id: str
    order_id: str
    buyer_user_id: str
    agent_id: str = "codex"
    mode_key: str = "direct_api"
    remaining_uses: int = 1
    status: str = "active"
    source: str = "paid"
    delivery_scope: str = "codex_agent_config"
    is_unlimited: bool = False
    device_limit: int = 1
    bound_device_ids: set[str] | None = None


@dataclass
class ContractConfigSession:
    config_session_id: str
    entitlement_id: str
    buyer_user_id: str
    operator_user_id: str
    agent_id: str
    mode_key: str
    device_id: str
    diagnostic_code: str
    delivery_scope: str = "codex_agent_config"
    status: str = "reserved"
    deducted: bool = False


@dataclass
class ContractAgentProduct:
    product_id: str
    level: str
    name: str
    price_cents: int = 0
    currency: str = "CNY"
    validity_days: int = 365
    requires_review: bool = False
    status: str = "listed"
    intro_page_enabled: bool = True


@dataclass
class ContractAgentProfile:
    user_id: str
    level: str
    status: str
    product_id: str
    invite_code: str
    activated_at: str = ""
    expires_at: str = ""


@dataclass
class ContractReferralBinding:
    buyer_user_id: str
    direct_agent_user_id: str
    bound_at: str
    source_invite_code: str


@dataclass
class ContractAgentChainSnapshot:
    buyer_user_id: str
    source_event_id: str
    chain: list[str]


@dataclass
class ContractAgentApplication:
    application_id: str
    user_id: str
    product_id: str
    status: str
    reviewer_user_id: str = ""
    review_reason: str = ""


@dataclass
class ContractCommissionPolicyRule:
    event_type: str
    receiver_level: str
    depth: int
    rate_bps: int
    status: str = "active"


@dataclass
class ContractCommissionEvent:
    event_id: str
    source_event_id: str
    event_type: str
    buyer_user_id: str
    amount_cents: int
    status: str = "recorded"


@dataclass
class ContractCommissionEntry:
    # Service-side commission bookkeeping, not a desktop-side product flow.
    commission_id: str
    order_id: str
    agent_user_id: str
    status: str = "pending"
    source_event_id: str = ""
    event_type: str = ""
    depth: int = 0
    rate_bps: int = 0
    commission_cents: int = 0
    available_after_days: int = 7
    settlement_id: str = ""


@dataclass
class ContractCommissionReversal:
    # Service-side commission reversal bookkeeping.
    reversal_id: str
    order_id: str
    reason: str


@dataclass
class ContractSettlementRequest:
    settlement_id: str
    agent_user_id: str
    requested_cents: int
    commission_ids: list[str]
    status: str = "pending"
    admin_user_id: str = ""


@dataclass
class ContractServiceProduct:
    product_id: str
    service_type: str
    name: str
    price_cents: int
    currency: str = "CNY"
    status: str = "listed"
    requires_base_agent_delivery: bool = False
    agent_runtime_readiness_policy: str = "manual_or_detected"
    allowed_agent_sources: tuple[str, ...] = ()
    supported_agent_ids: tuple[str, ...] = ()
    supported_channels: tuple[str, ...] = ()
    intro_copy: str = ""


@dataclass
class ContractServiceOrder:
    order_id: str
    idempotency_key: str
    buyer_user_id: str
    service_product_id: str
    service_type: str
    agent_id: str
    channel: str
    agent_source: str
    status: str = "created"
    charge_status: str = "unpaid"
    payment_id: str = ""
    delivered_at: str = ""
    cancelled_at: str = ""


@dataclass
class ContractCommunicationSoftwareLinkSession:
    session_id: str
    order_id: str
    buyer_user_id: str
    agent_id: str
    channel: str
    platform_account_id: str
    platform_chat_id: str
    gateway_mode: str
    agent_source: str
    status: str = "pending_config"
    last_probe_at: str = ""
    accepted_at: str = ""


@dataclass
class ContractCommunicationSoftwareLinkAcceptanceRecord:
    acceptance_id: str
    order_id: str
    session_id: str
    source_event_id: str
    inbound_platform_message_id: str
    outbound_platform_message_id: str
    test_prompt: str
    agent_response_digest: str
    evidence_url: str
    accepted_by: str
    accepted_at: str = "day-0"


@dataclass
class ContractServiceLedgerEvent:
    ledger_event_id: str
    source_event_id: str
    service_type: str
    event_type: str
    order_id: str
    buyer_user_id: str
    amount_cents: int
    status: str = "recorded"


@dataclass(frozen=True)
class ContractCommunicationSoftwareLinkCallbackDecision:
    should_invoke_agent: bool
    status: str
    reason: str
    source_event_id: str = ""


@dataclass
class ContractCommunicationSoftwareLinkRuntimeResult:
    source_event_id: str
    session_id: str
    inbound_platform_message_id: str
    outbound_platform_message_id: str
    agent_response_digest: str
    status: str
    error_message: str = ""


@dataclass
class ContractCommunicationSoftwareLinkDeliveryResult:
    status: str
    decision: ContractCommunicationSoftwareLinkCallbackDecision
    runtime_result: ContractCommunicationSoftwareLinkRuntimeResult | None = None
    acceptance_record: ContractCommunicationSoftwareLinkAcceptanceRecord | None = None
    reason: str = ""


# 连接通讯软件使用统一服务类型、账本事件和验收记录。
COMMUNICATION_SOFTWARE_LINK_SERVICE_TYPE = "communication_software_link"
AGENT_INSTALL_SERVICE_TYPE = "agent_install_delivery"
COMMUNICATION_SOFTWARE_LINK_DELIVERED_EVENT = "communication_software_link_delivered"
AGENT_INSTALL_DELIVERED_EVENT = "agent_install_delivered"
TOOL_ORDER_PAID_EVENT = "tool_order_paid"
COMMUNICATION_SOFTWARE_LINK_CHANNELS = {"qq_bot", "weixin", "feishu", "dingtalk", "wecom"}
COMMUNICATION_SOFTWARE_LINK_AGENT_IDS = {"codex", "claude_code", "openclaw", "hermes"}
COMMUNICATION_SOFTWARE_LINK_AGENT_SOURCES = {
    "current_delivery",
    "historical_delivery",
    "existing_local_agent",
    "manual_review",
}
COMMUNICATION_SOFTWARE_LINK_SESSION_TERMINAL_STATUSES = {"acceptance_passed", "failed", "disabled"}
AGENT_CENTER_REQUIRED_SUMMARY_FIELDS = (
    "downstream_count",
    "token_commission_cents",
    "activation_commission_cents",
    "agent_install_commission_cents",
    "available_settlement_cents",
    "pending_settlement_cents",
    "frozen_cents",
)


def _require_current_buyer_operator(buyer_user_id: str, operator_user_id: str) -> None:
    if str(buyer_user_id or "").strip() != str(operator_user_id or "").strip():
        raise ValueError("客户端商业操作必须由当前买家本人发起。")


class CommercialLedgerContract:
    def __init__(self) -> None:
        self.orders: dict[str, ContractOrder] = {}
        self.order_idempotency: dict[str, str] = {}
        self.order_idempotency_payloads: dict[str, tuple[object, ...]] = {}
        self.entitlements: dict[str, ContractEntitlement] = {}
        self.payment_idempotency: dict[str, str] = {}
        self.payment_idempotency_payloads: dict[str, tuple[object, ...]] = {}
        self.trial_idempotency: dict[str, str] = {}
        self.trial_idempotency_payloads: dict[str, tuple[object, ...]] = {}
        self.trial_claims: dict[str, str] = {}
        self.config_sessions: dict[str, ContractConfigSession] = {}
        self.session_idempotency: dict[str, str] = {}
        self.session_idempotency_payloads: dict[str, tuple[object, ...]] = {}
        self.api_key_owners: dict[str, str] = {}
        # Agent center is a service-side snapshot shown in the embedded site
        # flow. It must not be treated as a local proxy-mode state machine.
        self.agent_center: dict[str, object] = {"enabled": False}
        self.agent_products: dict[str, ContractAgentProduct] = {}
        self.agent_profiles: dict[str, ContractAgentProfile] = {}
        self.agent_applications: list[ContractAgentApplication] = []
        self.invite_codes: dict[str, str] = {}
        self.referral_bindings: dict[str, ContractReferralBinding] = {}
        self.referral_binding_idempotency: dict[str, str] = {}
        self.referral_binding_payloads: dict[str, tuple[object, ...]] = {}
        self.agent_chain_snapshots: list[ContractAgentChainSnapshot] = []
        self.agent_marketing_content: dict[str, object] = {
            "page_title": "胖虎AI代理招募",
            "hero_title": "成为胖虎AI代理",
            "selling_points": [],
            "faq": [],
            "materials": [],
        }
        self.commission_policy_rules: list[ContractCommissionPolicyRule] = []
        self.commission_events: list[ContractCommissionEvent] = []
        self.commission_event_idempotency: dict[str, str] = {}
        self.commission_event_payloads: dict[str, tuple[object, ...]] = {}
        self.commission_entries: list[ContractCommissionEntry] = []
        self.commission_reversals: list[ContractCommissionReversal] = []
        self.settlement_requests: dict[str, ContractSettlementRequest] = {}
        self.service_products: dict[str, ContractServiceProduct] = {}
        self.service_orders: dict[str, ContractServiceOrder] = {}
        self.service_order_idempotency: dict[str, str] = {}
        self.service_order_idempotency_payloads: dict[str, tuple[object, ...]] = {}
        self.communication_software_link_sessions: dict[str, ContractCommunicationSoftwareLinkSession] = {}
        self.communication_software_link_session_idempotency: dict[str, str] = {}
        self.communication_software_link_session_idempotency_payloads: dict[str, tuple[object, ...]] = {}
        self.communication_software_link_acceptance_records: dict[str, ContractCommunicationSoftwareLinkAcceptanceRecord] = {}
        self.communication_software_link_acceptance_payloads: dict[str, tuple[object, ...]] = {}
        self.communication_software_link_acceptance_by_source_event: dict[str, str] = {}
        self.communication_software_link_callback_source_events: dict[str, tuple[object, ...]] = {}
        self.communication_software_link_accepted_callback_source_events: set[str] = set()
        self.communication_software_link_runtime_results: dict[str, ContractCommunicationSoftwareLinkRuntimeResult] = {}
        self.service_ledger_events: dict[str, ContractServiceLedgerEvent] = {}
        self.service_ledger_events_by_source_event: dict[str, str] = {}
        self.service_ledger_event_payloads: dict[str, tuple[object, ...]] = {}

    def _api_key_fingerprint(self, api_key: str) -> str:
        return hashlib.sha256(api_key.strip().encode("utf-8")).hexdigest()

    def register_api_key_owner(self, api_key: str, owner_user_id: str) -> None:
        if not api_key.strip() or not owner_user_id.strip():
            raise ValueError("API Key 或归属用户为空。")
        self.api_key_owners[self._api_key_fingerprint(api_key)] = owner_user_id.strip()

    def verify_api_key_owner(
        self,
        api_key: str,
        target_buyer_user_id: str,
        operator_user_id: str,
    ) -> dict[str, str]:
        _require_current_buyer_operator(target_buyer_user_id, operator_user_id)
        owner_user_id = self.api_key_owners.get(self._api_key_fingerprint(api_key), "")
        if not owner_user_id:
            raise ValueError("服务端未确认 API Key 归属。")
        if owner_user_id != target_buyer_user_id:
            raise ValueError("API Key 归属与目标买家不一致。")
        return {
            "owner_user_id": owner_user_id,
            "target_buyer_user_id": target_buyer_user_id,
            "operator_user_id": operator_user_id,
        }

    def configure_agent_center(
        self,
        enabled: bool,
        current_level: str = "",
        upgrade_label: str = "",
        invite_url: str = "",
        join_page_url: str = "",
        backend_url: str = "",
        rules_url: str = "",
        status: str = "",
        settlement_status: str = "",
        last_synced_at: str = "",
        summary: dict[str, int] | None = None,
        benefits: list[str] | None = None,
        boundaries: list[str] | None = None,
        commission_ratio: str = "",
    ) -> None:
        self.agent_center = {
            "enabled": bool(enabled),
            "current_level": current_level,
            "upgrade_label": upgrade_label,
            "invite_url": invite_url,
            "join_page_url": join_page_url,
            "backend_url": backend_url,
            "rules_url": rules_url,
            "status": status,
            "settlement_status": settlement_status,
            "last_synced_at": last_synced_at,
            "summary": dict(summary or {}),
            "benefits": list(benefits or []),
            "boundaries": list(boundaries or []),
            "commission_ratio": commission_ratio,
        }

    def agent_center_snapshot(self) -> dict[str, object]:
        status = str(self.agent_center.get("status") or "").strip().lower()
        enabled = bool(self.agent_center.get("enabled"))
        summary = sanitize_agent_center_summary(self.agent_center.get("summary"))
        settlement_status = str(self.agent_center.get("settlement_status") or "").strip().lower()
        last_synced_at = str(self.agent_center.get("last_synced_at") or "").strip()
        missing_fields: list[str] = []
        blocking_gaps: list[str] = []

        if status == "not_agent":
            snapshot_status = "not_agent"
        elif not status and not enabled:
            snapshot_status = "snapshot_missing"
            blocking_gaps.append("Agent Center 服务端快照未返回，不能视为代理中心完成。")
        else:
            for field in AGENT_CENTER_REQUIRED_SUMMARY_FIELDS:
                if field not in summary:
                    missing_fields.append(f"summary.{field}")
            if not settlement_status:
                missing_fields.append("settlement_status")
            if not last_synced_at:
                missing_fields.append("last_synced_at")
            if missing_fields:
                snapshot_status = "guarded"
                blocking_gaps.append("Agent Center 管理员后台字段缺失，保持本地 guarded 状态。")
            elif settlement_status == "pending":
                snapshot_status = "settlement_pending"
            else:
                snapshot_status = status or "active"

        return {
            "enabled": enabled,
            "status": status,
            "snapshot_status": snapshot_status,
            "settlement_status": settlement_status,
            "last_synced_at": last_synced_at,
            "missing_fields": missing_fields,
            "blocking_gaps": blocking_gaps,
            "required_summary_fields": list(AGENT_CENTER_REQUIRED_SUMMARY_FIELDS),
            "current_level": str(self.agent_center.get("current_level") or ""),
            "upgrade_label": str(self.agent_center.get("upgrade_label") or ""),
            "invite_url": str(self.agent_center.get("invite_url") or ""),
            "join_page_url": str(self.agent_center.get("join_page_url") or ""),
            "backend_url": str(self.agent_center.get("backend_url") or ""),
            "rules_url": str(self.agent_center.get("rules_url") or ""),
            "summary": summary,
            "benefits": list(self.agent_center.get("benefits") or []),
            "boundaries": list(self.agent_center.get("boundaries") or []),
        }

    def configure_agent_product(
        self,
        product_id: str,
        level: str,
        name: str,
        price_cents: int = 0,
        currency: str = "CNY",
        validity_days: int = 365,
        requires_review: bool = False,
        status: str = "listed",
        intro_page_enabled: bool = True,
    ) -> ContractAgentProduct:
        if level not in {"L1", "L2", "L3", "L4", "L5"}:
            raise ValueError("代理等级必须是 L1-L5。")
        if price_cents < 0:
            raise ValueError("代理费用不能为负数。")
        product = ContractAgentProduct(
            product_id=product_id,
            level=level,
            name=name,
            price_cents=price_cents,
            currency=currency,
            validity_days=validity_days,
            requires_review=requires_review,
            status=status,
            intro_page_enabled=intro_page_enabled,
        )
        self.agent_products[product_id] = product
        return product

    def configure_agent_marketing_content(
        self,
        page_title: str,
        hero_title: str,
        selling_points: list[str] | None = None,
        faq: list[dict[str, str]] | None = None,
        materials: list[dict[str, str]] | None = None,
        level_descriptions: dict[str, str] | None = None,
    ) -> dict[str, object]:
        self.agent_marketing_content = {
            "page_title": page_title,
            "hero_title": hero_title,
            "selling_points": list(selling_points or []),
            "faq": [dict(item) for item in (faq or [])],
            "materials": [dict(item) for item in (materials or [])],
            "level_descriptions": dict(level_descriptions or {}),
        }
        return dict(self.agent_marketing_content)

    def public_agent_offering(self) -> dict[str, object]:
        products: list[dict[str, object]] = []
        for product in self.agent_products.values():
            if product.status != "listed" or not product.intro_page_enabled:
                continue
            products.append(
                {
                    "id": product.product_id,
                    "level": product.level,
                    "name": product.name,
                    "price_cents": product.price_cents,
                    "currency": product.currency,
                    "validity_days": product.validity_days,
                    "requires_review": product.requires_review,
                    "status": product.status,
                    "intro_page_enabled": product.intro_page_enabled,
                }
            )
        products.sort(key=lambda item: str(item["level"]))
        available_levels = sorted({str(product["level"]) for product in products})
        return {
            "marketing_content": dict(self.agent_marketing_content),
            "products": products,
            "available_levels": available_levels,
        }

    def apply_agent(self, user_id: str, product_id: str) -> ContractAgentProfile:
        product = self.agent_products[product_id]
        if product.status != "listed":
            raise ValueError("代理产品未上架。")
        status = "pending_review" if product.requires_review or product.price_cents > 0 else "active"
        invite_code = f"invite-{user_id}".replace("_", "-")
        profile = ContractAgentProfile(
            user_id=user_id,
            level=product.level,
            status=status,
            product_id=product.product_id,
            invite_code=invite_code,
            activated_at="day-0" if status == "active" else "",
            expires_at=f"day-{max(0, product.validity_days)}" if status == "active" else "",
        )
        self.agent_profiles[user_id] = profile
        self.invite_codes[invite_code] = user_id
        self.agent_applications.append(
            ContractAgentApplication(
                application_id=f"app-{len(self.agent_applications) + 1}",
                user_id=user_id,
                product_id=product.product_id,
                status=status if status == "pending_review" else "approved",
            )
        )
        return profile

    def review_agent_application(
        self,
        application_id: str,
        decision: str,
        reviewer_user_id: str,
        reason: str,
    ) -> ContractAgentApplication:
        application = next(
            (item for item in self.agent_applications if item.application_id == application_id),
            None,
        )
        if application is None:
            raise ValueError("代理申请不存在。")
        if decision not in {"approve", "reject"}:
            raise ValueError("未知代理审核动作。")
        profile = self.agent_profiles[application.user_id]
        product = self.agent_products[application.product_id]
        application.reviewer_user_id = reviewer_user_id
        application.review_reason = reason
        if decision == "approve":
            application.status = "approved"
            profile.status = "active"
            profile.activated_at = "day-0"
            profile.expires_at = f"day-{max(0, product.validity_days)}"
        else:
            application.status = "rejected"
            profile.status = "rejected"
        return application

    def bind_referral_request(
        self,
        idempotency_key: str,
        buyer_user_id: str,
        invite_code: str,
    ) -> ContractReferralBinding:
        normalized_idempotency_key = str(idempotency_key or "").strip()
        normalized_buyer_user_id = str(buyer_user_id or "").strip()
        normalized_invite_code = str(invite_code or "").strip()
        if not normalized_idempotency_key:
            raise ValueError("代理绑定幂等键为空。")
        payload = (normalized_buyer_user_id, normalized_invite_code)
        if normalized_idempotency_key in self.referral_binding_idempotency:
            if self.referral_binding_payloads[normalized_idempotency_key] != payload:
                raise ValueError("代理绑定幂等键请求参数不一致。")
            bound_buyer_user_id = self.referral_binding_idempotency[normalized_idempotency_key]
            return self.referral_bindings[bound_buyer_user_id]
        agent_user_id = self.invite_codes.get(normalized_invite_code)
        if not agent_user_id:
            raise ValueError("邀请码无效。")
        if normalized_buyer_user_id == agent_user_id:
            raise ValueError("代理不能绑定自己。")
        profile = self.agent_profiles.get(agent_user_id)
        if profile is None or profile.status != "active":
            raise ValueError("代理账号未激活，不能绑定返佣关系。")
        binding = self.bind_referral(normalized_buyer_user_id, normalized_invite_code)
        self.referral_binding_idempotency[normalized_idempotency_key] = binding.buyer_user_id
        self.referral_binding_payloads[normalized_idempotency_key] = payload
        return binding

    def bind_referral(self, buyer_user_id: str, invite_code: str) -> ContractReferralBinding:
        if buyer_user_id in self.referral_bindings:
            return self.referral_bindings[buyer_user_id]
        agent_user_id = self.invite_codes.get(invite_code)
        if not agent_user_id:
            raise ValueError("邀请码无效。")
        binding = ContractReferralBinding(
            buyer_user_id=buyer_user_id,
            direct_agent_user_id=agent_user_id,
            bound_at="day-0",
            source_invite_code=invite_code,
        )
        self.referral_bindings[buyer_user_id] = binding
        return binding

    def build_agent_chain_snapshot(self, buyer_user_id: str, source_event_id: str) -> ContractAgentChainSnapshot:
        chain: list[str] = []
        current_user_id = buyer_user_id
        seen: set[str] = set()
        while len(chain) < 5:
            binding = self.referral_bindings.get(current_user_id)
            if binding is None or binding.direct_agent_user_id in seen:
                break
            agent_user_id = binding.direct_agent_user_id
            profile = self.agent_profiles.get(agent_user_id)
            if profile is None or profile.status != "active":
                break
            chain.append(agent_user_id)
            seen.add(agent_user_id)
            current_user_id = agent_user_id
        snapshot = ContractAgentChainSnapshot(
            buyer_user_id=buyer_user_id,
            source_event_id=source_event_id,
            chain=chain,
        )
        self.agent_chain_snapshots.append(snapshot)
        return snapshot

    def configure_commission_policy_rule(
        self,
        event_type: str,
        receiver_level: str,
        depth: int,
        rate_bps: int,
        status: str = "active",
    ) -> ContractCommissionPolicyRule:
        if event_type not in {
            "token_usage_settled",
            "activation_paid",
            AGENT_INSTALL_DELIVERED_EVENT,
            TOOL_ORDER_PAID_EVENT,
            COMMUNICATION_SOFTWARE_LINK_DELIVERED_EVENT,
        }:
            raise ValueError("未知代理返佣事件类型。")
        if receiver_level not in {"L1", "L2", "L3", "L4", "L5"}:
            raise ValueError("代理等级必须是 L1-L5。")
        if depth < 1 or depth > 5:
            raise ValueError("代理返佣层级必须在 1-5 层。")
        if rate_bps < 0:
            raise ValueError("返佣比例不能为负数。")
        rule = ContractCommissionPolicyRule(
            event_type=event_type,
            receiver_level=receiver_level,
            depth=depth,
            rate_bps=rate_bps,
            status=status,
        )
        self.commission_policy_rules.append(rule)
        return rule

    def record_commission_event(
        self,
        source_event_id: str,
        event_type: str,
        buyer_user_id: str,
        amount_cents: int,
    ) -> ContractCommissionEvent:
        payload = (event_type, buyer_user_id, amount_cents)
        if source_event_id in self.commission_event_idempotency:
            if self.commission_event_payloads[source_event_id] != payload:
                raise ValueError("事件幂等键请求参数不一致。")
            event_id = self.commission_event_idempotency[source_event_id]
            return next(event for event in self.commission_events if event.event_id == event_id)
        if amount_cents < 0:
            raise ValueError("返佣来源金额不能为负数。")
        event = ContractCommissionEvent(
            event_id=f"evt-{len(self.commission_events) + 1}",
            source_event_id=source_event_id,
            event_type=event_type,
            buyer_user_id=buyer_user_id,
            amount_cents=amount_cents,
        )
        self.commission_events.append(event)
        self.commission_event_idempotency[source_event_id] = event.event_id
        self.commission_event_payloads[source_event_id] = payload
        snapshot = self.build_agent_chain_snapshot(buyer_user_id, source_event_id)
        for depth, agent_user_id in enumerate(snapshot.chain, start=1):
            profile = self.agent_profiles[agent_user_id]
            level_number = self._level_number(profile.level)
            if level_number < depth:
                continue
            rule = self._commission_rule_for(event_type, profile.level, depth)
            if rule is None or rule.status != "active" or rule.rate_bps <= 0:
                continue
            self.commission_entries.append(
                ContractCommissionEntry(
                    commission_id=f"com-{len(self.commission_entries) + 1}",
                    order_id="",
                    agent_user_id=agent_user_id,
                    source_event_id=source_event_id,
                    event_type=event_type,
                    depth=depth,
                    rate_bps=rule.rate_bps,
                    commission_cents=amount_cents * rule.rate_bps // 10000,
                    available_after_days=7,
                )
            )
        return event

    def release_commissions_after_days(self, elapsed_days: int) -> None:
        for entry in self.commission_entries:
            if entry.status == "pending" and elapsed_days >= entry.available_after_days:
                entry.status = "available"

    def create_settlement_request(self, agent_user_id: str, requested_cents: int) -> ContractSettlementRequest:
        if requested_cents <= 0:
            raise ValueError("结算金额必须大于 0。")
        available_entries = [
            entry
            for entry in self.commission_entries
            if entry.agent_user_id == agent_user_id and entry.status == "available"
        ]
        available_cents = sum(entry.commission_cents for entry in available_entries)
        if available_cents < requested_cents:
            raise ValueError("可结算金额不足。")
        selected: list[ContractCommissionEntry] = []
        selected_cents = 0
        for entry in available_entries:
            selected.append(entry)
            selected_cents += entry.commission_cents
            if selected_cents >= requested_cents:
                break
        settlement = ContractSettlementRequest(
            settlement_id=f"stl-{len(self.settlement_requests) + 1}",
            agent_user_id=agent_user_id,
            requested_cents=requested_cents,
            commission_ids=[entry.commission_id for entry in selected],
        )
        self.settlement_requests[settlement.settlement_id] = settlement
        for entry in selected:
            entry.status = "settlement_requested"
            entry.settlement_id = settlement.settlement_id
        return settlement

    def mark_settlement_paid(self, settlement_id: str, admin_user_id: str) -> ContractSettlementRequest:
        settlement = self.settlement_requests.get(settlement_id)
        if settlement is None:
            raise ValueError("结算申请不存在。")
        if settlement.status == "settled":
            return settlement
        settlement.status = "settled"
        settlement.admin_user_id = admin_user_id
        commission_ids = set(settlement.commission_ids)
        for entry in self.commission_entries:
            if entry.commission_id in commission_ids:
                entry.status = "settled"
        return settlement

    def admin_update_commission_entry(
        self,
        commission_id: str,
        action: str,
        reason: str,
    ) -> ContractCommissionEntry:
        if action not in {"freeze", "release", "reverse"}:
            raise ValueError("未知代理账本动作。")
        entry = next((item for item in self.commission_entries if item.commission_id == commission_id), None)
        if entry is None:
            raise ValueError("代理佣金记录不存在。")
        if action == "freeze":
            if entry.status in {"available", "pending", "settlement_requested"}:
                entry.status = "frozen"
        elif action == "release":
            if entry.status == "frozen":
                entry.status = "available"
        else:
            if entry.status in {"settled", "withdrawn"}:
                entry.status = "manual_review"
            elif entry.status != "manual_review":
                entry.status = "reversed"
            self.commission_reversals.append(
                ContractCommissionReversal(
                    reversal_id=f"rev-{len(self.commission_reversals) + 1}",
                    order_id=entry.source_event_id or entry.order_id or commission_id,
                    reason=reason,
                )
            )
        return entry

    def reverse_commission_event(self, source_event_id: str, reason: str) -> None:
        for entry in self.commission_entries:
            if entry.source_event_id != source_event_id:
                continue
            if entry.status in {"settled", "withdrawn"}:
                entry.status = "manual_review"
            elif entry.status != "manual_review":
                entry.status = "reversed"
        self.commission_reversals.append(
            ContractCommissionReversal(
                reversal_id=f"rev-{len(self.commission_reversals) + 1}",
                order_id=source_event_id,
                reason=reason,
            )
        )

    def configure_service_product(
        self,
        product_id: str,
        service_type: str,
        name: str,
        price_cents: int,
        currency: str = "CNY",
        status: str = "listed",
        requires_base_agent_delivery: bool = False,
        agent_runtime_readiness_policy: str = "manual_or_detected",
        allowed_agent_sources: list[str] | tuple[str, ...] | None = None,
        supported_agent_ids: list[str] | tuple[str, ...] | None = None,
        supported_channels: list[str] | tuple[str, ...] | None = None,
        intro_copy: str = "",
    ) -> ContractServiceProduct:
        if service_type not in {AGENT_INSTALL_SERVICE_TYPE, COMMUNICATION_SOFTWARE_LINK_SERVICE_TYPE}:
            raise ValueError("未知服务类型。")
        if price_cents < 0:
            raise ValueError("服务价格不能为负数。")
        product = ContractServiceProduct(
            product_id=product_id,
            service_type=service_type,
            name=name,
            price_cents=price_cents,
            currency=currency,
            status=status,
            requires_base_agent_delivery=bool(requires_base_agent_delivery),
            agent_runtime_readiness_policy=agent_runtime_readiness_policy,
            allowed_agent_sources=tuple(allowed_agent_sources or sorted(COMMUNICATION_SOFTWARE_LINK_AGENT_SOURCES)),
            supported_agent_ids=tuple(supported_agent_ids or sorted(COMMUNICATION_SOFTWARE_LINK_AGENT_IDS)),
            supported_channels=tuple(supported_channels or sorted(COMMUNICATION_SOFTWARE_LINK_CHANNELS)),
            intro_copy=intro_copy,
        )
        self.service_products[product_id] = product
        return product

    def create_communication_software_link_order(
        self,
        idempotency_key: str,
        service_product_id: str,
        buyer_user_id: str,
        agent_id: str,
        channel: str,
        agent_source: str,
        allow_admin_presale: bool = False,
    ) -> ContractServiceOrder:
        product = self.service_products[service_product_id]
        payload = (
            service_product_id,
            buyer_user_id,
            agent_id,
            channel,
            agent_source,
            bool(allow_admin_presale),
        )
        if idempotency_key in self.service_order_idempotency:
            if self.service_order_idempotency_payloads[idempotency_key] != payload:
                raise ValueError("连接通讯软件订单幂等键请求参数不一致。")
            return self.service_orders[self.service_order_idempotency[idempotency_key]]
        self._validate_communication_software_link_product(product, agent_id, channel, agent_source)
        if product.status != "listed" and not allow_admin_presale:
            raise ValueError("连接通讯软件服务未上架。")
        if (
            product.requires_base_agent_delivery
            and agent_source == "current_delivery"
            and not self._has_completed_base_agent_delivery(buyer_user_id, agent_id)
            and not allow_admin_presale
        ):
            raise ValueError("尚未形成基础 Agent 交付验收，不能按本次交付来源创建连接通讯软件订单。")
        order_id = f"svc-ord-{len(self.service_orders) + 1}"
        order = ContractServiceOrder(
            order_id=order_id,
            idempotency_key=idempotency_key,
            buyer_user_id=buyer_user_id,
            service_product_id=service_product_id,
            service_type=COMMUNICATION_SOFTWARE_LINK_SERVICE_TYPE,
            agent_id=agent_id,
            channel=channel,
            agent_source=agent_source,
            charge_status="manual_review" if allow_admin_presale else "unpaid",
        )
        self.service_orders[order_id] = order
        self.service_order_idempotency[idempotency_key] = order_id
        self.service_order_idempotency_payloads[idempotency_key] = payload
        return order

    def mark_communication_software_link_order_paid(self, order_id: str, payment_id: str) -> ContractServiceOrder:
        order = self.service_orders[order_id]
        if order.service_type != COMMUNICATION_SOFTWARE_LINK_SERVICE_TYPE:
            raise ValueError("订单不是连接通讯软件服务。")
        if not str(payment_id or "").strip():
            raise ValueError("连接通讯软件支付 ID 为空。")
        if order.status in {"delivered", "failed", "cancelled", "canceled", "refunded", "reversed", "revoked"}:
            raise ValueError("连接通讯软件订单状态不可支付。")
        if order.charge_status == "paid":
            if order.payment_id != payment_id:
                raise ValueError("连接通讯软件订单支付 ID 不一致。")
            return order
        order.charge_status = "paid"
        order.payment_id = payment_id
        order.status = "paid"
        return order

    def create_communication_software_link_session(
        self,
        idempotency_key: str,
        order_id: str,
        buyer_user_id: str,
        agent_id: str,
        channel: str,
        platform_account_id: str,
        platform_chat_id: str,
        gateway_mode: str,
        agent_source: str,
    ) -> ContractCommunicationSoftwareLinkSession:
        payload = (
            order_id,
            buyer_user_id,
            agent_id,
            channel,
            platform_account_id,
            platform_chat_id,
            gateway_mode,
            agent_source,
        )
        if idempotency_key in self.communication_software_link_session_idempotency:
            if self.communication_software_link_session_idempotency_payloads[idempotency_key] != payload:
                raise ValueError("连接通讯软件会话幂等键请求参数不一致。")
            return self.communication_software_link_sessions[self.communication_software_link_session_idempotency[idempotency_key]]
        order = self.service_orders[order_id]
        if order.service_type != COMMUNICATION_SOFTWARE_LINK_SERVICE_TYPE:
            raise ValueError("订单不是连接通讯软件服务。")
        if order.status in {"delivered", "failed", "cancelled", "canceled", "refunded", "reversed", "revoked"}:
            raise ValueError("连接通讯软件订单状态不可创建会话。")
        if order.charge_status not in {"paid", "manual_review"}:
            raise ValueError("连接通讯软件订单未支付或未进入人工预售审核，不能创建配置会话。")
        if order.buyer_user_id != buyer_user_id or order.agent_id != agent_id or order.channel != channel:
            raise ValueError("连接通讯软件会话与订单不一致。")
        if order.agent_source != agent_source:
            raise ValueError("连接通讯软件来源与订单不一致。")
        session_id = f"csl-{len(self.communication_software_link_sessions) + 1}"
        session = ContractCommunicationSoftwareLinkSession(
            session_id=session_id,
            order_id=order_id,
            buyer_user_id=buyer_user_id,
            agent_id=agent_id,
            channel=channel,
            platform_account_id=platform_account_id,
            platform_chat_id=platform_chat_id,
            gateway_mode=gateway_mode,
            agent_source=agent_source,
        )
        self.communication_software_link_sessions[session_id] = session
        self.communication_software_link_session_idempotency[idempotency_key] = session_id
        self.communication_software_link_session_idempotency_payloads[idempotency_key] = payload
        order.status = "in_progress"
        return session

    def mark_communication_software_link_connected(self, session_id: str) -> ContractCommunicationSoftwareLinkSession:
        session = self.communication_software_link_sessions[session_id]
        if session.status in COMMUNICATION_SOFTWARE_LINK_SESSION_TERMINAL_STATUSES:
            raise ValueError("连接通讯软件会话状态不可连接。")
        session.status = "connected"
        session.last_probe_at = "day-0"
        self.service_orders[session.order_id].status = "acceptance_pending"
        return session

    def evaluate_communication_software_link_callback(
        self,
        session_id: str,
        channel: str,
        platform_message_id: str,
        sender_id: str,
        text: str,
        mentioned_bot: bool = False,
        wake_word_matched: bool = False,
        authorized_sender_ids: set[str] | list[str] | tuple[str, ...] | None = None,
        require_wake_signal: bool = True,
        source_event_id: str = "",
    ) -> ContractCommunicationSoftwareLinkCallbackDecision:
        session = self.communication_software_link_sessions[session_id]
        order = self.service_orders[session.order_id]
        source_event_id = str(source_event_id or platform_message_id or "").strip()
        if session.channel != channel:
            return ContractCommunicationSoftwareLinkCallbackDecision(False, "rejected", "平台通道与会话不一致。", source_event_id)
        if session.status == "acceptance_passed" or order.status == "delivered":
            return ContractCommunicationSoftwareLinkCallbackDecision(False, "already_delivered", "连接通讯软件已完成验收交付，新的平台回调不会再次交付。", source_event_id)
        if session.status not in {"connected", "test_pending", "acceptance_passed"}:
            return ContractCommunicationSoftwareLinkCallbackDecision(False, "ignored", "连接通讯软件会话尚未连接。", source_event_id)
        authorized = set(authorized_sender_ids or [])
        if authorized and sender_id not in authorized:
            return ContractCommunicationSoftwareLinkCallbackDecision(False, "rejected", "非授权用户不能触发 Agent。", source_event_id)
        if require_wake_signal and not mentioned_bot and not wake_word_matched:
            return ContractCommunicationSoftwareLinkCallbackDecision(False, "ignored", "未 @ 机器人或未匹配唤醒词。", source_event_id)
        if not platform_message_id.strip() or not str(text or "").strip():
            return ContractCommunicationSoftwareLinkCallbackDecision(False, "ignored", "消息为空或缺少平台消息 ID。", source_event_id)
        payload = (
            session_id,
            channel,
            platform_message_id,
            sender_id,
            str(text or ""),
            bool(mentioned_bot),
            bool(wake_word_matched),
        )
        if source_event_id in self.communication_software_link_callback_source_events:
            if self.communication_software_link_callback_source_events[source_event_id] == payload:
                return ContractCommunicationSoftwareLinkCallbackDecision(False, "replayed", "重复平台回调已忽略。", source_event_id)
            return ContractCommunicationSoftwareLinkCallbackDecision(False, "replayed", "重复 source_event_id 参数不一致，已阻断。", source_event_id)
        self.communication_software_link_callback_source_events[source_event_id] = payload
        self.communication_software_link_accepted_callback_source_events.add(source_event_id)
        session.status = "test_pending"
        session.last_probe_at = "day-0"
        return ContractCommunicationSoftwareLinkCallbackDecision(True, "accepted", "消息可进入 Agent Runtime Adapter。", source_event_id)

    def record_communication_software_link_runtime_result(
        self,
        session_id: str,
        source_event_id: str,
        inbound_platform_message_id: str,
        outbound_platform_message_id: str,
        agent_response_digest: str,
        status: str,
        error_message: str = "",
    ) -> ContractCommunicationSoftwareLinkRuntimeResult:
        session = self.communication_software_link_sessions[session_id]
        normalized_status = str(status or "").strip().lower()
        if normalized_status not in {"success", "failed"}:
            raise ValueError("未知 Agent Runtime Adapter 结果状态。")
        required = [source_event_id, inbound_platform_message_id]
        if normalized_status == "success":
            required.extend([outbound_platform_message_id, agent_response_digest])
        if any(not str(item or "").strip() for item in required):
            raise ValueError("Agent Runtime Adapter 结果缺少必要字段。")
        if session.status not in {"test_pending", "connected"}:
            raise ValueError("连接通讯软件会话未进入测试状态，不能记录 Runtime Adapter 结果。")
        result = ContractCommunicationSoftwareLinkRuntimeResult(
            source_event_id=str(source_event_id).strip(),
            session_id=session_id,
            inbound_platform_message_id=str(inbound_platform_message_id).strip(),
            outbound_platform_message_id=str(outbound_platform_message_id or "").strip(),
            agent_response_digest=str(agent_response_digest or "").strip(),
            status=normalized_status,
            error_message=str(error_message or "").strip(),
        )
        self.communication_software_link_runtime_results[result.source_event_id] = result
        if normalized_status == "failed":
            session.status = "manual_review"
            self.service_orders[session.order_id].status = "acceptance_pending"
        return result

    def record_communication_software_link_acceptance(
        self,
        session_id: str,
        source_event_id: str,
        inbound_platform_message_id: str,
        outbound_platform_message_id: str,
        test_prompt: str,
        agent_response_digest: str,
        evidence_url: str,
        accepted_by: str,
    ) -> ContractCommunicationSoftwareLinkAcceptanceRecord:
        session = self.communication_software_link_sessions[session_id]
        order = self.service_orders[session.order_id]
        payload = (
            session_id,
            order.order_id,
            inbound_platform_message_id,
            outbound_platform_message_id,
            test_prompt,
            agent_response_digest,
            evidence_url,
            accepted_by,
        )
        if source_event_id in self.communication_software_link_acceptance_by_source_event:
            acceptance_id = self.communication_software_link_acceptance_by_source_event[source_event_id]
            if self.communication_software_link_acceptance_payloads[source_event_id] != payload:
                raise ValueError("连接通讯软件验收 source_event_id 请求参数不一致。")
            return self.communication_software_link_acceptance_records[acceptance_id]
        if session.status not in {"connected", "test_pending"}:
            raise ValueError("连接通讯软件未完成平台连接和测试，不能验收。")
        required_evidence = [
            source_event_id,
            inbound_platform_message_id,
            outbound_platform_message_id,
            test_prompt,
            agent_response_digest,
            evidence_url,
            accepted_by,
        ]
        if any(not str(item or "").strip() for item in required_evidence):
            raise ValueError("连接通讯软件缺少闭环验收证据。")
        if source_event_id not in self.communication_software_link_accepted_callback_source_events:
            raise ValueError("连接通讯软件验收缺少已 accepted 的平台回调记录。")
        callback_payload = self.communication_software_link_callback_source_events.get(source_event_id)
        if callback_payload is None:
            raise ValueError("连接通讯软件验收缺少平台回调记录。")
        callback_session_id, _, callback_inbound_platform_message_id, *_ = callback_payload
        if callback_session_id != session_id or callback_inbound_platform_message_id != inbound_platform_message_id:
            raise ValueError("连接通讯软件验收平台回调与当前会话不匹配。")
        runtime_result = self.communication_software_link_runtime_results.get(source_event_id)
        if runtime_result is None or runtime_result.status != "success":
            raise ValueError("连接通讯软件缺少 Agent Runtime Adapter 成功结果，不能验收。")
        if (
            runtime_result.session_id != session_id
            or runtime_result.inbound_platform_message_id != inbound_platform_message_id
            or runtime_result.outbound_platform_message_id != outbound_platform_message_id
            or runtime_result.agent_response_digest != agent_response_digest
        ):
            raise ValueError("连接通讯软件验收证据与 Runtime Adapter 结果不一致。")
        acceptance_id = f"csl-acc-{len(self.communication_software_link_acceptance_records) + 1}"
        record = ContractCommunicationSoftwareLinkAcceptanceRecord(
            acceptance_id=acceptance_id,
            order_id=order.order_id,
            session_id=session_id,
            source_event_id=source_event_id,
            inbound_platform_message_id=inbound_platform_message_id,
            outbound_platform_message_id=outbound_platform_message_id,
            test_prompt=test_prompt,
            agent_response_digest=agent_response_digest,
            evidence_url=evidence_url,
            accepted_by=accepted_by,
        )
        self.communication_software_link_acceptance_records[acceptance_id] = record
        self.communication_software_link_acceptance_by_source_event[source_event_id] = acceptance_id
        self.communication_software_link_acceptance_payloads[source_event_id] = payload
        session.status = "acceptance_passed"
        session.accepted_at = record.accepted_at
        order.status = "delivered"
        order.charge_status = "chargeable" if order.charge_status != "paid" else "paid"
        order.delivered_at = record.accepted_at
        product = self.service_products[order.service_product_id]
        self.record_service_ledger_event(
            source_event_id=source_event_id,
            service_type=COMMUNICATION_SOFTWARE_LINK_SERVICE_TYPE,
            event_type=COMMUNICATION_SOFTWARE_LINK_DELIVERED_EVENT,
            order_id=order.order_id,
            buyer_user_id=order.buyer_user_id,
            amount_cents=product.price_cents,
        )
        if product.price_cents > 0:
            self.record_commission_event(
                source_event_id=source_event_id,
                event_type=COMMUNICATION_SOFTWARE_LINK_DELIVERED_EVENT,
                buyer_user_id=order.buyer_user_id,
                amount_cents=product.price_cents,
            )
        return record

    def process_communication_software_link_callback_delivery(
        self,
        session_id: str,
        channel: str,
        platform_message_id: str,
        sender_id: str,
        text: str,
        outbound_platform_message_id: str,
        agent_response_digest: str,
        evidence_url: str,
        accepted_by: str,
        mentioned_bot: bool = False,
        wake_word_matched: bool = False,
        authorized_sender_ids: set[str] | list[str] | tuple[str, ...] | None = None,
        require_wake_signal: bool = True,
        source_event_id: str = "",
    ) -> ContractCommunicationSoftwareLinkDeliveryResult:
        normalized_source_event_id = str(source_event_id or platform_message_id or "").strip()
        existing_acceptance = self.communication_software_link_acceptance_by_source_event.get(normalized_source_event_id)
        existing_result = self.communication_software_link_runtime_results.get(normalized_source_event_id)
        if existing_acceptance:
            decision = ContractCommunicationSoftwareLinkCallbackDecision(
                should_invoke_agent=False,
                status="replayed",
                reason="重复平台回调已返回已有验收记录。",
                source_event_id=normalized_source_event_id,
            )
            return ContractCommunicationSoftwareLinkDeliveryResult(
                status="replayed",
                decision=decision,
                runtime_result=existing_result,
                acceptance_record=self.communication_software_link_acceptance_records[existing_acceptance],
                reason=decision.reason,
            )

        decision = self.evaluate_communication_software_link_callback(
            session_id=session_id,
            channel=channel,
            platform_message_id=platform_message_id,
            sender_id=sender_id,
            text=text,
            mentioned_bot=mentioned_bot,
            wake_word_matched=wake_word_matched,
            authorized_sender_ids=authorized_sender_ids,
            require_wake_signal=require_wake_signal,
            source_event_id=normalized_source_event_id,
        )
        if not decision.should_invoke_agent:
            return ContractCommunicationSoftwareLinkDeliveryResult(status=decision.status, decision=decision, reason=decision.reason)

        runtime_result = self.record_communication_software_link_runtime_result(
            session_id=session_id,
            source_event_id=decision.source_event_id,
            inbound_platform_message_id=platform_message_id,
            outbound_platform_message_id=outbound_platform_message_id,
            agent_response_digest=agent_response_digest,
            status="success",
        )
        acceptance_record = self.record_communication_software_link_acceptance(
            session_id=session_id,
            source_event_id=decision.source_event_id,
            inbound_platform_message_id=platform_message_id,
            outbound_platform_message_id=outbound_platform_message_id,
            test_prompt=text,
            agent_response_digest=agent_response_digest,
            evidence_url=evidence_url,
            accepted_by=accepted_by,
        )
        return ContractCommunicationSoftwareLinkDeliveryResult(
            status="delivered",
            decision=decision,
            runtime_result=runtime_result,
            acceptance_record=acceptance_record,
        )

    def record_service_ledger_event(
        self,
        source_event_id: str,
        service_type: str,
        event_type: str,
        order_id: str,
        buyer_user_id: str,
        amount_cents: int,
    ) -> ContractServiceLedgerEvent:
        payload = (service_type, event_type, order_id, buyer_user_id, amount_cents)
        if source_event_id in self.service_ledger_events_by_source_event:
            if self.service_ledger_event_payloads[source_event_id] != payload:
                raise ValueError("服务账本 source_event_id 请求参数不一致。")
            return self.service_ledger_events[self.service_ledger_events_by_source_event[source_event_id]]
        if event_type == AGENT_INSTALL_DELIVERED_EVENT and service_type != AGENT_INSTALL_SERVICE_TYPE:
            raise ValueError("基础 Agent 交付事件不能用于其他服务类型。")
        if event_type == COMMUNICATION_SOFTWARE_LINK_DELIVERED_EVENT and service_type != COMMUNICATION_SOFTWARE_LINK_SERVICE_TYPE:
            raise ValueError("连接通讯软件交付事件不能用于其他服务类型。")
        if amount_cents < 0:
            raise ValueError("服务账本金额不能为负数。")
        ledger_event = ContractServiceLedgerEvent(
            ledger_event_id=f"svc-ledger-{len(self.service_ledger_events) + 1}",
            source_event_id=source_event_id,
            service_type=service_type,
            event_type=event_type,
            order_id=order_id,
            buyer_user_id=buyer_user_id,
            amount_cents=amount_cents,
        )
        self.service_ledger_events[ledger_event.ledger_event_id] = ledger_event
        self.service_ledger_events_by_source_event[source_event_id] = ledger_event.ledger_event_id
        self.service_ledger_event_payloads[source_event_id] = payload
        return ledger_event

    def fail_communication_software_link_session(self, session_id: str, reason: str) -> None:
        session = self.communication_software_link_sessions[session_id]
        if session.status == "disabled":
            raise ValueError("连接通讯软件会话已禁用，不能自动标记失败。")
        if session.status == "acceptance_passed":
            raise ValueError("连接通讯软件已形成验收证据，不能自动标记失败或免单。")
        session.status = "failed"
        order = self.service_orders[session.order_id]
        order.status = "failed"
        if order.charge_status == "chargeable":
            order.charge_status = "manual_review"

    def pause_communication_software_link_session_for_external_dependency(
        self,
        session_id: str,
        reason: str,
    ) -> ContractCommunicationSoftwareLinkSession:
        session = self.communication_software_link_sessions[session_id]
        if session.status == "disabled":
            raise ValueError("连接通讯软件会话已禁用，不能自动暂停。")
        session.status = "paused_external_dependency"
        order = self.service_orders[session.order_id]
        if order.status == "delivered":
            order.charge_status = "chargeable" if order.charge_status != "paid" else "paid"
        else:
            order.status = "acceptance_pending"
            order.charge_status = "manual_review"
        return session

    def disable_communication_software_link_session(self, session_id: str) -> ContractCommunicationSoftwareLinkSession:
        session = self.communication_software_link_sessions[session_id]
        session.status = "disabled"
        order = self.service_orders[session.order_id]
        if order.status != "delivered":
            order.status = "cancelled"
            order.cancelled_at = "day-0"
        return session

    def _validate_communication_software_link_product(
        self,
        product: ContractServiceProduct,
        agent_id: str,
        channel: str,
        agent_source: str,
    ) -> None:
        if product.service_type != COMMUNICATION_SOFTWARE_LINK_SERVICE_TYPE:
            raise ValueError("服务商品不是连接通讯软件。")
        if agent_id not in product.supported_agent_ids:
            raise ValueError("服务端未开放该 Agent 的连接通讯软件。")
        if channel not in product.supported_channels or channel not in COMMUNICATION_SOFTWARE_LINK_CHANNELS:
            raise ValueError("服务端未开放该连接通讯软件平台通道。")
        if agent_source not in product.allowed_agent_sources or agent_source not in COMMUNICATION_SOFTWARE_LINK_AGENT_SOURCES:
            raise ValueError("连接通讯软件来源未被服务端允许。")

    def _has_completed_base_agent_delivery(self, buyer_user_id: str, agent_id: str) -> bool:
        for session in self.config_sessions.values():
            if session.buyer_user_id == buyer_user_id and session.agent_id == agent_id and session.status == "completed":
                return True
        for event in self.service_ledger_events.values():
            if (
                event.service_type == AGENT_INSTALL_SERVICE_TYPE
                and event.event_type == AGENT_INSTALL_DELIVERED_EVENT
                and event.buyer_user_id == buyer_user_id
            ):
                return True
        return False

    def _commission_rule_for(
        self,
        event_type: str,
        receiver_level: str,
        depth: int,
    ) -> ContractCommissionPolicyRule | None:
        for rule in reversed(self.commission_policy_rules):
            if rule.event_type == event_type and rule.receiver_level == receiver_level and rule.depth == depth:
                return rule
        return None

    def _level_number(self, level: str) -> int:
        if level.startswith("L") and level[1:].isdigit():
            return int(level[1:])
        return 0

    def create_order(
        self,
        idempotency_key: str,
        product_id: str,
        buyer_user_id: str,
        operator_user_id: str,
        agent_chain: list[str],
        diagnostic_code: str,
        delivery_scope: str = "codex_agent_config",
    ) -> ContractOrder:
        _require_current_buyer_operator(buyer_user_id, operator_user_id)
        payload = (
            product_id,
            buyer_user_id,
            operator_user_id,
            tuple(agent_chain),
            diagnostic_code,
            delivery_scope,
        )
        if idempotency_key in self.order_idempotency:
            if self.order_idempotency_payloads[idempotency_key] != payload:
                raise ValueError("订单幂等键请求参数不一致。")
            return self.orders[self.order_idempotency[idempotency_key]]
        order_id = f"ord-{len(self.orders) + 1}"
        order = ContractOrder(
            order_id=order_id,
            idempotency_key=idempotency_key,
            product_id=product_id,
            buyer_user_id=buyer_user_id,
            operator_user_id=operator_user_id,
            agent_chain=list(agent_chain),
            diagnostic_code=diagnostic_code,
            delivery_scope=delivery_scope,
        )
        self.orders[order_id] = order
        self.order_idempotency[idempotency_key] = order_id
        self.order_idempotency_payloads[idempotency_key] = payload
        return order

    def mark_paid_and_create_entitlement(
        self,
        order_id: str,
        payment_id: str,
        payment_amount_cents: int | None = None,
        is_unlimited: bool = False,
    ) -> ContractEntitlement:
        payload = (order_id, payment_amount_cents, bool(is_unlimited))
        if payment_id in self.payment_idempotency:
            if self.payment_idempotency_payloads[payment_id] != payload:
                raise ValueError("支付幂等键请求参数不一致。")
            return self.entitlements[self.payment_idempotency[payment_id]]
        order = self.orders[order_id]
        entitlement_id = f"ent-{len(self.entitlements) + 1}"
        entitlement = ContractEntitlement(
            entitlement_id=entitlement_id,
            order_id=order_id,
            buyer_user_id=order.buyer_user_id,
            remaining_uses=0 if is_unlimited else 1,
            delivery_scope=order.delivery_scope,
            is_unlimited=bool(is_unlimited),
        )
        order.status = "paid"
        order.entitlement_id = entitlement_id
        self.entitlements[entitlement_id] = entitlement
        self.payment_idempotency[payment_id] = entitlement_id
        self.payment_idempotency_payloads[payment_id] = payload
        amount_cents = int(payment_amount_cents or 0)
        for depth, agent_user_id in enumerate(order.agent_chain[:5], start=1):
            profile = self.agent_profiles.get(agent_user_id)
            rule = self._commission_rule_for(TOOL_ORDER_PAID_EVENT, profile.level, depth) if profile else None
            commission_cents = (
                amount_cents * rule.rate_bps // 10000
                if rule is not None and rule.status == "active" and rule.rate_bps > 0
                else 0
            )
            self.commission_entries.append(
                ContractCommissionEntry(
                    commission_id=f"com-{len(self.commission_entries) + 1}",
                    order_id=order_id,
                    agent_user_id=agent_user_id,
                    source_event_id=payment_id,
                    event_type=TOOL_ORDER_PAID_EVENT if commission_cents else "",
                    depth=depth,
                    rate_bps=rule.rate_bps if rule is not None and commission_cents else 0,
                    commission_cents=commission_cents,
                )
            )
        return entitlement

    def grant_trial_entitlement(
        self,
        idempotency_key: str,
        buyer_user_id: str,
        agent_id: str,
        mode_key: str,
        remaining_uses: int,
    ) -> ContractEntitlement:
        payload = (buyer_user_id, agent_id, mode_key, remaining_uses)
        if idempotency_key in self.trial_idempotency:
            if self.trial_idempotency_payloads[idempotency_key] != payload:
                raise ValueError("试用权益幂等键请求参数不一致。")
            return self.entitlements[self.trial_idempotency[idempotency_key]]
        if not buyer_user_id.strip():
            raise ValueError("试用权益买家为空。")
        if remaining_uses <= 0:
            raise ValueError("试用权益次数必须大于 0。")
        if mode_key == "dual_state":
            raise ValueError("免费试用权益不包含双态模式。")
        claim_key = buyer_user_id
        if claim_key in self.trial_claims:
            raise ValueError("该买家已领取过免费试用权益。")
        entitlement_id = f"ent-{len(self.entitlements) + 1}"
        entitlement = ContractEntitlement(
            entitlement_id=entitlement_id,
            order_id="",
            buyer_user_id=buyer_user_id,
            agent_id=agent_id,
            mode_key=mode_key,
            remaining_uses=remaining_uses,
            source="trial",
            delivery_scope="trial",
        )
        self.entitlements[entitlement_id] = entitlement
        self.trial_idempotency[idempotency_key] = entitlement_id
        self.trial_idempotency_payloads[idempotency_key] = payload
        self.trial_claims[claim_key] = entitlement_id
        return entitlement

    def reserve_config_session(
        self,
        idempotency_key: str,
        entitlement_id: str,
        operator_user_id: str,
        agent_id: str,
        mode_key: str,
        device_id: str,
        diagnostic_code: str,
        delivery_scope: str = "",
    ) -> ContractConfigSession:
        entitlement = self.entitlements[entitlement_id]
        effective_delivery_scope = str(delivery_scope or entitlement.delivery_scope or "codex_agent_config")
        _require_current_buyer_operator(entitlement.buyer_user_id, operator_user_id)
        payload = (
            entitlement_id,
            operator_user_id,
            agent_id,
            mode_key,
            device_id,
            diagnostic_code,
            effective_delivery_scope,
        )
        if idempotency_key in self.session_idempotency:
            if self.session_idempotency_payloads[idempotency_key] != payload:
                raise ValueError("配置会话幂等键请求参数不一致。")
            return self.config_sessions[self.session_idempotency[idempotency_key]]
        if entitlement.status != "active" or (entitlement.remaining_uses <= 0 and not entitlement.is_unlimited):
            raise ValueError("权益不可用。")
        bound_device_ids = entitlement.bound_device_ids
        if bound_device_ids is None:
            bound_device_ids = set()
            entitlement.bound_device_ids = bound_device_ids
        if device_id not in bound_device_ids and len(bound_device_ids) >= entitlement.device_limit:
            raise ValueError("设备数量已超过该权益限制。")
        active = [
            session for session in self.config_sessions.values()
            if session.entitlement_id == entitlement_id and session.status in {"reserved", "manual_review"}
        ]
        if active:
            if active[0].status == "manual_review":
                raise ValueError("同一权益已有人工复核中的配置会话。")
            raise ValueError("同一权益已有活跃配置会话。")
        bound_device_ids.add(device_id)
        session_id = f"cfg-{len(self.config_sessions) + 1}"
        session = ContractConfigSession(
            config_session_id=session_id,
            entitlement_id=entitlement_id,
            buyer_user_id=entitlement.buyer_user_id,
            operator_user_id=operator_user_id,
            agent_id=agent_id,
            mode_key=mode_key,
            device_id=device_id,
            diagnostic_code=diagnostic_code,
            delivery_scope=effective_delivery_scope,
        )
        self.config_sessions[session_id] = session
        self.session_idempotency[idempotency_key] = session_id
        self.session_idempotency_payloads[idempotency_key] = payload
        return session

    def complete_config_session(self, config_session_id: str, real_task_verified: bool) -> bool:
        session = self.config_sessions[config_session_id]
        if session.status == "completed":
            return session.deducted
        if session.status == "manual_review":
            raise ValueError("配置会话已进入人工复核，不能自动完成。")
        if session.status == "failed":
            raise ValueError("配置会话已失败，不能自动完成。")
        if session.status == "cancelled":
            raise ValueError("配置会话已取消，不能自动完成。")
        if session.status != "reserved":
            raise ValueError("配置会话状态不可完成。")
        if not real_task_verified:
            raise ValueError("真实任务未验证，不能扣次。")
        entitlement = self.entitlements[session.entitlement_id]
        if entitlement.remaining_uses <= 0 and not entitlement.is_unlimited:
            raise ValueError("权益次数不足。")
        if not entitlement.is_unlimited:
            entitlement.remaining_uses -= 1
        session.status = "completed"
        session.deducted = True
        return True

    def fail_config_session(self, config_session_id: str, reason: str) -> None:
        session = self.config_sessions[config_session_id]
        if session.status == "completed":
            raise ValueError("已完成会话不能标记失败。")
        if session.status == "manual_review":
            raise ValueError("配置会话已进入人工复核，不能自动失败。")
        session.status = "failed"
        session.deducted = False

    def mark_config_session_manual_review(self, config_session_id: str, reason: str) -> None:
        session = self.config_sessions[config_session_id]
        if session.status == "completed":
            raise ValueError("已完成会话不能进入人工复核。")
        if session.status == "manual_review":
            return
        session.status = "manual_review"
        session.deducted = False

    def reverse_order(self, order_id: str, reason: str) -> None:
        order = self.orders[order_id]
        if order.status == "reversed":
            return
        order.status = "reversed"
        if order.entitlement_id:
            self.entitlements[order.entitlement_id].status = "revoked"
            for session in self.config_sessions.values():
                if session.entitlement_id == order.entitlement_id and session.status == "reserved":
                    session.status = "cancelled"
        for entry in self.commission_entries:
            if entry.order_id == order_id:
                if entry.status == "withdrawn":
                    entry.status = "manual_review"
                elif entry.status != "manual_review":
                    entry.status = "reversed"
        self.commission_reversals.append(
            ContractCommissionReversal(
                reversal_id=f"rev-{len(self.commission_reversals) + 1}",
                order_id=order_id,
                reason=reason,
            )
        )

    def order_entitlement_status_report(self, order_id: str) -> dict[str, object]:
        order = self.orders[order_id]
        entitlement = self.entitlements.get(order.entitlement_id) if order.entitlement_id else None
        sessions = {
            session.config_session_id: session
            for session in self.config_sessions.values()
            if entitlement is not None and session.entitlement_id == entitlement.entitlement_id
        }
        blocking_gaps: list[str] = []

        if order.status == "reversed":
            order_status_report = "local_reversed"
            blocking_gaps.append("订单已撤销或反转，不能视为客户可交付完成。")
        elif order.status in {"created", "pending", ""}:
            order_status_report = "payment_pending"
            blocking_gaps.append("支付未确认，不能进入客户交付完成。")
        elif order.status == "paid" and entitlement is None:
            order_status_report = "entitlement_pending"
            blocking_gaps.append("服务端权益未确认，不能进入客户交付完成。")
        elif order.status == "paid":
            if any(session.status == "completed" for session in sessions.values()):
                order_status_report = "local_session_completed_pending_real_delivery"
                blocking_gaps.append("本地配置会话完成不代表客户真实交付完成。")
            else:
                order_status_report = "paid_unconfirmed"
                blocking_gaps.append("已支付但配置会话未完成真实任务验收。")
        else:
            order_status_report = "blocked"
            blocking_gaps.append("订单状态未进入可交付状态。")

        if entitlement is None:
            entitlement_status_report = "unpaid" if order_status_report == "payment_pending" else "paid_unconfirmed"
        elif entitlement.status == "revoked":
            entitlement_status_report = "revoked"
        elif entitlement.status == "active":
            entitlement_status_report = "authorized"
        else:
            entitlement_status_report = "server_confirmation_missing"
            blocking_gaps.append("权益缺少服务端可用确认。")

        return {
            "order_id": order.order_id,
            "order_status": order.status,
            "order_status_report": order_status_report,
            "delivery_scope": order.delivery_scope,
            "entitlement_id": order.entitlement_id,
            "entitlement_status_report": entitlement_status_report,
            "config_session_statuses": {
                session_id: session.status
                for session_id, session in sorted(sessions.items())
            },
            "blocking_gaps": blocking_gaps,
        }
