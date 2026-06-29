# 连接通讯软件文档维护窗口交接说明

最后更新：2026-06-28

## 1. 交接目标

你是专门负责本项目产品手册、技术维护手册、商业合同文档、验收说明和客户说明的 Codex 窗口。

项目路径：

```text
C:\Users\Administrator\Documents\codex\panghu-codex-installer
```

本次需要把新增产品能力写入文档体系：

```text
连接通讯软件
```

该能力是登录后“配置Agent”模块内的独立增值交付项目。它不是基础 Agent 安装配置的一部分，也不是代理中心能力。

## 2. 必读顺序

开始前先读：

```text
C:\Users\Administrator\.codex\进化.md
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
BACKEND_COMMUNICATION_SOFTWARE_LINK_HANDOFF.md
BACKEND_OPTIMIZATION_HANDOFF.md
DOC_MAINTENANCE_HANDOFF.md
```

## 3. 产品口径

新增功能名称固定为：

```text
连接通讯软件
```

买家能理解的说明：

```text
Agent 安装配置完成后，可额外开通连接通讯软件服务，把已配置好的 Agent 接入 QQ、微信、飞书、钉钉、企业微信等常用通讯或办公软件，在通讯软件聊天窗口里直接向 Agent 发送消息并接收回复。
```

文档必须强调：

- 这是额外增值服务。
- 推荐发生在基础 Agent 配置成功之后，但入口不能被本工具本次基础配置会话硬锁死。
- 买家电脑原本已有可用 Agent、历史订单已交付 Agent，或人工复核确认 Agent 可用时，也可以直接进入连接通讯软件检测、配置和单独验收。
- 它单独收费。
- 它单独验收。
- 它失败不影响基础 Agent 配置交付。
- 它成功才代表“连接通讯软件”交付完成。

## 4. 界面入口口径

登录后主模块仍保持：

```text
配置Agent
胖虎AI网站
增值业务
代理中心
```

“连接通讯软件”主操作入口放在：

```text
配置Agent -> 连接通讯软件
```

建议流程位置：

```text
选择Agent
安装Agent
写入配置
启动检测
连通性测试
基础交付验收
连接通讯软件
连接通讯软件交付验收
```

增值业务模块可以展示“连接通讯软件”的销售卡片、价格说明和服务介绍，但正式配置、检测和验收入口仍应回到“配置Agent -> 连接通讯软件”。

代理中心不得作为连接通讯软件入口。代理中心只负责代理身份、下游、返佣、结算和代理业务管理入口。

## 5. 两套交付验收口径

文档必须拆成两套验收。

基础 Agent 配置交付：

```text
安装成功
配置写入成功
启动检测通过
最小中文对话成功
基础 Agent 交付验收通过
基础配置服务可收费
```

连接通讯软件交付：

```text
选择可用 Agent：本次基础交付 / 历史交付 / 本机已有 Agent 检测 / 人工复核
选择平台：QQ / 微信 / 飞书 / 钉钉 / 企业微信
配置平台机器人或消息通道
通讯软件端发送测试消息
Agent 收到消息并执行
通讯软件端收到 Agent 回复
连接通讯软件交付验收通过
连接通讯软件服务可收费
```

禁止写成：

```text
Agent 配置 + 连接通讯软件 一次性统一验收
```

原因：

```text
基础 Agent 配置和连接通讯软件是两个不同收费项目。把两者放在一个验收里，会导致 Agent 已经能对话但手机未接通时，扣费、退款、交付状态和客户说明全部混乱。
```

额外防漏洞口径：

```text
连接通讯软件不能只用“当前能不能收到消息”判断是否收费。配置完成并形成入站消息、Agent 调用、出站回复和 source_event_id 等验收证据后，如果客户自行断网、禁用 API Key、取消平台授权、关闭机器人、删除群聊或阻断回调，只能进入暂停、重试或人工复核，不能自动判定配置失败、自动退款或不收费。反过来，如果从未形成这些验收证据，也不能标记连接通讯软件交付完成。
```

## 6. 客户可见文案建议

功能标题：

```text
连接通讯软件
```

短说明：

```text
把已配置好的 Agent 接入微信、飞书等通讯软件，手机或电脑端都可以在聊天窗口里发送任务、查看回复。
```

服务说明：

```text
本服务独立于基础 Agent 安装配置。基础 Agent 能正常对话后，即可完成基础交付；如需通过 QQ、微信、飞书、钉钉或企业微信等通讯软件调用 Agent，可额外开通连接通讯软件服务，并进行单独配置与验收。
```

验收提示：

```text
请在通讯软件端发送指定测试消息。系统确认消息进入 Agent 并成功回复到同一聊天窗口后，才会标记连接通讯软件交付完成。
```

已有 Agent 提示：

```text
如果这台电脑已经有可用 Agent，可直接选择已有 Agent 进行检测并配置连接通讯软件，不需要重新购买或重新安装基础 Agent。
```

失败提示：

```text
当前仅连接通讯软件接入失败，不影响已完成的基础 Agent 安装配置交付。可重新配置平台通道或联系人工处理。
```

## 7. 平台支持文档口径

平台支持状态必须由后端或服务端配置下发，不得在产品手册里写死为永久可用。

建议文档表述：

```text
首批建议支持：飞书、钉钉、QQ Bot。
企业微信作为企业客户增强通道。
微信相关能力需按官方或已明确支持的通道标注边界，不承诺普通个人微信号稳定官方可控。
```

平台说明建议：

