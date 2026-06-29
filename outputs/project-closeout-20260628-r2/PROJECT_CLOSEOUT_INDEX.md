# 胖虎AI客户端项目收口索引 2026-06-28 R2

## 主控结论

当前工作树不是单一“脏代码”问题，而是多轮后端、前端、文档、发布脚本、截图证据和本地依赖混在同一状态里。本轮主控收口目标是把可交付源码和证据边界捋清楚，禁止把发布包、生产下载入口或历史截图清理误写成已经完成。

## 当前已执行的本地治理

- 已确认项目身份：`C:\Users\Administrator\Documents\codex\panghu-codex-installer`，分支 `main`。
- 已禁止 fork、派生、新工作树、提交和发布。
- 已更新 `.gitignore`，让 `node_modules/`、`scratch/`、`.pytest_cache/` 不再污染工作树视野。
- 已更新主文档中的本轮验证数字：`unittest 300 OK`、商业后端 focused `145 passed, 11 subtests passed`、发布脚本 focused `31 passed`。
- 已增强 `commercial_flow_acceptance.py --json`，输出 `backend_closeout_matrix`，固定区分本地已闭合、真实服务待接入、发布暂缓。
- 已调用两个只读子 agent 做团队模式分工审计，均未修改文件、未创建 fork、未创建分支、未创建工作树。

## 当前交付提交候选

### 后端与合同

- `src/commercial_api.py`
- `src/commercial_backend_contract.py`
- `src/panghu_codex_installer.py`
- `scripts/agent_delivery_acceptance.py`
- `scripts/commercial_flow_acceptance.py`
- `scripts/customer_web_entry_acceptance.py`
- `tests/test_agent_delivery_acceptance_script.py`
- `tests/test_commercial_api.py`
- `tests/test_commercial_backend_contract.py`
- `tests/test_commercial_flow_acceptance.py`
- `tests/test_panghu_commercial_manifest.py`
- `tests/test_customer_web_entry_acceptance.py`

### 前端与本地 UI 交付

- `src/ui/index.html`
- `src/ui/assets/`
- `outputs/capture_ui_preview.py`
- `outputs/panghu-installer-agent-center.png`
- `outputs/panghu-installer-agent-config.png`
- `outputs/panghu-installer-login-gate.png`
- `outputs/panghu-installer-site-console.png`
- `outputs/panghu-installer-value-added.png`
- `package.json`
- `package-lock.json`

### 文档和验收口径

- `README.md`
- `PROJECT_BLUEPRINT.md`
- `PLAN.md`
- `TASK_GRAPH.md`
- `ACCEPTANCE.md`
- `RUNBOOK.md`
- `FINAL_REPORT.md`
- `BACKEND_CURRENT_WINDOW_HANDOFF.md`
- `docs/PRODUCT_MANUAL_SINGLE_SOURCE_OF_TRUTH.md`
- `docs/TECHNICAL_MAINTENANCE_MANUAL.md`
- `docs/COMMERCIAL_BACKEND_API_CONTRACT.md`
- `docs/发送客户说明.txt`
- `outputs/backend-closeout-20260628-r1/`
- `outputs/qa-closeout-20260628-r1/`
- `outputs/version-closeout-20260628-r1/`
- `outputs/local-repairability-20260628-r1/`
- `outputs/ui-delivery-framework-20260628-r1/`
- `outputs/ui-b-level-20260628-r1-frontend-b-acceptance/`
- `outputs/project-closeout-20260628-r2/`

## 暂缓发布相关

这些文件可以保留在工作树中继续审查，但不能作为“已经发布完成”的证据。

- `.github/workflows/build-mac-release.yml`
- `scripts/build-windows-exe.ps1`
- `scripts/build-mac-app.command`
- `scripts/commercial_release_acceptance.py`
- `scripts/generate-download-qr.py`
- `tests/test_commercial_build_scripts.py`
- `tests/test_commercial_release_acceptance.py`

暂缓原因：

