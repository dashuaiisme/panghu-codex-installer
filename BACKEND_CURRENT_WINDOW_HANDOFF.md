# 后端当前窗口交接说明

最后更新：2026-06-26

## 1. 当前状态

当前仓库分支是 `main`，本窗口的后端改动已经落在主工作树内；这里的“合并到主树”从文件位置上已经完成。后续主控提交时不要直接 `git add .`，因为工作树还混有前端、输出图片、构建依赖和其他窗口改动。

本窗口严格按后端范围推进。用户已明确要求“涉及前端先不要管”，因此不要在本窗口成果里纳入：

- `src/ui/index.html`
- `outputs/*.png`
- `outputs/capture_ui_preview.py`
- `outputs/ui-*`
- `node_modules/`
- `package.json`
- `package-lock.json`
- 其他非本窗口生成或非后端合同链路文件

## 2. 本窗口建议提交文件

建议主控只审查并提交以下后端成果文件：

```text
docs/COMMERCIAL_BACKEND_API_CONTRACT.md
docs/TECHNICAL_MAINTENANCE_MANUAL.md
scripts/agent_delivery_acceptance.py
scripts/commercial_flow_acceptance.py
src/commercial_api.py
src/commercial_backend_contract.py
src/panghu_codex_installer.py
tests/test_agent_delivery_acceptance_script.py
tests/test_commercial_api.py
tests/test_commercial_backend_contract.py
tests/test_commercial_backend_contract_docs.py
tests/test_commercial_flow_acceptance.py
tests/test_installer_backend.py
tests/test_panghu_commercial_manifest.py
BACKEND_CURRENT_WINDOW_HANDOFF.md
```

如果主控要分批提交，建议拆成三组：

1. 登录账号与本地安全边界：`src/panghu_codex_installer.py`、`tests/test_installer_backend.py`。
2. Mobile Control Agent 商业合同：`src/commercial_api.py`、`src/commercial_backend_contract.py`、`scripts/commercial_flow_acceptance.py`、相关商业测试和合同文档。
3. Agent 真实验收脚本：`scripts/agent_delivery_acceptance.py`、`tests/test_agent_delivery_acceptance_script.py`、技术维护手册相关段落。

## 3. 已完成后端功能

### 登录门禁与账号状态

- `profile.json` 继续按白名单保存，不保存密码、部署授权 token、订单号、权益 ID、配置会话 ID。
- 历史登录账号进入独立 `login_accounts.json`；密码只允许本机加密 blob。
- 旧版明文 `password` 字段不再迁移；只有可解密的 legacy protected blob 才迁移到 `protected_password`。
- WebView 初始状态和账号下拉只返回公开账号状态，不返回明文密码。
- 账号下拉选择会清空当前密码输入，只返回 `has_password`、`remember_password`、`auto_login` 等公开字段。
- 退出当前账号只关闭该账号 `auto_login`，保留用户显式保存的本机加密密码。
- 删除当前账号记录会同步清当前 cookie/session、`logged_in_user`、`deployer_auth`、`commercial_contexts`，并回到登录门禁。

### Mobile Control Agent

- Mobile Control Agent 被建模为独立增值服务，不复用基础 Agent 配置订单、权益、配置会话或验收事件。
- `ContractServiceOrder` 增加 `payment_id`。
- 新增 `mark_mobile_control_order_paid(order_id, payment_id)`。
- 创建 Mobile Control 配置会话前，订单必须是 `paid` 或 `manual_review`，未支付订单会被阻断。
- 客户端后端缓存订单支付/人工复核状态；未确认支付或人工复核前，阻止创建 Mobile Control 会话。
- Mobile Control 验收必须形成入站平台消息、Agent 响应摘要、出站平台消息、证据 URL 和唯一 `source_event_id`。
- 商业流离线验收脚本现在覆盖 Mobile Control：未支付阻断、支付后建会话、平台回调 accepted、验收后写入独立 `mobile_control_agent_delivered` 服务账本事件。

