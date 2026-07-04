# 本地运行、验证与发布手册

最后更新：2026-07-03

## 0. 本文件职责

本文件负责（原 `DEPLOYMENT.md` 已并入本文件）：

- 本地进入项目、运行命令、验证命令
- 截图命令状态
- 构建入口、发布前条件与发布顺序

本文件不负责产品定义或当前项目状态判断（状态见 `FINAL_REPORT.md`）。

## 1. 进入项目

```powershell
cd C:\Users\Administrator\Documents\codex\胖虎AI客户端
```

## 2. 代码健康检查

```powershell
python -m py_compile src\panghu_ai_client.py scripts\agent_delivery_acceptance.py scripts\customer_web_entry_acceptance.py
python src\panghu_ai_client.py --self-test
python -m unittest discover -s tests -p "test_*.py"
```

验证数字不在本文件重复维护；最近记录和历史记录以 `TESTING.md` 为准。

说明：项目 `.venv` 已在 2026-07-03 按用户确认作为可重建环境清理。需要 pywebview 或打包依赖时，先按 `requirements-build.txt` 重建虚拟环境。

## 3. 源码启动与停止

Windows：

```powershell
scripts\run-windows.bat
```

Mac：

```bash
scripts/run-mac.command
```

停止：

- 普通源码运行：关闭客户端窗口或终止对应 Python 进程。
- 预览/截图脚本：脚本结束后应自动关闭浏览器上下文；如残留进程，先确认不是用户正在操作的窗口再处理。

## 4. 日志位置

- 本地命令输出以终端为准。
- `tmp/` 下的 agy / Gemini 日志仅作调试证据，不是长期权威文档。
- 日志不得保存 API Key、密码、部署 token、订单号、权益 ID 或配置会话 ID。

## 5. 健康检查

```powershell
python src\panghu_ai_client.py --self-test
python scripts\commercial_flow_acceptance.py --json
python -m pytest -q
```

## 6. 备份与回滚

- 修改客户配置写入逻辑时，必须保留写入前快照和失败恢复路径。
- 本地源码回滚只允许回滚自己明确负责的改动；不得用 `git reset --hard` 或 `git checkout --` 覆盖他人工作。
- 生产订单、权益、账本、代理结算和下载入口不在本仓本地回滚。
- 客户包、Release、下载页和 `latest.json` 的备份规则以 `docs\TECHNICAL_MAINTENANCE_MANUAL.md` 为准。

## 7. UI 截图

当前 WebView 前端入口为 `src/ui/index.html`，截图脚本为：

```powershell
python scripts\capture_ui_preview.py
```

运行后会重建以下本地截图证据；截图文件属于可重建输出，不提交源码仓。当前未见 `outputs/`，不能把历史截图路径写成当前证据：

- `outputs\panghu-installer-login-gate.png`
- `outputs\panghu-installer-agent-config.png`
- `outputs\panghu-installer-site-console.png`
- `outputs\panghu-installer-value-added.png`
- `outputs\panghu-installer-agent-center.png`
- `outputs\panghu-installer-agent-config-1365.png`

截图只代表本地前端视觉和结构验收，不代表真实网页登录、充值购买、创建 Key、Agent 最小中文对话、代理中心服务端合同、客户功能验收矩阵、打包发布或生产上线已经完成。

## 8. 辅助验收脚本

```powershell
python scripts\customer_web_entry_acceptance.py
python scripts\agent_delivery_acceptance.py
python scripts\commercial_flow_acceptance.py --json
python scripts\commercial_release_acceptance.py --json
```

说明：

- `customer_web_entry_acceptance.py` 只验证网站入口、域名和 WebView 前提。历史记录中 `.venv` 下返回 `web_entry_status` = `ready`；当前 `.venv` 已清理，需要 pywebview 时先重建。
- 登录态恢复验收必须区分三类数据：`profile.json` 只存账号提示和偏好，买家会话走 cookie/WebView profile，用户显式记住的胖虎AI密码只走本机系统加密 `login_accounts.json`。
- `agent_delivery_acceptance.py` 默认只读检查，不代表真实客户闭环已完成。
- `commercial_flow_acceptance.py --json` 是本地离线商业合同验收；最近记录 `status=PASS`，但必须标注 `offline_only` / `offline_guarded` / `mock_guarded`。
- `commercial_release_acceptance.py --json` 是本地轻量发布前检查，不等于允许发布；最近记录 `status=WARN`，原因是旧客户包已清理、三端本地客户包缺失、未注入商业清单生产公钥。
- 源码层 pytest、unittest 和 focused pytest 的历史记录统一见 `TESTING.md`；未重新执行前不得写成当前已复验。

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

