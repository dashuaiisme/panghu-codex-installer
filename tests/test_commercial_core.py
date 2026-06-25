import sys
import unittest
import base64
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from commercial_core import (  # noqa: E402
    CommercialEntry,
    CommercialEntryId,
    AgentAssistDraft,
    AgentAssistNode,
    BuyerSelfServiceNode,
    CommercialProduct,
    CommercialWebProfile,
    ConfigSessionContract,
    DeliveryScope,
    DeploymentNode,
    DeploymentProgress,
    EntitlementContract,
    NodeStatus,
    RealTaskVerificationResult,
    UserContext,
    WebProfileScope,
    build_commercial_agent_capabilities,
    build_agent_assist_status_rows,
    build_buyer_self_service_status_rows,
    build_agent_customer_state,
    build_commercial_entry_cards,
    build_commercial_product_catalog,
    build_customer_commercial_summary_lines,
    build_entitlement_summary_rows,
    build_node_status_rows,
    build_customer_delivery_verdict,
    build_customer_delivery_report,
    build_support_diagnostic_packet,
    canonical_commercial_manifest_payload,
    commercial_deployment_blockers,
    commercial_config_gate,
    config_session_terminal_action,
    api_key_owner_gate,
    build_agent_center_summary_lines,
    build_real_task_diagnostic_summary,
    build_persistent_profile_payload,
    create_agent_assist_contexts,
    create_buyer_contexts,
    create_commercial_web_profile,
    find_orderable_product,
    find_usable_entitlement,
    find_listed_product,
    sanitize_customer_diagnostic_text,
    validate_commercial_manifest_trust,
    verify_real_task_evidence,
)


