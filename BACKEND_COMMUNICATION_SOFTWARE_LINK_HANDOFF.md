# 连接通讯软件后端窗口交接说明

最后更新：2026-06-28

## 1. 交接目标

你是专门负责本项目后端合同、计费、状态机和验收闭环的 Codex 窗口。

项目路径：

```text
C:\Users\Administrator\Documents\codex\panghu-codex-installer
```

本次新增产品能力叫：

```text
连接通讯软件
```

目标不是把 QQ、微信、飞书等平台直接塞进现有 Agent 配置验收里，而是新增一个独立增值交付项目：客户在 Agent 已安装、已配置、已能对话之后，可额外购买“连接通讯软件”，通过通讯软件端常用通讯或办公软件调用已配置好的 Agent。

重要修正：这里的“之后”是推荐业务顺序，不是 UI 和后端的硬解锁条件。买家电脑原本已有可用 Agent、历史订单已交付 Agent，或人工复核确认可用时，也可以直接进入连接通讯软件服务链路；不能要求必须由本工具本次先完成基础 Agent 配置，才允许创建连接通讯软件订单或配置会话。

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

第二项：连接通讯软件

```text
选择可用 Agent：本次基础交付 / 历史交付 / 本机已有 Agent 检测 / 人工复核
客户选择手机/通讯平台
配置平台机器人或消息通道
通讯软件端发送测试消息
消息进入 Agent
Agent 回复回通讯软件端
连接通讯软件验收通过
连接通讯软件服务可收费
```

硬规则：

- 基础 Agent 交付和连接通讯软件不得共用订单、权益、验收记录或扣费事件。
- 基础 Agent 已能对话后即可完成基础交付；手机未接通不得回滚基础交付。
- 连接通讯软件必须单独创建服务订单、单独记录配置会话、单独验收、单独收费。
- 连接通讯软件未验收通过，不得把该项服务标记为已交付。
- 连接通讯软件失败只影响该增值项，不影响客户已经购买并验收的基础 Agent 配置服务。
- 连接通讯软件入口不得只用“本工具本次基础 Agent 配置会话已完成”作为创建订单或配置会话的唯一前置条件。

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
- agent_runtime_readiness_policy
- allowed_agent_sources
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

communication_software_link_sessions
- id
- order_id
- buyer_user_id
- agent_id
- channel
- platform_account_id
- platform_chat_id
- gateway_mode
- agent_source
- status
- created_at
- last_probe_at
- accepted_at

communication_software_link_acceptance_records
- id
- order_id
- session_id
- source_event_id
- inbound_platform_message_id
- outbound_platform_message_id
- test_prompt
- agent_response_digest
- evidence_url
- source_event_id
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
- communication_software_link

channel:
- qq_bot
- weixin
- feishu
- dingtalk
- wecom

communication_software_link_session.status:
- pending_config
- waiting_platform_auth
- connected
- test_pending
- acceptance_passed
- failed
- disabled
- paused_external_dependency
- manual_review

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

连接通讯软件必须新增独立收费事件，例如：

```text
communication_software_link_delivered
```

关键要求：

