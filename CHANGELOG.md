# 变更记录

## 2026-07-03（R3-DOCS-01 文档收尾）

- 记录 R3 连接通讯软件守卫完成项：服务端合同新增平台回调跨会话隔离和入站消息匹配守卫，防止其它会话或不匹配消息污染验收。
- 记录客户端状态刷新修正：服务端返回 `False` 时覆盖本地旧 `True`，避免旧完成态残留。
- 记录 focused 验证：`python -m pytest tests\test_commercial_backend_contract.py tests\test_installer_backend.py -q -k "communication_software_link" -p no:cacheprovider` -> `24 passed, 54 deselected`。
- 保留未完成边界：这仍不是生产真实闭环；真实平台、Runtime Adapter 生产接入、支付/账本生产记录仍未完成。

## 2026-07-03（团队模式代码推进轮）

- 修正 `src/ui/index.html` 客户运行资产：默认非 preview 状态不再携带示例买家/代理账号，不再硬编码演示次数、设备数、授权日期或全量通过的 Agent 矩阵。
- 修正代理中心和通用服务入口假成功态：将“通道激活”“已连接”“已完成检验”“服务端快照已返回”等客户可误解为真实闭环的文案改为等待服务端确权和同步。
- 修正连接通讯软件一键流程边界：客户端一键连接现在只执行订单/会话/测试/本地预检，不再自动提交真实验收；客户 UI 和 bridge 文案同步改为“一键连接并本地预检”，明确本地预检不能替代平台回调。
- 补强连接通讯软件本地合同闭环：离线合同层要求验收必须绑定已接受的平台回调、Agent Runtime Adapter 成功结果和唯一 `source_event_id`；API 解析新增真实服务、平台回调、Runtime Adapter、验收状态和服务端显式完成声明字段；客户端只展示这些服务端字段，不本地推断真实交付完成。
- 新增 WebView 客户资产静态守卫测试，防止示例账号、演示商业数值和假成功态重新进入 `src/ui/index.html`。
- 补齐前端键盘焦点态、减少动画媒体查询，并把部分裸色值收敛到 CSS token，使 Gemini 风格审计从 FAIL 降为 PASS（仍有设计债级 warning）。
- 本轮重新执行本地验证：全量 pytest `330 passed, 187 subtests passed`，客户端自检通过，商业流程离线验收 `PASS`，前端结构检查通过，Gemini 风格审计 `PASS`。
- 轻量发布前检查仍为 `WARN`：三端客户包缺失，商业清单生产公钥未注入；本轮未打包、未发布、未提交。

## 2026-07-03（第二轮：文档结构合并）

经用户批准执行文档结构合并，根目录文档从 23 个收敛为 12 个。只动文档，未改源码、脚本、测试或版本控制状态。

合并映射：

- `PROJECT_BLUEPRINT.md` → 并入 `PRODUCT.md`（产品说明与项目蓝图）。
- `BACKEND.md`、`FRONTEND.md`、`DESIGN.md` → 并入 `ARCHITECTURE.md`（架构与工程边界）。
- `PLAN.md`、`TASKS.md`、`TASK_GRAPH.md` → 并入 `FINAL_REPORT.md`（当前状态、任务节点、阻塞、下一步的唯一归口）。
- `DEPLOYMENT.md` → 并入 `RUNBOOK.md`（运行、验证与发布手册）。
- `SAFETY.md` → 并入 `SECURITY.md`（安全与边界）。
- `ENGINEERING_CLOSEOUT.md`、`PRODUCT_TREE_MASTER_CONTROL_HANDOFF_2026-06-30.md` → 并入 `HANDOFF.md`（交接与工程盘点，含产品树主控指引）。

同轮修正：

- 文档权威顺序改为只在 `AGENTS.md` 维护，`README.md` 改为文档地图并引用。
- 修正 `ACCEPTANCE.md` 重复的“## 0”章节和“进入 F 级”笔误（应为发布前阶段 I 级）。
- 修正 `FINAL_REPORT.md` 章节乱序（原 6/7 倒置）和“本轮返回”时态（统一为“最近记录”）。
- 修正 `INTEGRATION.md` 章节乱序（8.3/8.4 倒置）。
- 更新 `docs/TECHNICAL_MAINTENANCE_MANUAL.md` 三处对已合并文件的引用。
- 更新 `RUNBOOK.md` 连接通讯软件回归 rg 命令的文件清单为合并后文件。
- 合并前已确认 `tests/`、`scripts/`、`.github/` 对被合并文档无路径依赖；`tests/test_commercial_backend_contract_docs.py` 要求的 README 关键短语全部保留。

## 2026-07-03