### Agent 真实交付验收脚本

- `scripts/agent_delivery_acceptance.py` 增加隔离配置能力，避免用本机残留配置当事实。
- 支持 `--isolated-config-from-env`、`--dialogue-timeout`、`--run-codex-gateway-probe`。
- 支持 Codex gateway probe，并对 API Key 输出做脱敏。
- ClaudeCode/CC、OpenClaw、Hermes 可走隔离配置和最小对话探测。
- Gemini/agy 保留安装入口，但配置和对话验收返回 `not_supported`；不能计入完整交付。

## 4. 未完成和阻塞

- 真实 WebView/SSO 仍需实机验证：必须是软件内置浏览器；`pywebview` 不可用或打开失败时应阻断，不能自动跳系统浏览器包装成完成。
- Codex、ClaudeCode/CC、OpenClaw、Hermes 的“最小对话真实打通”还需要用真实买家 API Key 跑 `agent_delivery_acceptance.py`。
- Gemini/agy 仍是配置待开发，只能算安装入口，不能算完整交付。
- 真实服务端登录、支付、订单、权益、配置会话、Mobile Control 平台回调仍未接生产服务端验证。
- release 验收仍是 `WARN`：客户包 stale，生产商业清单公钥未注入。此为打包/发布边界，本窗口未处理。
- 前端文件和输出图存在脏项，本窗口按用户要求未处理。

## 5. 已运行验证命令

```powershell
python -m unittest discover -s tests -p "test_installer_backend.py"
python -m unittest discover -s tests -p "test_panghu_commercial_manifest.py"
python -m unittest discover -s tests -p "test_commercial_backend_contract_docs.py"
python -m unittest discover -s tests -p "test_commercial_flow_acceptance.py"
python -m unittest discover -s tests -p "test_*.py"
python -m py_compile src\panghu_codex_installer.py scripts\commercial_flow_acceptance.py scripts\agent_delivery_acceptance.py src\commercial_api.py src\commercial_backend_contract.py
python scripts\commercial_flow_acceptance.py --json
python scripts\commercial_release_acceptance.py --json
python src\panghu_codex_installer.py --self-test
git diff --check -- . ':(exclude)src/ui/index.html' ':(exclude)outputs/*.png' ':(exclude)outputs/capture_ui_preview.py'
```

结果：

- 全量单测：`271 tests OK`
- 商业流验收：`PASS`
- 安装器 self-test：`UI self-test OK`
- py_compile：通过
- diff check：无空白错误，仅 Git CRLF 提示
- release 验收：`WARN`，原因是客户包 stale、生产商业清单公钥未注入

## 6. 主控提交建议

不要执行：

```powershell
git add .
```

建议用显式路径 stage：

```powershell
git add -- `
  docs/COMMERCIAL_BACKEND_API_CONTRACT.md `
  docs/TECHNICAL_MAINTENANCE_MANUAL.md `
  scripts/agent_delivery_acceptance.py `
  scripts/commercial_flow_acceptance.py `
  src/commercial_api.py `
  src/commercial_backend_contract.py `
  src/panghu_codex_installer.py `
  tests/test_agent_delivery_acceptance_script.py `
  tests/test_commercial_api.py `
  tests/test_commercial_backend_contract.py `
  tests/test_commercial_backend_contract_docs.py `
  tests/test_commercial_flow_acceptance.py `
  tests/test_installer_backend.py `
  tests/test_panghu_commercial_manifest.py `
  BACKEND_CURRENT_WINDOW_HANDOFF.md
```

提交前建议再跑：

```powershell
python -m unittest discover -s tests -p "test_*.py"
python scripts\commercial_flow_acceptance.py --json
python src\panghu_codex_installer.py --self-test
```

提交信息建议：

```text
feat: harden backend account sessions and mobile control contract
```