- `commercial_release_acceptance.py --json` 当前仍为 `WARN`。
- 只有旧名历史客户包，新产品名客户包需要重包。
- 三端包 `stale`。
- 商业清单生产公钥未注入。
- 用户当前未授权发布包、GitHub Release、下载页或 `latest.json`。

## 子 agent 只读审计结论

### 代码审计

- P0：未发现指定源码、脚本和 tests 的阻断级不一致。
- P1：未发现新增契约字段漏接到测试的明显问题；`source_event_id`、Agent Center guarded 字段、communication software link runtime/acceptance、WebView `accepted` 返回均有覆盖。
- P2：工作区未提交范围很大，正式合并前必须拆清源码/测试改动和验收产物。
- 建议命令已执行：无缓存 focused pytest `158 passed, 11 subtests passed`。

### 文档和产物治理

- 当前 git status 是“交付候选 + 验收证据 + 历史/临时产物待清理”的混合工作区，不是单一发布完成态。
- `package.json` / `package-lock.json` 只含 Playwright，应作为验收工具依赖候选单独确认。
- outputs 建议只保留最新且被最终报告引用的证据目录；旧轮次 UI 截图、重复 evidence 和 `outputs/test_out.png` 需要用户确认后清理。
- 发布相关文件不能算完成，只能标记为暂缓或待发布链路验证。

## 需要用户确认后再清理或归档

这些属于历史截图、旧验收证据或一次性输出。不得擅自删除；下一步可以按用户确认批量归档或清理。

- `outputs/R1-DELIVERY-A-C-F/`
- `outputs/delivery-evidence-20260627-r8/`
- `outputs/ui-all-20260626/`
- `outputs/ui-all-20260626-correct/`
- `outputs/ui-b-level-20260627-r2/`
- `outputs/ui-b-level-20260627-r5-qa/`
- `outputs/ui-b-level-20260627-r7-header-recheck/`
- `outputs/ui-b-level-20260627-r8-desktop-qa/`
- `outputs/ui-review-20260626-round2/`
- `outputs/test_out.png`

## 本轮验证证据

```powershell
python -m py_compile src\panghu_codex_installer.py src\commercial_api.py src\commercial_backend_contract.py scripts\agent_delivery_acceptance.py scripts\customer_web_entry_acceptance.py scripts\commercial_flow_acceptance.py scripts\commercial_release_acceptance.py
python -m unittest discover -s tests -p "test_*.py"
python -m pytest tests\test_commercial_api.py tests\test_commercial_backend_contract.py tests\test_commercial_flow_acceptance.py tests\test_panghu_commercial_manifest.py -q
python -m pytest tests\test_commercial_release_acceptance.py tests\test_commercial_build_scripts.py -q
python scripts\commercial_flow_acceptance.py --json
python src\panghu_codex_installer.py --self-test
$env:PYTHONDONTWRITEBYTECODE='1'; $env:PYTHONIOENCODING='utf-8'; python -m pytest -q -p no:cacheprovider tests/test_commercial_api.py tests/test_commercial_backend_contract.py tests/test_commercial_flow_acceptance.py tests/test_agent_delivery_acceptance_script.py tests/test_customer_web_entry_acceptance.py tests/test_panghu_commercial_manifest.py
```

结果：

- `py_compile` 通过。
- `unittest discover`：300 tests OK。
- 商业后端 focused：145 passed, 11 subtests passed。
- 发布脚本 focused：31 passed。
- 无缓存 focused：158 passed, 11 subtests passed。
- `commercial_flow_acceptance.py --json`：`status=PASS`，但为 `offline_only` / `offline_guarded` / `mock_guarded`。
- `panghu_codex_installer.py --self-test`：`UI self-test OK`。

## 仍未完成

- 真实数据库、真实支付回调、真实 Agent Runtime Adapter、真实 agent_center 快照。
- 客户真实账号、真实设备和端到端验收。
- 生产服务器联调。
- 三端客户包、签名、公钥注入、GitHub Release、下载页和 `latest.json`。
