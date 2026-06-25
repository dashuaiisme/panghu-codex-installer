import unittest
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CommercialBackendContractDocsTests(unittest.TestCase):
    def test_backend_contract_doc_covers_all_p0_commercial_surfaces(self) -> None:
        path = ROOT / "docs" / "COMMERCIAL_BACKEND_API_CONTRACT.md"
        text = path.read_text(encoding="utf-8")

        required_terms = [
            "商品配置",
            "工具订单",
            "支付回调",
            "权益",
            "配置会话",
            "权益预占",
            "真实任务验证",
            "五级代理",
            "返佣账本",
            "订单撤销",
            "佣金冲正",
            "幂等",
            "diagnostic_code",
            "operator_context",
            "target_buyer_context",
            "manifest_signature",
            "manifest_issued_at",
            "commercial_manifest_signer.py",
            "PANGHU_COMMERCIAL_MANIFEST_PUBLIC_KEY_PEM",
            "私钥不得进入客户端",
            "Authorization: Bearer",
            "当前登录买家 token",
            "commercial_flow_acceptance.py",
        ]
        for term in required_terms:
            with self.subTest(term=term):
                self.assertIn(term, text)

    def test_backend_contract_doc_covers_unlimited_and_single_trial_account_rules(self) -> None:
        path = ROOT / "docs" / "COMMERCIAL_BACKEND_API_CONTRACT.md"
        text = path.read_text(encoding="utf-8")

        required_terms = [
            "`is_unlimited`",
            "`remaining_uses=0`",
            "同一买家账号只能领取一次免费试用权益",
            "不能按 Agent 或模式分别重复领取",
        ]
        for term in required_terms:
            with self.subTest(term=term):
                self.assertIn(term, text)

    def test_backend_contract_doc_covers_legacy_agent_login_cleanup(self) -> None:
        path = ROOT / "docs" / "COMMERCIAL_BACKEND_API_CONTRACT.md"
        text = path.read_text(encoding="utf-8")

        required_terms = [
            "历史版本残留的代理登录态不得写入或继续保留在 `profile.json`",
            "旧 `profile.json`",
            "代理身份、代理 token、买家登录 token、`assist_session_id`",
            "启动恢复时不得把旧代理登录态或旧买家 token 当成当前账号",
            "只能恢复账号提示、API Key、模型和界面偏好",
            "真正的登录、授权和部署 token 必须来自本次重新登录",
            "代理身份不再是客户端登录前模式",
        ]
        for term in required_terms:
            with self.subTest(term=term):
                self.assertIn(term, text)

    def test_backend_contract_section_numbers_are_continuous(self) -> None:
        path = ROOT / "docs" / "COMMERCIAL_BACKEND_API_CONTRACT.md"
        text = path.read_text(encoding="utf-8")

        numbers = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\. ", text, re.MULTILINE)]

        self.assertEqual(numbers, list(range(1, max(numbers) + 1)))

    def test_maintenance_manual_documents_release_freshness_gate(self) -> None:
        path = ROOT / "docs" / "TECHNICAL_MAINTENANCE_MANUAL.md"
        text = path.read_text(encoding="utf-8")

        required_terms = [
            "freshness",
            "stale",
            "早于当前源码或构建脚本",
            "packaged_artifact_contents",
            "internal_file_hits",
            "内部维护、测试、源码或签名资料",
            "release_temp_files",
            "release 目录存在临时验证残留",
            "packaged_app_source_files_scanned",
            "客户包商业源码扫描清单",
            "客户 App 运行面",
            "后端合约模拟器",
            "内部验收面",
            "不得进入客户包",
            "non_codex_full_config_delivery_found",
            "未完成配置写入、启动检测、最小对话验证前",
            "胖虎AI-Agent功能验收矩阵.txt",
            "矩阵未通过时必须 fail 配置会话、不扣次",
            "Mac AppleSilicon",
            "Mac Intel",
        ]
        for term in required_terms:
            with self.subTest(term=term):
                self.assertIn(term, text)

    def test_maintenance_manual_documents_ci_commercial_release_contract(self) -> None:
        path = ROOT / "docs" / "TECHNICAL_MAINTENANCE_MANUAL.md"
        text = path.read_text(encoding="utf-8")

        required_terms = [
            "GitHub Actions 必须配置 `PANGHU_COMMERCIAL_MANIFEST_PUBLIC_KEY_PEM` secret",
            "Windows 和 Mac 构建步骤都必须注入该 secret",
            "workflow 必须运行 `commercial_release_acceptance.py --with-exe-self-test --deep-scan --json`",
            "CI 单平台验收必须使用 `--artifact-scope` 和 `--strict`",
            "Mac 公证后如果重新压 zip，必须在 `Prepare release asset` 前再次运行商业发布验收",
            "Test final Mac zip",
            "最终 Mac zip 必须先解压到临时目录",
            "解压出来的 `.app` 内二进制 `--self-test`",
            "构建脚本每次都覆盖生成 `src/commercial_manifest_public_key.py`",
            "CI 和生产构建缺少该 secret 时必须快速失败",
            "本地未设置强制开关的测试包会写入空公钥并保持商业清单拒绝状态",
        ]
        for term in required_terms:
            with self.subTest(term=term):
                self.assertIn(term, text)

    def test_customer_instructions_do_not_sell_unfinished_non_codex_agents_as_full_delivery(self) -> None:
        path = ROOT / "docs" / "发送客户说明.txt"
        text = path.read_text(encoding="utf-8")

        required_terms = [
            "Codex：可安装和自动配置胖虎AI API Key",
            "ClaudeCode：覆盖官方 CLI 和客户端入口",
            "OpenClaw：覆盖官方 CLI 和 Hub/客户端入口",
            "Hermes：覆盖官方 CLI 和客户端入口",
            "是否完整交付以工具生成的“功能验收矩阵”为准",
            "不扣次、不算完整交付",
        ]
        for term in required_terms:
            with self.subTest(term=term):
                self.assertIn(term, text)

    def test_readme_stays_as_repo_entry_and_points_to_authoritative_docs(self) -> None:
        path = ROOT / "README.md"
        text = path.read_text(encoding="utf-8")

        required_terms = [
            "本 README 只做仓库入口摘要",
            "docs/PRODUCT_MANUAL_SINGLE_SOURCE_OF_TRUTH.md",
            "docs/TECHNICAL_MAINTENANCE_MANUAL.md",
            "FINAL_REPORT.md",
            "不把未真实验收通过的 Agent 包装为完整付费交付",
        ]
        for term in required_terms:
            with self.subTest(term=term):
                self.assertIn(term, text)


if __name__ == "__main__":
    unittest.main()
