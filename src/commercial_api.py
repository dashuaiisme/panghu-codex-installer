from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import re
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request


SENSITIVE_FIELDS = {
    "password",
    "verification_code",
    "invite_code",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "Authorization",
    "authorization",
    "entitlement_id",
    "buyer_user_id",
    "operator_user_id",
    "target_buyer_user_id",
    "order_id",
    "service_order_id",
    "config_session_id",
    "session_id",
    "source_event_id",
    "platform_account_id",
    "platform_chat_id",
    "platform_message_id",
    "inbound_platform_message_id",
    "outbound_platform_message_id",
    "evidence_url",
    "sender_id",
}

SENSITIVE_TEXT_PATTERNS = (
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b1[3-9]\d{9}\b"),
    re.compile(r"\bsk-[A-Za-z0-9._-]+\b"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+\b"),
    re.compile(r"(?i)\b(token|access_token|refresh_token|api_key|invite_code|order_id|entitlement_id|config_session_id)\s*[:=]\s*[A-Za-z0-9._~:/+-]+\b"),
    re.compile(r"(?i)\b(token|access_token|refresh_token|api_key|invite_code|order_id|entitlement_id|config_session_id)\s+[A-Za-z0-9._~:/+-]+\b"),
    re.compile(r"\b(?:ord|order|ent|cfg|assist|invite|mca|svc|evt)-[A-Za-z0-9._-]+\b", re.IGNORECASE),
)


@dataclass(frozen=True)
class CommercialApiContract:
    base_url: str

    def _url(self, path: str) -> str:
        return self.base_url.rstrip("/") + path

    @property
    def api_key_owner_verify_url(self) -> str:
        return self._url("/api/deployer/api-keys/verify-owner")

    @property
    def entitlements_url(self) -> str:
        return self._url("/api/deployer/entitlements")

    @property
    def order_create_url(self) -> str:
        return self._url("/api/deployer/orders")

    @property
    def payment_status_url(self) -> str:
        return self._url("/api/deployer/orders/payment-status")

    @property
    def config_session_reserve_url(self) -> str:
        return self._url("/api/deployer/config-sessions/reserve")

    @property
    def config_session_complete_url(self) -> str:
        return self._url("/api/deployer/config-sessions/complete")

    @property
    def config_session_fail_url(self) -> str:
        return self._url("/api/deployer/config-sessions/fail")

    @property
    def agent_public_offering_url(self) -> str:
        return self._url("/api/agent/public/offering")

    @property
    def agent_apply_url(self) -> str:
        return self._url("/api/agent/apply")

    @property
    def agent_center_url(self) -> str:
        return self._url("/api/agent/center")

    @property
    def agent_downstreams_url(self) -> str:
        return self._url("/api/agent/downstreams")

    @property
    def agent_commissions_url(self) -> str:
        return self._url("/api/agent/commissions")

    @property
    def agent_settlements_url(self) -> str:
        return self._url("/api/agent/settlements")

    @property
    def referral_bind_url(self) -> str:
        return self._url("/api/referrals/bind")

    @property
    def admin_agent_products_url(self) -> str:
        return self._url("/api/admin/agent/products")

    @property
    def admin_agent_policies_url(self) -> str:
        return self._url("/api/admin/agent/policies")

    @property
    def admin_agent_marketing_content_url(self) -> str:
        return self._url("/api/admin/agent/marketing-content")

    @property
    def admin_agent_applications_url(self) -> str:
        return self._url("/api/admin/agent/applications")

    @property
    def admin_agent_settlements_url(self) -> str:
        return self._url("/api/admin/agent/settlements")

    def admin_agent_ledger_action_url(self, ledger_id: str, action: str) -> str:
        if action not in {"freeze", "release", "reverse"}:
            raise ValueError("未知代理账本动作。")
        safe_ledger_id = str(ledger_id or "").strip().strip("/")
        if not safe_ledger_id:
            raise ValueError("代理账本 ID 为空。")
        return self._url(f"/api/admin/agent/ledger/{safe_ledger_id}/{action}")

    @property
    def mobile_control_offering_url(self) -> str:
        return self._url("/api/mobile-control/offering")

    @property
    def mobile_control_orders_url(self) -> str:
        return self._url("/api/mobile-control/orders")

    def mobile_control_order_url(self, order_id: str) -> str:
        safe_order_id = str(order_id or "").strip().strip("/")
        if not safe_order_id:
            raise ValueError("手机控制Agent订单 ID 为空。")
        return self._url(f"/api/mobile-control/orders/{safe_order_id}")

    @property
    def mobile_control_sessions_url(self) -> str:
        return self._url("/api/mobile-control/sessions")

    def mobile_control_session_url(self, session_id: str) -> str:
        safe_session_id = str(session_id or "").strip().strip("/")
        if not safe_session_id:
            raise ValueError("手机控制Agent会话 ID 为空。")
        return self._url(f"/api/mobile-control/sessions/{safe_session_id}")

    def mobile_control_session_test_url(self, session_id: str) -> str:
        return self.mobile_control_session_url(session_id) + "/test"

    def mobile_control_session_acceptance_url(self, session_id: str) -> str:
        return self.mobile_control_session_url(session_id) + "/acceptance"

    def mobile_control_session_disable_url(self, session_id: str) -> str:
        return self.mobile_control_session_url(session_id) + "/disable"

    def mobile_control_callback_url(self, channel: str) -> str:
        normalized = str(channel or "").strip().replace("_", "-")
        if normalized not in {"qq-bot", "weixin", "feishu", "dingtalk", "wecom"}:
            raise ValueError("未知手机控制Agent平台通道。")
        return self._url(f"/api/mobile-control/callbacks/{normalized}")

    @property
    def admin_mobile_control_products_url(self) -> str:
        return self._url("/api/admin/mobile-control/products")

    @property
    def admin_mobile_control_channel_policies_url(self) -> str:
        return self._url("/api/admin/mobile-control/channel-policies")

    @property
    def admin_mobile_control_sessions_url(self) -> str:
        return self._url("/api/admin/mobile-control/sessions")

    def admin_mobile_control_session_action_url(self, session_id: str, action: str) -> str:
        if action not in {"freeze", "release"}:
            raise ValueError("未知手机控制Agent会话后台动作。")
        safe_session_id = str(session_id or "").strip().strip("/")
        if not safe_session_id:
            raise ValueError("手机控制Agent会话 ID 为空。")
        return self._url(f"/api/admin/mobile-control/sessions/{safe_session_id}/{action}")

    def admin_mobile_control_order_action_url(self, order_id: str, action: str) -> str:
        if action not in {"refund", "manual-review"}:
            raise ValueError("未知手机控制Agent订单后台动作。")
        safe_order_id = str(order_id or "").strip().strip("/")
        if not safe_order_id:
            raise ValueError("手机控制Agent订单 ID 为空。")
        return self._url(f"/api/admin/mobile-control/orders/{safe_order_id}/{action}")


@dataclass(frozen=True)
class CommercialApiRequest:
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    body: dict[str, Any] = field(default_factory=dict)
    query: dict[str, str] = field(default_factory=dict)


def sanitize_commercial_api_payload(payload: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in payload.items():
        if key in SENSITIVE_FIELDS:
            safe[key] = "***" if value else ""
        elif isinstance(value, dict):
            safe[key] = sanitize_commercial_api_payload(value)
        else:
            safe[key] = value
    return safe


def sanitize_commercial_text(text: str) -> str:
    safe = str(text or "")
    for pattern in SENSITIVE_TEXT_PATTERNS:
        safe = pattern.sub("***", safe)
    return safe


def mask_business_identifier(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    prefix = text.split("-", 1)[0]
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
    return f"{prefix}-***{digest}"


def stable_config_session_idempotency_key(action: str, config_session_id: str, diagnostic_code: str) -> str:
    if action not in {"reserve", "complete", "fail"}:
        raise ValueError("未知配置会话动作。")
    seed = f"{action}:{config_session_id}:{diagnostic_code}".encode("utf-8")
    digest = hashlib.sha256(seed).hexdigest()[:24]
    return f"cfg-{action}-{digest}"


def stable_config_reserve_idempotency_key(
    entitlement_id: str,
    buyer_user_id: str,
    operator_user_id: str,
    agent_id: str,
    mode_key: str,
    device_id: str,
    diagnostic_code: str,
) -> str:
    seed = (
        f"reserve:{entitlement_id}:{buyer_user_id}:{operator_user_id}:"
        f"{agent_id}:{mode_key}:{device_id}:{diagnostic_code}"
    ).encode("utf-8")
    digest = hashlib.sha256(seed).hexdigest()[:24]
    return f"cfg-reserve-{digest}"


def stable_order_idempotency_key(
    product_id: str,
    buyer_user_id: str,
    operator_user_id: str,
) -> str:
    seed = f"order:{product_id}:{buyer_user_id}:{operator_user_id}".encode("utf-8")
    digest = hashlib.sha256(seed).hexdigest()[:24]
    return f"order-{digest}"


def stable_mobile_control_idempotency_key(action: str, *parts: str) -> str:
    if action not in {"order", "session", "test", "acceptance", "disable", "callback"}:
        raise ValueError("未知手机控制Agent幂等动作。")
    seed = (action + ":" + ":".join(str(part or "") for part in parts)).encode("utf-8")
    digest = hashlib.sha256(seed).hexdigest()[:24]
    return f"mca-{action}-{digest}"


def build_urllib_request_parts(request: CommercialApiRequest) -> tuple[str, dict[str, str], bytes | None]:
    url = request.url
    if request.query:
        separator = "&" if "?" in url else "?"
        url = url + separator + urlencode(request.query)
    headers = dict(request.headers)
    body: bytes | None = None
    if request.body:
        headers.setdefault("Content-Type", "application/json")
        body = json.dumps(request.body, ensure_ascii=False).encode("utf-8")
    return url, headers, body


def with_operator_auth(request: CommercialApiRequest, token: str) -> CommercialApiRequest:
    if not token.strip():
        raise ValueError("商业接口缺少操作者授权 token。")
    headers = dict(request.headers)
    headers["Authorization"] = f"Bearer {token.strip()}"
    return CommercialApiRequest(
        method=request.method,
        url=request.url,
        headers=headers,
        body=dict(request.body),
        query=dict(request.query),
    )


def execute_commercial_api_request(
    request: CommercialApiRequest,
    opener,
    timeout: int = 20,
) -> tuple[dict[str, Any], str]:
    url, headers, body = build_urllib_request_parts(request)
    req = Request(url, data=body, headers=headers, method=request.method)
    safe_payload = sanitize_commercial_api_payload(request.body)
    with opener(req, timeout) as resp:
        raw = resp.read().decode("utf-8")
    data = parse_api_envelope(json.loads(raw))
    summary = f"{request.method} {request.url} -> OK；payload={safe_payload}"
    return data, summary


def build_api_key_owner_verify_request(
    contract: CommercialApiContract,
    api_key: str,
    target_buyer_user_id: str,
    operator_user_id: str,
) -> CommercialApiRequest:
    return CommercialApiRequest(
        method="POST",
        url=contract.api_key_owner_verify_url,
        body={
            "api_key": api_key,
            "target_buyer_user_id": target_buyer_user_id,
            "operator_user_id": operator_user_id,
        },
    )


def build_entitlement_query_request(
    contract: CommercialApiContract,
    buyer_user_id: str,
    operator_user_id: str,
) -> CommercialApiRequest:
    return CommercialApiRequest(
        method="GET",
        url=contract.entitlements_url,
        query={"buyer_user_id": buyer_user_id, "operator_user_id": operator_user_id},
    )


def build_order_create_request(
    contract: CommercialApiContract,
    product_id: str,
    buyer_user_id: str,
    operator_user_id: str,
    idempotency_key: str,
) -> CommercialApiRequest:
    return CommercialApiRequest(
        method="POST",
        url=contract.order_create_url,
        headers={"Idempotency-Key": idempotency_key},
        body={
            "product_id": product_id,
            "target_buyer_user_id": buyer_user_id,
            "operator_user_id": operator_user_id,
        },
    )


def build_agent_apply_request(
    contract: CommercialApiContract,
    product_id: str,
    idempotency_key: str,
) -> CommercialApiRequest:
    return CommercialApiRequest(
        method="POST",
        url=contract.agent_apply_url,
        headers={"Idempotency-Key": idempotency_key},
        body={"product_id": product_id},
    )


def build_agent_public_offering_request(contract: CommercialApiContract) -> CommercialApiRequest:
    return CommercialApiRequest(method="GET", url=contract.agent_public_offering_url)


def build_agent_center_request(contract: CommercialApiContract) -> CommercialApiRequest:
    return CommercialApiRequest(method="GET", url=contract.agent_center_url)


def build_agent_downstreams_request(
    contract: CommercialApiContract,
    cursor: str = "",
    limit: int = 50,
) -> CommercialApiRequest:
    query = {"limit": str(max(1, min(int(limit), 100)))}
    if cursor.strip():
        query["cursor"] = cursor.strip()
    return CommercialApiRequest(method="GET", url=contract.agent_downstreams_url, query=query)


def build_agent_commissions_request(
    contract: CommercialApiContract,
    status: str = "",
    event_type: str = "",
    cursor: str = "",
    limit: int = 50,
) -> CommercialApiRequest:
    query = {"limit": str(max(1, min(int(limit), 100)))}
    if status.strip():
        query["status"] = status.strip()
    if event_type.strip():
        query["event_type"] = event_type.strip()
    if cursor.strip():
        query["cursor"] = cursor.strip()
    return CommercialApiRequest(method="GET", url=contract.agent_commissions_url, query=query)


def build_agent_settlement_request(
    contract: CommercialApiContract,
    requested_cents: int,
    idempotency_key: str,
) -> CommercialApiRequest:
    return CommercialApiRequest(
        method="POST",
        url=contract.agent_settlements_url,
        headers={"Idempotency-Key": idempotency_key},
        body={"requested_cents": requested_cents},
    )


def build_referral_bind_request(
    contract: CommercialApiContract,
    invite_code: str,
    idempotency_key: str,
) -> CommercialApiRequest:
    return CommercialApiRequest(
        method="POST",
        url=contract.referral_bind_url,
        headers={"Idempotency-Key": idempotency_key},
        body={"invite_code": invite_code},
    )


def build_admin_agent_product_update_request(
    contract: CommercialApiContract,
    product: dict[str, Any],
) -> CommercialApiRequest:
    return CommercialApiRequest(method="PUT", url=contract.admin_agent_products_url, body={"product": dict(product)})


def build_admin_agent_policy_update_request(
    contract: CommercialApiContract,
    policy: dict[str, Any],
) -> CommercialApiRequest:
    return CommercialApiRequest(method="PUT", url=contract.admin_agent_policies_url, body={"policy": dict(policy)})


def build_admin_agent_marketing_content_update_request(
    contract: CommercialApiContract,
    content: dict[str, Any],
) -> CommercialApiRequest:
    return CommercialApiRequest(
        method="PUT",
        url=contract.admin_agent_marketing_content_url,
        body={"content": dict(content)},
    )


def build_admin_agent_application_review_request(
    contract: CommercialApiContract,
    application_id: str,
    decision: str,
    reason: str,
) -> CommercialApiRequest:
    return CommercialApiRequest(
        method="POST",
        url=contract.admin_agent_applications_url,
        body={"application_id": application_id, "decision": decision, "reason": reason},
    )


def build_admin_agent_settlement_action_request(
    contract: CommercialApiContract,
    settlement_id: str,
    action: str,
    reason: str,
) -> CommercialApiRequest:
    return CommercialApiRequest(
        method="POST",
        url=contract.admin_agent_settlements_url,
        body={"settlement_id": settlement_id, "action": action, "reason": reason},
    )


def build_admin_agent_ledger_action_request(
    contract: CommercialApiContract,
    ledger_id: str,
    action: str,
    reason: str,
) -> CommercialApiRequest:
    return CommercialApiRequest(
        method="POST",
        url=contract.admin_agent_ledger_action_url(ledger_id, action),
        body={"reason": reason},
    )


def build_mobile_control_offering_request(contract: CommercialApiContract) -> CommercialApiRequest:
    return CommercialApiRequest(method="GET", url=contract.mobile_control_offering_url)


def build_mobile_control_order_create_request(
    contract: CommercialApiContract,
    service_product_id: str,
    buyer_user_id: str,
    agent_id: str,
    channel: str,
    agent_source: str,
    idempotency_key: str,
) -> CommercialApiRequest:
    return CommercialApiRequest(
        method="POST",
        url=contract.mobile_control_orders_url,
        headers={"Idempotency-Key": idempotency_key},
        body={
            "service_product_id": service_product_id,
            "target_buyer_user_id": buyer_user_id,
            "agent_id": agent_id,
            "channel": channel,
            "agent_source": agent_source,
        },
    )


def build_mobile_control_order_get_request(
    contract: CommercialApiContract,
    order_id: str,
) -> CommercialApiRequest:
    return CommercialApiRequest(method="GET", url=contract.mobile_control_order_url(order_id))


def build_mobile_control_session_create_request(
    contract: CommercialApiContract,
    order_id: str,
    agent_id: str,
    channel: str,
    platform_account_id: str,
    platform_chat_id: str,
    gateway_mode: str,
    agent_source: str,
    idempotency_key: str,
) -> CommercialApiRequest:
    return CommercialApiRequest(
        method="POST",
        url=contract.mobile_control_sessions_url,
        headers={"Idempotency-Key": idempotency_key},
        body={
            "order_id": order_id,
            "agent_id": agent_id,
            "channel": channel,
            "platform_account_id": platform_account_id,
            "platform_chat_id": platform_chat_id,
            "gateway_mode": gateway_mode,
            "agent_source": agent_source,
        },
    )


def build_mobile_control_session_get_request(
    contract: CommercialApiContract,
    session_id: str,
) -> CommercialApiRequest:
    return CommercialApiRequest(method="GET", url=contract.mobile_control_session_url(session_id))


def build_mobile_control_session_test_request(
    contract: CommercialApiContract,
    session_id: str,
    test_prompt: str,
    idempotency_key: str,
) -> CommercialApiRequest:
    return CommercialApiRequest(
        method="POST",
        url=contract.mobile_control_session_test_url(session_id),
        headers={"Idempotency-Key": idempotency_key},
        body={"test_prompt": test_prompt},
    )


def build_mobile_control_session_acceptance_request(
    contract: CommercialApiContract,
    session_id: str,
    source_event_id: str,
    inbound_platform_message_id: str,
    outbound_platform_message_id: str,
    test_prompt: str,
    agent_response_digest: str,
    evidence_url: str,
    idempotency_key: str,
) -> CommercialApiRequest:
    return CommercialApiRequest(
        method="POST",
        url=contract.mobile_control_session_acceptance_url(session_id),
        headers={"Idempotency-Key": idempotency_key},
        body={
            "source_event_id": source_event_id,
            "inbound_platform_message_id": inbound_platform_message_id,
            "outbound_platform_message_id": outbound_platform_message_id,
            "test_prompt": test_prompt,
            "agent_response_digest": agent_response_digest,
            "evidence_url": evidence_url,
        },
    )


def build_mobile_control_session_disable_request(
    contract: CommercialApiContract,
    session_id: str,
    reason: str,
    idempotency_key: str,
) -> CommercialApiRequest:
    return CommercialApiRequest(
        method="POST",
        url=contract.mobile_control_session_disable_url(session_id),
        headers={"Idempotency-Key": idempotency_key},
        body={"reason": reason},
    )


def build_mobile_control_callback_request(
    contract: CommercialApiContract,
    channel: str,
    platform_message_id: str,
    platform_chat_id: str,
    sender_id: str,
    text: str,
    mentioned_bot: bool = False,
    wake_word_matched: bool = False,
) -> CommercialApiRequest:
    return CommercialApiRequest(
        method="POST",
        url=contract.mobile_control_callback_url(channel),
        body={
            "channel": channel,
            "platform_message_id": platform_message_id,
            "platform_chat_id": platform_chat_id,
            "sender_id": sender_id,
            "text": text,
            "mentioned_bot": bool(mentioned_bot),
            "wake_word_matched": bool(wake_word_matched),
        },
    )


def build_admin_mobile_control_product_update_request(
    contract: CommercialApiContract,
    product: dict[str, Any],
) -> CommercialApiRequest:
    return CommercialApiRequest(method="PUT", url=contract.admin_mobile_control_products_url, body={"product": dict(product)})


def build_admin_mobile_control_channel_policy_update_request(
    contract: CommercialApiContract,
    policy: dict[str, Any],
) -> CommercialApiRequest:
    return CommercialApiRequest(
        method="PUT",
        url=contract.admin_mobile_control_channel_policies_url,
        body={"policy": dict(policy)},
    )


def build_admin_mobile_control_sessions_request(
    contract: CommercialApiContract,
    status: str = "",
    cursor: str = "",
    limit: int = 50,
) -> CommercialApiRequest:
    query = {"limit": str(max(1, min(int(limit), 100)))}
    if status.strip():
        query["status"] = status.strip()
    if cursor.strip():
        query["cursor"] = cursor.strip()
    return CommercialApiRequest(method="GET", url=contract.admin_mobile_control_sessions_url, query=query)


def build_admin_mobile_control_session_action_request(
    contract: CommercialApiContract,
    session_id: str,
    action: str,
    reason: str,
) -> CommercialApiRequest:
    return CommercialApiRequest(
        method="POST",
        url=contract.admin_mobile_control_session_action_url(session_id, action),
        body={"reason": reason},
    )


def build_admin_mobile_control_order_action_request(
    contract: CommercialApiContract,
    order_id: str,
    action: str,
    reason: str,
) -> CommercialApiRequest:
    return CommercialApiRequest(
        method="POST",
        url=contract.admin_mobile_control_order_action_url(order_id, action),
        body={"reason": reason},
    )


def build_payment_poll_request(
    contract: CommercialApiContract,
    order_id: str,
    buyer_user_id: str,
) -> CommercialApiRequest:
    return CommercialApiRequest(
        method="GET",
        url=contract.payment_status_url,
        query={"order_id": order_id, "buyer_user_id": buyer_user_id},
    )


def build_config_session_reserve_request(
    contract: CommercialApiContract,
    entitlement_id: str,
    buyer_user_id: str,
    operator_user_id: str,
    agent_id: str,
    mode_key: str,
    device_id: str,
    diagnostic_code: str,
    idempotency_key: str,
) -> CommercialApiRequest:
    return CommercialApiRequest(
        method="POST",
        url=contract.config_session_reserve_url,
        headers={"Idempotency-Key": idempotency_key},
        body={
            "entitlement_id": entitlement_id,
            "buyer_user_id": buyer_user_id,
            "operator_user_id": operator_user_id,
            "agent_id": agent_id,
            "mode_key": mode_key,
            "device_id": device_id,
            "diagnostic_code": diagnostic_code,
        },
    )


def build_config_session_complete_request(
    contract: CommercialApiContract,
    config_session_id: str,
    diagnostic_code: str,
    real_task_verified: bool,
    idempotency_key: str,
) -> CommercialApiRequest:
    return CommercialApiRequest(
        method="POST",
        url=contract.config_session_complete_url,
        headers={"Idempotency-Key": idempotency_key},
        body={
            "config_session_id": config_session_id,
            "diagnostic_code": diagnostic_code,
            "real_task_verified": real_task_verified,
        },
    )


def build_config_session_fail_request(
    contract: CommercialApiContract,
    config_session_id: str,
    diagnostic_code: str,
    failure_reason: str,
    idempotency_key: str,
) -> CommercialApiRequest:
    return CommercialApiRequest(
        method="POST",
        url=contract.config_session_fail_url,
        headers={"Idempotency-Key": idempotency_key},
        body={
            "config_session_id": config_session_id,
            "diagnostic_code": diagnostic_code,
            "failure_reason": failure_reason,
            "deduct_entitlement": False,
        },
    )


def parse_api_envelope(payload: dict[str, Any]) -> dict[str, Any]:
    if not payload.get("success"):
        raise ValueError(sanitize_commercial_text(str(payload.get("message") or "服务端返回失败。")))
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError("服务端返回缺少 data。")
    return data


def parse_config_session_reserve_data(data: dict[str, Any]) -> dict[str, str]:
    config_session_id = str(data.get("config_session_id") or "").strip()
    if not config_session_id:
        raise ValueError("服务端未返回配置会话 ID，不能提交成功或失败。")
    return {"config_session_id": config_session_id}


def parse_payment_status_data(data: dict[str, Any]) -> dict[str, Any]:
    order_id = str(data.get("order_id") or "").strip()
    payment_status = str(data.get("payment_status") or data.get("status") or "").strip().lower()
    if not order_id or not payment_status:
        raise ValueError("服务端支付状态缺少订单 ID 或支付状态。")

    entitlement_id = str(data.get("entitlement_id") or "").strip()
    entitlement_status = str(data.get("entitlement_status") or "").strip().lower()
    successful_statuses = {"paid", "success", "completed"}
    ready_for_delivery = (
        payment_status in successful_statuses
        and bool(entitlement_id)
        and entitlement_status == "active"
    )
    return {
        "order_id": order_id,
        "payment_status": payment_status,
        "entitlement_id": entitlement_id,
        "entitlement_status": entitlement_status,
        "ready_for_delivery": ready_for_delivery,
        "requires_manual_review": payment_status in successful_statuses and not ready_for_delivery,
    }
