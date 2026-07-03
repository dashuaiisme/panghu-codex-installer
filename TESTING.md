# 测试与验收

最后更新：2026-07-03

## 1. 标准验证矩阵

| 执行域 | 命令来源 | 标准命令 | 退出结果要求 | 证据路径 |
| --- | --- | --- | --- | --- |
| 客户端自检 | 本文件 / `RUNBOOK.md` | `python src\panghu_ai_client.py --self-test` | `UI self-test OK` | 终端输出 |
| 商业流程离线验收 | `RUNBOOK.md` | `python scripts\commercial_flow_acceptance.py --json` | `status=PASS` | 终端 JSON 输出 |
| 轻量发布验收 | `RUNBOOK.md` | `python scripts\commercial_release_acceptance.py --json` | 发布前不得 WARN | 终端 JSON 输出 |
| 单元测试 | 本文件 | `python -m pytest -q` | 全部通过 | 终端输出 |
| 前端结构 | 本文件 | Node 结构检查命令 | `HTML/JS structure OK` | 终端输出 |
| 截图 | 本文件 | `python scripts\capture_ui_preview.py` | 成功生成截图 | `outputs\panghu-installer-*.png`，当前目录未见时由脚本重建 |

## 2. 常用验证命令

```powershell
cd C:\Users\Administrator\Documents\codex\胖虎AI客户端
python src\panghu_ai_client.py --self-test
python scripts\commercial_flow_acceptance.py --json
python scripts\commercial_release_acceptance.py --json
python -m pytest -q
```

前端结构和截图验证：

```powershell
node -e "const fs=require('fs');const html=fs.readFileSync('src/ui/index.html','utf8'); if(!html.includes('<title>胖虎AI客户端</title>')) throw new Error('bad title'); const opens=(html.match(/<style>/g)||[]).length; const closes=(html.match(/<\/style>/g)||[]).length; if(opens!==1||closes!==1) throw new Error('bad style count '+opens+'/'+closes); const scripts=[...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/gi)].map(m=>m[1]).join('\n;\n'); new (require('vm').Script)(scripts); console.log('HTML/JS structure OK', scripts.length)"
python C:\Users\Administrator\.codex\skills\gemini-style-frontend-design\scripts\audit_gemini_style.py src\ui\index.html
python scripts\capture_ui_preview.py
```

商业硬编码扫描：

```powershell
rg -n "48 人|2000|350|50\.00|downstream_count: 48|available_settlement_cents: 200000|pending_settlement_cents: 35000|frozen_cents: 5000|硬编码|终身|永久|套餐价|返佣比例|金牌代理|安全通信通道|数据保护|防篡改|AES-256|NODE-CN-EAST|WSS ACTIVE|Cloud License|Ledger Sync Event Log|SYSTEM:|POLICY:" src\ui\index.html
```

## 3. 本轮验证记录

### 2026-07-03 R5 买家机器人创建/注册/凭证填写引导

- `tests/test_panghu_commercial_manifest.py` 机器人创建/注册/凭证填写引导 focused 验证：`28 passed, 74 deselected`；覆盖 `src/ui/index.html` 引导卡片、官方入口、`platform_account_id`、`platform_chat_id`、`gateway_mode`、回调地址和验签密钥说明的防回归断言。
- `python -m pytest -q`：`338 passed, 187 subtests passed`。
- `python scripts\commercial_release_acceptance.py --json`：仍为 `WARN`；阻塞仍是三端客户包缺失、商业清单生产公钥未注入。

本轮 R5 验证只覆盖客户端 UI 前置引导和测试防回归，不代表真实平台回调、Runtime Adapter 生产接入或服务端验收闭环完成。

### 2026-07-03 团队模式代码推进轮

本轮修正 `src/ui/index.html` 客户运行资产中的演示态污染和假成功态，并新增静态守卫测试。已执行：

