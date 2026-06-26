# 当前状态报告

最后更新：2026-06-26

## 0. 本文件职责

本文件只负责：

- 当前真实状态
- 当前已验证项
- 当前未完成项
- 当前阻塞
- 下一步建议

本文件不是产品手册、技术手册、运行手册或蓝图。

## 1. 当前结论

当前不是最终交付完成状态。

当前阶段是：

- 工程文档体系已基本收束
- 后端与主程序实现偏差审计中
- 未进入打包发布和生产下载入口更新

## 2. 当前已验证

- 登录闸口与登录后主控制台的分层已回到正确方向。
- `profile.json` 持久化出口已收紧：不保存可恢复登录 token 或部署 token。
- 商业 API 主程序分发器已收紧：邀请码绑定/注册必须走胖虎AI网站内置浏览器，桌面端不提供本地代操作、绑定、下单或支付查询入口。
- 买家自助购买状态节点已独立为当前登录买家链路。
- 当前商业 API 请求构造只围绕当前登录买家上下文；订单、支付、权益和配置会话不得使用本地代操作会话字段。
- `胖虎AI网站` 顶级模块默认落点已改为网站首页，不再默认先落到“账号中心”子页。
- 产品手册、维护手册、后端合同、验收和安全文档已同步该口径。
- 文档已补充代理中心架构边界：代理中心是登录后的独立代理业务模块；它需要服务端合同覆盖 token 返佣、下游付费激活返佣、付费安装 Agent 返佣、下游客户归因和结算状态。
- 代理业务商业化合同已在本仓库可控范围落地：离线服务端合同覆盖代理产品、公开招商内容、代理申请审核、五级链路、三类佣金事件、T+7 结算申请和管理员账本冻结/解冻/冲正。
- 客户端 API 合同已新增代理公开招商、下游客户、佣金账本、结算申请、后台产品、政策、营销内容、审核、结算和账本动作请求构造；桌面端仍只展示服务端快照和入口，不计算费用、等级或返佣。
- `agent_center` 已纳入商业 manifest 签名控制字段，避免收益和结算快照绕过服务端签名保护。
- 产品手册和商业后端合同已同步：胖虎AI管理员后台需要“代理业务管理”，公开招商页固定为 `/agent/join`。
- 自动化测试基线可运行。
- 内置网站入口映射和 WebView 前提脚本可运行。
- Codex、ClaudeCode、OpenClaw、Hermes 的安装 / 配置 / 验收框架存在，但不能据此声明完整交付；Gemini / agy 当前只保留官方入口和待接入状态。
- Codex 三种配置模式的本地代码与文档已同步：普通模式、双态模式、官方直登。
- Codex 模式切换已加入本机快照机制，目标目录为 `~/.codex/panghu_modes/`。

## 3. 当前未完成

- 真实网页登录、注册、邀请码、充值购买、支付、创建 API Key 闭环验收。
- Codex、ClaudeCode、OpenClaw、Hermes 使用真实客户 API Key 的最小中文对话闭环验收；Gemini / agy 配置链路待开发。
- Codex 三模式在真实客户机器上分别完成重开 Codex 后的最小对话验收。
- 代理中心真实服务端实现和数据闭环，包括 token 返佣、下游付费激活返佣、付费安装 Agent 返佣、下游客户归因、结算状态和胖虎AI管理员后台“代理业务管理”。当前只完成本仓库的离线合同、请求构造、文档合同和测试守卫。
- 三端客户包打包、Release、下载页和 `latest.json` 更新。
- 后端和主程序的商业合同边界逐项审计尚未全部完成。

## 4. 当前阻塞

- 后端合同与主程序实现还未做完逐项对照。
- 代理中心真实服务端和管理员后台尚未验收，不能把代理中心写成已完成业务闭环。
- 真实客户授权上下文和真实业务闭环验收尚未完成。

## 5. 最近通过的检查

```powershell
python -m py_compile src\panghu_codex_installer.py src\commercial_core.py src\commercial_api.py src\commercial_backend_contract.py
python src\panghu_codex_installer.py --self-test
python -m unittest discover -s tests -p "test_*.py"
python -m pytest tests/test_commercial_core.py tests/test_panghu_commercial_manifest.py tests/test_commercial_api.py tests/test_commercial_backend_contract.py tests/test_commercial_flow_acceptance.py -q
python -m pytest tests/test_commercial_backend_contract_docs.py -q
```

说明：

- 最近一次代理商业化相关验证为 170 条 pytest 通过；商业合同文档为 9 条测试和 111 个 subtests 通过。
- 更大范围的 unittest、UI self-test 和 py_compile 仍需在本轮收尾复跑。
- 这些结果只代表代码健康、离线合同和已有回归测试通过。
- 不代表客户可交付。

## 6. 下一步

1. 继续用统一文档审计后端与主程序实现。
2. 输出剩余后端偏差清单。
3. 再进入后端修正与并行评审。