- `agent_install_delivered` 只能代表基础 Agent 安装配置和连通性验收成功。
- `communication_software_link_delivered` 只能代表通讯软件端平台到 Agent 再回到通讯软件端的闭环验收成功。
- 两类事件都必须有唯一 `source_event_id`，防止重复扣费、重复返佣或重复结算。
- 如果连接通讯软件验收失败，只能把连接通讯软件订单置为 `failed` 或 `manual_review`，不能撤销基础 Agent 交付。
- 如果客户先支付后配置，连接通讯软件失败应进入退款、重试或人工处理流程；如果客户是按交付后扣费，则必须等 `communication_software_link_delivered` 后才扣费。
- 扣费或免单不能只根据“当前是否能收到手机消息”判断。配置完成并形成入站消息、Agent 调用、出站回复、响应摘要和唯一 `source_event_id` 后，如果客户自行断网、禁用 API Key、取消平台授权、关闭机器人、删除群聊或阻断回调，只能进入 `paused_external_dependency`、重试或 `manual_review`，不得自动把配置会话置为失败、自动退款或取消收费。
- 如果从未形成上述验收证据，不得记录 `communication_software_link_delivered`。

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
  "source_event_id": "communication-software-link-test-xxx",
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
GET  /api/communication-software-link/offering
POST /api/communication-software-link/orders
GET  /api/communication-software-link/orders/:id
POST /api/communication-software-link/sessions
GET  /api/communication-software-link/sessions/:id
POST /api/communication-software-link/sessions/:id/test
POST /api/communication-software-link/sessions/:id/acceptance
POST /api/communication-software-link/sessions/:id/disable
```

平台回调侧：

```text
POST /api/communication-software-link/callbacks/qq-bot
POST /api/communication-software-link/callbacks/feishu
POST /api/communication-software-link/callbacks/dingtalk
POST /api/communication-software-link/callbacks/wecom
POST /api/communication-software-link/callbacks/weixin
```

管理员侧：

```text
GET/PUT /api/admin/communication-software-link/products
GET/PUT /api/admin/communication-software-link/channel-policies
GET     /api/admin/communication-software-link/sessions
POST    /api/admin/communication-software-link/sessions/:id/freeze
POST    /api/admin/communication-software-link/sessions/:id/release
POST    /api/admin/communication-software-link/orders/:id/refund
POST    /api/admin/communication-software-link/orders/:id/manual-review
```

## 8. 客户端 Manifest 快照建议

桌面端只展示服务端快照，不计算价格、扣费、平台可用性或验收结果。

```json
{
  "communication_software_link": {
    "enabled": true,
    "title": "连接通讯软件",
    "entry_label": "连接通讯软件",
    "status": "available",
    "requires_agent_runtime": true,
    "allowed_agent_sources": ["current_delivery", "historical_delivery", "existing_local_agent", "manual_review"],
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
      "连接通讯软件是独立增值服务，不等同于基础Agent安装配置",
      "未完成通讯软件端闭环验收前不得标记为已交付",
      "已有可用Agent可进入连接通讯软件检测与单独验收",
      "验收证据形成后客户断网、禁Key或取消平台授权不得自动免单"
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

连接通讯软件验收：

- 平台通道配置成功。
- 通讯软件端或平台聊天窗口发送指定测试消息。
- 后端记录平台入站消息 ID。
- Agent Runtime Adapter 成功执行请求。
- 平台聊天窗口收到 Agent 回复。
- 后端记录出站消息 ID 和响应摘要。
- 记录 `communication_software_link_delivered`。
- 后端记录唯一 `source_event_id`，并把后续客户断网、禁 Key、取消授权等外部中断与配置失败区分开。

## 10. 测试计划

单元测试：

- 基础 Agent 交付和连接通讯软件使用不同订单、不同验收记录。
- 连接通讯软件未验收通过不得产生 `communication_software_link_delivered`。
- 连接通讯软件失败不得回滚基础 Agent 交付。
- 同一 `source_event_id` 重复回调不得重复扣费。
- 没有本次基础交付、历史交付、本机已有 Agent 检测或人工复核任一可用 Agent 来源时，不得直接标记连接通讯软件可交付；可进入预售、待检测或人工复核，但不能假装已具备运行基础。

集成测试：

- Hermes + 飞书：通讯软件端发消息，Agent 回复，验收通过。
- Hermes + QQ Bot：群内 @ 机器人，Agent 回复，验收通过。
- OpenClaw + 飞书或 QQ：通道接入，Agent 回复，验收通过。
- Codex / Claude Code / Gemini：暂按 Runtime Adapter 待接入状态，不包装成已交付。

风控测试：

- 平台重复推送同一消息。
- Agent 执行超时。
- 平台回发失败。
- 群聊未 @ 机器人时不响应。
- 非授权用户触发 Agent 时拒绝。
- 连接通讯软件退款不影响基础 Agent 交付状态。
- 已验收后断网、禁 Key、取消平台授权、删除机器人或阻断回调不得自动免单。
- 未形成入站/Agent 调用/出站证据不得标记交付完成。

## 11. 禁止事项

- 不得把连接通讯软件写成基础 Agent 交付的子状态。
- 不得把连接通讯软件失败当成基础 Agent 失败。
- 不得把基础 Agent 的扣费事件复用于连接通讯软件。
- 不得在客户端硬编码连接通讯软件价格、次数、平台可用性或收费规则。
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
