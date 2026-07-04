# 交接与工程盘点

最后更新：2026-07-03

本文件是后续窗口 / agent 的统一接手入口（原 `ENGINEERING_CLOSEOUT.md` 和 `PRODUCT_TREE_MASTER_CONTROL_HANDOFF_2026-06-30.md` 已并入本文件）。

## 1. 项目身份

| 项目项 | 当前口径 |
| --- | --- |
| 客户可见名称 | 胖虎AI客户端 |
| 用户可见入口 / 本地 git root | `C:\Users\Administrator\Documents\codex\胖虎AI客户端` |
| GitHub 远程仓库 | `https://github.com/dashuaiisme/panghu-ai-client` |
| 长期登记 | `C:\Users\Administrator\Documents\codex\工具项目目录\projects\胖虎AI客户端.md` |

`panghu-ai-client` 是 GitHub 远程仓库 slug；本地项目名称和本地根目录统一为 `胖虎AI客户端`。

## 2. 当前目标

把“胖虎AI客户端”作为主产品本体维护：入口清楚、权威文档清楚、工程职责清楚、删除和发布边界清楚。同时以产品树方式统筹关联项目：树根是胖虎AI客户端，树枝是胖虎AI中转站（API 网关分支）、手机号接码控制中心、Plus session.脚本工具、连接通讯软件、代理中心。

权威材料顺序只在 `AGENTS.md` 维护，本文件不重复。

## 3. 根目录文档结构（2026-07-03 合并后）

| 文件 | 职责 | 吸收了 |
| --- | --- | --- |
| `README.md` | 仓库入口摘要 | — |
| `AGENTS.md` | Agent 规则与唯一权威文档顺序 | — |
| `PRODUCT.md` | 产品摘要与项目蓝图 | `PROJECT_BLUEPRINT.md` |
| `ARCHITECTURE.md` | 架构、后端、前端、设计边界 | `BACKEND.md`、`FRONTEND.md`、`DESIGN.md` |
| `ACCEPTANCE.md` | 验收标准（Definition of Done） | — |
| `TESTING.md` | 验证矩阵与历史验证记录（数字唯一归口） | — |
| `RUNBOOK.md` | 运行、验证、构建与发布手册 | `DEPLOYMENT.md` |
| `SECURITY.md` | 安全、商业边界与禁止事项 | `SAFETY.md` |
| `INTEGRATION.md` | 跨项目集成主控（接入卡、服务目录合同） | — |
| `FINAL_REPORT.md` | 当前状态、任务节点、阻塞与下一步（状态唯一归口） | `PLAN.md`、`TASKS.md`、`TASK_GRAPH.md` |
| `HANDOFF.md` | 交接与工程盘点（本文件） | `ENGINEERING_CLOSEOUT.md`、`PRODUCT_TREE_MASTER_CONTROL_HANDOFF_2026-06-30.md` |
| `CHANGELOG.md` | 变更记录 | — |

产品/技术权威仍以 `docs/` 两本主手册和商业合同文档为准。

## 4. 根目录其他内容分类

| 类别 | 当前文件或目录 | 处理口径 |
| --- | --- | --- |
| 源码 | `src/` | 客户端主程序、商业合同模型、WebView UI。整理任务不改业务代码。 |
| 配置 | `.github/`、`.gitignore`、`requirements-build.txt` | `.github/` 属于发布 CI；`.gitignore` 管理本地输出、缓存和构建目录。 |
| 测试 | `tests/` | 本地自动化测试；测试通过不等于真实客户闭环完成。 |
| 脚本 | `scripts/` | 运行、构建、截图、验收脚本。普通工程化整理不运行打包和深度发布验收。 |
| 构建产物 | `build/`、`dist/`、`release/` | 当前根目录未见；若出现，按生成/客户包边界处理，不直接删除。 |
| 日志/缓存 | `.pytest_cache/`、`.venv/`、`tmp/`、`__pycache__/`、`*.log` | 本地环境或缓存，已纳入忽略规则；2026-07-03 已按用户确认清理。 |
| 素材/数据 | `assets/`、`docs/胖虎AI下载二维码.png`、`docs/发送客户说明.txt` | 客户材料和品牌素材，不能按临时文件清理。 |
| 本地证据输出 | `outputs/` | 可重建截图/报告输出，不提交源码仓；需要保留证据时在 `FINAL_REPORT.md` 记录命令和文件名。 |

## 5. 工程化闭环职责

| 职责 | 当前承担材料 |
| --- | --- |
| Agent 规则入口 | `AGENTS.md` |
| 需求/任务/进度状态 | `FINAL_REPORT.md` |
| 架构/决策记录 | `PRODUCT.md`、`ARCHITECTURE.md`、`INTEGRATION.md` |
| 验收标准 | `ACCEPTANCE.md`、`TESTING.md` |
| 变更记录 | `CHANGELOG.md` |
| 运行/发布手册 | `RUNBOOK.md` |
| 安全边界 | `SECURITY.md` |
| 交接/盘点 | 本文件 |

