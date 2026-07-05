# -*- coding: utf-8 -*-
"""本地联调网关（仅开发/集成测试用，绝不部署到生产）。

作用：让胖虎AI客户端在本机走通完整买家链路，而不触碰生产服务器。
- 模拟中转站 deployer 侧：登录 / 部署授权 / 签名清单（含测试权益）/
  权益查询 / 订单 / 配置会话 / Key 归属校验 / 支付状态。
- 模拟网关模型接口：/v1/chat/completions 返回"胖虎AI配置验证成功"。
- 其余 /api/* 全部反代到本地"胖虎AI后台管理系统"（默认 127.0.0.1:8300），
  并注入 X-Panghu-User 买家身份头（生产由 Nginx 反代层完成同样注入）。

清单签名：启动时在 outputs/dev_integration/ 生成 Ed25519 测试密钥对，并写出
commercial_manifest_public_key.py。客户端进程用 PYTHONPATH 指向该目录即可
用测试公钥验签（生产公钥走构建注入，互不影响）。

用法（三个终端）：
  1) 后台系统：
     cd ..\胖虎AI后台管理系统
     $env:PANGHU_ADMIN_TOKEN='dev-token'
     .venv\Scripts\python.exe -m uvicorn app.main:app --port 8300
  2) 本网关（用后台系统的 venv，含 fastapi/httpx/cryptography）：
     ..\胖虎AI后台管理系统\.venv\Scripts\python.exe scripts\local_integration_server.py
  3) 客户端：
     $env:PANGHU_DEV_BASE_URL_OVERRIDE='http://127.0.0.1:8299'
     $env:PYTHONPATH='outputs\dev_integration'
     .venv\Scripts\python.exe src\panghu_ai_client.py
"""
from __future__ import annotations

import base64
import json
import sys
import time
import uuid
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, Request, Response

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from commercial_core import canonical_commercial_manifest_payload  # noqa: E402

PORT = 8299
BACKEND_BASE = "http://127.0.0.1:8300"
DEV_BUYER_ID = "900001"
DEV_KEY_DIR = ROOT / "outputs" / "dev_integration"
DEV_MODEL = "gpt-5.4"

app = FastAPI(title="胖虎AI本地联调网关（仅开发）", docs_url=None, redoc_url=None)
_state: dict = {"orders": {}, "sessions": {}, "entitlement_uses": 5}


