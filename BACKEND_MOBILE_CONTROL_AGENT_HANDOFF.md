# 手机控制Agent后端窗口交接说明

最后更新：2026-06-26

## 1. 交接目标

你是专门负责本项目后端合同、计费、状态机和验收闭环的 Codex 窗口。

项目路径：

```text
C:\Users\Administrator\Documents\codex\panghu-codex-installer
```

本次新增产品能力叫：

```text
手机控制Agent
```

目标不是把 QQ、微信、飞书等平台直接塞进现有 Agent 配置验收里，而是新增一个独立增值交付项目：客户在 Agent 已安装、已配置、已能对话之后，可额外购买“手机控制Agent”，通过手机端常用通讯或办公软件调用已配置好的 Agent。

## 2. 必读顺序

开始前先读：

```text
C:\Users\Administrator\.codex\进化.md
docs\PRODUCT_MANUAL_SINGLE_SOURCE_OF_TRUTH.md
docs\COMMERCIAL_BACKEND_API_CONTRACT.md
docs\TECHNICAL_MAINTENANCE_MANUAL.md
BACKEND_OPTIMIZATION_HANDOFF.md
DOC_MAINTENANCE_HANDOFF.md
```

重点读源码：

```text
src\panghu_codex_installer.py
src\commercial_api.py
src\commercial_core.py
src\commercial_backend_contract.py
scripts\commercial_flow_acceptance.py
tests\test_commercial_backend_contract.py
tests\test_commercial_api.py
tests\test_commercial_core.py
tests\test_panghu_commercial_manifest.py
```

## 3. 核心产品规则

必须拆成两个独立交付项目。

第一项：基础 Agent 配置交付

```text
安装 Agent
写入配置
启动检测
Agent 连通性测试
最小对话成功
基础 Agent 交付验收通过
基础配置服务可收费
```

第二项：手机控制Agent

```text
基础 Agent 已交付
客户选择手机/通讯平台
配置平台机器人或消息通道
手机端发送测试消息
消息进入 Agent
Agent 回复回手机端
手机控制Agent验收通过
手机控制Agent服务可收费
```

硬规则：

- 基础 Agent 交付和手机控制Agent不得共用订单、权益、验收记录或扣费事件。
- 基础 Agent 已能对话后即可完成基础交付；手机未接通不得回滚基础交付。
- 手机控制Agent必须单独创建服务订单、单独记录配置会话、单独验收、单独收费。
- 手机控制Agent未验收通过，不得把该项服务标记为已交付。
- 手机控制Agent失败只影响该增值项，不影响客户已经购买并验收的基础 Agent 配置服务。

## 4. 建议数据合同

后端可以在现有商业合同基础上扩展，不要在客户端本地硬编码价格、次数、平台支持状态或扣费规则。

建议新增或扩展：

```text
service_products
- id
- service_type
- name
- price_cents
- currency
- status
- requires_base_agent_delivery
- supported_agent_ids
- supported_channels
- intro_copy

service_orders
- id
- buyer_user_id
- service_product_id
- service_type
- agent_id
- channel
- status
- charge_status
- created_at
- delivered_at
- cancelled_at

mobile_control_sessions
- id
- order_id
- buyer_user_id
- agent_id
- channel
- platform_account_id
- platform_chat_id
- gateway_mode
- status
- created_at
- last_probe_at
- accepted_at

mobile_control_acceptance_records
- id
- order_id
- session_id
- source_event_id
- inbound_platform_message_id
- outbound_platform_message_id
- test_prompt
- agent_response_digest
- evidence_url
- accepted_by
- accepted_at

service_ledger_events
- id
- source_event_id
- service_type
- order_id
- buyer_user_id
- amount_cents
- status
- created_at
```

推荐枚举：

```text
service_type:
- agent_install_delivery
- mobile_control_agent

channel:
- qq_bot
- weixin
- feishu
- dingtalk
- wecom

mobile_control_session.status:
- pending_config
- waiting_platform_auth
- connected
- test_pending
- acceptance_passed
- failed
- disabled

service_order.status:
- created
- in_progress
- acceptance_pending
- delivered
- failed
- cancelled

charge_status:
- unpaid
- authorized
- chargeable
- paid
- refunded
- manual_review
```

## 5. 计费和扣费边界

基础 Agent 配置交付的收费事件继续保持独立，例如：

```text
agent_install_delivered
```

手机控制Agent必须新增独立收费事件，例如：

```text
mobile_control_agent_delivered
```

关键要求：

- `agent_install_delivered` 只能代表基础 Agent 安装配置和连通性验收成功。
- `mobile_control_agent_delivered` 只能代表手机端平台到 Agent 再回到手机端的闭环验收成功。
- 两类事件都必须有唯一 `source_event_id`，防止重复扣费、重复返佣或重复结算。
- 如果手机控制Agent验收失败，只能把手机控制Agent订单置为 `failed` 或 `manual_review`，不能撤销基础 Agent 交付。
- 如果客户先支付后配置，手机控制Agent失败应进入退款、重试或人工处理流程；如果客户是按交付后扣费，则必须等 `mobile_control_agent_delivered` 后才扣费。

## 6. 平台通道后端抽象

不要让每个 Agent 分别实现 QQ、微信、飞书、钉钉、企业微信。应使用两层适配：

```text
Channel Adapter
QQ / 微信 / 飞书 / 钉钉 / 企业微信

Agent Runtime Adapter
Codex / Claude Code / OpenClaw / Hermes / Gemini
```

统一消息对象建议：

