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
    "assist_session_id",
    "order_id",
    "config_session_id",
}

SENSITIVE_TEXT_PATTERNS = (
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b1[3-9]\d{9}\b"),
    re.compile(r"\bsk-[A-Za-z0-9._-]+\b"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+\b"),
    re.compile(r"(?i)\b(token|access_token|refresh_token|api_key|invite_code|order_id|entitlement_id|config_session_id|assist_session_id)\s*[:=]\s*[A-Za-z0-9._~:/+-]+\b"),
    re.compile(r"(?i)\b(token|access_token|refresh_token|api_key|invite_code|order_id|entitlement_id|config_session_id|assist_session_id)\s+[A-Za-z0-9._~:/+-]+\b"),
    re.compile(r"\b(?:ord|order|ent|cfg|assist|invite)-[A-Za-z0-9._-]+\b", re.IGNORECASE),
)


@dataclass(frozen=True)
class CommercialApiContract:
    base_url: str

    def _url(self, path: str) -> str:
        return self.base_url.rstrip("/") + path

    # Legacy proxy/agent-assist contract endpoints retained only for
    # compatibility review and cleanup. Current buyer flow should not depend on
    # them as primary product APIs.
    @property
    def agent_assist_login_url(self) -> str:
        return self._url("/api/deployer/agent-assist/login")

    @property
    def buyer_bind_url(self) -> str:
        return self._url("/api/deployer/agent-assist/bind-buyer")

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
    assist_session_id: str,
) -> str:
    # Keep assist_session_id in the hash for legacy compatibility, but current
    # buyer self-service flow should pass an empty value here.
    seed = f"order:{product_id}:{buyer_user_id}:{operator_user_id}:{assist_session_id}".encode("utf-8")
    digest = hashlib.sha256(seed).hexdigest()[:24]
    return f"order-{digest}"


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


def build_agent_assist_login_request(
    contract: CommercialApiContract,
    agent_username: str,
    agent_password: str,
    verification_code: str,
    invite_code: str,
    device_id: str,
    app_version: str,
) -> CommercialApiRequest:
    # Legacy proxy/agent-assist login request. Current product flow should not
    # call this in customer-facing deployment paths.
    return CommercialApiRequest(
        method="POST",
        url=contract.agent_assist_login_url,
        body={
            "role": "agent",
            "username": agent_username,
            "password": agent_password,
            "verification_code": verification_code,
            "invite_code": invite_code,
            "device_id": device_id,
            "app_version": app_version,
        },
    )


def build_buyer_bind_request(
    contract: CommercialApiContract,
    operator_user_id: str,
    target_buyer_user_id: str,
    assist_session_id: str,
    invite_code: str,
) -> CommercialApiRequest:
    # Legacy proxy/agent-assist buyer binding request.
    return CommercialApiRequest(
        method="POST",
        url=contract.buyer_bind_url,
        body={
            "operator_user_id": operator_user_id,
            "target_buyer_user_id": target_buyer_user_id,
            "assist_session_id": assist_session_id,
            "invite_code": invite_code,
        },
    )


def build_api_key_owner_verify_request(
    contract: CommercialApiContract,
    api_key: str,
    target_buyer_user_id: str,
    operator_user_id: str,
    assist_session_id: str = "",
) -> CommercialApiRequest:
    body = {
        "api_key": api_key,
        "target_buyer_user_id": target_buyer_user_id,
        "operator_user_id": operator_user_id,
    }
    if str(assist_session_id or "").strip():
        body["assist_session_id"] = assist_session_id
    return CommercialApiRequest(
        method="POST",
        url=contract.api_key_owner_verify_url,
        body=body,
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
    assist_session_id: str,
    idempotency_key: str,
) -> CommercialApiRequest:
    body = {
        "product_id": product_id,
        "target_buyer_user_id": buyer_user_id,
        "operator_user_id": operator_user_id,
    }
    if str(assist_session_id or "").strip():
        body["assist_session_id"] = assist_session_id
    return CommercialApiRequest(
        method="POST",
        url=contract.order_create_url,
        headers={"Idempotency-Key": idempotency_key},
        body=body,
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