- `python -m py_compile src\panghu_ai_client.py src\commercial_api.py src\commercial_backend_contract.py src\commercial_core.py scripts\agent_delivery_acceptance.py scripts\customer_web_entry_acceptance.py`：通过。
- `python -m pytest -q`：`330 passed, 187 subtests passed`。
- `python src\panghu_ai_client.py --self-test`：`UI self-test OK`。
- `python scripts\commercial_flow_acceptance.py --json`：`status=PASS`，仅代表 `offline_only` / `offline_guarded` / `mock_guarded` 范围。
- `python scripts\commercial_release_acceptance.py --json`：`status=WARN`；阻塞为三端客户包缺失、未注入商业清单生产公钥。
- `python scripts\customer_web_entry_acceptance.py`：`web_entry_status=blocked`；当前系统 Python 未加载 `pywebview`，脚本按规则阻断内置网站闭环，不打开系统浏览器冒充完成。
- `python scripts\agent_delivery_acceptance.py`：`delivery_status=blocked`；默认只读检查未执行最小中文对话，ClaudeCode/OpenClaw/Hermes 客户端形态未确认，Gemini / agy 配置待开发。
- `python scripts\capture_ui_preview.py`：成功生成 6 张当前截图证据，路径为 `outputs\panghu-installer-*.png`。
- 前端结构检查 Node 命令：`HTML/JS structure OK`。
- `python C:\Users\Administrator\.codex\skills\gemini-style-frontend-design\scripts\audit_gemini_style.py src\ui\index.html`：`PASS`，仍有设计债级 warning。
- `python C:\Users\Administrator\.codex\skills\codex-project-engineering\scripts\audit_project_files.py C:\Users\Administrator\Documents\codex\胖虎AI客户端`：返回 warning；主要是文档合并后旧审计脚本仍按独立 `TASKS.md`、`DEPLOYMENT.md` 等文件检查，不代表代码回归失败。
- `python -m pytest tests\test_installer_backend.py -q -k "communication_software_link_one_click" -p no:cacheprovider`：`2 passed, 25 deselected`；确认连接通讯软件一键流程停在本地预检，不自动提交真实验收。
- `python -m pytest tests\test_panghu_commercial_manifest.py -q -k webview_backend_bridge_contracts -p no:cacheprovider`：`1 passed, 70 deselected`；确认客户 UI 和 WebView bridge 已切到本地预检口径，不再暴露旧的一键提交验收口径。
- `python -m pytest tests\test_commercial_backend_contract.py -q -k "communication_software_link" -p no:cacheprovider`：`17 passed, 31 deselected`；确认离线合同层要求连接通讯软件验收必须有已接受平台回调、Runtime Adapter 成功结果和幂等 `source_event_id`。
- `python -m pytest tests\test_commercial_api.py -q -k "communication_software_link" -p no:cacheprovider`：`10 passed, 28 deselected`；确认 API 请求/解析能携带平台授权、平台回调、真实服务状态和客户端完成声明字段。
- `python -m pytest tests\test_installer_backend.py -q -k "communication_software_link" -p no:cacheprovider`：`5 passed, 23 deselected`；确认客户端展示服务端真实闭环字段，但默认仍不能声明交付完成。
- `python -m pytest tests\test_commercial_backend_contract.py tests\test_installer_backend.py -q -k "communication_software_link" -p no:cacheprovider`：`24 passed, 54 deselected`；R3 focused 验证覆盖服务端合同平台回调跨会话/入站消息匹配守卫，以及客户端服务端状态刷新用服务端 `False` 覆盖旧 `True` 的防残留逻辑。
- `python -m pytest tests\test_commercial_api.py tests\test_commercial_backend_contract.py tests\test_commercial_flow_acceptance.py tests\test_installer_backend.py -q -p no:cacheprovider`：`115 passed`。

本轮未验证生产服务器、真实数据库、真实支付回调、真实客户设备、真实平台、Runtime Adapter 生产接入、支付/账本生产记录、GitHub Release、下载页、`latest.json` 和三端客户包。R3 focused 验证仍是本地回归，不代表生产真实闭环完成。

### 2026-07-03 文档一致性修正轮

本轮文档一致性修正执行的是文档级检查：

- 旧冲突文本扫描：未再命中“目录为空、源码不存在、旧前端已删除、旧发布包 stale”等高风险旧口径。
- 限定文档差异检查：`git diff --check` 未发现空白错误。
- 项目文件审计：八类工程化职责均已有承接文件；审计仍提示本文件需要保留“本轮验证记录”章节，因此补充本节。

文档一致性修正轮没有重新执行 pytest、unittest、截图、`.venv` 网站入口检查、商业流程脚本或发布前脚本。下面记录只作为历史验证索引。

## 4. 历史验证记录

