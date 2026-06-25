from __future__ import annotations

from dataclasses import dataclass
import hashlib


@dataclass
class ContractOrder:
    # Service-side commercial model. The current desktop client should not
    # interpret agent_chain as a local proxy/agent-assist workflow contract.
    order_id: str
    idempotency_key: str
    product_id: str
    buyer_user_id: str
    operator_user_id: str
    agent_chain: list[str]
    diagnostic_code: str
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
    status: str = "reserved"
    deducted: bool = False


@dataclass
class ContractCommissionEntry:
    # Service-side commission bookkeeping, not a desktop-side product flow.
    commission_id: str
    order_id: str
    agent_user_id: str
    status: str = "pending"


@dataclass
class ContractCommissionReversal:
    # Service-side commission reversal bookkeeping.
    reversal_id: str
    order_id: str
    reason: str


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
        self.commission_entries: list[ContractCommissionEntry] = []
        self.commission_reversals: list[ContractCommissionReversal] = []

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
        benefits: list[str] | None = None,
        boundaries: list[str] | None = None,
        commission_ratio: str = "",
    ) -> None:
        self.agent_center = {
            "enabled": bool(enabled),
            "current_level": current_level,
            "upgrade_label": upgrade_label,
            "invite_url": invite_url,
            "benefits": list(benefits or []),
            "boundaries": list(boundaries or []),
            "commission_ratio": commission_ratio,
        }

    def agent_center_snapshot(self) -> dict[str, object]:
        return {
            "enabled": bool(self.agent_center.get("enabled")),
            "current_level": str(self.agent_center.get("current_level") or ""),
            "upgrade_label": str(self.agent_center.get("upgrade_label") or ""),
            "invite_url": str(self.agent_center.get("invite_url") or ""),
            "benefits": list(self.agent_center.get("benefits") or []),
            "boundaries": list(self.agent_center.get("boundaries") or []),
        }

    def create_order(
        self,
        idempotency_key: str,
        product_id: str,
        buyer_user_id: str,
        operator_user_id: str,
        agent_chain: list[str],
        diagnostic_code: str,
    ) -> ContractOrder:
        payload = (
            product_id,
            buyer_user_id,
            operator_user_id,
            tuple(agent_chain),
            diagnostic_code,
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
            is_unlimited=bool(is_unlimited),
        )
        order.status = "paid"
        order.entitlement_id = entitlement_id
        self.entitlements[entitlement_id] = entitlement
        self.payment_idempotency[payment_id] = entitlement_id
        self.payment_idempotency_payloads[payment_id] = payload
        for agent_user_id in order.agent_chain[:5]:
            self.commission_entries.append(
                ContractCommissionEntry(
                    commission_id=f"com-{len(self.commission_entries) + 1}",
                    order_id=order_id,
                    agent_user_id=agent_user_id,
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
    ) -> ContractConfigSession:
        payload = (
            entitlement_id,
            operator_user_id,
            agent_id,
            mode_key,
            device_id,
            diagnostic_code,
        )
        if idempotency_key in self.session_idempotency:
            if self.session_idempotency_payloads[idempotency_key] != payload:
                raise ValueError("配置会话幂等键请求参数不一致。")
            return self.config_sessions[self.session_idempotency[idempotency_key]]
        entitlement = self.entitlements[entitlement_id]
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