## 6. 产品树主控指引

产品树口径：

```text
胖虎AI客户端
├─ 配置Agent
│  ├─ Codex / ClaudeCode / OpenClaw / Hermes
│  ├─ Gemini / agy：当前只保留官方入口和待接入状态
│  └─ 连接通讯软件：独立增值服务，不能和基础 Agent 配置混成一个扣费/验收
├─ 胖虎AI网站
│  ├─ 登录、注册、邀请码、充值购买、API Key
│  └─ WebView 会话桥接和服务端页面入口
├─ 增值业务
│  ├─ Plus 订阅 / Plus 充值：关联 Plus session.脚本工具
│  ├─ 接码控制台 sms_code：关联 手机号接码控制中心
│  └─ 国外手机卡 / 云号码 phone_card：关联 手机号接码控制中心
├─ 代理中心
│  └─ 代理等级、下游客户、返佣、结算都由服务端/后台控制
└─ 胖虎AI中转站
   └─ 只作为 API 网关分支：API Token、余额扣费、模型调用、用量记录、模型价格、网关侧充值记账、必要 token 返佣
```

接手产品树主控时的必读顺序：

1. `C:\Users\Administrator\.codex\进化.md`
2. 本仓 `AGENTS.md` → `README.md` → `docs/` 三份权威文档 → `PRODUCT.md` → `INTEGRATION.md` → `FINAL_REPORT.md`
3. 关联项目：`C:\Users\Administrator\Documents\codex\工具项目目录\` 下登记文件；`手机号接码控制中心\docs\胖虎AI客户端接入卡.md`；`Plus session.脚本工具\README.md` 和 `INTEGRATION.md`；`胖虎AI中转站\docs\PANGHUAI_PRODUCT_BOUNDARY_HANDOFF.md`

如果某个文件不存在，不要猜；记录为缺口，继续读同项目其他权威文件。

跨项目状态口径、接入卡、验收门和冲突裁决顺序统一见 `INTEGRATION.md`；各 `service_id` 当前均为 `pending_production` 或 `manual_review`，任何服务写成 `available` 前必须满足 `INTEGRATION.md` 的集成验收门。

产品树主控禁止事项：

- 不读项目入口和接入卡就开工；不凭聊天上下文或记忆判断项目状态。
- 不把 `/health 200`、本地测试、本地 mock 或旧交接说明写成生产闭环完成。
- 不把胖虎AI中转站写成平台主后台或客户端后台。
- 不把功能项目本地验收直接写成胖虎AI客户端总体验收完成。
- 不直接修改生产服务器、数据库、DNS、反向代理、支付、钱包、正式 token 或客户数据。
- 不删除、移动、重命名、归档文件，除非用户明确授权且已有清单；不回退当前仓库已有未提交改动。

## 7. 当前未完成与阻塞

- 当前工作树仍有大量未提交业务代码、文档改动和删除标记（含 2026-07-03 两轮文档整理与合并），尚未 stage、commit 或发布；是否提交需用户确认。
- 真实网页登录、充值购买、创建 Key、代理中心真实服务端、连接通讯软件真实闭环、三端客户包和生产下载入口仍未完成（详见 `FINAL_REPORT.md`）。
- `commercial_release_acceptance.py --json` 最近记录为 WARN，不能进入发布。
- 生产、服务器、支付、数据库、账号、密钥、客户数据、Release、下载页和 `latest.json` 都不在当前整理的自动执行范围内。

## 8. 后续维护方式

1. 新需求、任务状态和进度统一进入 `FINAL_REPORT.md`。
2. 改变产品口径时同步 `docs/PRODUCT_MANUAL_SINGLE_SOURCE_OF_TRUTH.md`，不要只改 README。
3. 改变技术接口、构建、发布或脚本时同步 `docs/TECHNICAL_MAINTENANCE_MANUAL.md`、`RUNBOOK.md` 或 `TESTING.md`。
4. 改变架构边界或跨项目职责时同步 `PRODUCT.md`、`ARCHITECTURE.md` 或 `INTEGRATION.md`。
5. 每轮收口在 `CHANGELOG.md` 追加用户可读记录，不把聊天记录当长期变更记录。
6. 验证数字只记录在 `TESTING.md`；其他文档一律引用，不复制数字。

## 9. 风险

- 本地验证不能替代真实客户设备、真实账号、真实支付、真实生产服务端或真实客户包验收。
- 当前仓库有其它窗口或前序任务留下的改动，不能用回退命令统一清空。
- `outputs/` 是可重建输出目录；长期保存验收证据应在 `FINAL_REPORT.md` 记录命令、文件名和生成时间。