```json
{
  "channel": "feishu",
  "platform_message_id": "msg_xxx",
  "platform_chat_id": "chat_xxx",
  "sender_id": "user_xxx",
  "buyer_user_id": "buyer_xxx",
  "agent_id": "hermes",
  "text": "请帮我检查当前项目状态",
  "attachments": [],
  "received_at": "2026-06-26T00:00:00Z"
}
```

统一回复对象建议：

```json
{
  "source_event_id": "mobile-control-test-xxx",
  "channel": "feishu",
  "platform_chat_id": "chat_xxx",
  "reply_to_message_id": "msg_xxx",
  "text": "已收到，我可以帮你检查当前项目状态。",
  "status": "ready_to_send"
}
```

## 7. API 建议

买家侧：

```text
GET  /api/mobile-control/offering
POST /api/mobile-control/orders
GET  /api/mobile-control/orders/:id
POST /api/mobile-control/sessions
GET  /api/mobile-control/sessions/:id
POST /api/mobile-control/sessions/:id/test
POST /api/mobile-control/sessions/:id/acceptance
POST /api/mobile-control/sessions/:id/disable
```

平台回调侧：

```text
POST /api/mobile-control/callbacks/qq-bot
POST /api/mobile-control/callbacks/feishu
POST /api/mobile-control/callbacks/dingtalk
POST /api/mobile-control/callbacks/wecom
POST /api/mobile-control/callbacks/weixin
```

管理员侧：

```text
GET/PUT /api/admin/mobile-control/products
GET/PUT /api/admin/mobile-control/channel-policies
GET     /api/admin/mobile-control/sessions
POST    /api/admin/mobile-control/sessions/:id/freeze
POST    /api/admin/mobile-control/sessions/:id/release
POST    /api/admin/mobile-control/orders/:id/refund
POST    /api/admin/mobile-control/orders/:id/manual-review
```

## 8. 客户端 Manifest 快照建议

桌面端只展示服务端快照，不计算价格、扣费、平台可用性或验收结果。

```json
{
  "mobile_control_agent": {
    "enabled": true,
    "title": "手机控制Agent",
    "entry_label": "手机控制Agent",
    "status": "available",
    "requires_base_agent_delivery": true,
    "supported_channels": [
      {
        "id": "feishu",
        "name": "飞书",
        "status": "available",
        "intro": "通过飞书机器人与已配置 Agent 对话"
      }
    ],
    "buyer_summary": {
      "delivered_count": 0,
      "active_session_count": 0,
      "pending_acceptance_count": 0
    },
    "boundaries": [
      "手机控制Agent是独立增值服务，不等同于基础Agent安装配置",
      "未完成手机端闭环验收前不得标记为已交付"
    ]
  }
}
```

## 9. 验收标准

基础 Agent 交付验收：

- Agent 安装成功。
- 配置写入成功。
- 启动检测通过。
- 最小中文对话成功。
- 记录 `agent_install_delivered` 或现有基础交付事件。

手机控制Agent验收：

- 平台通道配置成功。
- 手机端或平台聊天窗口发送指定测试消息。
- 后端记录平台入站消息 ID。
- Agent Runtime Adapter 成功执行请求。
- 平台聊天窗口收到 Agent 回复。
- 后端记录出站消息 ID 和响应摘要。
- 记录 `mobile_control_agent_delivered`。

## 10. 测试计划

单元测试：

- 基础 Agent 交付和手机控制Agent使用不同订单、不同验收记录。
- 手机控制Agent未验收通过不得产生 `mobile_control_agent_delivered`。
- 手机控制Agent失败不得回滚基础 Agent 交付。
- 同一 `source_event_id` 重复回调不得重复扣费。
- 未完成基础 Agent 交付时不得创建手机控制Agent交付订单，除非管理员明确允许预售。

集成测试：

- Hermes + 飞书：手机端发消息，Agent 回复，验收通过。
- Hermes + QQ Bot：群内 @ 机器人，Agent 回复，验收通过。
- OpenClaw + 飞书或 QQ：通道接入，Agent 回复，验收通过。
- Codex / Claude Code / Gemini：暂按 Runtime Adapter 待接入状态，不包装成已交付。

风控测试：

- 平台重复推送同一消息。
- Agent 执行超时。
- 平台回发失败。
- 群聊未 @ 机器人时不响应。
- 非授权用户触发 Agent 时拒绝。
- 手机控制Agent退款不影响基础 Agent 交付状态。

## 11. 禁止事项

- 不得把手机控制Agent写成基础 Agent 交付的子状态。
- 不得把手机控制Agent失败当成基础 Agent 失败。
- 不得把基础 Agent 的扣费事件复用于手机控制Agent。
- 不得在客户端硬编码手机控制Agent价格、次数、平台可用性或收费规则。
- 不得承诺普通个人微信号稳定官方可控；微信相关能力必须按官方或已明确支持的通道标注边界。
- 不得让群聊消息默认触发高风险本地操作；默认需要 @ 机器人或明确唤醒词。

## 12. 官方资料参考

```text
OpenAI Codex CLI:
https://developers.openai.com/codex/cli/reference

Claude Code CLI:
https://docs.anthropic.com/en/docs/claude-code/cli-reference

Claude Code Agent SDK:
https://docs.anthropic.com/en/docs/claude-code/sdk

Hermes Messaging Gateway:
https://hermes-agent.nousresearch.com/docs/user-guide/messaging/

OpenClaw Gateway:
https://docs.openclaw.ai/

QQ Bot API:
https://bot.q.qq.com/wiki/develop/api-v2/

Feishu Message Events:
https://open.feishu.cn/document/server-docs/im-v1/message/events/receive?lang=zh-CN

DingTalk Robot Receive Message:
https://open.dingtalk.com/document/dingstart/robot-receive-message
```