以下记录来自既有文档和前序窗口输出。本轮文档一致性修正未重新执行这些测试；需要发布、客户验收或视觉验收前必须按命令重新复验。

| 日期/来源 | 命令或范围 | 记录结果 | 当前可用性 |
| --- | --- | --- | --- |
| 旧收口记录 | `python -m unittest discover -s tests -p "test_*.py"` | `unittest`: `306 OK` | 历史记录，需复验 |
| 旧 focused 记录 | 旧前端删除 / 商业 manifest / 发布脚本 focused pytest | `98 passed, 11 subtests passed` | 历史记录，需复验 |
| 旧 focused 记录 | 商业后端 focused pytest | `158 passed, 11 subtests passed` | 历史记录，需复验 |
| 后续整理记录 | `python -m pytest -q` | `pytest`: `320 passed, 185 subtests passed` | 历史记录，需复验 |
| 2026-07-03 R5 买家机器人引导 focused 验证 | `tests/test_panghu_commercial_manifest.py` 相关 focused 回归 | `28 passed, 74 deselected` | 覆盖机器人创建/注册/凭证填写引导；不代表真实平台回调或服务端验收闭环 |
| 2026-07-03 R5 全量回归 | `python -m pytest -q` | `pytest`: `338 passed, 187 subtests passed` | 当前最新本地复验；release acceptance 仍 WARN |
| 2026-07-03 团队模式代码推进轮 | `python -m pytest -q` | `pytest`: `330 passed, 187 subtests passed` | 当前本地复验 |
| 2026-07-03 R3 focused 验证 | `python -m pytest tests\test_commercial_backend_contract.py tests\test_installer_backend.py -q -k "communication_software_link" -p no:cacheprovider` | `24 passed, 54 deselected` | 覆盖跨会话/入站消息匹配守卫和服务端 `False` 覆盖旧 `True`；不代表生产真实闭环 |
| 最近记录（原 `TASKS.md`，已并入 `FINAL_REPORT.md`） | `python -m pytest -q` | `pytest`: `329 passed, 187 subtests passed` | 历史记录，已被本轮 `330 passed` 覆盖 |
| 历史 `.venv` 记录 | `.venv\Scripts\python.exe scripts\customer_web_entry_acceptance.py` | `web_entry_status` = `ready` | 历史记录；当前未见 `.venv`，需重建后复验 |
| 2026-07-03 团队模式代码推进轮 | `python scripts\capture_ui_preview.py` | 生成 6 张当前本地截图 | 当前本地 UI 截图证据；不代表真实客户闭环 |
| 发布前轻量检查记录 | `python scripts\commercial_release_acceptance.py --json` | `status=WARN` | 发布阻塞；需修复后重跑 |
| 商业流程离线记录 | `python scripts\commercial_flow_acceptance.py --json` | `status=PASS` | 仅代表 `offline_only` / `offline_guarded` / `mock_guarded` 范围 |

文档一致性修正轮只做文档 grep 和限定文件 diff；团队模式代码推进轮已重新执行上方本轮验证命令并重新生成截图。当前系统 Python 的网站入口检查仍为 `blocked`，需要重建含 `pywebview` 的 `.venv` 后才能复验内置网站入口前提。

说明：项目 `.venv` 已在 2026-07-03 按用户确认作为可重建环境清理。后续如需复验 pywebview 入口，需要先重建 `.venv`。当前 `outputs/` 只保存本地可重建截图证据，不提交源码仓。

## 5. 无法验证记录

本轮未验证生产服务器、真实数据库、真实支付回调、真实客户设备、真实平台、Runtime Adapter 生产接入、支付/账本生产记录、GitHub Release、下载页和 `latest.json`。原因：当前是源码仓整理和本地验证，不是发布或生产变更。

`audit_project_files.py` 当前不在 git 跟踪文件中，本轮未把它作为验收项。

## 6. WARN 不等于可发布

`commercial_release_acceptance.py --json` 当前仍为 WARN，原因包括：

- 旧客户包和历史构建产物已清理。
- Windows、Mac AppleSilicon、Mac Intel 本地客户包缺失，需要重新打包。
- 当前构建未注入商业清单生产公钥，商业清单会保持拒绝状态。

因此当前只代表源码层和本地离线合同验证可继续推进，不代表正式客户包、GitHub Release、下载页或 `latest.json` 已可发布。
