# 文档维护窗口交接说明

最后更新：2026-06-26

## 1. 交接目标

你是专门负责本项目文档维护的 Codex 窗口。

项目路径：

```text
C:\Users\Administrator\Documents\codex\panghu-codex-installer
```

你的目标不是改代码、不是打包、不是发布，而是把当前项目的产品手册、技术维护手册、商业后端合同、蓝图、计划、验收、运行手册、最终状态报告和客户说明维护成同一套口径，防止不同窗口继续按旧上下文跑偏。

## 2. 必读顺序

开始前先读：

```text
C:\Users\Administrator\.codex\进化.md
C:\Users\Administrator\Documents\codex\工具项目目录\README.md
C:\Users\Administrator\Documents\codex\工具项目目录\PROJECTS.md
C:\Users\Administrator\Documents\codex\工具项目目录\projects\多 Agent 一键配置工具.md
```

然后按顺序读本项目文件：

```text
README.md
docs\PRODUCT_MANUAL_SINGLE_SOURCE_OF_TRUTH.md
docs\TECHNICAL_MAINTENANCE_MANUAL.md
docs\COMMERCIAL_BACKEND_API_CONTRACT.md
PROJECT_BLUEPRINT.md
PLAN.md
TASK_GRAPH.md
ACCEPTANCE.md
SAFETY.md
RUNBOOK.md
FINAL_REPORT.md
docs\发送客户说明.txt
```

以下目录不作为当前产品判断依据：

```text
legacy\
docs\superpowers\
```

不得把这些目录作为当前产品判断依据。

## 3. 当前真实状态

当前项目处于：

```text
文档收束完成后的后端审计与功能闭环补齐阶段
```

已基本确认：

- 登录前是胖虎AI账号登录闸口，不展示完整控制台。
- 登录后固定主模块为：配置Agent、胖虎AI网站、增值业务、代理中心。
- 代理中心是登录后的独立代理业务模块。
- 本地客户端不提供代操作会话、第三方账号代登录或本地代理操作者身份。
- `profile.json` 只保存账号提示、API Key、模型和界面偏好，不保存可恢复登录 token 或部署 token。
- Codex 支持普通模式、双态模式、官方直登。
- 注册、邀请码、创建 API Key、充值购买、推广返佣、代理中心都应走胖虎AI网站服务端页面。
- 代理业务商业化合同已补齐到本仓库文档和离线合同层：胖虎AI管理员后台需要“代理业务管理”，公开招商页固定为 `/agent/join`，桌面端只展示服务端 `agent_center` 快照和入口，不计算费用、等级、返佣比例或结算结果。
- `agent_center` 属于商业 manifest 控制字段，必须参与服务端签名验签。
- ClaudeCode、OpenClaw、Hermes 目前只能说代码中有安装、配置、验收框架，不能包装成完整交付；Gemini / agy 当前只保留官方入口和待接入状态。

当前未完成：

- 真实网页登录、注册、邀请码、充值购买、支付、创建 API Key 闭环验收。
- Codex、ClaudeCode、OpenClaw、Hermes 使用真实客户 API Key 的最小中文对话闭环验收；Gemini / agy 配置链路待开发。
- Codex 三模式在真实客户机器上重开 Codex 后的最小对话验收。
- 后端合同与主程序实现逐项对照尚未全部完成。
- 真实胖虎AI后端、管理员后台“代理业务管理”和公开招商页 `/agent/join` 尚未验收；当前只是文档合同、离线模拟、请求构造和测试守卫完成。
- 三端客户包、GitHub Release、下载页、`latest.json` 不进入新一轮发布。

## 4. 文档维护任务

文档维护不能只做关键词扫描。每轮维护必须先按第 2 节顺序通读当前有效文档，再用搜索命令做补充验证；如果只看到关键词命中或无命中，不能直接下结论。

### N-DOC-01 文档权威顺序检查

确认所有入口文档都遵守：

1. 产品结构、客户可见文案、交付边界、验收标准以 `docs\PRODUCT_MANUAL_SINGLE_SOURCE_OF_TRUTH.md` 为准。
2. 技术维护、接口、构建、发布、脚本以 `docs\TECHNICAL_MAINTENANCE_MANUAL.md` 为准。
3. 商业服务端合同以 `docs\COMMERCIAL_BACKEND_API_CONTRACT.md` 为准。
4. 当前阶段和节点状态以 `PLAN.md`、`TASK_GRAPH.md`、`FINAL_REPORT.md` 为准。

验收：