class CommercialCoreTests(unittest.TestCase):
    def test_commercial_manifest_with_commercial_controls_requires_server_signature(self) -> None:
        decision = validate_commercial_manifest_trust({"products": []})

        self.assertFalse(decision.trusted)
        self.assertTrue(decision.requires_signature)
        self.assertIn("签名", decision.message)

    def test_legacy_manifest_without_commercial_controls_does_not_require_signature(self) -> None:
        decision = validate_commercial_manifest_trust({"agents": [{"id": "codex"}]})

        self.assertTrue(decision.trusted)
        self.assertFalse(decision.requires_signature)

    def test_signed_commercial_manifest_without_public_key_is_rejected(self) -> None:
        decision = validate_commercial_manifest_trust(
            {
                "products": [],
                "manifest_signature": "ed25519:" + "a" * 88,
                "manifest_issued_at": "2026-06-21T00:00:00+08:00",
                "manifest_signature_algorithm": "ed25519",
                "manifest_key_id": "test-key-1",
            }
        )

        self.assertFalse(decision.trusted)
        self.assertIn("公钥", decision.message)

    def test_ed25519_signed_commercial_manifest_is_verified_with_public_key(self) -> None:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        private_key = Ed25519PrivateKey.generate()
        public_key_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("ascii")
        manifest = {
            "products": [],
            "manifest_issued_at": "2026-06-21T00:00:00+08:00",
            "manifest_signature_algorithm": "ed25519",
            "manifest_key_id": "test-key-1",
        }
        signature = private_key.sign(canonical_commercial_manifest_payload(manifest))
        manifest["manifest_signature"] = "ed25519:" + base64.b64encode(signature).decode("ascii")

        decision = validate_commercial_manifest_trust(manifest, public_key_pem=public_key_pem)

        self.assertTrue(decision.trusted)

    def test_tampered_ed25519_signed_commercial_manifest_is_rejected(self) -> None:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        private_key = Ed25519PrivateKey.generate()
        public_key_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("ascii")
        manifest = {
            "products": [],
            "manifest_issued_at": "2026-06-21T00:00:00+08:00",
            "manifest_signature_algorithm": "ed25519",
            "manifest_key_id": "test-key-1",
        }
        signature = private_key.sign(canonical_commercial_manifest_payload(manifest))
        manifest["manifest_signature"] = "ed25519:" + base64.b64encode(signature).decode("ascii")
        manifest["products"] = [{"product_id": "tampered"}]

        decision = validate_commercial_manifest_trust(manifest, public_key_pem=public_key_pem)

        self.assertFalse(decision.trusted)
        self.assertIn("验签失败", decision.message)

    def test_buyer_mode_uses_same_operator_and_target_buyer(self) -> None:
        buyer = UserContext(user_id="buyer-1", display_name="买家A", role="buyer")

        contexts = create_buyer_contexts(buyer)

        self.assertEqual(contexts.operator.user_id, "buyer-1")
        self.assertEqual(contexts.target_buyer.user_id, "buyer-1")
        self.assertEqual(contexts.effective_buyer_user_id, "buyer-1")
        self.assertEqual(contexts.web_profile_scope, WebProfileScope.BUYER)

    def test_agent_assist_context_keeps_operator_and_buyer_separate(self) -> None:
        agent = UserContext(user_id="agent-1", display_name="代理A", role="agent")
        buyer = UserContext(user_id="buyer-2", display_name="买家B", role="buyer")

        contexts = create_agent_assist_contexts(agent, buyer, assist_session_id="assist-1")

        self.assertEqual(contexts.operator.user_id, "agent-1")
        self.assertEqual(contexts.target_buyer.user_id, "buyer-2")
        self.assertEqual(contexts.effective_buyer_user_id, "buyer-2")
        self.assertEqual(contexts.web_profile_scope, WebProfileScope.AGENT_ASSIST_EPHEMERAL)

    def test_api_key_owner_gate_allows_only_target_buyer_key_in_agent_assist(self) -> None:
        contexts = create_agent_assist_contexts(
            UserContext(user_id="agent-1", display_name="代理A", role="agent"),
            UserContext(user_id="buyer-2", display_name="买家B", role="buyer"),
            assist_session_id="assist-1",
        )

        allowed = api_key_owner_gate(contexts, verified_owner_user_id="buyer-2")
        blocked = api_key_owner_gate(contexts, verified_owner_user_id="agent-1")

        self.assertTrue(allowed.allowed)
        self.assertFalse(blocked.allowed)
        self.assertIn("目标买家", blocked.message)
        self.assertNotIn("agent-1", blocked.message)
        self.assertNotIn("buyer-2", blocked.message)

    def test_api_key_owner_gate_blocks_unknown_owner_for_commercial_delivery(self) -> None:
        contexts = create_buyer_contexts(UserContext(user_id="buyer-1", display_name="买家A", role="buyer"))

        decision = api_key_owner_gate(contexts, verified_owner_user_id="")

        self.assertFalse(decision.allowed)
        self.assertIn("归属", decision.message)

    def test_agent_assist_draft_creates_contexts_and_clears_sensitive_fields(self) -> None:
        draft = AgentAssistDraft(
            agent_username="agent@example.com",
            agent_password="agent-password",
            verification_code="123456",
            invite_code="INVITE-001",
            agent_user=UserContext(user_id="agent-1", display_name="代理A", role="agent", token="agent-token"),
            target_buyer=UserContext(user_id="buyer-1", display_name="买家A", role="buyer"),
            assist_session_id="assist-1",
        )

        contexts = draft.to_contexts()

        self.assertEqual(contexts.operator.user_id, "agent-1")
        self.assertEqual(contexts.target_buyer.user_id, "buyer-1")
        self.assertEqual(contexts.assist_session_id, "assist-1")
        draft.clear_sensitive_fields()
        self.assertEqual(draft.agent_username, "")
        self.assertEqual(draft.agent_password, "")
        self.assertEqual(draft.verification_code, "")
        self.assertEqual(draft.agent_user, None)

    def test_agent_assist_status_rows_are_ordered_and_customer_safe(self) -> None:
        rows = build_agent_assist_status_rows(
            {
                AgentAssistNode.AGENT_LOGIN: NodeStatus.PASS,
                AgentAssistNode.BUYER_BIND: NodeStatus.RUNNING,
            }
        )

        self.assertEqual([row.node for row in rows[:3]], [
            AgentAssistNode.AGENT_LOGIN,
            AgentAssistNode.BUYER_BIND,
            AgentAssistNode.ORDER_PAYMENT,
        ])
        row_text = " ".join(row.customer_message for row in rows)
        self.assertIn("代理身份", row_text)
        self.assertIn("绑定买家", row_text)
        self.assertNotIn("password", row_text.lower())
        self.assertNotIn("token", row_text.lower())

    def test_buyer_self_service_status_rows_hide_agent_only_nodes(self) -> None:
        rows = build_buyer_self_service_status_rows(
            {
                BuyerSelfServiceNode.ORDER_PAYMENT: NodeStatus.RUNNING,
                BuyerSelfServiceNode.ENTITLEMENT_REFRESH: NodeStatus.PASS,
            }
        )

        self.assertEqual(
            [row.node for row in rows],
            [BuyerSelfServiceNode.ORDER_PAYMENT, BuyerSelfServiceNode.ENTITLEMENT_REFRESH],
        )
        row_text = " ".join(row.customer_message for row in rows)
        self.assertIn("订单支付", row_text)
        self.assertIn("刷新权益", row_text)
        self.assertNotIn("代理身份", row_text)
        self.assertNotIn("绑定买家", row_text)

    def test_agent_assist_profile_payload_persists_buyer_config_without_agent_identity(self) -> None:
        agent = UserContext(
            user_id="agent-1",
            display_name="agent@example.com",
            role="agent",
            token="secret-token",
        )
        buyer = UserContext(user_id="buyer-2", display_name="买家B", role="buyer")
        contexts = create_agent_assist_contexts(agent, buyer, assist_session_id="assist-1")

        payload = build_persistent_profile_payload(
            current_profile={"username": "old", "api_key": "sk-test"},
            updates={
                "username": "agent@example.com",
                "user": {"id": "agent-1"},
                "deployer_auth": {"token": "secret-token"},
                "api_key": "sk-buyer-live",
                "model": "gpt-5.4",
                "skip_test": True,
                "open_app": False,
            },
            contexts=contexts,
            default_base_url="https://aitokenapi.cc",
            default_model="gpt-5.4",
        )

        self.assertNotIn("agent@example.com", str(payload))
        self.assertNotIn("secret-token", str(payload))
        self.assertEqual(payload["username"], "old")
        self.assertEqual(payload["api_key"], "sk-buyer-live")
        self.assertEqual(payload["model"], "gpt-5.4")
        self.assertTrue(payload["skip_test"])
        self.assertFalse(payload["open_app"])

    def test_agent_assist_profile_payload_drops_existing_agent_assist_pollution(self) -> None:
        agent = UserContext(
            user_id="agent-1",
            display_name="agent@example.com",
            role="agent",
            token="agent-secret-token",
        )
        buyer = UserContext(user_id="buyer-2", display_name="买家B", role="buyer")
        contexts = create_agent_assist_contexts(agent, buyer, assist_session_id="assist-secret")

        payload = build_persistent_profile_payload(
            current_profile={
                "username": "buyer@example.com",
                "user": {"id": "buyer-2", "role": "buyer"},
                "deployer_auth": {"token": "buyer-token"},
                "api_key": "sk-buyer-old",
                "agent_user": {"id": "agent-1", "token": "agent-secret-token"},
                "agent_assist": {"assist_session_id": "assist-secret", "invite_code": "INVITE-SECRET"},
                "assist_session_id": "assist-secret",
                "order_id": "ord-secret",
                "config_session_id": "cfg-secret",
            },
            updates={
                "api_key": "sk-buyer-live",
                "model": "gpt-5.4",
            },
            contexts=contexts,
            default_base_url="https://aitokenapi.cc",
            default_model="gpt-5.4",
        )

        text = str(payload)
        self.assertNotIn("agent-secret-token", text)
        self.assertNotIn("assist-secret", text)
        self.assertNotIn("INVITE-SECRET", text)
        self.assertNotIn("ord-secret", text)
        self.assertNotIn("cfg-secret", text)
        self.assertNotIn("agent_user", payload)
        self.assertNotIn("agent_assist", payload)
        self.assertEqual(payload["username"], "buyer@example.com")
        self.assertEqual(payload["api_key"], "sk-buyer-live")
        self.assertEqual(payload["deployer_auth"], {})

    def test_agent_assist_profile_payload_drops_existing_agent_login_state(self) -> None:
        agent = UserContext(
            user_id="agent-1",
            display_name="agent@example.com",
            role="agent",
            token="agent-secret-token",
        )
        buyer = UserContext(user_id="buyer-2", display_name="买家B", role="buyer")
        contexts = create_agent_assist_contexts(agent, buyer, assist_session_id="assist-secret")

        payload = build_persistent_profile_payload(
            current_profile={
                "username": "agent@example.com",
                "user": {"id": "agent-1", "role": "agent", "username": "agent@example.com"},
                "deployer_auth": {"token": "agent-secret-token", "role": "agent"},
                "api_key": "sk-agent-old",
            },
            updates={
                "api_key": "sk-buyer-live",
                "model": "gpt-5.4",
            },
            contexts=contexts,
            default_base_url="https://aitokenapi.cc",
            default_model="gpt-5.4",
        )

        text = str(payload)
        self.assertNotIn("agent@example.com", text)
        self.assertNotIn("agent-secret-token", text)
        self.assertEqual(payload["username"], "")
        self.assertEqual(payload["user"], {})
        self.assertEqual(payload["deployer_auth"], {})
        self.assertEqual(payload["api_key"], "sk-buyer-live")

    def test_profile_payload_never_persists_restorable_login_token(self) -> None:
        buyer_contexts = create_buyer_contexts(
            UserContext(user_id="buyer-1", display_name="buyer@example.com", role="buyer")
        )

        payload = build_persistent_profile_payload(
            current_profile={
                "username": "old@example.com",
                "user": {"id": "old-buyer", "role": "buyer"},
                "deployer_auth": {"token": "old-token", "role": "buyer"},
            },
            updates={
                "username": "buyer@example.com",
                "user": {"id": "buyer-1", "role": "buyer", "username": "buyer@example.com"},
                "deployer_auth": {"token": "buyer-secret-token", "role": "buyer"},
                "api_key": "sk-buyer-live",
                "model": "gpt-5.4",
                "skip_test": True,
                "open_app": False,
            },
            contexts=buyer_contexts,
            default_base_url="https://aitokenapi.cc",
            default_model="gpt-5.4",
        )

        text = str(payload)
        self.assertEqual(payload["username"], "buyer@example.com")
        self.assertEqual(payload["user"], {})
        self.assertEqual(payload["deployer_auth"], {})
        self.assertNotIn("buyer-secret-token", text)
        self.assertNotIn("old-token", text)
        self.assertEqual(payload["api_key"], "sk-buyer-live")
        self.assertTrue(payload["skip_test"])
        self.assertFalse(payload["open_app"])

    def test_web_profile_contract_separates_buyer_and_ephemeral_agent_assist(self) -> None:
        buyer_contexts = create_buyer_contexts(UserContext(user_id="buyer-1", display_name="买家", role="buyer"))
        buyer_profile = create_commercial_web_profile(buyer_contexts, "root")
        assist_contexts = create_agent_assist_contexts(
            UserContext(user_id="agent-1", display_name="代理", role="agent"),
            UserContext(user_id="buyer-1", display_name="买家", role="buyer"),
            assist_session_id="assist-1",
        )
        assist_profile = create_commercial_web_profile(assist_contexts, "root")

        self.assertIsInstance(buyer_profile, CommercialWebProfile)
        self.assertFalse(buyer_profile.ephemeral)
        self.assertTrue(assist_profile.ephemeral)
        self.assertNotEqual(buyer_profile.profile_key, assist_profile.profile_key)
        self.assertNotIn("agent-1", assist_profile.profile_key)
        self.assertNotIn("buyer-1", assist_profile.profile_key)

    def test_manifest_capabilities_pause_non_full_config_agents(self) -> None:
        manifest = {
            "agents": [
                {"id": "codex", "delivery_scope": "full_config", "full_config_allowed": True},
                {"id": "claude_code", "delivery_scope": "install_guided", "full_config_allowed": False},
                {"id": "openclaw", "delivery_scope": "hidden", "full_config_allowed": False},
            ]
        }

        capabilities = build_commercial_agent_capabilities(manifest)

        self.assertEqual(capabilities["codex"].delivery_scope, DeliveryScope.FULL_CONFIG)
        self.assertTrue(capabilities["codex"].can_sell_full_config)
        self.assertFalse(capabilities["claude_code"].can_sell_full_config)
        self.assertFalse(capabilities["openclaw"].is_visible)

    def test_hidden_and_paused_agents_block_deployment(self) -> None:
        capabilities = build_commercial_agent_capabilities(
            {
                "agents": [
                    {"id": "codex", "delivery_scope": "full_config", "full_config_allowed": True},
                    {"id": "openclaw", "delivery_scope": "hidden", "full_config_allowed": False},
                    {"id": "hermes", "delivery_scope": "paused", "full_config_allowed": False},
                ]
            }
        )

        blockers = commercial_deployment_blockers(["codex", "openclaw", "hermes"], capabilities)

        self.assertEqual(blockers, ["openclaw 当前已隐藏，不能部署。", "hermes 当前已暂停，不能部署。"])

    def test_non_full_config_agents_block_paid_deployment_before_install(self) -> None:
        capabilities = build_commercial_agent_capabilities(
            {
                "agents": [
                    {"id": "claude_code", "delivery_scope": "install_guided", "full_config_allowed": False},
                    {"id": "openclaw", "delivery_scope": "guide_only", "full_config_allowed": False},
                    {"id": "hermes", "delivery_scope": "official_entry_only", "full_config_allowed": False},
                ]
            }
        )

        blockers = commercial_deployment_blockers(["claude_code", "openclaw", "hermes"], capabilities)

        self.assertEqual(
            blockers,
            [
                "claude_code 当前未开放完整配置交付，不能作为付费部署。",
                "openclaw 当前未开放完整配置交付，不能作为付费部署。",
                "hermes 当前未开放完整配置交付，不能作为付费部署。",
            ],
        )

    def test_agent_customer_state_reflects_commercial_visibility_and_sellability(self) -> None:
        capabilities = build_commercial_agent_capabilities(
            {
                "agents": [
                    {"id": "codex", "delivery_scope": "full_config", "full_config_allowed": True},
                    {"id": "openclaw", "delivery_scope": "hidden", "full_config_allowed": False},
                    {"id": "hermes", "delivery_scope": "paused", "full_config_allowed": False},
                ]
            }
        )

        codex = build_agent_customer_state("codex", capabilities, commercial_manifest_present=True)
        openclaw = build_agent_customer_state("openclaw", capabilities, commercial_manifest_present=True)
        hermes = build_agent_customer_state("hermes", capabilities, commercial_manifest_present=True)

        self.assertTrue(codex.selectable)
        self.assertIn("完整配置", codex.badge)
        self.assertFalse(openclaw.visible)
        self.assertFalse(openclaw.selectable)
        self.assertFalse(hermes.selectable)
        self.assertIn("暂停", hermes.badge)

    def test_agent_customer_state_explains_matrix_gate_before_full_delivery(self) -> None:
        capabilities = build_commercial_agent_capabilities(
            {
                "agents": [
                    {"id": "openclaw", "delivery_scope": "official_entry_only", "full_config_allowed": False},
                ]
            }
        )

        state = build_agent_customer_state("openclaw", capabilities, commercial_manifest_present=True)

        self.assertTrue(state.visible)
        self.assertFalse(state.selectable)
        self.assertIn("功能验收矩阵", state.note)
        self.assertIn("不扣次", state.note)

    def test_agent_customer_state_defaults_to_not_open_without_server_capability_in_commercial_manifest(self) -> None:
        state = build_agent_customer_state("openclaw", {}, commercial_manifest_present=True)

        self.assertTrue(state.visible)
        self.assertFalse(state.selectable)
        self.assertIn("未开放", state.badge)
        self.assertIn("服务端", state.note)

    def test_agent_customer_state_keeps_legacy_compatibility_before_commercial_manifest_loads(self) -> None:
        state = build_agent_customer_state("codex", {}, commercial_manifest_present=False)

        self.assertTrue(state.visible)
        self.assertTrue(state.selectable)
        self.assertIn("兼容", state.badge)

    def test_commercial_entry_cards_show_unified_login_and_agent_center_only(self) -> None:
        entries = build_commercial_entry_cards()

        self.assertEqual([entry.entry_id for entry in entries], [
            CommercialEntryId.BUYER_SELF_SERVICE,
            CommercialEntryId.AGENT_CENTER,
        ])
        self.assertTrue(all(isinstance(entry, CommercialEntry) for entry in entries))
        self.assertIn("账号", entries[0].title)
        self.assertIn("代理中心", entries[1].title)
        self.assertNotIn(CommercialEntryId.AGENT_ASSIST, [entry.entry_id for entry in entries])

    def test_legacy_agent_assist_structures_are_marked_for_compatibility_only(self) -> None:
        source = (ROOT / "src" / "commercial_core.py").read_text(encoding="utf-8")

        self.assertIn("Legacy compatibility structure", source)
        self.assertIn("Legacy compatibility factory", source)
        self.assertIn("Legacy customer entry id kept only for compatibility", source)

    def test_agent_center_summary_requires_server_snapshot(self) -> None:
        lines = build_agent_center_summary_lines({})

        self.assertEqual(lines, ["代理中心：服务端暂未开放，请以后台开关为准。"])

    def test_agent_center_summary_uses_server_snapshot_without_commission_defaults(self) -> None:
        lines = build_agent_center_summary_lines(
            {
                "agent_center": {
                    "enabled": True,
                    "current_level": "L2",
                    "upgrade_label": "升级到 L3",
                    "invite_url": "https://aitokenapi.cc/invite/abc",
                    "commission_ratio": "30%",
                    "benefits": ["可查看直推订单", "可绑定新买家"],
                    "boundaries": ["收益以后台结算账本为准"],
                }
            }
        )
        text = "\n".join(lines)

        self.assertIn("当前等级：L2", text)
        self.assertIn("升级入口：升级到 L3", text)
        self.assertIn("邀请入口：已开放", text)
        self.assertIn("可绑定新买家", text)
        self.assertIn("后台结算账本", text)
        self.assertNotIn("30%", text)

    def test_node_status_rows_are_customer_safe_and_ordered(self) -> None:
        progress = DeploymentProgress()
        progress.mark(DeploymentNode.LOGIN, NodeStatus.PASS)
        progress.mark(DeploymentNode.ENTITLEMENT, NodeStatus.BLOCKED)
        rows = build_node_status_rows(progress)

        self.assertEqual([row.node for row in rows[:3]], [
            DeploymentNode.LOGIN,
            DeploymentNode.ENTITLEMENT,
            DeploymentNode.API_KEY,
        ])
        entitlement_row = rows[1]
        self.assertEqual(entitlement_row.status, NodeStatus.BLOCKED)
        self.assertIn("权益", entitlement_row.title)
        self.assertNotIn("ConfigSession", entitlement_row.customer_message)

    def test_product_catalog_uses_server_snapshot_without_client_pricing_defaults(self) -> None:
        manifest = {
            "products": [
                {
                    "product_id": "prod-codex-basic",
                    "title": "Codex 普通配置",
                    "agent_id": "codex",
                    "mode_key": "direct_api",
                    "delivery_scope": "full_config",
                    "price_cents": 9900,
                    "currency": "CNY",
                    "remaining_uses": 3,
                    "valid_until": "2026-12-31T23:59:59+08:00",
                    "includes_dual_state": False,
                    "device_limit": 1,
                    "is_listed": True,
                }
            ]
        }

        catalog = build_commercial_product_catalog(manifest)

        self.assertEqual(len(catalog), 1)
        product = catalog[0]
        self.assertIsInstance(product, CommercialProduct)
        self.assertEqual(product.price_cents, 9900)
        self.assertEqual(product.remaining_uses, 3)
        self.assertFalse(product.includes_dual_state)

    def test_product_catalog_parses_backend_rollout_gates(self) -> None:
        manifest = {
            "products": [
                {
                    "product_id": "prod-codex-gray",
                    "title": "Codex 灰度配置",
                    "agent_id": "codex",
                    "mode_key": "direct_api",
                    "delivery_scope": "full_config",
                    "price_cents": 9900,
                    "currency": "CNY",
                    "remaining_uses": 1,
                    "valid_until": "2026-12-31T23:59:59+08:00",
                    "includes_dual_state": False,
                    "device_limit": 1,
                    "is_listed": True,
                    "min_client_version": "1.0.15",
                    "allowed_buyer_user_ids": ["buyer-1", ""],
                }
            ]
        }

        catalog = build_commercial_product_catalog(manifest)

        self.assertEqual(len(catalog), 1)
        self.assertEqual(catalog[0].min_client_version, "1.0.15")
        self.assertEqual(catalog[0].allowed_buyer_user_ids, ("buyer-1",))

    def test_product_catalog_skips_incomplete_server_product_instead_of_defaulting_commercial_rules(self) -> None:
        catalog = build_commercial_product_catalog(
            {
                "products": [
                    {
                        "product_id": "prod-incomplete",
                        "title": "缺字段商品",
                        "agent_id": "codex",
                        "mode_key": "direct_api",
                        "delivery_scope": "full_config",
                    }
                ]
            }
        )

        self.assertEqual(catalog, [])

    def test_product_catalog_skips_products_missing_customer_visible_contract_fields(self) -> None:
        base_product = {
            "product_id": "prod-codex-basic",
            "title": "Codex 普通配置",
            "agent_id": "codex",
            "mode_key": "direct_api",
            "delivery_scope": "full_config",
            "price_cents": 9900,
            "currency": "CNY",
            "remaining_uses": 3,
            "valid_until": "2026-12-31T23:59:59+08:00",
            "device_limit": 1,
            "is_listed": True,
        }

        for required_field in ("title", "agent_id", "mode_key", "delivery_scope", "currency", "valid_until"):
            product = dict(base_product)
            product[required_field] = ""

            catalog = build_commercial_product_catalog({"products": [product]})

            self.assertEqual(catalog, [], required_field)

    def test_product_catalog_skips_products_missing_explicit_listing_state(self) -> None:
        product = {
            "product_id": "prod-codex-basic",
            "title": "Codex 普通配置",
            "agent_id": "codex",
            "mode_key": "direct_api",
            "delivery_scope": "full_config",
            "price_cents": 9900,
            "currency": "CNY",
            "remaining_uses": 3,
            "valid_until": "2026-12-31T23:59:59+08:00",
            "device_limit": 1,
        }

        catalog = build_commercial_product_catalog({"products": [product]})

        self.assertEqual(catalog, [])

    def test_product_catalog_skips_invalid_numeric_commercial_contract_values(self) -> None:
        base_product = {
            "product_id": "prod-codex-basic",
            "title": "Codex 普通配置",
            "agent_id": "codex",
            "mode_key": "direct_api",
            "delivery_scope": "full_config",
            "price_cents": 9900,
            "currency": "CNY",
            "remaining_uses": 3,
            "valid_until": "2026-12-31T23:59:59+08:00",
            "device_limit": 1,
            "is_listed": True,
        }

        invalid_cases = {
            "price_cents": -1,
            "remaining_uses": 0,
            "device_limit": 0,
        }
        for field, value in invalid_cases.items():
            product = dict(base_product)
            product[field] = value

            catalog = build_commercial_product_catalog({"products": [product]})

            self.assertEqual(catalog, [], field)

    def test_product_catalog_accepts_explicit_unlimited_server_product_without_client_defaults(self) -> None:
        manifest = {
            "products": [
                {
                    "product_id": "prod-codex-unlimited",
                    "title": "Codex 不限次配置",
                    "agent_id": "codex",
                    "mode_key": "direct_api",
                    "delivery_scope": "full_config",
                    "price_cents": 29900,
                    "currency": "CNY",
                    "remaining_uses": 0,
                    "is_unlimited": True,
                    "valid_until": "2026-12-31T23:59:59+08:00",
                    "device_limit": 1,
                    "is_listed": True,
                }
            ]
        }

        catalog = build_commercial_product_catalog(manifest)

        self.assertEqual(len(catalog), 1)
        self.assertTrue(catalog[0].is_unlimited)
        self.assertEqual(catalog[0].remaining_uses, 0)

    def test_find_listed_product_requires_server_listed_full_config_match(self) -> None:
        products = [
            CommercialProduct(
                product_id="hidden",
                title="隐藏商品",
                agent_id="codex",
                mode_key="direct_api",
                delivery_scope=DeliveryScope.FULL_CONFIG,
                price_cents=9900,
                currency="CNY",
                remaining_uses=1,
                valid_until="2026-12-31",
                includes_dual_state=False,
                device_limit=1,
                is_listed=False,
            ),
            CommercialProduct(
                product_id="listed",
                title="可售商品",
                agent_id="codex",
                mode_key="direct_api",
                delivery_scope=DeliveryScope.FULL_CONFIG,
                price_cents=9900,
                currency="CNY",
                remaining_uses=1,
                valid_until="2026-12-31",
                includes_dual_state=False,
                device_limit=1,
                is_listed=True,
            ),
        ]

        product = find_listed_product(products, agent_id="codex", mode_key="direct_api")

        self.assertIsNotNone(product)
        self.assertEqual(product.product_id, "listed")
        self.assertIsNone(find_listed_product(products, agent_id="hermes", mode_key="direct_api"))

    def test_find_orderable_product_requires_product_id_agent_mode_and_listing_match(self) -> None:
        products = [
            CommercialProduct(
                product_id="hidden",
                title="隐藏商品",
                agent_id="codex",
                mode_key="direct_api",
                delivery_scope=DeliveryScope.FULL_CONFIG,
                price_cents=9900,
                currency="CNY",
                remaining_uses=1,
                valid_until="2026-12-31",
                includes_dual_state=False,
                device_limit=1,
                is_listed=False,
            ),
            CommercialProduct(
                product_id="dual",
                title="双态商品",
                agent_id="codex",
                mode_key="dual_state",
                delivery_scope=DeliveryScope.FULL_CONFIG,
                price_cents=9900,
                currency="CNY",
                remaining_uses=1,
                valid_until="2026-12-31",
                includes_dual_state=True,
                device_limit=1,
                is_listed=True,
            ),
            CommercialProduct(
                product_id="direct",
                title="普通商品",
                agent_id="codex",
                mode_key="direct_api",
                delivery_scope=DeliveryScope.FULL_CONFIG,
                price_cents=9900,
                currency="CNY",
                remaining_uses=1,
                valid_until="2026-12-31",
                includes_dual_state=False,
                device_limit=1,
                is_listed=True,
            ),
        ]

        product = find_orderable_product(products, product_id="direct", agent_id="codex", mode_key="direct_api")

        self.assertIsNotNone(product)
        self.assertEqual(product.product_id, "direct")
        self.assertIsNone(find_orderable_product(products, product_id="dual", agent_id="codex", mode_key="direct_api"))
        self.assertIsNone(find_orderable_product(products, product_id="hidden", agent_id="codex", mode_key="direct_api"))
        self.assertIsNone(find_orderable_product(products, product_id="direct", agent_id="hermes", mode_key="direct_api"))

    def test_product_ordering_respects_min_client_version_and_gray_buyer_list(self) -> None:
        products = [
            CommercialProduct(
                product_id="gated",
                title="灰度商品",
                agent_id="codex",
                mode_key="direct_api",
                delivery_scope=DeliveryScope.FULL_CONFIG,
                price_cents=9900,
                currency="CNY",
                remaining_uses=1,
                valid_until="2026-12-31",
                includes_dual_state=False,
                device_limit=1,
                is_listed=True,
                min_client_version="1.0.15",
                allowed_buyer_user_ids=("buyer-allowed",),
            ),
        ]

        self.assertIsNone(
            find_orderable_product(
                products,
                product_id="gated",
                agent_id="codex",
                mode_key="direct_api",
                app_version="1.0.14",
                buyer_user_id="buyer-allowed",
            )
        )
        self.assertIsNone(
            find_orderable_product(
                products,
                product_id="gated",
                agent_id="codex",
                mode_key="direct_api",
                app_version="1.0.15",
                buyer_user_id="buyer-other",
            )
        )
        product = find_orderable_product(
            products,
            product_id="gated",
            agent_id="codex",
            mode_key="direct_api",
            app_version="1.0.15",
            buyer_user_id="buyer-allowed",
        )

        self.assertIsNotNone(product)

    def test_entitlement_and_config_session_contract_keep_buyer_owner_and_diagnostic_code(self) -> None:
        entitlement = EntitlementContract(
            entitlement_id="ent-1",
            buyer_user_id="buyer-1",
            agent_id="codex",
            mode_key="direct_api",
            remaining_uses=1,
            valid_until="2026-12-31T23:59:59+08:00",
            delivery_scope=DeliveryScope.FULL_CONFIG,
            includes_dual_state=False,
            device_limit=1,
            status="active",
        )
        session = ConfigSessionContract(
            config_session_id="cfg-1",
            buyer_user_id="buyer-1",
            operator_user_id="agent-1",
            entitlement_id="ent-1",
            agent_id="codex",
            mode_key="direct_api",
            diagnostic_code="PH-CFG-20260621-0001",
            progress=DeploymentProgress(),
        )

        self.assertEqual(entitlement.buyer_user_id, session.buyer_user_id)
        self.assertEqual(session.operator_user_id, "agent-1")
        self.assertFalse(session.can_commit_success())
        session.progress.mark(DeploymentNode.REAL_TASK_VERIFY, NodeStatus.PASS)
        self.assertTrue(session.can_commit_success())

    def test_real_task_verification_is_required_for_success_commit(self) -> None:
        progress = DeploymentProgress()
        progress.mark(DeploymentNode.INSTALL, NodeStatus.PASS)
        progress.mark(DeploymentNode.CONFIG_WRITE, NodeStatus.PASS)
        progress.mark(DeploymentNode.LAUNCH_VERIFY, NodeStatus.PASS)

        self.assertFalse(progress.can_commit_success())

        progress.mark(DeploymentNode.REAL_TASK_VERIFY, NodeStatus.PASS)

        self.assertTrue(progress.can_commit_success())

    def test_real_task_evidence_requires_request_and_response_before_success(self) -> None:
        missing_response = verify_real_task_evidence(
            diagnostic_code="PH-CFG-1",
            agent_id="codex",
            mode_key="direct_api",
            request_ok=True,
            response_ok=False,
            response_excerpt="",
        )

        self.assertFalse(missing_response.passed)
        self.assertEqual(missing_response.status, NodeStatus.FAILED)
        self.assertIn("真实任务", missing_response.customer_message)

        passed = verify_real_task_evidence(
            diagnostic_code="PH-CFG-2",
            agent_id="codex",
            mode_key="direct_api",
            request_ok=True,
            response_ok=True,
            response_excerpt="你好，配置已生效。",
        )

        self.assertTrue(passed.passed)
        self.assertEqual(passed.status, NodeStatus.PASS)
        self.assertIn("PH-CFG-2", passed.diagnostic_code)
        self.assertIsInstance(passed, RealTaskVerificationResult)

    def test_config_session_terminal_action_fails_any_reserved_incomplete_flow(self) -> None:
        progress = DeploymentProgress()
        progress.mark(DeploymentNode.INSTALL, NodeStatus.FAILED)

        self.assertEqual(config_session_terminal_action(progress, reserved=True), "fail")

        progress = DeploymentProgress()
        progress.mark(DeploymentNode.INSTALL, NodeStatus.PASS)
        progress.mark(DeploymentNode.CONFIG_WRITE, NodeStatus.PASS)
        progress.mark(DeploymentNode.REAL_TASK_VERIFY, NodeStatus.PASS)

        self.assertEqual(config_session_terminal_action(progress, reserved=True), "complete")
        self.assertEqual(config_session_terminal_action(progress, reserved=False), "none")

    def test_real_task_diagnostic_summary_masks_sensitive_response_text(self) -> None:
        result = RealTaskVerificationResult(
            diagnostic_code="PH-CFG-3",
            agent_id="codex",
            mode_key="direct_api",
            passed=False,
            status=NodeStatus.FAILED,
            customer_message="真实任务验证失败。",
            response_excerpt="sk-secret-token should not leak",
        )

        summary = build_real_task_diagnostic_summary(result, api_key="sk-secret-token")

        self.assertIn("PH-CFG-3", summary)
        self.assertIn("Codex", summary)
        self.assertNotIn("sk-secret-token", summary)

    def test_support_diagnostic_packet_is_customer_safe(self) -> None:
        progress = DeploymentProgress()
        progress.mark(DeploymentNode.INSTALL, NodeStatus.PASS)
        progress.mark(DeploymentNode.CONFIG_WRITE, NodeStatus.FAILED)

        packet = build_support_diagnostic_packet(
            diagnostic_code="PH-CFG-1",
            progress=progress,
            agent_id="codex",
            mode_key="direct_api",
            customer_message="配置写入失败，已恢复备份。",
            api_key="sk-secret-token",
            commercial_ids=["ent-real", "cfg-real"],
        )

        self.assertIn("PH-CFG-1", packet)
        self.assertIn("安装 Agent", packet)
        self.assertIn("配置写入", packet)
        self.assertNotIn("sk-secret-token", packet)
        self.assertNotIn("ent-real", packet)
        self.assertNotIn("cfg-real", packet)

    def test_support_diagnostic_packet_sanitizes_sensitive_customer_message(self) -> None:
        progress = DeploymentProgress()
        progress.mark(DeploymentNode.API_KEY, NodeStatus.FAILED)

        packet = build_support_diagnostic_packet(
            diagnostic_code="PH-CFG-SAFE",
            progress=progress,
            agent_id="codex",
            mode_key="direct_api",
            customer_message=(
                "代理 user@example.com 手机 13800138000 token secret-token "
                "api_key=sk-live-secret order_id=ord-real invite_code INVITE-SECRET "
                "config_session_id cfg-real Authorization: Bearer bearer-secret-token"
            ),
            api_key="sk-live-secret",
            commercial_ids=["ord-real", "cfg-real"],
        )

        self.assertNotIn("user@example.com", packet)
        self.assertNotIn("13800138000", packet)
        self.assertNotIn("secret-token", packet)
        self.assertNotIn("sk-live-secret", packet)
        self.assertNotIn("ord-real", packet)
        self.assertNotIn("INVITE-SECRET", packet)
        self.assertNotIn("cfg-real", packet)
        self.assertNotIn("bearer-secret-token", packet)
        self.assertIn("***", packet)

    def test_customer_diagnostic_sanitizer_masks_assist_and_auth_token_fields(self) -> None:
        message = (
            "assist_session_id assist-real-001 access_token=access-secret "
            "refresh_token:refresh-secret"
        )

        safe = sanitize_customer_diagnostic_text(message)

        self.assertNotIn("assist-real-001", safe)
        self.assertNotIn("access-secret", safe)
        self.assertNotIn("refresh-secret", safe)
        self.assertIn("***", safe)

    def test_entitlement_summary_rows_hide_internal_contract_fields(self) -> None:
        entitlements = [
            EntitlementContract(
                entitlement_id="ent-1",
                buyer_user_id="buyer-1",
                agent_id="codex",
                mode_key="direct_api",
                remaining_uses=2,
                valid_until="2026-12-31T23:59:59+08:00",
                delivery_scope=DeliveryScope.FULL_CONFIG,
                includes_dual_state=False,
                device_limit=1,
                status="active",
            )
        ]

        rows = build_entitlement_summary_rows(entitlements)

        self.assertEqual(len(rows), 1)
        row_text = " ".join(rows[0])
        self.assertIn("Codex", row_text)
        self.assertIn("普通模式", row_text)
        self.assertIn("可用", row_text)
        self.assertIn("2次", row_text)
        self.assertNotIn("ent-1", row_text)
        self.assertNotIn("buyer-1", row_text)

    def test_entitlement_summary_rows_show_paid_or_trial_source_without_internal_ids(self) -> None:
        entitlements = [
            EntitlementContract(
                entitlement_id="ent-paid-secret",
                buyer_user_id="buyer-secret",
                agent_id="codex",
                mode_key="direct_api",
                remaining_uses=1,
                valid_until="2026-12-31T23:59:59+08:00",
                delivery_scope=DeliveryScope.FULL_CONFIG,
                includes_dual_state=False,
                device_limit=1,
                status="active",
                source="paid",
            ),
            EntitlementContract(
                entitlement_id="ent-trial-secret",
                buyer_user_id="buyer-secret",
                agent_id="codex",
                mode_key="direct_api",
                remaining_uses=1,
                valid_until="2026-12-31T23:59:59+08:00",
                delivery_scope=DeliveryScope.FULL_CONFIG,
                includes_dual_state=False,
                device_limit=1,
                status="active",
                source="trial",
            ),
        ]

        text = "\n".join(" ".join(row) for row in build_entitlement_summary_rows(entitlements))

        self.assertIn("付费权益", text)
        self.assertIn("试用权益", text)
        self.assertNotIn("ent-paid-secret", text)
        self.assertNotIn("ent-trial-secret", text)
        self.assertNotIn("buyer-secret", text)

    def test_entitlement_summary_never_marks_negative_remaining_uses_as_unlimited(self) -> None:
        entitlements = [
            EntitlementContract(
                entitlement_id="ent-bad",
                buyer_user_id="buyer-1",
                agent_id="codex",
                mode_key="direct_api",
                remaining_uses=-1,
                valid_until="2026-12-31T23:59:59+08:00",
                delivery_scope=DeliveryScope.FULL_CONFIG,
                includes_dual_state=False,
                device_limit=1,
                status="active",
            )
        ]

        rows = build_entitlement_summary_rows(entitlements)

        row_text = " ".join(rows[0])
        self.assertIn("次数已用完", row_text)
        self.assertNotIn("不限次", row_text)

    def test_unlimited_entitlement_uses_explicit_server_flag(self) -> None:
        entitlements = [
            EntitlementContract(
                entitlement_id="ent-unlimited",
                buyer_user_id="buyer-1",
                agent_id="codex",
                mode_key="direct_api",
                remaining_uses=0,
                valid_until="2026-12-31T23:59:59+08:00",
                delivery_scope=DeliveryScope.FULL_CONFIG,
                includes_dual_state=False,
                device_limit=1,
                status="active",
                is_unlimited=True,
            )
        ]

        rows = build_entitlement_summary_rows(entitlements)
        entitlement = find_usable_entitlement(entitlements, agent_id="codex", mode_key="direct_api")

        self.assertEqual(entitlement.entitlement_id, "ent-unlimited")
        self.assertIn("不限次", " ".join(rows[0]))

    def test_find_usable_entitlement_requires_active_matching_remaining_full_config(self) -> None:
        entitlements = [
            EntitlementContract(
                entitlement_id="paused",
                buyer_user_id="buyer-1",
                agent_id="codex",
                mode_key="direct_api",
                remaining_uses=3,
                valid_until="2026-12-31T23:59:59+08:00",
                delivery_scope=DeliveryScope.PAUSED,
                includes_dual_state=False,
                device_limit=1,
                status="active",
            ),
            EntitlementContract(
                entitlement_id="used",
                buyer_user_id="buyer-1",
                agent_id="codex",
                mode_key="direct_api",
                remaining_uses=0,
                valid_until="2026-12-31T23:59:59+08:00",
                delivery_scope=DeliveryScope.FULL_CONFIG,
                includes_dual_state=False,
                device_limit=1,
                status="active",
            ),
            EntitlementContract(
                entitlement_id="backend-rejected-unlimited",
                buyer_user_id="buyer-1",
                agent_id="codex",
                mode_key="direct_api",
                remaining_uses=-1,
                valid_until="2026-12-31T23:59:59+08:00",
                delivery_scope=DeliveryScope.FULL_CONFIG,
                includes_dual_state=False,
                device_limit=1,
                status="active",
            ),
            EntitlementContract(
                entitlement_id="usable",
                buyer_user_id="buyer-1",
                agent_id="codex",
                mode_key="direct_api",
                remaining_uses=1,
                valid_until="2026-12-31T23:59:59+08:00",
                delivery_scope=DeliveryScope.FULL_CONFIG,
                includes_dual_state=False,
                device_limit=1,
                status="active",
            ),
        ]

        entitlement = find_usable_entitlement(entitlements, agent_id="codex", mode_key="direct_api")

        self.assertIsNotNone(entitlement)
        self.assertEqual(entitlement.entitlement_id, "usable")
        self.assertIsNone(find_usable_entitlement(entitlements, agent_id="claude_code", mode_key="direct_api"))

    def test_find_usable_entitlement_blocks_expired_server_entitlement_snapshot(self) -> None:
        entitlements = [
            EntitlementContract(
                entitlement_id="expired",
                buyer_user_id="buyer-1",
                agent_id="codex",
                mode_key="direct_api",
                remaining_uses=1,
                valid_until="2020-01-01T00:00:00+08:00",
                delivery_scope=DeliveryScope.FULL_CONFIG,
                includes_dual_state=False,
                device_limit=1,
                status="active",
            )
        ]

        entitlement = find_usable_entitlement(entitlements, agent_id="codex", mode_key="direct_api")

        self.assertIsNone(entitlement)

    def test_find_orderable_product_blocks_expired_server_product_snapshot(self) -> None:
        products = [
            CommercialProduct(
                product_id="expired-product",
                title="过期商品",
                agent_id="codex",
                mode_key="direct_api",
                delivery_scope=DeliveryScope.FULL_CONFIG,
                price_cents=9900,
                currency="CNY",
                remaining_uses=1,
                valid_until="2020-01-01T00:00:00+08:00",
                includes_dual_state=False,
                device_limit=1,
                is_listed=True,
            )
        ]

        product = find_orderable_product(products, product_id="expired-product", agent_id="codex", mode_key="direct_api")

        self.assertIsNone(product)

    def test_commercial_config_gate_blocks_without_active_entitlement(self) -> None:
        capabilities = build_commercial_agent_capabilities(
            {"agents": [{"id": "codex", "delivery_scope": "full_config", "full_config_allowed": True}]}
        )

        decision = commercial_config_gate(
            agent_id="codex",
            mode_key="direct_api",
            capabilities=capabilities,
            entitlements=[],
            commercial_manifest_present=True,
        )

        self.assertFalse(decision.allowed)
        self.assertIn("没有可用权益", decision.message)

    def test_commercial_config_gate_blocks_missing_agent_capability_when_commercial_manifest_present(self) -> None:
        decision = commercial_config_gate(
            agent_id="openclaw",
            mode_key="cli",
            capabilities={},
            entitlements=[],
            commercial_manifest_present=True,
        )

        self.assertFalse(decision.allowed)
        self.assertIn("服务端未开放", decision.message)

    def test_commercial_config_gate_blocks_hidden_or_paused_delivery_even_with_entitlement(self) -> None:
        capabilities = build_commercial_agent_capabilities(
            {"agents": [{"id": "openclaw", "delivery_scope": "hidden", "full_config_allowed": False}]}
        )
        entitlement = EntitlementContract(
            entitlement_id="ent-1",
            buyer_user_id="buyer-1",
            agent_id="openclaw",
            mode_key="cli",
            remaining_uses=1,
            valid_until="2026-12-31T23:59:59+08:00",
            delivery_scope=DeliveryScope.FULL_CONFIG,
            includes_dual_state=False,
            device_limit=1,
            status="active",
        )

        decision = commercial_config_gate(
            agent_id="openclaw",
            mode_key="cli",
            capabilities=capabilities,
            entitlements=[entitlement],
            commercial_manifest_present=True,
        )

        self.assertFalse(decision.allowed)
        self.assertIn("隐藏", decision.message)

    def test_commercial_config_gate_allows_active_entitled_codex_full_config(self) -> None:
        capabilities = build_commercial_agent_capabilities(
            {"agents": [{"id": "codex", "delivery_scope": "full_config", "full_config_allowed": True}]}
        )
        entitlement = EntitlementContract(
            entitlement_id="ent-1",
            buyer_user_id="buyer-1",
            agent_id="codex",
            mode_key="direct_api",
            remaining_uses=1,
            valid_until="2026-12-31T23:59:59+08:00",
            delivery_scope=DeliveryScope.FULL_CONFIG,
            includes_dual_state=False,
            device_limit=1,
            status="active",
        )

        decision = commercial_config_gate(
            agent_id="codex",
            mode_key="direct_api",
            capabilities=capabilities,
            entitlements=[entitlement],
            commercial_manifest_present=True,
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.entitlement_id, "ent-1")

    def test_customer_commercial_summary_lines_are_customer_safe(self) -> None:
        products = [
            CommercialProduct(
                product_id="prod-1",
                title="Codex 普通配置",
                agent_id="codex",
                mode_key="direct_api",
                delivery_scope=DeliveryScope.FULL_CONFIG,
                price_cents=9900,
                currency="CNY",
                remaining_uses=3,
                valid_until="2026-12-31",
                includes_dual_state=False,
                device_limit=1,
                is_listed=True,
            )
        ]
        entitlements = [
            EntitlementContract(
                entitlement_id="ent-secret",
                buyer_user_id="buyer-secret",
                agent_id="codex",
                mode_key="direct_api",
                remaining_uses=1,
                valid_until="2026-12-31",
                delivery_scope=DeliveryScope.FULL_CONFIG,
                includes_dual_state=False,
                device_limit=1,
                status="active",
            )
        ]

        lines = build_customer_commercial_summary_lines(products, entitlements)
        text = "\n".join(lines)

        self.assertIn("服务端商品", text)
        self.assertIn("Codex 普通配置", text)
        self.assertIn("可用权益", text)
        self.assertIn("1次", text)
        self.assertNotIn("ent-secret", text)
        self.assertNotIn("buyer-secret", text)

    def test_customer_commercial_summary_does_not_mark_unlimited_entitlement_used_up(self) -> None:
        entitlements = [
            EntitlementContract(
                entitlement_id="ent-unlimited",
                buyer_user_id="buyer-1",
                agent_id="codex",
                mode_key="direct_api",
                remaining_uses=0,
                valid_until="2026-12-31",
                delivery_scope=DeliveryScope.FULL_CONFIG,
                includes_dual_state=False,
                device_limit=1,
                status="active",
                is_unlimited=True,
            )
        ]

        text = "\n".join(build_customer_commercial_summary_lines([], entitlements))

        self.assertIn("不限次", text)
        self.assertIn("可用", text)
        self.assertNotIn("已用完", text)

    def test_customer_delivery_verdict_explains_success_and_deduction(self) -> None:
        progress = DeploymentProgress()
        progress.mark(DeploymentNode.LOGIN, NodeStatus.PASS)
        progress.mark(DeploymentNode.ENTITLEMENT, NodeStatus.PASS)
        progress.mark(DeploymentNode.CONFIG_WRITE, NodeStatus.PASS)
        progress.mark(DeploymentNode.REAL_TASK_VERIFY, NodeStatus.PASS)

        verdict = build_customer_delivery_verdict(progress, reserved=True, diagnostic_code="PH-CFG-1")

        self.assertEqual(verdict.status, NodeStatus.PASS)
        self.assertTrue(verdict.deduct_entitlement)
        self.assertIn("可以扣次", verdict.customer_message)
        self.assertIn("PH-CFG-1", verdict.customer_message)

    def test_customer_delivery_verdict_explains_failure_without_deduction(self) -> None:
        progress = DeploymentProgress()
        progress.mark(DeploymentNode.LOGIN, NodeStatus.PASS)
        progress.mark(DeploymentNode.CONFIG_WRITE, NodeStatus.PASS)
        progress.mark(DeploymentNode.REAL_TASK_VERIFY, NodeStatus.FAILED)

        verdict = build_customer_delivery_verdict(progress, reserved=True, diagnostic_code="PH-CFG-2")

        self.assertEqual(verdict.status, NodeStatus.FAILED)
        self.assertFalse(verdict.deduct_entitlement)
        self.assertIn("不扣次", verdict.customer_message)
        self.assertIn("客服", verdict.customer_message)
        self.assertIn("PH-CFG-2", verdict.customer_message)

    def test_customer_delivery_verdict_explains_no_server_session_as_not_deducted(self) -> None:
        progress = DeploymentProgress()
        progress.mark(DeploymentNode.REAL_TASK_VERIFY, NodeStatus.PASS)

        verdict = build_customer_delivery_verdict(progress, reserved=False, diagnostic_code="PH-CFG-3")

        self.assertEqual(verdict.status, NodeStatus.WARNING)
        self.assertFalse(verdict.deduct_entitlement)
        self.assertIn("未获得服务端配置会话", verdict.customer_message)

    def test_customer_delivery_report_unifies_verdict_nodes_and_support_packet(self) -> None:
        progress = DeploymentProgress()
        progress.mark(DeploymentNode.LOGIN, NodeStatus.PASS)
        progress.mark(DeploymentNode.ENTITLEMENT, NodeStatus.PASS)
        progress.mark(DeploymentNode.CONFIG_WRITE, NodeStatus.PASS)
        progress.mark(DeploymentNode.REAL_TASK_VERIFY, NodeStatus.FAILED)

        report = build_customer_delivery_report(
            diagnostic_code="PH-CFG-RPT",
            progress=progress,
            reserved=True,
            agent_id="codex",
            mode_key="direct_api",
            api_key="sk-live-secret",
            commercial_ids=["ent-secret-1", "cfg-secret-1"],
        )

        self.assertEqual(report.diagnostic_code, "PH-CFG-RPT")
        self.assertEqual(report.status, NodeStatus.FAILED)
        self.assertEqual(report.terminal_action, "fail")
        self.assertFalse(report.deduct_entitlement)
        self.assertIn("真实任务验证", report.customer_message)
        self.assertIn("客服诊断包", report.support_packet)
        self.assertIn("PH-CFG-RPT", report.support_packet)
        self.assertNotIn("sk-live-secret", report.support_packet)
        self.assertNotIn("ent-secret-1", report.support_packet)
        self.assertTrue(any(row.title == "真实任务验证" and row.status == NodeStatus.FAILED for row in report.node_rows))

    def test_customer_delivery_report_keeps_no_session_as_none_terminal_action(self) -> None:
        progress = DeploymentProgress()
        progress.mark(DeploymentNode.REAL_TASK_VERIFY, NodeStatus.PASS)

        report = build_customer_delivery_report(
            diagnostic_code="PH-CFG-NOSESSION",
            progress=progress,
            reserved=False,
            agent_id="codex",
            mode_key="direct_api",
        )

        self.assertEqual(report.terminal_action, "none")
        self.assertFalse(report.deduct_entitlement)
        self.assertEqual(report.status, NodeStatus.WARNING)
        self.assertIn("未获得服务端配置会话", report.customer_message)


if __name__ == "__main__":
    unittest.main()
