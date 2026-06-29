# 本地可修复标准工作树分类 - 2026-06-28 R1

## 结论

当前工作树不是“全错”，而是产品代码、验收测试、文档、发布链路和生成证据混在同一个未提交状态里。按用户当前口径，本轮只收口本地产品框架、后端交付 UI、前端交付状态和可修复分类；发布包、Release、下载页、公钥注入、线上发布不进入本轮完成口径。

## 本轮已收口

- 前端交付框架：`src/ui/index.html`
  - 网站、增值业务、代理中心不再隐藏右侧账号/权益/交付状态栏。
  - 非 Agent 模块保留诊断日志和 300px 右栏，隐藏 Agent 专属五维矩阵和步骤进度。
  - 非 Agent 模块按服务端边界显示交付状态：网站入口、增值业务商品快照、代理中心 `agent_center` 快照。
  - 本地交付 UI 不再把发布包、Release、下载入口作为当前步骤焦点。

- 回归测试：`tests/test_panghu_commercial_manifest.py`
  - 新增 UI 合同测试，防止后续再次把右侧交付栏和日志在非 Agent 模块隐藏。

- 证据截图：`outputs/ui-delivery-framework-20260628-r1/`
  - `site-right-rail.png`
  - `value-added-right-rail.png`
  - `agent-center-right-rail.png`
  - `agent-matrix-right-rail.png`

## 当前未提交改动分类

### A. 本地产品框架核心

这些文件属于本地可修复标准的主体，后续提交时应作为一个或多个产品交付提交处理：

- `src/ui/index.html`
- `src/panghu_codex_installer.py`
- `src/commercial_api.py`
- `src/commercial_backend_contract.py`
- `scripts/agent_delivery_acceptance.py`
- `scripts/commercial_flow_acceptance.py`
- `scripts/customer_web_entry_acceptance.py`
- `tests/test_agent_delivery_acceptance_script.py`
- `tests/test_commercial_api.py`
- `tests/test_commercial_backend_contract.py`
- `tests/test_commercial_flow_acceptance.py`
- `tests/test_panghu_commercial_manifest.py`
- `tests/test_customer_web_entry_acceptance.py`
- `src/ui/assets/`

### B. 项目文档和验收口径

这些文件用于解释当前本地交付状态、边界和维护方法，适合随产品框架一起审阅：

- `ACCEPTANCE.md`
- `BACKEND_CURRENT_WINDOW_HANDOFF.md`
- `FINAL_REPORT.md`
- `PLAN.md`
- `PROJECT_BLUEPRINT.md`
- `README.md`
- `RUNBOOK.md`
- `TASK_GRAPH.md`
- `docs/COMMERCIAL_BACKEND_API_CONTRACT.md`
- `docs/PRODUCT_MANUAL_SINGLE_SOURCE_OF_TRUTH.md`
- `docs/TECHNICAL_MAINTENANCE_MANUAL.md`
- `docs/发送客户说明.txt`

### C. 发布链路相关，本轮不收口

用户已明确“发布包不用管”，所以这些文件当前只保留现状，不作为本轮完成判断：

- `.github/workflows/build-mac-release.yml`
- `scripts/build-mac-app.command`
- `scripts/build-windows-exe.ps1`
- `scripts/commercial_release_acceptance.py`
- `scripts/generate-download-qr.py`
- `tests/test_commercial_build_scripts.py`
- `tests/test_commercial_release_acceptance.py`

### D. 验收证据和生成输出

这些是截图、审计输出或历史验收材料。不要直接删除；清理前应另走“盘点后审批”流程。

- `outputs/capture_ui_preview.py`
- `outputs/panghu-installer-*.png`
- `outputs/R1-DELIVERY-A-C-F/`
- `outputs/delivery-evidence-20260627-r8/`
- `outputs/ui-all-20260626-correct/`
- `outputs/ui-all-20260626/`
- `outputs/ui-b-level-20260627-r2/`
- `outputs/ui-b-level-20260627-r5-qa/`
- `outputs/ui-b-level-20260627-r7-header-recheck/`
- `outputs/ui-b-level-20260627-r8-desktop-qa/`
- `outputs/ui-b-level-20260628-r1-frontend-b-acceptance/`
- `outputs/ui-delivery-framework-20260628-r1/`
- `outputs/ui-review-20260626-round2/`
- `outputs/test_out.png`
- `outputs/local-repairability-20260628-r1/`

### E. 本地依赖和临时工作区

这些不是产品源码。删除或迁移前必须先确认没有测试脚本依赖当前状态：

- `node_modules/`
- `package.json`
- `package-lock.json`
- `scratch/`

## 验证记录

- `python -m pytest tests\test_panghu_commercial_manifest.py -q`
  - 结果：65 passed, 11 subtests passed
- `python -m unittest discover -s tests -p "test_*.py"`
  - 结果：298 tests OK
- `python src\panghu_codex_installer.py --self-test`
  - 结果：UI self-test OK
- `.venv\Scripts\python.exe scripts\customer_web_entry_acceptance.py`
  - 结果：`web_entry_status=ready`
- `python scripts\commercial_flow_acceptance.py --json`
  - 结果：`status=PASS`
- 浏览器插件本地 HTTP 预览
  - URL：`http://127.0.0.1:3188/index.html?preview=agent&module=site`
  - 结果：页面非空、控制台无 error/warn、右栏显示、日志显示、非 Agent 模块矩阵和进度隐藏。

## 仍未计入完成

- 真实服务端、数据库、支付、正式 token、公钥注入、正式 Release、下载页授权。
- 真实 Agent Runtime Adapter 和真实平台回调。
- 对历史 `outputs/`、`scratch/`、`node_modules/` 的删除或归档清理。