def _ensure_dev_keys() -> tuple[object, str]:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    DEV_KEY_DIR.mkdir(parents=True, exist_ok=True)
    priv_path = DEV_KEY_DIR / "dev_manifest_private.pem"
    if priv_path.exists():
        private_key = serialization.load_pem_private_key(priv_path.read_bytes(), password=None)
    else:
        private_key = Ed25519PrivateKey.generate()
        priv_path.write_bytes(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
    (DEV_KEY_DIR / "commercial_manifest_public_key.py").write_text(
        '"""本地联调用测试验签公钥（自动生成，勿用于生产）。"""\n'
        f'PUBLIC_KEY_PEM = """{public_pem}"""\n',
        encoding="utf-8",
    )
    # 客户端经 PANGHU_DEV_MANIFEST_PUBLIC_KEY_FILE 读取（src 下的构建占位模块会
    # 遮蔽 PYTHONPATH，所以不能只靠模块注入）。
    (DEV_KEY_DIR / "dev_manifest_public.pem").write_text(public_pem, encoding="utf-8")
    return private_key, public_pem


PRIVATE_KEY, PUBLIC_PEM = _ensure_dev_keys()


def _dev_entitlements() -> list[dict]:
    remaining = _state["entitlement_uses"]
    items = []
    for agent_id, mode_key in (
        ("codex", "direct_api"),
        ("codex", "cli"),
        ("codex", "dual_state"),
        ("claude_code", "cli"),
        ("openclaw", "cli"),
        ("hermes", "cli"),
        ("gemini_agy", "cli"),
    ):
        items.append(
            {
                "entitlement_id": f"ent-dev-{agent_id}-{mode_key}",
                "buyer_user_id": DEV_BUYER_ID,
                "agent_id": agent_id,
                "mode_key": mode_key,
                "remaining_uses": remaining,
                "valid_until": "2099-12-31",
                "delivery_scope": "full_config",
                "device_limit": 3,
                "status": "active",
            }
        )
    return items


def _signed_manifest() -> dict:
    manifest = {
        # agents 即安装授权白名单 + 每 Agent 商业能力开关
        "agents": [
            {"id": aid, "delivery_scope": "full_config", "full_config_allowed": True}
            for aid in ("codex", "claude_code", "openclaw", "hermes", "gemini_agy")
        ],
        "products": [
            {
                "product_id": "prod-dev-full",
                "title": "联调测试·五 Agent 完整配置",
                "price_cents": 0,
                "delivery_scope": "full_config",
                "status": "active",
            }
        ],
        "entitlements": _dev_entitlements(),
        "manifest_signature_algorithm": "ed25519",
        "manifest_key_id": "dev-local-1",
        "manifest_issued_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
    }
    signature = PRIVATE_KEY.sign(canonical_commercial_manifest_payload(manifest))
    manifest["manifest_signature"] = "ed25519:" + base64.b64encode(signature).decode("ascii")
    return manifest


def _ok(data: dict | list | None = None, message: str = "") -> dict:
    return {"success": True, "message": message, "data": data if data is not None else {}}


# ---------- 模拟 deployer / 登录（生产由中转站服务端提供） ----------

@app.post("/api/user/login")
async def dev_login(request: Request) -> dict:
    body = await request.json()
    username = str(body.get("username") or "dev-buyer")
    return _ok({"id": DEV_BUYER_ID, "username": username}, "本地联调登录成功")


@app.post("/api/deployer/activate")
async def dev_activate() -> dict:
    return _ok({"token": "dev-deployer-token"})


@app.get("/api/deployer/manifest")
async def dev_manifest() -> dict:
    return _ok(_signed_manifest())


@app.get("/api/deployer/entitlements")
async def dev_entitlements() -> dict:
    return _ok({"entitlements": _dev_entitlements()})


@app.post("/api/deployer/orders")
async def dev_order_create(request: Request) -> dict:
    body = await request.json()
    order_id = f"ord-dev-{uuid.uuid4().hex[:8]}"
    _state["orders"][order_id] = body
    return _ok({"order_id": order_id, "payment_status": "paid",
                "entitlement_id": "ent-dev-codex", "entitlement_status": "active"})


@app.get("/api/tool-orders/payment-status")
async def dev_payment_status(order_id: str = "") -> dict:
    oid = order_id or (next(iter(_state["orders"]), "ord-dev-none"))
    return _ok({"order_id": oid, "payment_status": "paid",
                "entitlement_id": "ent-dev-codex", "entitlement_status": "active"})


@app.post("/api/deployer/api-keys/verify-owner")
async def dev_verify_owner(request: Request) -> dict:
    body = await request.json()
    # 客户端 execute_api_key_owner_verify 读取 data.owner_user_id 并与当前买家比对。
    return _ok({"owner_user_id": str(body.get("target_buyer_user_id") or DEV_BUYER_ID)})


@app.post("/api/deployer/config-sessions/reserve")
async def dev_session_reserve(request: Request) -> dict:
    body = await request.json()
    sid = f"cfg-dev-{uuid.uuid4().hex[:10]}"
    _state["sessions"][sid] = {"status": "reserved", "request": body}
    return _ok({"config_session_id": sid, "status": "reserved"})


@app.post("/api/deployer/config-sessions/complete")
async def dev_session_complete(request: Request) -> dict:
    body = await request.json()
    sid = str(body.get("config_session_id") or "")
    if sid in _state["sessions"]:
        _state["sessions"][sid]["status"] = "completed"
        if _state["entitlement_uses"] > 0:
            _state["entitlement_uses"] -= 1  # 模拟扣次
    return _ok({"config_session_id": sid, "status": "completed"})


@app.post("/api/deployer/config-sessions/fail")
async def dev_session_fail(request: Request) -> dict:
    body = await request.json()
    sid = str(body.get("config_session_id") or "")
    if sid in _state["sessions"]:
        _state["sessions"][sid]["status"] = "failed-without-deduct"
    return _ok({"config_session_id": sid, "status": "failed-without-deduct"})


@app.post("/api/referrals/bind")
async def dev_referral_bind() -> dict:
    return _ok({"bound": True})


# ---------- 模拟网关模型接口（最小中文对话验收用） ----------

VERIFY_TEXT = "胖虎AI配置验证成功"


def _sse(events: list[str]) -> Response:
    payload = "".join(f"data: {e}\n\n" for e in events) + "data: [DONE]\n\n"
    return Response(content=payload, media_type="text/event-stream")


@app.get("/v1/models")
async def dev_models() -> dict:
    return {"object": "list", "data": [{"id": DEV_MODEL, "object": "model"}]}


@app.post("/v1/chat/completions")
async def dev_chat(request: Request) -> Response:
    try:
        body = json.loads(await request.body() or b"{}")
    except Exception:
        body = {}
    model = str(body.get("model") or DEV_MODEL)
    if body.get("stream"):
        chunk = {
            "id": "chatcmpl-dev", "object": "chat.completion.chunk", "model": model,
            "choices": [{"index": 0, "delta": {"role": "assistant", "content": VERIFY_TEXT},
                         "finish_reason": None}],
        }
        end = {
            "id": "chatcmpl-dev", "object": "chat.completion.chunk", "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
        return _sse([json.dumps(chunk, ensure_ascii=False), json.dumps(end, ensure_ascii=False)])
    return Response(content=json.dumps({
        "id": "chatcmpl-dev", "object": "chat.completion", "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": VERIFY_TEXT},
                     "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }, ensure_ascii=False), media_type="application/json")


@app.post("/v1/messages")
async def dev_anthropic_messages(request: Request) -> Response:
    """Anthropic Messages 格式（ClaudeCode 最小对话验收）。"""
    try:
        body = json.loads(await request.body() or b"{}")
    except Exception:
        body = {}
    model = str(body.get("model") or DEV_MODEL)
    if body.get("stream"):
        events = [
            json.dumps({"type": "message_start", "message": {
                "id": "msg-dev", "type": "message", "role": "assistant", "model": model,
                "content": [], "stop_reason": None,
                "usage": {"input_tokens": 1, "output_tokens": 0}}}, ensure_ascii=False),
            json.dumps({"type": "content_block_start", "index": 0,
                        "content_block": {"type": "text", "text": ""}}, ensure_ascii=False),
            json.dumps({"type": "content_block_delta", "index": 0,
                        "delta": {"type": "text_delta", "text": VERIFY_TEXT}}, ensure_ascii=False),
            json.dumps({"type": "content_block_stop", "index": 0}, ensure_ascii=False),
            json.dumps({"type": "message_delta", "delta": {"stop_reason": "end_turn"},
                        "usage": {"output_tokens": 1}}, ensure_ascii=False),
            json.dumps({"type": "message_stop"}, ensure_ascii=False),
        ]
        return _sse(events)
    return Response(content=json.dumps({
        "id": "msg-dev", "type": "message", "role": "assistant", "model": model,
        "content": [{"type": "text", "text": VERIFY_TEXT}],
        "stop_reason": "end_turn", "stop_sequence": None,
        "usage": {"input_tokens": 1, "output_tokens": 1},
    }, ensure_ascii=False), media_type="application/json")


@app.post("/v1beta/models/{model_action:path}")
async def dev_gemini_generate(model_action: str, request: Request) -> Response:
    """Gemini generateContent / streamGenerateContent 格式（agy 最小对话验收）。"""
    reply = {
        "candidates": [{
            "content": {"parts": [{"text": VERIFY_TEXT}], "role": "model"},
            "finishReason": "STOP", "index": 0,
        }],
        "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 1, "totalTokenCount": 2},
        "modelVersion": DEV_MODEL,
    }
    if "streamGenerateContent" in model_action:
        if "alt=sse" in str(request.url.query):
            return _sse([json.dumps(reply, ensure_ascii=False)])
        return Response(content=json.dumps([reply], ensure_ascii=False), media_type="application/json")
    return Response(content=json.dumps(reply, ensure_ascii=False), media_type="application/json")


# ---------- 其余 /api/* 反代到本地后台管理系统，注入买家身份 ----------

@app.api_route("/api/{rest:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_backend(rest: str, request: Request) -> Response:
    url = f"{BACKEND_BASE}/api/{rest}"
    headers = {k: v for k, v in request.headers.items()
               if k.lower() not in {"host", "content-length"}}
    headers["X-Panghu-User"] = DEV_BUYER_ID
    body = await request.body()
    async with httpx.AsyncClient(timeout=30) as client:
        upstream = await client.request(
            request.method, url, params=dict(request.query_params), headers=headers, content=body
        )
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type", "application/json"),
    )


if __name__ == "__main__":
    print("=" * 64)
    print("胖虎AI本地联调网关（仅开发） http://127.0.0.1:%d" % PORT)
    print("测试验签公钥模块：%s" % (DEV_KEY_DIR / "commercial_manifest_public_key.py"))
    print("客户端启动环境变量：")
    print("  PANGHU_DEV_BASE_URL_OVERRIDE=http://127.0.0.1:%d" % PORT)
    print("  PYTHONPATH=%s" % DEV_KEY_DIR)
    print("=" * 64)
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
