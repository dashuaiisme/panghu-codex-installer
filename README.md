# 胖虎AI多 Agent 一键部署工具

最后更新：2026-06-26

## 文档权威顺序

1. 产品结构、客户可见规则、交付边界：
   `docs/PRODUCT_MANUAL_SINGLE_SOURCE_OF_TRUTH.md`
2. 技术维护、接口、构建、发布、脚本：
   `docs/TECHNICAL_MAINTENANCE_MANUAL.md`
3. 项目蓝图、任务图、验收、运行、状态：
   `PROJECT_BLUEPRINT.md`
   `PLAN.md`
   `TASK_GRAPH.md`
   `ACCEPTANCE.md`
   `RUNBOOK.md`
   `FINAL_REPORT.md`

本 README 只做仓库入口摘要，不再承担分散的产品定义、当前状态说明或验收结论。

## 项目定位

这是一个客户侧桌面工具。

目标：

- 客户先登录胖虎AI账号。
- 登录后在工具内完成已接入 Agent 的安装、配置、检测和交付验收；未接入完整配置链路的 Agent 只能显示为官方入口或待接入状态。
- 通过内置网站入口打开胖虎AI网站的注册、邀请码、创建 API Key、充值购买等服务端页面，并在代理中心承接本工具独立代理业务入口。
- Codex 支持普通模式、双态模式、官方直登三种配置模式，并在切换前保存本机配置快照。

非目标：

- 不在本仓实现胖虎AI网站、支付、钱包、数据库或后台管理逻辑。
- 不在本仓硬编码价格、次数、有效期、设备数、返佣比例或商品上架状态。
- 不在本仓硬编码 token 返佣、下游付费激活返佣、付费安装 Agent 返佣、下游客户归因或代理等级。
- 不把未真实验收通过的 Agent 包装为完整付费交付。

## 核心路径

1. 登录胖虎AI账号。
2. 获取部署授权。
3. 创建或填写 API Key。
4. 检测环境和风险插件。
5. 选择 Agent 并执行安装与配置。
6. 运行最小中文对话验收。
7. 根据功能验收矩阵判断是否可交付。

## Codex 三种模式

- 普通模式：默认模式，Codex 使用胖虎AI中转站 API，消耗胖虎AI额度，不需要登录 ChatGPT 账号。
- 双态模式：保留客户自己的 ChatGPT 登录态，但模型请求仍走胖虎AI中转站 API，消耗胖虎AI额度。
- 官方直登：Codex 使用客户自己的 ChatGPT 账号登录态，消耗 ChatGPT 账号额度，不写入胖虎AI中转站 Key。

胖虎AI账号只用于登录本工具和胖虎AI网站，不是 Codex 登录账号。所有 Codex 配置模式写入后，都必须完全退出 Codex 再重新打开才会生效。

## 关键目录

```text
src/
  panghu_codex_installer.py
  commercial_api.py
  commercial_backend_contract.py
  commercial_core.py
scripts/
docs/
tests/
```

## 本地常用命令

```powershell
cd C:\Users\Administrator\Documents\codex\panghu-codex-installer
python -m py_compile src\panghu_codex_installer.py scripts\agent_delivery_acceptance.py scripts\customer_web_entry_acceptance.py
python src\panghu_codex_installer.py --self-test
python -m unittest discover -s tests -p "test_*.py"
```

更完整的运行、截图、验收和发布前说明见 `RUNBOOK.md` 与 `docs/TECHNICAL_MAINTENANCE_MANUAL.md`。

## 当前阶段

当前仓库处于“文档收束 + 后端审计 + 功能闭环补齐”阶段。

是否已可正式交付、哪些功能已完成、哪些仍阻塞，以 `FINAL_REPORT.md` 为准。

当前不处于三端打包、GitHub Release、下载页或 `latest.json` 更新阶段。
