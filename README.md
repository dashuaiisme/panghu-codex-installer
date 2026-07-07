# 胖虎AI客户端

最后更新：2026-07-07

## 文档地图

文档权威顺序只在 `AGENTS.md` 维护。一次性历史交接/需求/草稿已于 2026-07-07 清理（git 历史可追溯），`docs/` 仅保留权威文档。根目录文档职责：

- 产品事实：`docs/PRODUCT_MANUAL_SINGLE_SOURCE_OF_TRUTH.md`
- 技术事实：`docs/TECHNICAL_MAINTENANCE_MANUAL.md`
- 商业服务端合同：`docs/COMMERCIAL_BACKEND_API_CONTRACT.md`
- 产品摘要与蓝图：`PRODUCT.md`
- 架构、后端、前端、设计边界：`ARCHITECTURE.md`
- 验收标准：`ACCEPTANCE.md`
- 验证命令与历史验证记录：`TESTING.md`
- 运行、构建与发布：`RUNBOOK.md`
- 安全与禁止事项：`SECURITY.md`
- 跨项目集成：`INTEGRATION.md`
- 当前状态、任务与阻塞：`FINAL_REPORT.md`
- 交接与工程盘点：`HANDOFF.md`
- 变更记录：`CHANGELOG.md`

本 README 只做仓库入口摘要，不再承担分散的产品定义、当前状态说明或验收结论。

## 项目是什么

“胖虎AI客户端”是一款面向买家和新手用户的一站式 AI 客户端服务工具。

## 项目定位

它不是单纯的 Agent 配置器，而是把 AI 使用过程中常见的下载、账号、API、中转、充值、会员、接码、连接通讯软件和交付验收卡点集中到一个登录后的客户端里处理。

当前产品主从口径：

- 胖虎AI客户端是主产品和客户统一入口。
- 胖虎AI中转站、手机接码、Plus 充值 / Plus 订阅、连接通讯软件、代理中心都属于胖虎AI客户端里的功能区或分支服务。
- 胖虎AI中转站只按 API 网关、API Token、余额扣费、模型调用、用量记录和网关侧充值记账分支承接，不再写成整个平台后台或客户端后台。
- 独立胖虎AI后台管理系统负责账号、订单、支付、权益、代理、服务目录、运营配置和各分支服务编排。

目标：

- 客户先登录胖虎AI账号。
- 登录后在工具内完成已接入 Agent 的安装、配置、检测和交付验收；未接入完整配置链路的 Agent 只能显示为官方入口或待接入状态。
- 登录页支持账号提示、历史账号下拉、可选记住密码和自动登录；记住密码只使用本机系统加密，退出或删除账号时会清理对应买家会话。
- 登录后可在“配置Agent -> 连接通讯软件”进入独立增值服务：把已可用的 Agent 接入 QQ、微信、飞书、钉钉、企业微信等通讯软件或办公协同通道。该入口不能被“本工具本次基础 Agent 配置是否完成”硬锁死；买家电脑已有可用 Agent 时，也可以走已有 Agent 检测、选择和单独验收链路。
- 通过内置网站入口打开胖虎AI网站的注册、邀请码、创建 API Key、充值购买等服务端页面，并在代理中心承接本工具独立代理业务入口。
- 在“增值业务”中承接 Plus 订阅、账号服务、手机卡/云号码、手机号/短信接码、连接通讯软件等服务入口；商品、价格、履约、上架状态和服务入口以服务端为准。接码链路关联“手机号接码控制中心”，Plus 订阅履约关联“Plus session.脚本工具”，客户端只做买家入口和状态展示。
- 目标是把买家使用 AI 过程中遇到的卡点、阻点和流程门槛尽量集中打通，但未真实接入或未验收的链路必须显示为待接入/待服务端返回。
- Codex 支持普通模式、双态模式、官方直登三种配置模式，并在切换前保存本机配置快照。

非目标：

- 不在本仓实现胖虎AI中转站、网站、支付、钱包、数据库或后台管理逻辑。
- 不在本仓硬编码价格、次数、有效期、设备数、返佣比例或商品上架状态。
- 不在本仓硬编码 token 返佣、下游付费激活返佣、付费安装 Agent 返佣、下游客户归因或代理等级。
- 不把未真实验收通过的 Agent 包装为完整付费交付。

## 核心路径

1. 登录胖虎AI账号。
2. 获取部署授权。
3. 创建或填写 API Key。
4. 检测环境和风险插件。
5. 选择 Agent 后先「安装」（仅安装、不写配置、不扣次）；再「写入配置并交付」（写配置 + 最小对话/客户端验收，验收通过才计入交付、扣次）。安装与写配置是两个独立步骤。
6. 运行最小中文对话验收。
7. 根据功能验收矩阵判断基础 Agent 配置是否可交付。
8. 如客户额外购买连接通讯软件，在独立订单、独立配置会话和独立验收记录中完成通讯软件消息通道闭环；该项失败不回滚基础 Agent 配置交付。

## Codex 三种模式

- 普通模式：默认模式，Codex 使用胖虎AI中转站 API，消耗胖虎AI额度，不需要登录 ChatGPT 账号。
- 双态模式：保留客户自己的 ChatGPT 登录态，但模型请求仍走胖虎AI中转站 API，消耗胖虎AI额度。
- 官方直登：Codex 使用客户自己的 ChatGPT 账号登录态，消耗 ChatGPT 账号额度，不写入胖虎AI中转站 Key。

胖虎AI账号只用于登录本工具和胖虎AI网站，不是 Codex 登录账号。所有 Codex 配置模式写入后，都必须完全退出 Codex 再重新打开才会生效。

## 关键目录

```text
src/
  panghu_ai_client.py
  commercial_api.py
  commercial_backend_contract.py
  commercial_core.py
scripts/
docs/
tests/
```

## 本地常用命令

怎么启动：

```powershell
scripts\run-windows.bat
```

验证命令：

```powershell
cd C:\Users\Administrator\Documents\codex\胖虎AI客户端
python -m py_compile src\panghu_ai_client.py scripts\agent_delivery_acceptance.py scripts\customer_web_entry_acceptance.py
python src\panghu_ai_client.py --self-test
python -m unittest discover -s tests -p "test_*.py"
```

更完整的运行、截图、验收和发布前说明见 `RUNBOOK.md` 与 `docs/TECHNICAL_MAINTENANCE_MANUAL.md`。

## 当前阶段

当前仓库处于“文档收束 + 后端审计 + 功能闭环补齐”阶段。

是否已可正式交付、哪些功能已完成、哪些仍阻塞，以 `FINAL_REPORT.md` 为准。

当前不处于三端打包、GitHub Release、下载页或 `latest.json` 更新阶段。
