# 本地运行与验证手册

最后更新：2026-06-28

## 0. 本文件职责

本文件只负责：

- 本地进入项目
- 运行命令
- 验证命令
- 截图命令状态
- 发布前本地操作顺序

本文件不负责产品定义或当前项目状态判断。

## 1. 进入项目

```powershell
cd C:\Users\Administrator\Documents\codex\胖虎AI客户端
```

## 2. 代码健康检查

```powershell
.venv\Scripts\python.exe -m py_compile src\panghu_codex_installer.py scripts\agent_delivery_acceptance.py scripts\customer_web_entry_acceptance.py
.venv\Scripts\python.exe src\panghu_codex_installer.py --self-test
.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

本轮记录：`py_compile OK`、`self-test OK`、`unittest 306 OK`。

## 3. 源码启动

Windows：

```powershell
scripts\run-windows.bat
```

Mac：

```bash
scripts/run-mac.command
```

## 4. UI 截图

旧 WebView 前端和旧截图脚本已删除，当前没有可复用的 UI 截图命令。

新前端重做并接入后，必须重新提供截图脚本和 B 级截图证据。历史截图目录不得继续作为当前验收依据。

## 5. 辅助验收脚本

```powershell
.venv\Scripts\python.exe scripts\customer_web_entry_acceptance.py
python scripts\agent_delivery_acceptance.py
python scripts\commercial_flow_acceptance.py --json
python scripts\commercial_release_acceptance.py --json
```

说明：

- `customer_web_entry_acceptance.py` 只验证网站入口、域名和 WebView 前提。
- 本轮 `.venv\Scripts\python.exe scripts\customer_web_entry_acceptance.py` 返回 `web_entry_status=ready`；系统 Python 返回 `blocked` 是因为没有 `webview`，不代表项目运行环境失败。后续网站入口前提检查优先使用 `.venv`。
- 登录态恢复验收必须区分三类数据：`profile.json` 只存账号提示和偏好，买家会话走 cookie/WebView profile，用户显式记住的胖虎AI密码只走本机系统加密 `login_accounts.json`。
- `agent_delivery_acceptance.py` 默认只读检查，不代表真实客户闭环已完成。
- `commercial_flow_acceptance.py --json` 是本地离线商业合同验收；本轮返回 `status=PASS`，但必须标注 `offline_only` / `offline_guarded` / `mock_guarded`。
- `commercial_release_acceptance.py --json` 是本地轻量发布前检查，不等于允许发布；本轮返回 `status=WARN`，原因是只有旧名历史客户包、三端包 `stale`、未注入商业清单生产公钥。
- 本轮旧前端删除 / 商业 manifest / 发布脚本 focused pytest 为 `98 passed, 11 subtests passed`；商业后端 focused pytest 为 `158 passed, 11 subtests passed`。

CLI-only Agent 交付验收命令：

```powershell
python scripts\agent_delivery_acceptance.py --delivery-scope cli --agents codex,claude_code,openclaw,hermes
$env:PANGHU_AGENT_ACCEPTANCE_API_KEY="<current-buyer-panghuai-api-key>"
python scripts\agent_delivery_acceptance.py --delivery-scope cli --agents codex,claude_code,openclaw,hermes --run-dialogue --isolated-config-from-env --run-codex-gateway-probe --dialogue-timeout 45
Remove-Item Env:\PANGHU_AGENT_ACCEPTANCE_API_KEY
```

说明：

- API Key 只能通过环境变量临时传入，不写入文档、日志、截图或报告。
- 无密钥命令可用于确认 CLI-only 范围不会被“客户端未确认”阻断；未执行最小中文对话时可以 `exit 1`。
- 带真实买家 Key 的命令只验收所选 CLI scope，不代表客户端 scope、Gemini / agy、三端包、Release 或 `latest.json` 通过。

## 6. Codex 三模式回归

修改 Codex 配置模式、按钮、快照或 `auth.json` / `config.toml` 写入逻辑后，至少运行：

```powershell
python src\panghu_codex_installer.py --self-test
python -m pytest tests\test_panghu_commercial_manifest.py tests\test_commercial_core.py tests\test_agent_playbooks.py -q
```

必须确认：

- 普通模式仍写入胖虎AI中转站 API 配置。
- 双态模式保留 ChatGPT 登录态，但模型消耗仍走胖虎AI API Key。
- 官方直登写入官方 `openai` provider，不写胖虎AI中转站 Key。
- 模式切换前会保存 `~\.codex\panghu_modes\` 快照。
- 任何模式写完后都提示完全退出 Codex 再重新打开。

## 7. 连接通讯软件文档/实现回归

修改连接通讯软件产品文档、服务合同、订单/验收状态机或平台通道后，至少检查：

```powershell
rg -n "连接通讯软件|communication_software_link|communication-software-link|communication_software_link|source_event_id|断网|禁用 API Key|取消平台授权" README.md docs PROJECT_BLUEPRINT.md PLAN.md TASK_GRAPH.md ACCEPTANCE.md SAFETY.md RUNBOOK.md FINAL_REPORT.md
python -m pytest tests\test_commercial_backend_contract_docs.py -q
```

如果已进入代码实现阶段，还必须补充对应单元测试，验证：

- 基础 Agent 配置和连接通讯软件订单、配置会话、验收记录、扣费事件互相独立。
- 已有可用 Agent 或历史交付可以进入连接通讯软件链路，不被本次基础配置会话硬锁死。
- 已形成验收证据后，断网、禁 Key 或取消平台授权不会自动免单。

## 8. 禁止本地命令

当前阶段不要运行：

```powershell
python scripts\commercial_release_acceptance.py --with-exe-self-test --deep-scan --json
```

## 9. 发布前顺序

只有在 `ACCEPTANCE.md` 允许进入发布前阶段后，才按这个顺序继续：

1. 跑代码健康检查。
2. 跑辅助验收脚本。
3. 新前端接入后重新补截图与功能矩阵。
4. 确认 `FINAL_REPORT.md` 状态允许进入下一阶段。
5. 再按技术维护手册处理打包、Release、下载页和 `latest.json`。