- `README.md` 不再承担分散产品定义。
- `legacy\` 不被引用为当前依据。
- 所有文档都明确当前不是最终交付完成状态。

### N-DOC-02 代理中心当前口径检查

全文搜索并判断代理中心是否仍按当前口径表达：

```powershell
rg -n "代理中心|本地代操作|第三方账号代登录|身份分流|token 返佣|激活返佣|安装返佣" README.md docs PROJECT_BLUEPRINT.md PLAN.md TASK_GRAPH.md ACCEPTANCE.md SAFETY.md RUNBOOK.md FINAL_REPORT.md
rg -n "代理业务管理|/agent/join|agent_center|五级费用设置|推广素材|风控冻结|T\\+7|source_event_id" README.md docs PROJECT_BLUEPRINT.md PLAN.md TASK_GRAPH.md ACCEPTANCE.md SAFETY.md RUNBOOK.md FINAL_REPORT.md
```

不允许出现的场景：

- 把代理身份作为登录前入口。
- 把代理身份作为客户端本地配置操作者。
- 让客户误以为本工具支持第三方账号代登录或本地代操作。
- 让客户误以为桌面端本地会计算代理费用、返佣比例、下游归因或结算结果。
- 忘记说明代理业务管理属于胖虎AI管理员后台，不属于桌面端本地规则入口。

### N-DOC-03 完成态和验收口径检查

所有文档必须统一表达：

- 自动化测试通过不等于客户可交付。
- WebView 入口存在不等于网页登录、充值、支付、Key 创建闭环完成。
- 已接入 Agent 框架存在不等于完整付费交付；Gemini / agy 未接入前不计完整配置交付。
- 功能验收矩阵未通过，不得扣次或包装成交付完成。
- 发布前必须重包、注入生产商业 manifest 公钥、跑对应验收。
- `agent_center` 快照必须被视为商业 manifest 控制字段，缺签名或验签失败时客户端不得信任代理中心收益/结算摘要。
- 代理业务真实服务端未验收前，只能写“合同和测试守卫已补齐”，不能写“代理业务已上线”或“管理员后台已完成”。

### N-DOC-04 客户说明一致性检查

检查 `docs\发送客户说明.txt` 是否仍能让客户看懂：

- 下载入口。
- 安装方式。
- 胖虎AI账号登录和 API Key 创建。
- Codex 普通模式、双态模式、官方直登的区别。
- 配置后必须完全退出 Codex 再重新打开。
- Mac 未公证时的安全提示。
- 未打通项不能说成已完成。

客户说明必须是中文，不要出现整句英文说明。

### N-DOC-05 状态文件同步

如果文档维护过程中发现口径变化，要同步这些文件：

```text
PLAN.md
TASK_GRAPH.md
FINAL_REPORT.md
ACCEPTANCE.md
RUNBOOK.md
```

不要只改一个文档导致状态漂移。

## 5. 禁止事项

- 不改 `src\` 代码。
- 不改配置。
- 不打包。
- 不发布 GitHub Release。
- 不更新生产下载页。
- 不更新 `latest.json`。
- 不删除 `release\`、客户包、截图、交接文件。
- 不把胖虎AI服务器、控制台、后端、支付、钱包逻辑写进本仓库文档。

## 6. 建议验证命令

只读检查：

```powershell
git status --short
rg -n "代理中心|本地代操作|第三方账号代登录|身份分流|token 返佣|激活返佣|安装返佣" README.md docs PROJECT_BLUEPRINT.md PLAN.md TASK_GRAPH.md ACCEPTANCE.md SAFETY.md RUNBOOK.md FINAL_REPORT.md
rg -n "代理业务管理|/agent/join|agent_center|五级费用设置|推广素材|风控冻结|T\\+7|source_event_id" README.md docs PROJECT_BLUEPRINT.md PLAN.md TASK_GRAPH.md ACCEPTANCE.md SAFETY.md RUNBOOK.md FINAL_REPORT.md
rg -n "最终交付|完整交付|已完成|已上线|latest.json|Release|扣次|付费交付" README.md docs PROJECT_BLUEPRINT.md PLAN.md TASK_GRAPH.md ACCEPTANCE.md SAFETY.md RUNBOOK.md FINAL_REPORT.md
python -m pytest tests\test_commercial_backend_contract_docs.py -q
python src\panghu_codex_installer.py --self-test
```

除非用户明确授权，不运行发布前深度验收，不打包。

## 7. 交付物

完成后输出：

- 修改了哪些文档。
- 保持不变的关键口径。
- 仍未完成的产品/后端/验收项。
- 使用过的验证命令和结果。
- `git status --short` 说明。

不要说“完成交付”，只能说“文档口径已收束”或“文档维护已完成”。
