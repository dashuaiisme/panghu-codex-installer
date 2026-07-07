# 当前状态报告

最后更新：2026-07-07

> **当前状态基线（2026-07-07，最新）——以此为准，下方 07-04 及更早为历史增量记录：**
> - 型号：`gpt-5.5`（codex/openclaw/hermes）/ `claude-opus-4-8`（中划线）/ `gemini-3.5`（中转站未接入，真机不通）。旧型号 `gpt-5.4`/`claude-opus-4.8`(点) 已废弃。
> - 安装（第4步，仅安装不扣次）与写入配置（第5步，写配置+验收+扣次）已拆成两个独立步骤。
> - 支付走支付宝 WAP（`alipay.trade.wap.pay`）：工具订单与连接通讯软件订单均返回 `payment_url`，客户端本地生成二维码。
> - 连接通讯软件(#4)为服务端自动验收，已接支付宝自助付款并上线生产。
> - 客户端模式（Claude/Gemini 客户端）装好 + 写入配置即验收合格，不做联网验收；撤单退款走管理员后台人工；结算默认 T+7、后台可配。
> - 客户端最新测试：`367 passed`（以 `TESTING.md` 为准）；服务端 `164 passed`，已上线生产。
> - tkinter 旧桌面界面已确认永不执行并清除约 1826 行死代码；当前 UI 仅 WebView(HTML) 一套。
> - 当前活跃交接见 `docs/交接说明_2026-07-07_Claude.md` 与 `CHANGELOG.md`。

## 0.-1 2026-07-04 增量（第四轮：本地联调全链收口）

## 0.-1 2026-07-04 增量（第四轮：本地联调全链收口）

- **五个 Agent（Codex/ClaudeCode/OpenClaw/Hermes/Gemini-agy）在本地联调栈全部走通完整商业链路**：权益→门禁→预占→安装→配置→真实 CLI 中文对话验收→扣次→交付矩阵。失败不扣次守卫验证生效。
- 后台管理系统已对齐客户端合同（含 16 项跨项目集成测试）并补齐第 4 类佣金事件 tool_order_paid；**后台 77 测试、客户端 359 测试全绿**。
- 代理中心已用本地后台真数据走通：申请→审批→客户端同步 L1 快照。
- 5 个合同歧义点已全部决议并记录（CHANGELOG 第三、四轮条目）。
- 剩余：增值业务目录数据（底座已就绪）；生产部署（待用户批准 + PRODUCTION_LOCK 流程，联调环境所有开关生产构建默认关闭）。

## 0.0 2026-07-04 增量（第二轮：登录后链路全面打通）

- 用户真实账号登录后"很多链路没打通"已定位为五类断链并全部修复（busy 泄漏、Tk messagebox 全失效、evaluate_js 启动竞态锁死、toast 登录后不可见、算力文案误导），详见 `CHANGELOG.md` 2026-07-04 第二轮条目。
- 真机验证已通：会话恢复、检查更新（自动+手动）、环境诊断前置提示、Codex 模式检测、配置健康巡检、网关测速、快照列表、登录失败中文提示。359 tests + 187 subtests 全绿。
- 仍受限：买家购买/扣次/部署/对话验收链路需要账号有活跃权益（当前测试账号"无可用权益"），须服务端发测试权益后才能真机走通。

## 0.1 2026-07-04 增量（Claude Code CLI 接手轮）

- 登录阻塞项已在 Windows 真机修复并验证：前端重复 `submitLogin` 覆盖 + webview 模式 Tk 变量跨线程崩溃两个根因均已消除（详见 `CHANGELOG.md` 2026-07-04 条目）；假账号真机走通"点击→正在登录→失败原因红条→按钮恢复"完整反馈链路，界面全程不卡死。
- 全量测试首次在 Windows 本机复验通过：358 passed + 187 subtests；07-03 各批次"需 Windows 复验"标记全部清账。
- 待办：真实账号登录成功路径（切进配置流程）待用户验证；随后按 `docs/Codex三模式真机验证清单_2026-07-03.md` 推进。

## 0. 本文件职责

本文件是项目状态的单一事实来源（原 `PLAN.md`、`TASKS.md`、`TASK_GRAPH.md` 已并入本文件），只负责：

- 当前阶段与真实状态
- 当前已验证项
- 任务节点与依赖
- 当前未完成项、阻塞与待决策项
- 下一步建议

本文件不是产品手册、技术手册、运行手册或蓝图。验证数字统一见 `TESTING.md` 的历史验证记录表，本文件不重复维护具体通过数量。

## 1. 当前结论

当前仍不是整体交付收口状态。

当前阶段：源码仓整理与文档收束已完成，处于后端审计与功能闭环补齐阶段，不处于正式发布阶段。

- 工程文档体系已收束（2026-07-03 完成第二轮结构合并，根目录文档从 23 个收敛为 12 个）
- 本地代码健康、网站入口前提和离线商业合同验收已有明确结果（历史记录见 `TESTING.md`）
- 旧 WebView shell 和历史客户包/截图/临时产物已清理，当前 WebView 前端以 `src/ui/index.html` 为准
- CLI-only 交付范围有历史本机真实最小对话验收记录
- 客户端 scope、Gemini / agy、连接通讯软件真实闭环、代理中心真实服务端仍未完成
- 未进入打包发布和生产下载入口更新

## 2. 当前已验证

- 登录闸口与登录后主控制台的分层已回到正确方向。
- `profile.json` 持久化出口已收紧：不保存部署 token、密码或商业污染字段；买家会话恢复走独立 cookie/WebView profile，可选记住密码记录走本机系统加密账号库。
- 商业 API 主程序分发器已收紧：邀请码绑定/注册必须走胖虎AI网站内置浏览器，桌面端不提供本地代操作、绑定、下单或支付查询入口。
- 买家自助购买状态节点已独立为当前登录买家链路。
- 当前商业 API 请求构造只围绕当前登录买家上下文；订单、支付、权益和配置会话不得使用本地代操作会话字段。
- `胖虎AI网站` 顶级模块默认落点已改为网站首页，不再默认先落到“账号中心”子页。
- `src/ui/index.html` 已移除默认客户运行资产中的示例账号、演示次数/设备数和“通道激活/已连接/已完成检验”等假成功态；服务端入口、代理中心和预览态均回到等待服务端确权口径。
- 产品手册、维护手册、后端合同、验收和安全文档已同步该口径。
- 代理中心架构边界已入文档（文档合同层面）：代理中心是登录后的独立代理业务模块；离线服务端合同覆盖代理产品、公开招商内容、代理申请审核、五级链路、三类佣金事件、T+7 结算申请和管理员账本冻结/解冻/冲正。真实服务端实现未完成，见第 5 节。
- 客户端 API 合同已新增代理公开招商、下游客户、佣金账本、结算申请、后台产品、政策、营销内容、审核、结算和账本动作请求构造；桌面端仍只展示服务端快照和入口，不计算费用、等级或返佣。
- `agent_center` 已纳入商业 manifest 签名控制字段，避免收益和结算快照绕过服务端签名保护。
- 产品手册和商业后端合同已同步：胖虎AI管理员后台需要“代理业务管理”，公开招商页固定为 `/agent/join`。
- 连接通讯软件已完成文档合同口径收束，并补齐本地合同/客户端边界：定位为“配置Agent”模块内的独立增值服务，必须独立订单、独立配置会话、独立验收、独立收费；客户端一键连接只创建订单/会话、发起测试并生成本地预检字段，不自动提交真实验收。R3 已补齐服务端合同守卫：平台回调必须隔离跨会话污染，入站消息必须匹配当前会话；客户端刷新服务端状态时会用服务端返回的 `False` 覆盖本地旧 `True`，避免旧完成态残留。离线合同层已要求验收必须绑定服务端已接受的平台回调、Agent Runtime Adapter 成功结果和唯一 `source_event_id`；客户端可展示服务端真实闭环字段，但默认不得本地声明完成。真实服务端闭环仍未完成，见第 5 节。
- R5 已补齐买家机器人创建/注册/凭证填写引导：`src/ui/index.html` 新增引导卡片，提供官方入口，并说明需要回填 `platform_account_id`、`platform_chat_id`、`gateway_mode`、回调地址和验签密钥；`tests/test_panghu_commercial_manifest.py` 增加防回归断言。该项只是连接通讯软件真实接入前置条件和买家填表链路，不代表真实平台回调、Runtime Adapter 或服务端验收闭环已完成。
- 客户端主从关系已统一：胖虎AI客户端是主产品和统一入口；中转站只写作 API 网关分支。
- 跨项目增值业务集成图已建立（见 `INTEGRATION.md`）；客户端已具备 `value_added_services` 服务目录底座：签名控制、敏感字段过滤、WebView 目录同步；没有服务端目录时继续使用当前过渡入口。
- 自动化测试基线可运行；内置网站入口映射和 WebView 前提脚本可运行。
- Agent 交付验收脚本已支持 `delivery_scope=cli|client|both` 和 `--agents` 精确选择；CLI 与客户端按独立付费、独立交付范围验收。
- CLI-only 交付范围有历史本机真实最小对话验收记录：Codex、ClaudeCode CLI、OpenClaw CLI、Hermes CLI 均曾通过胖虎AI网关返回“胖虎AI配置验证成功”；验收命令不写入 API Key，记录结果为 `exit 0`，`blocking_gaps=[]`。
- Gemini / agy 配置链路代码已实现（写 `~/.gemini/.env` 走胖虎AI网关 Gemini 格式，型号 `gemini-3.5`），但中转站 gemini 尚未接入、真机未验收，因此对外仍按「待接入」展示；代码存在 ≠ 已验收交付。
- Codex 三种配置模式的本地代码与文档已同步：普通模式、双态模式、官方直登；模式切换有本机快照机制（`~/.codex/panghu_modes/`）。
- 历史记录中 `.venv\Scripts\python.exe scripts\customer_web_entry_acceptance.py` 返回 `web_entry_status` = `ready`；当前未见 `.venv`，后续需重建后复验。
- 旧 WebView shell、旧截图、历史输出报告、临时日志、历史 handoff、旧构建目录和旧客户包已清理；当前客户 UI 入口仍是 `src/ui/index.html`。
- 截图脚本为 `scripts/capture_ui_preview.py`，输出目录 `outputs/` 属可重建产物，不提交源码仓；2026-07-03 复核轮已重新生成 6 张当前截图证据。
- `legacy/` 下旧材料已按用户授权删除；旧名称口径已全仓清扫。
- 2026-07-03 已按用户确认清理本地可重建内容：`.pytest_cache/`、`.venv/`、`outputs/`、空 `legacy/` 目录和 `__pycache__/`。
- `commercial_flow_acceptance.py --json` 最近记录为 `status=PASS`，但必须按 `offline_only` / `offline_guarded` / `mock_guarded` 口径理解。
- `commercial_release_acceptance.py --json` 最近记录为 `status=WARN`，原因是旧客户包已清理、三端本地客户包缺失、未注入商业清单生产公钥。

## 3. 任务节点图

| ID | 节点 | 依赖 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| N01 | 文档权威顺序与职责边界收束 | 无 | verified | 2026-07-03 完成第二轮结构合并：23 个根目录文档收敛为 12 个 |
| N02 | 文档一致性检查 | N01 | verified | 验证数字归口 `TESTING.md`；状态归口本文件；真实服务链路仍单列未完成 |
| N03 | 后端与主程序实现偏差审计 | N02 | verified_with_minor_notes | 2026-07-03 完成合同↔实现逐项对照审计：27/27 路由覆盖、字段一致、敏感字段过滤完整、幂等键全覆盖、主程序 22 个调用点全走构造器无绕过。已修复 `build_payment_poll_request` 缺操作者校验；遗留 2 个待澄清项见第 6 节 |
| N04 | 后端修正任务拆分 | N03 | pending | 可并行子任务、范围和验证命令 |
| N05 | 登录 / 授权 / profile 边界修正 | N04 | verified | `profile.json` 不保存可恢复登录 token；商业 API 只接受当前登录买家上下文 |
| N06 | 商业合同 / 配置会话 / 扣次边界修正 | N04 | in_progress | 离线验收 PASS（offline/mock 范围）；真实服务端链路未完成 |
| N07 | 代理中心服务端合同与下游返佣边界 | N04 | in_progress | 文档合同、离线守卫、请求构造和测试边界已覆盖；真实服务端实现和后台界面未验收 |
| N08 | 连接通讯软件独立增值服务合同 | N02,N04 | in_progress | 文档合同、离线合同状态机、API 字段解析、跨会话/入站消息匹配守卫和客户端服务端状态刷新守卫已收束；真实平台、Runtime Adapter 生产接入、支付/账本生产记录未完成 |
| N09 | 目标 Agent 真实能力边界复核 | N04 | in_progress | 五个 Agent（含 Gemini / agy，2026-07-03 接入完整配置链路）按真实配置链路验收；真实机器对话验收待执行 |
| N10 | 文档与代码二次对照验收 | N05-N09 | in_progress | 本轮已重新执行本地代码和前端结构验证；验证数字统一见 `TESTING.md` |
| N11 | B 级截图与验收状态更新 | N10 | locally_verified | 已用 `scripts/capture_ui_preview.py` 重新生成 6 张当前截图；仅代表本地 UI 结构与视觉证据 |
| N12 | 本地轻量发布前检查 | N10 | blocked | 最近记录 `WARN`：三端客户包缺失、未注入商业清单生产公钥 |

## 4. 本轮验证记录（2026-07-03）

团队模式代码推进轮已重新执行本地验证：

- py_compile、全量 pytest、客户端自检、商业流程离线验收、前端结构检查、截图脚本和 Gemini 风格审计通过。
- `customer_web_entry_acceptance.py` 当前系统 Python 下为 `blocked`：未加载 `pywebview`，不能声明内置网站闭环完成。
- `agent_delivery_acceptance.py` 默认只读检查为 `blocked`：未执行最小中文对话，多个客户端 scope 未确认，Gemini / agy 配置待开发。
- 轻量发布前检查仍为 `WARN`，阻塞为三端客户包缺失和商业清单生产公钥未注入。
- R3 focused 验证记录：`python -m pytest tests\test_commercial_backend_contract.py tests\test_installer_backend.py -q -k "communication_software_link" -p no:cacheprovider` -> `24 passed, 54 deselected`。
- R5 验证记录：机器人创建/注册/凭证填写引导 focused `28 passed, 74 deselected`；全量 `338 passed, 187 subtests passed`；`commercial_release_acceptance.py --json` 仍为 `WARN`。
- 项目文件审计仍有文档结构 warning，主要来自文档合并后旧审计脚本仍查找独立 `TASKS.md`、`DEPLOYMENT.md` 等文件。

具体命令、结果和当前可用性见 `TESTING.md`。

## 4.1 文档合并轮验证记录

本轮只做文档合并与口径修正，未重新执行代码测试。文档级检查：

- 合并前已确认 `tests/`、`scripts/`、`.github/` 对被合并文档无路径依赖（唯一代码侧断言在 `tests/test_commercial_backend_contract_docs.py`，只要求 README 保留权威手册指向，已保留）。
- 合并后已全仓扫描被删除文件名残留引用并修正。

历史验证记录统一见 `TESTING.md`。

## 5. 当前未完成

- 真实网页登录、注册、邀请码、充值购买、支付、创建 API Key 闭环验收。
- 客户端 scope（2026-07-03 修正版口径已实现）：Codex / ClaudeCode（Claude Desktop）/ Gemini-agy（Antigravity）做真实客户端交付，客户端安装检测已实现；OpenClaw / Hermes 只销售 CLI，client scope 明确不适用。客户端内最小中文任务的自动化验收和真实客户机器交付验收仍未执行。
- Gemini / agy 配置链路代码已实现（写入 `~/.gemini/.env` 走胖虎AI网关 Gemini 格式，`agy -m <模型> -p` 对话探针）；真实客户机器上的安装、启动检测和最小中文对话验收尚未执行，未通过前不计完整交付。
- Codex 三模式在真实客户机器上分别完成重开 Codex 后的最小对话验收。
- 代理中心真实服务端实现和数据闭环（token 返佣、下游付费激活返佣、付费安装 Agent 返佣、下游客户归因、结算状态、管理员后台“代理业务管理”）。当前只完成离线合同、请求构造、文档合同和测试守卫。
- 连接通讯软件真实平台、Runtime Adapter 生产接入、支付/账本生产记录和生产端到端闭环仍未完成；当前只完成本地合同状态机、API 请求/解析、跨会话/入站消息匹配守卫、客户端订单/会话/测试/本地预检、买家机器人创建/注册/凭证填写引导和服务端状态展示边界，不代表真实平台已接通。
- 手机号接码控制中心与本客户端的生产打通（`sim` 子域名和 HTTPS 收尾由接码项目窗口负责）。
- Plus session.脚本工具生产打通：`license.aitokenapi.cc` 激活服务、支付后发码、履约队列、真实 Plus 自动化、日志回写、退款/失败重试和人工复核闭环。
- 三端客户包重新打包、Release、下载页和 `latest.json` 更新。
- 后端和主程序的商业合同边界逐项审计。
- B 级截图已重新生成当前本地证据，但仍不代表真实网页登录、Agent 对话、服务端代理中心、连接通讯软件或发布完成。

## 6. 当前阻塞与待决策项

阻塞：

- 后端合同与主程序实现还未做完逐项对照。
- 代理中心真实服务端和管理员后台尚未验收，不能把代理中心写成已完成业务闭环。
- 连接通讯软件仍需完成真实平台、Runtime Adapter 生产接入、支付/账本生产记录和生产验收链路；R3 守卫只覆盖合同、状态刷新和本地 focused 验证范围，R5 机器人引导只覆盖买家填表前置链路。
- 跨项目增值业务仍需胖虎AI服务端真实提供 `value_added_services` 服务目录和摘要接口；客户端底座已准备好，真实生产目录未接入。
- 轻量发布前检查最近记录为 `WARN`，不能作为进入客户分发或生产下载入口更新的依据。
- 当前系统 Python 未加载 `pywebview`，网站入口验收脚本会阻断内置网站闭环；需要重建含 `pywebview` 的 `.venv` 后复验。

待用户决策：

- 是否提交当前工作树的删除标记（历史 handoff、旧 `legacy/` 文件、旧 `outputs/` 报告）和本轮文档合并改动。
- 是否先单独提交工程化整理，还是等业务代码收束一起提交。
- 本阶段是只售卖 CLI-only，还是继续推进客户端 scope。
- N03 审计遗留待澄清：`build_order_create_request` / `build_config_session_reserve_request` 的 `delivery_scope` 默认值 `codex_agent_config` 不在合同允许值（cli/client/both）内，默认值定什么取决于交付范围决策；连接通讯软件回调是否需携带 `delivery_scope`/`service_type` 标记需服务端澄清。
- 商业清单生产密钥对尚未生成：注入机制已完备（构建脚本读 `PANGHU_COMMERCIAL_MANIFEST_PUBLIC_KEY_PEM`，CI 读同名 GitHub Secret，`scripts/commercial_manifest_signer.py generate-keypair` 可生成 Ed25519 密钥对），需用户在本机生成并妥善保管私钥后配置公钥。

## 7. 最近通过的检查

命令清单见 `RUNBOOK.md`，历史数字见 `TESTING.md`。要点：

- 代码健康、unittest、focused pytest 和全量 pytest 的历史记录统一见 `TESTING.md`；团队模式代码推进轮已重新执行全量 pytest。
- 商业合同离线验收最近记录 `PASS`（`offline_only` / `offline_guarded` / `mock_guarded` 范围）。
- 商业轻量发布前检查最近记录 `WARN`（三端客户包缺失、未注入商业清单生产公钥）。
- 历史 CLI-only 验收记录 `exit 0`，`blocking_gaps=[]`。
- 这些结果只代表代码健康、网站入口前提、离线合同和已有回归测试通过；不代表项目整体收口。

## 8. 无法验证记录

本轮未验证生产服务器、真实数据库、真实支付回调、真实客户设备、GitHub Release、下载页和 `latest.json`。原因：当前任务是源码仓整理和文档收束，尚未进入重新打包、生产或发布阶段。

## 8.1 开源对标功能补足进度（2026-07-03 起）

方案见 `docs/开源对标功能补足方案_2026-07-03.md`。
- 第一批（配置快照层 + 一键恢复）：后端逻辑+测试完成，Windows 已复验 5/5 通过。
- 第二批（配置漂移巡检 + 一键修复）：后端逻辑+测试完成（沙箱等价验证通过，待 Windows 复验）。
- 第三批（配置健康 UI）：bridge 方法 + index.html "配置健康"面板（快照列表/一键恢复/漂移红黄灯/一键修复）完成，待 Windows 复验前端结构检查与 self-test。
- 第四批（网关线路测速 P1）：后端+bridge+UI+测试完成（沙箱等价验证通过，待 Windows 复验）。
- 后续批次：用量面板（P1，阻塞于中转站统计接口）、MCP 管理/提示词模板/配置导入（P2，MCP 管理做成免费+增值可后台切换）。

## 9. 下一步

1. 完成客户端 scope 的真实检测、交付和客户机器验收，或明确本阶段只售卖 CLI-only。
2. 让胖虎AI服务端补真实 `value_added_services` 服务目录和摘要接口，客户端即可从过渡入口切到服务端目录驱动。
3. 继续完成手机号接码控制中心和 Plus session.脚本工具的生产部署与真实端到端验收。
4. 继续完成后端合同、代理中心真实服务端数据闭环和连接通讯软件真实平台 / Runtime Adapter / 支付账本生产闭环。
5. 需要进一步视觉复核时，使用本轮 `outputs\panghu-installer-*.png` 或重新运行 `python scripts\capture_ui_preview.py` 生成 B 级截图证据。
6. A 到 H 级全部通过后，重新打包三端客户包，再进入 Release、下载页和 `latest.json` 更新。