| 平台 | 文档口径 |
| --- | --- |
| 飞书 | 适合正式机器人接入，可做事件订阅和消息回复 |
| 钉钉 | 适合企业群机器人或 Stream 模式接入 |
| QQ Bot | 适合 QQ 群或频道机器人接入 |
| 企业微信 | 适合企业客户自建应用或群机器人场景 |
| 微信 | 只能按官方或已验证通道说明，不能承诺普通个人微信全兼容 |

## 8. 需要同步更新的文档

文档维护窗口需要更新：

```text
docs\PRODUCT_MANUAL_SINGLE_SOURCE_OF_TRUTH.md
docs\TECHNICAL_MAINTENANCE_MANUAL.md
docs\COMMERCIAL_BACKEND_API_CONTRACT.md
README.md
PROJECT_BLUEPRINT.md
PLAN.md
TASK_GRAPH.md
ACCEPTANCE.md
SAFETY.md
RUNBOOK.md
FINAL_REPORT.md
docs\发送客户说明.txt
```

更新重点：

- 在产品结构中加入“配置Agent -> 连接通讯软件”。
- 在增值业务里加入“连接通讯软件”销售说明，但不要把它作为主配置入口。
- 在商业合同中加入独立服务类型、订单、验收、收费事件。
- 在验收文档中拆分“基础 Agent 交付验收”和“连接通讯软件交付验收”。
- 在商业合同和验收文档中明确：已有 Agent / 历史交付 / 人工复核可以进入连接通讯软件链路，不得用本次基础配置完成状态硬锁入口。
- 在商业合同和验收文档中明确：验收证据形成后，客户断网、禁 Key、取消平台授权或阻断回调不得自动免单。
- 在安全文档中加入平台密钥、群聊唤醒、权限控制、个人微信边界。
- 在客户说明中用买家能理解的话解释“为什么这是单独收费项目”。

## 9. 不得出现的旧口径

不得写：

- 连接通讯软件是基础 Agent 配置的一部分。
- Agent 安装成功就等于连接通讯软件成功。
- 微信个人号一定可以稳定接入。
- 所有平台默认都已完整支持。
- 平台接入失败会导致基础 Agent 交付失败。
- 连接通讯软件收费和基础 Agent 配置收费共用一个验收状态。

必须写：

- 基础 Agent 配置和连接通讯软件是两个服务。
- 两者分别收费、分别验收、分别交付。
- 连接通讯软件必须完成通讯软件到 Agent 再回到通讯软件的闭环测试。
- 平台能力以服务端配置和实际验收为准。
- 连接通讯软件入口支持已有可用 Agent 检测或人工复核，不与本工具本次基础配置会话强绑定。
- 已形成验收证据后，客户主动断网、禁 Key、取消平台授权或阻断回调不得自动变成配置失败。

## 10. 建议客户 FAQ

问：我已经付了 Agent 配置费，为什么连接通讯软件还要另外收费？

答：基础 Agent 配置费覆盖安装、配置和连通性验收，确保 Agent 在电脑端可以正常对话。连接通讯软件需要额外接入 QQ、微信、飞书、钉钉或企业微信等平台，涉及平台机器人、消息回调、通道测试和单独交付，因此作为独立增值服务收费。

问：如果连接通讯软件没接通，之前的 Agent 配置费会退吗？

答：不会混在一起判断。基础 Agent 已经安装配置并通过对话验收的，基础交付仍然成立；连接通讯软件未完成时，只处理连接通讯软件这一项服务。

问：是不是所有微信都能接？

答：不是。微信相关能力必须以官方或已明确支持的通道为准，不能承诺普通个人微信号稳定接入。企业微信、飞书、钉钉、QQ Bot 等官方机器人能力更适合作为正式交付通道。

问：通讯软件端怎么验收？

答：客户在通讯软件端指定平台发送测试消息，系统确认消息进入 Agent，并把 Agent 回复发回同一聊天窗口后，才算连接通讯软件验收通过。

问：我电脑上已经有 Agent 能用，还要重新做基础配置吗？

答：不一定。连接通讯软件可以选择已有 Agent 做运行检测并单独配置通讯软件通道；如果检测不清楚，会进入人工复核或提示先修复 Agent，而不是强制重装。

问：如果配置好后我这边断网、禁用了 Key 或取消了平台授权，还算失败吗？

答：不自动算失败。配置过程中已经形成验收证据的，后续由客户本机网络、Key、平台授权或群聊设置造成的不可达，会进入暂停、重试或人工处理，不会自动取消交付记录。

## 11. 官方资料参考

```text
Hermes Messaging Gateway:
https://hermes-agent.nousresearch.com/docs/user-guide/messaging/

Hermes QQ Bot:
https://hermes-agent.nousresearch.com/docs/user-guide/messaging/qqbot

Hermes Weixin:
https://hermes-agent.nousresearch.com/docs/user-guide/messaging/weixin

Hermes DingTalk:
https://hermes-agent.nousresearch.com/docs/user-guide/messaging/dingtalk

OpenClaw Gateway:
https://docs.openclaw.ai/

OpenClaw QQ Bot:
https://docs.openclaw.ai/channels/qqbot

OpenClaw WeChat:
https://docs.openclaw.ai/channels/wechat

OpenClaw Feishu:
https://docs.openclaw.ai/channels/feishu

QQ Bot API:
https://bot.q.qq.com/wiki/develop/api-v2/

Feishu Message Events:
https://open.feishu.cn/document/server-docs/im-v1/message/events/receive?lang=zh-CN

DingTalk Robot Receive Message:
https://open.dingtalk.com/document/dingstart/robot-receive-message
```
