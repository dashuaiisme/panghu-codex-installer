# 本地运行与验证手册

最后更新：2026-06-26

## 0. 本文件职责

本文件只负责：

- 本地进入项目
- 运行命令
- 验证命令
- 截图命令
- 发布前本地操作顺序

本文件不负责产品定义或当前项目状态判断。

## 1. 进入项目

```powershell
cd C:\Users\Administrator\Documents\codex\panghu-codex-installer
```

## 2. 代码健康检查

```powershell
python -m py_compile src\panghu_codex_installer.py scripts\agent_delivery_acceptance.py scripts\customer_web_entry_acceptance.py
python src\panghu_codex_installer.py --self-test
python -m unittest discover -s tests -p "test_*.py"
```

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

```powershell
python outputs\capture_ui_preview.py
```

截图只能证明界面渲染，不代表网站业务或 Agent 真实闭环。

## 5. 辅助验收脚本

```powershell
.venv\Scripts\python.exe scripts\customer_web_entry_acceptance.py
python scripts\agent_delivery_acceptance.py
python scripts\commercial_flow_acceptance.py --json
python scripts\commercial_release_acceptance.py --json
```

说明：

- `customer_web_entry_acceptance.py` 只验证网站入口、域名和 WebView 前提。
- 登录态恢复验收必须区分三类数据：`profile.json` 只存账号提示和偏好，买家会话走 cookie/WebView profile，用户显式记住的胖虎AI密码只走本机系统加密 `login_accounts.json`。
- `agent_delivery_acceptance.py` 默认只读检查，不代表真实客户闭环已完成。
- `commercial_flow_acceptance.py --json` 是本地离线商业合同验收。
- `commercial_release_acceptance.py --json` 是本地轻量发布前检查，不等于允许发布。

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

## 7. 手机控制Agent文档/实现回归

修改手机控制Agent产品文档、服务合同、订单/验收状态机或平台通道后，至少检查：

```powershell
rg -n "手机控制Agent|mobile_control_agent|mobile-control|mobile_control|source_event_id|断网|禁用 API Key|取消平台授权" README.md docs PROJECT_BLUEPRINT.md PLAN.md TASK_GRAPH.md ACCEPTANCE.md SAFETY.md RUNBOOK.md FINAL_REPORT.md
python -m pytest tests\test_commercial_backend_contract_docs.py -q
```

如果已进入代码实现阶段，还必须补充对应单元测试，验证：

- 基础 Agent 配置和手机控制Agent订单、配置会话、验收记录、扣费事件互相独立。
- 已有可用 Agent 或历史交付可以进入手机控制Agent链路，不被本次基础配置会话硬锁死。
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
3. 补截图与功能矩阵。
4. 确认 `FINAL_REPORT.md` 状态允许进入下一阶段。
5. 再按技术维护手册处理打包、Release、下载页和 `latest.json`。