## 9. Codex 三模式回归

修改 Codex 配置模式、按钮、快照或 `auth.json` / `config.toml` 写入逻辑后，至少运行：

```powershell
python src\panghu_ai_client.py --self-test
python -m pytest tests\test_panghu_commercial_manifest.py tests\test_commercial_core.py tests\test_agent_playbooks.py -q
```

必须确认：

- 普通模式仍写入胖虎AI中转站 API 配置。
- 双态模式保留 ChatGPT 登录态，但模型消耗仍走胖虎AI API Key。
- 官方直登写入官方 `openai` provider，不写胖虎AI中转站 Key。
- 模式切换前会保存 `~\.codex\panghu_modes\` 快照。
- 任何模式写完后都提示完全退出 Codex 再重新打开。

## 10. 连接通讯软件文档/实现回归

修改连接通讯软件产品文档、服务合同、订单/验收状态机或平台通道后，至少检查：

```powershell
rg -n "连接通讯软件|communication_software_link|communication-software-link|source_event_id|断网|禁用 API Key|取消平台授权" README.md docs PRODUCT.md ACCEPTANCE.md SECURITY.md RUNBOOK.md FINAL_REPORT.md INTEGRATION.md
python -m pytest tests\test_commercial_backend_contract_docs.py -q
```

如果已进入代码实现阶段，还必须补充对应单元测试，验证：

- 基础 Agent 配置和连接通讯软件订单、配置会话、验收记录、扣费事件互相独立。
- 已有可用 Agent 或历史交付可以进入连接通讯软件链路，不被本次基础配置会话硬锁死。
- 已形成验收证据后，断网、禁 Key 或取消平台授权不会自动免单。

## 11. 禁止本地命令

当前阶段不要运行：

```powershell
python scripts\commercial_release_acceptance.py --with-exe-self-test --deep-scan --json
```

## 12. 构建入口（原 DEPLOYMENT.md）

Windows：

```powershell
scripts\build-windows-exe.ps1
```

Mac：

```bash
scripts/build-mac-app.command
```

GitHub Actions：`.github/workflows/build-mac-release.yml`（文件名含 `mac`，但同时覆盖 Windows、Mac AppleSilicon、Mac Intel）。

## 13. 发布前最低条件

进入发布前，必须满足：

- `ACCEPTANCE.md` 明确允许进入发布前阶段（A 到 H 级全部通过）。
- 工作区没有未识别的业务改动。
- `python -m pytest -q` 通过。
- `python scripts\commercial_flow_acceptance.py --json` 返回 PASS。
- `python scripts\commercial_release_acceptance.py --json` 不再是 WARN。
- 三端客户包都是当前产品名、当前源码之后构建的新包，名称、时间、SHA256 和内容扫描符合技术维护手册。
- 商业清单生产公钥已注入。
- 客户包内容扫描未发现内部维护、测试、源码、签名资料或临时验证残留。
- 下载页和 `latest.json` 更新计划已明确。

当前状态：轻量发布验收最近记录为 `WARN`，不能进入 GitHub Release、下载页或 `latest.json` 更新。旧客户包和历史构建产物已清理，后续发布必须重新打包三端客户包。

## 14. 发布顺序

只有满足第 13 节条件后，才按这个顺序继续：

1. 跑代码健康检查。
2. 跑辅助验收脚本。
3. 新前端接入后重新补截图与功能矩阵。
4. 确认 `FINAL_REPORT.md` 状态允许进入下一阶段。
5. 再按 `docs/TECHNICAL_MAINTENANCE_MANUAL.md` 的 Release 流程处理打包、Release、下载页和 `latest.json`。

普通源码整理不得执行 GitHub Release、下载页或 `latest.json` 更新。

## 15. 发布回滚

本仓本地回滚只覆盖源码、构建产物和客户包。生产状态、下载页、`latest.json`、支付、订单、权益、账本和代理结算必须按服务端维护流程回滚。

如客户包已公开发布，回滚必须同时处理 GitHub Release、下载页和公开更新清单，不能只替换本地 `release/` 文件。

生产服务器、下载页和公开更新清单状态不以本地源码仓为准，必须通过真实线上检查确认。

## 16. 发布禁止事项

- 不得把本地源码验证通过说成正式发版完成。
- 不得删除有效客户 zip。
- 不得在普通源码整理中修改 GitHub Release、下载页或 `latest.json`。
