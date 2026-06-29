# 主线任务图

最后更新：2026-06-28

## 0. 本文件职责

本文件只负责节点、依赖、状态和验收证据。

本文件不负责展开产品定义、运行手册或最终报告。

## 1. 任务节点

| ID | 节点 | 负责人 | 依赖 | 状态 | 验收证据 |
| --- | --- | --- | --- | --- | --- |
| N01 | 文档权威顺序与职责边界收束 | 主线 | 无 | verified | `README`、蓝图、计划、验收、运行、最终报告、两份 docs 手册职责清晰 |
| N02 | 文档一致性检查 | 主线 | N01 | verified | 已同步登录态 / profile / 代理中心口径；本轮已把代码健康、旧前端删除状态、网站入口前提、离线商业合同和轻量发布前 `WARN` 写入收口文档；真实服务链路仍单列未完成 |
| N03 | 后端与主程序实现偏差审计 | 主线 | N02 | in_progress | 已修正 profile 持久化边界、商业 API 当前买家上下文、买家自助状态节点命名和 `agent_center` manifest 签名门槛；本轮商业后端 focused pytest `158 passed, 11 subtests passed`，仍需继续审计真实服务端合同一致性 |
| N04 | 后端修正任务拆分 | 主线 | N03 | pending | 可并行子任务、范围和验证命令 |
| N05 | 登录 / 授权 / profile 边界修正 | 后端分支 | N04 | verified | `profile.json` 不保存可恢复登录 token；商业 API 只接受当前登录买家上下文；单测、自检、编译通过 |
| N06 | 商业合同 / 配置会话 / 扣次边界修正 | 后端分支 | N04 | in_progress | `commercial_flow_acceptance.py --json` 为 `PASS`，但仅限 `offline_only` / `offline_guarded` / `mock_guarded`；真实服务端链路未完成 |
| N07 | 代理中心服务端合同与下游返佣边界 | 后端分支 | N04 | in_progress | 离线合同、API 请求构造、产品手册、后端合同和测试守卫已覆盖代理产品、公开招商页、管理员后台入口、五级链路、三类佣金、T+7 结算、风控冻结/冲正；真实胖虎AI服务端实现和后台界面仍未验收 |
| N08 | 连接通讯软件独立增值服务合同 | 文档/后端分支 | N02,N04 | in_progress | 文档已定义独立入口、独立订单、独立配置会话、独立验收、独立收费、防断网/禁 Key 卡扣费口径；真实后端、平台通道、客户端入口和验收记录尚未实现 |
| N09 | 目标 Agent 真实能力边界复核 | 后端分支 | N04 | pending | Codex、ClaudeCode、OpenClaw、Hermes 按真实配置链路验收；Gemini / agy 未接入前只保留官方入口或待接入状态 |
| N10 | 文档与代码二次对照验收 | 主线 | N05,N06,N07,N08,N09 | in_progress | 本轮 `py_compile OK`、`self-test OK`、`unittest 306 OK`；旧前端删除 / 商业 manifest / 发布脚本 focused pytest `98 passed, 11 subtests passed`；商业后端 focused pytest `158 passed, 11 subtests passed` |
| N11 | B 级截图与验收状态更新 | 主线 | N10 | deferred | 旧 WebView 前端、旧截图脚本和旧 B 级截图目录已删除；新前端单独重做后重新生成截图证据 |
| N12 | 本地轻量发布前检查 | 主线 | N10 | blocked | `commercial_release_acceptance.py --json` 为 `WARN`：只有旧名历史客户包、三端包 `stale`、未注入商业清单生产公钥 |

## 2. 当前说明

- 当前主线优先级是先收束文档，再审计后端。
- 未进入生产发布和打包阶段。
- 未完成真实客户闭环前，不允许把产品标记为整体收口或客户可分发状态。
- 连接通讯软件当前只完成文档口径收束，不代表客户端入口、平台通道或后端扣费状态机已实现。
- 最近验证：本轮 `py_compile OK`、`self-test OK`、`unittest 306 OK`；旧前端删除 / 商业 manifest / 发布脚本 focused pytest `98 passed, 11 subtests passed`；商业后端 focused pytest `158 passed, 11 subtests passed`。
- `.venv\Scripts\python.exe scripts\customer_web_entry_acceptance.py` 返回 `web_entry_status=ready`；系统 Python 返回 `blocked` 是因为没有 `webview`，不代表项目运行环境失败。
- 本轮 `commercial_flow_acceptance.py --json` 为 `PASS`，但属于 `offline_only` / `offline_guarded` / `mock_guarded` 范围。
- 本轮 `commercial_release_acceptance.py --json` 为 `WARN`，发布相关节点继续阻塞。