- 文档一致性修正：重写 `文档梳理报告_2026-07-03.md`，删除源码缺失/目录失真口径；验证数字统一归口到 `TESTING.md` 的历史记录表。
- 收敛当前状态口径：`FINAL_REPORT.md`、`TASKS.md`、`RUNBOOK.md`、`HANDOFF.md`、`PLAN.md`、`TASK_GRAPH.md`、`ACCEPTANCE.md` 不再重复维护 pytest/unittest 具体数量。
- 明确当前未见 `outputs/` 和 `.venv`；历史截图和 `.venv` 网站入口检查只作为历史记录，复验需重建环境或重新运行截图脚本。
- 修正前端状态：当前客户 UI 入口仍是 `src/ui/index.html`；已清理的是旧 WebView shell、旧截图和旧输出证据，B 级视觉验收待用当前脚本复验。
- 修正代理中心和连接通讯软件口径：本仓可控范围限于文档合同、离线守卫、请求构造和测试边界；真实服务端、平台通道、生产闭环仍未完成。
- 新增 `ENGINEERING_CLOSEOUT.md`，集中记录项目身份、权威材料顺序、根目录文件分类、工程化闭环八类职责、混乱点和待确认问题。
- 新增 `HANDOFF.md`，作为后续窗口接手入口，记录当前目标、已完成、未完成、阻塞、验证结果和下一步。
- 新增 `FRONTEND.md` 和 `DESIGN.md`，记录当前 WebView UI 入口、Python bridge 契约、四个一级模块、设计 token、截图验收和 UI 禁止改动区。
- 在 `README.md` 和 `AGENTS.md` 增加工程化盘点入口，便于后续 Codex / 其他 agent 接手时先确认文件边界。
- 更新 `TASKS.md` 和 `FINAL_REPORT.md`，把本轮工程化整理与仍待确认的删除标记、缓存/输出清理、发布边界分开。
- 收紧 `.gitignore`，补充更多本地缓存、覆盖率、日志和输出目录规则；未删除、移动、重命名任何项目文件。
- 用户确认后清理本地可重建内容：`.pytest_cache/`、`.venv/`、`outputs/`、空 `legacy/` 目录和源码/脚本/测试下的 `__pycache__/`。这些不是项目交付材料；后续 pywebview / 打包相关检查需要先重建 `.venv`。
- 全仓扫描并统一旧名称口径：客户可见应用名、发布包名、CI artifact、验收脚本和旧计划文档统一为 `胖虎AI客户端` / `胖虎AI客户端-*.zip`；移除历史英文包名前缀、历史多 Agent 工具名和旧 release alias。
- 纠正项目身份残留口径：本地用户入口和本地 git root 统一为 `C:\Users\Administrator\Documents\codex\胖虎AI客户端`；`panghu-ai-client` 是 GitHub 远程仓库 slug。

## 2026-06-30

影响范围：仓库入口文档、运行手册和源码整理基线。

- 建立源码仓整理基线：补齐仓库入口级 `AGENTS.md`、`PRODUCT.md`、`ARCHITECTURE.md`、`BACKEND.md`、`TESTING.md`、`SECURITY.md`、`DEPLOYMENT.md`。
- 记录本轮本地验证结果：前端结构、自检、Gemini 风格审计、商业硬编码扫描、商业流程离线验收和 pytest 均通过。
- 明确当前不能发布：轻量发布验收仍为 WARN，三端客户包陈旧，Mac 包仍为旧名历史包，商业清单生产公钥未注入。
- 按用户授权清理旧客户包、历史构建产物、临时日志、历史截图、候选图和历史 handoff；后续客户包必须重新打包。
- 新增 `INTEGRATION.md`，把手机号接码控制中心和 Plus session.脚本工具纳入胖虎AI客户端增值业务集成图；同步服务目录合同、验收标准、状态报告和客户端入口文案。
- 按中转站产品边界交接口径统一主从关系：胖虎AI客户端是主产品；胖虎AI中转站、手机接码、Plus 充值 / Plus 订阅、连接通讯软件、代理中心都是客户端功能区或分支服务；中转站只作为 API 网关分支，不写作平台主后台或客户端后台。
- 增加 `value_added_services` 客户端底座：服务目录纳入商业 manifest 签名控制，客户端解析时过滤敏感字段，并把安全目录同步到 WebView；前端在有服务端目录时优先用服务端入口，没有目录时继续使用过渡静态入口。
- 删除 `legacy/` 下旧一键安装脚本、旧 UI 安装脚本和旧客户说明；这些文件属于历史废弃客户端材料，不再参与当前源码交付。
- 重新生成当前 WebView UI 本地截图证据：登录闸口、配置 Agent、胖虎AI网站、增值业务、代理中心和 1365 宽度配置页。
- 明确跨项目分工：`sim.aitokenapi.cc` 生产 HTTPS 收尾由手机号接码控制中心窗口负责；本仓继续处理客户端入口、服务目录和 Plus 对接口径。
- 保留发布边界：本轮未 stage、未 commit、未发布。

回滚：如需撤销本轮文档整理，只回滚本轮新增入口文档和 `RUNBOOK.md` / `README.md` / `ACCEPTANCE.md` 的新增说明，不触碰其他窗口留下的业务代码改动。

残留风险：三端客户包已清空，发布前必须重新构建并重新验收；当前仍未注入商业清单生产公钥；手机号接码控制中心和 Plus session.脚本工具仍未完成生产端到端验收。
