# 主线推进计划

最后更新：2026-06-26

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
- 已清理桌面端旧代理协助主链路：不再暴露 `buyer_bind`、agent-assist 登录、旧协助 worker 或旧协助上下文工厂。
- 已把买家自助购买状态节点独立为当前买家链路，避免后续维护把买家购买链路误挂回旧代理模式命名。
- 已从当前商业 API 请求构造里移除旧协助会话字段，订单、支付、权益和配置会话只围绕当前登录买家上下文。
- 已同步产品手册、技术维护手册、后端 API 合同、验收和安全文档中的登录态持久化口径。
- 已确认当前自动化测试通过不等于客户可交付。

## 3. 当前正在做

1. 后端与主程序商业边界继续逐项对照。
2. 确认旧代理协助清理后的服务端合同、测试守卫和客户可见文案保持一致。
3. 为后续 agent 提供稳定执行依据。

## 4. 下一步

1. 继续审计 `src/panghu_codex_installer.py`、`src/commercial_api.py`、`src/commercial_backend_contract.py` 中的商业合同边界。
2. 输出剩余后端实现偏差清单。
3. 再决定后端修正任务拆分和并行评审。

## 5. 明确未完成

- 真实网页登录、注册、充值、支付、创建 API Key 闭环验收。
- 四 Agent 使用真实客户 API Key 的最小中文对话闭环验收。
- 三端客户包打包、Release、下载页和 `latest.json` 更新。

## 6. 当前验证命令

```powershell
python -m py_compile src\panghu_codex_installer.py scripts\agent_delivery_acceptance.py scripts\customer_web_entry_acceptance.py
python src\panghu_codex_installer.py --self-test
python -m unittest discover -s tests -p "test_*.py"
```

最近结果：`python -m unittest discover -s tests -p "test_*.py"` 已通过 209 条测试；`python src\panghu_codex_installer.py --self-test` 已通过；`python -m py_compile src\panghu_codex_installer.py src\commercial_core.py src\commercial_api.py src\commercial_backend_contract.py` 已通过。

这些命令只代表代码健康与回归检查通过，不代表产品已可正式交付。
