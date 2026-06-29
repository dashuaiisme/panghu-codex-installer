# 主线推进计划

最后更新：2026-06-28

## 0. 本文件职责

本文件只负责当前阶段计划：

- 当前阶段
- 当前目标
- 已完成
- 下一步
- 明确未完成
- 当前验证命令

本文件不负责长期产品定义、技术合同或最终交付结论。

## 1. 当前阶段

阶段：文档收束完成后的后端审计与功能闭环补齐阶段。

目标：

1. 把工程文档体系收束成单一权威结构。
2. 按统一文档去审计当前后端与主程序实现是否跑偏。
3. 明确真实已完成、未完成、阻塞点。

## 2. 已完成

- 已确认产品权威手册、技术维护手册、蓝图、验收、运行、最终报告的基本结构。
- 已确认登录门禁曾被本地会话恢复绕过，并已回到“未登录先闸口”的实现。
- 已收紧 `profile.json` 持久化出口：只保留账号提示、API Key、模型和界面偏好，不保存可恢复登录 token 或部署 token。
- 桌面端商业链路已收束为当前登录买家上下文，不提供本地代操作登录、绑定、下单或支付查询入口。
- 已把买家自助购买状态节点独立为当前登录买家链路。
- 当前商业 API 请求构造只围绕当前登录买家上下文；订单、支付、权益和配置会话不得使用本地代操作会话字段。
- 已同步产品手册、技术维护手册、后端 API 合同、验收和安全文档中的登录态持久化口径。
- 已按架构评审补充代理中心业务边界：代理中心是登录后的独立代理业务模块；后续需覆盖 token 返佣、下游付费激活返佣、付费安装 Agent 返佣和工具代理后端。
- 已把代理业务商业化合同落到本仓库可控范围：新增服务端离线合同对象覆盖代理产品、营销内容、代理申请审核、五级链路、三类佣金事件、T+7 结算申请、管理员账本冻结/解冻/冲正；客户端 API 合同增加公开招商、下游、佣金、结算、后台策略、营销内容、审核和结算动作请求构造。
- 已将 `agent_center` 纳入商业 manifest 签名控制字段，避免代理中心收益/结算快照绕过服务端签名保护。
- 已同步 `docs/COMMERCIAL_BACKEND_API_CONTRACT.md` 和 `docs/PRODUCT_MANUAL_SINGLE_SOURCE_OF_TRUTH.md`：胖虎AI管理员后台需要“代理业务管理”，公开招商页固定为 `/agent/join`，桌面端只展示服务端快照和入口。
- 已确认当前自动化测试通过不等于客户可交付。
- 本轮代码健康检查已完成：`py_compile OK`、`self-test OK`、`unittest 306 OK`。
- 本轮旧前端删除 / 商业 manifest / 发布脚本 focused pytest 为 `98 passed, 11 subtests passed`；商业后端 focused pytest 为 `158 passed, 11 subtests passed`。
- 本轮 `.venv\Scripts\python.exe scripts\customer_web_entry_acceptance.py` 返回 `web_entry_status=ready`；系统 Python 返回 `blocked` 是因为没有 `webview`，不代表项目运行环境失败。
- 旧 WebView 前端已按最新指令删除；旧截图脚本和旧 B 级截图目录不再作为当前验收证据。
- 本轮 `commercial_flow_acceptance.py --json` 返回 `status=PASS`，但只按 `offline_only` / `offline_guarded` / `mock_guarded` 范围确认。
- 本轮 `commercial_release_acceptance.py --json` 返回 `status=WARN`，原因是只有旧名历史客户包、三端包 `stale`、未注入商业清单生产公钥。

## 3. 当前正在做

1. 基于本轮验收结果更新收口文档，把旧前端和旧截图证据改为删除 / 暂停状态。
2. 保留真实服务端、真实交互、客户端 scope、连接通讯软件、代理中心服务端、新前端和发布链路未完成边界。
3. 将 `commercial_release_acceptance.py --json` 的 `WARN` 作为发布前阻塞项处理。
4. 继续确认代理中心三类返佣和下游客户合同尚未被客户端硬编码，也没有被误写成完成态。
5. 为后续 agent 提供稳定执行依据。

## 4. 下一步

1. 继续审计 `src/panghu_codex_installer.py`、`src/commercial_api.py`、`src/commercial_backend_contract.py` 中的商业合同边界。
2. 对照代理中心服务端合同，继续检查主程序是否只展示 `agent_center` 服务端快照，是否存在旧代理登录、本地代理模式或本地返佣计算残留。
3. 对照连接通讯软件服务合同，拆出后端商品、订单、会话、平台通道、验收记录、扣费事件和防套利状态机。
4. 新前端单独重做后，再重新生成 B 级截图证据。
5. 完成真实服务端和真实交互验收后，再决定是否进入打包和生产下载入口流程。

## 5. 明确未完成

- 真实网页登录、注册、充值、支付、创建 API Key 闭环验收。
- 代理中心真实服务端实现和真实数据闭环：token 返佣、下游付费激活返佣、付费安装 Agent 返佣、下游客户归因、结算状态和管理员后台配置页。当前仓库只有离线合同、请求构造、文档合同和测试守卫。
- 连接通讯软件真实后端、平台通道、客户端入口和交付验收尚未实现；当前只是文档合同和后续后端实现口径。
- Codex、ClaudeCode、OpenClaw、Hermes 使用真实客户 API Key 的最小中文对话闭环验收；Gemini / agy 配置链路待开发，当前不计完整交付。
- 新前端重做、接入和 B 级截图验收。
- 三端客户包打包、Release、下载页和 `latest.json` 更新。
- 轻量发布前检查当前仍为 `WARN`，旧名历史客户包、三端包 `stale`、商业清单生产公钥未注入。

## 6. 当前验证命令

```powershell
python -m py_compile src\panghu_codex_installer.py scripts\agent_delivery_acceptance.py scripts\customer_web_entry_acceptance.py
python src\panghu_codex_installer.py --self-test
python -m unittest discover -s tests -p "test_*.py"
.venv\Scripts\python.exe scripts\customer_web_entry_acceptance.py
python scripts\commercial_flow_acceptance.py --json
python scripts\commercial_release_acceptance.py --json
```

本轮结果：`py_compile OK`、`self-test OK`、`unittest 306 OK`；旧前端删除 / 商业 manifest / 发布脚本 focused pytest `98 passed, 11 subtests passed`；商业后端 focused pytest `158 passed, 11 subtests passed`；`.venv` 网站入口前提为 `web_entry_status=ready`；商业合同离线验收为 `PASS`，但属于 `offline_only` / `offline_guarded` / `mock_guarded`；轻量发布前检查为 `WARN`。

这些命令只代表代码健康与回归检查通过，不代表产品已可正式交付。
