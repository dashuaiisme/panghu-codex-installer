# 工作树收口分类报告 2026-06-28 R1

RID: R3-VERSION-VISIBLE-001
角色: 可见团队窗口 / 版本治理经理
项目: 胖虎AI客户端
真实 git root: `C:\Users\Administrator\Documents\codex\panghu-codex-installer`
分支: `main`

## 结论

当前未提交项很多，不等于后端没有做完。工作树里同时混有后端合同、前端 UI、测试验收、文档口径、发布脚本、截图证据、依赖目录和临时目录。后续要先分批收口，不应把所有改动混成一个“后端是否完成”的判断。

发布包和发布上线本轮暂缓；发布相关文件只分类，不建议本轮提交为“已发布完成”。

## 必须纳入当前交付提交候选

这些文件与本轮“本地可修复交付基线”直接相关，建议由对应 owner 再复核后纳入交付提交候选。

### 后端与合同

- `src/commercial_api.py`
- `src/commercial_backend_contract.py`
- `src/panghu_codex_installer.py`
- `scripts/commercial_flow_acceptance.py`
- `scripts/customer_web_entry_acceptance.py`
- `scripts/agent_delivery_acceptance.py`
- `tests/test_commercial_api.py`
- `tests/test_commercial_backend_contract.py`
- `tests/test_commercial_flow_acceptance.py`
- `tests/test_agent_delivery_acceptance_script.py`
- `tests/test_panghu_commercial_manifest.py`
- `tests/test_customer_web_entry_acceptance.py`

### 前端交付 UI 与证据

- `src/ui/index.html`
- `src/ui/assets/`
- `outputs/capture_ui_preview.py`
- `outputs/panghu-installer-agent-center.png`
- `outputs/panghu-installer-agent-config.png`
- `outputs/panghu-installer-login-gate.png`
- `outputs/panghu-installer-site-console.png`
- `outputs/panghu-installer-value-added.png`

### 项目文档与验收口径

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
- `outputs/local-repairability-20260628-r1/`
- `outputs/ui-delivery-framework-20260628-r1/`
- `outputs/ui-b-level-20260628-r1-frontend-b-acceptance/`

## 暂缓发布相关

这些文件与打包、发布、公开下载或 Release 验收有关。用户已明确“发布包不用管”，建议暂缓，不把它们作为本轮交付完成依据。

- `.github/workflows/build-mac-release.yml`
- `scripts/build-windows-exe.ps1`
- `scripts/build-mac-app.command`
- `scripts/commercial_release_acceptance.py`
- `scripts/generate-download-qr.py`
- `tests/test_commercial_build_scripts.py`
- `tests/test_commercial_release_acceptance.py`

## 需要用户确认清理

这些项目看起来像生成产物、历史截图、临时目录或依赖目录。不得直接删除，需要用户确认哪些保留为验收证据，哪些清理。

- `node_modules/`
- `package.json`
- `package-lock.json`
- `scratch/`
- `outputs/test_out.png`
- `outputs/R1-DELIVERY-A-C-F/`
- `outputs/delivery-evidence-20260627-r8/`
- `outputs/ui-all-20260626/`
- `outputs/ui-all-20260626-correct/`
- `outputs/ui-b-level-20260627-r2/`
- `outputs/ui-b-level-20260627-r5-qa/`
- `outputs/ui-b-level-20260627-r7-header-recheck/`
- `outputs/ui-b-level-20260627-r8-desktop-qa/`
- `outputs/ui-review-20260626-round2/`

## 可忽略或缓存候选

- `node_modules/` 通常不应提交；若当前仓库没有明确前端包管理交付要求，应列入清理候选。
- `scratch/` 通常是临时工作区，应列入清理候选。
- `outputs/test_out.png` 若不是最终验收截图，应列入清理候选。

以上仍需用户确认后才能删除或移动。

## 需要补测或补文档

本轮版本治理只做分类，不重新跑全量测试。根据其他 owner 汇报，本地后端、前端入口和全量 unittest 已通过；但以下内容仍不能写成完成:

- 真实服务端联调
- 真实数据库
- 真实支付回调
- 真实 Agent Runtime Adapter
- 生产发布包
- 客户实机链路

## 建议下一步

1. 主控先让后端、前端、QA owner 确认“必须纳入当前交付提交候选”是否完整。
2. 用户确认清理清单后，再由版本治理/CLI 执行删除或移动。
3. 发布相关文件单独开发布 RID，不混入本轮交付收口。
4. 最终提交前按批次拆分：后端合同、前端 UI、文档验收、证据产物、发布暂缓。
