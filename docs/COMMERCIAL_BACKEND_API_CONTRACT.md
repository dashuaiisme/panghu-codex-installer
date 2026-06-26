# 商业版后端 API 合同

本文是“胖虎AI多 Agent 一键部署工具”商业版的服务端合同。客户端不得硬编码价格、次数、有效期、设备数、返佣比例、商品上架状态或权益可售状态；这些值全部来自服务端。

## 1. 上下文模型

当前客户端只保留统一胖虎AI账号登录。商业接口必须围绕登录后的账号身份和真实买家权益工作：

- `operator_context`：当前登录账号。客户端侧必须等于买家本人。
- `target_buyer_context`：权益、订单、API Key、配置会话、设备绑定和扣次归属的真实买家；当前客户端侧与 `operator_context` 相同。
- `diagnostic_code`：客户端每次配置生成的客服诊断码，贯穿订单、权益、配置会话和日志。

代理身份只来自登录后的服务端权益，客户端不得建立本地代操作会话。代理中心不是单纯的网站推广返佣页，而是本工具独立代理业务模块。代理等级、邀请归因、返佣归因、下游客户、token 返佣、下游付费激活返佣、付费安装 Agent 返佣、收益和结算状态等信息只由服务端维护，并通过工具内置浏览器、代理后端入口或服务端下发的代理中心快照展示和办理。

所有商业接口必须要求请求头 `Authorization: Bearer <operator_token>`。服务端必须用 token 校验 `operator_context`，不能只信任客户端请求体里的 `operator_user_id`。创建订单、查询支付、刷新权益、API Key 归属校验、配置会话预占、配置成功和配置失败都必须使用当前登录买家 token。日志、摘要和诊断包不得输出完整 token 或授权头。

本地商业污染字段不得写入或继续保留在 `profile.json`。保存 profile 时必须按白名单重建 payload；如果 `profile.json` 已混入第三方身份、第三方 token、买家登录 token、邀请码、订单号、权益 ID、配置会话 ID、密码或密码 blob，下一次保存必须清除。买家登录态允许通过独立 cookie 文件和内置浏览器 profile 持久化；`buyer_session.json` 只能保存非敏感买家标识。历史账号和可选“记住密码”只能进入独立 `login_accounts.json`，其中密码必须是本机系统加密 blob，不能是明文；WebView 公开状态只能暴露账号、勾选标记和是否存在密码记录，不能暴露全量明文密码。启动恢复时不得把商业污染字段或部署 token 当成当前授权，只能用保存的买家会话向服务端重新申请本次部署授权；服务端返回 401/403 时客户端必须清理保存会话并回到登录门禁。

## 2. 商品配置

服务端必须提供商品配置接口，供客户端读取可售商品：

- 商品 ID
- Agent ID
- 模式 key
- 商品配置标题
- 价格
- 币种
- 次数
- 是否不限次 `is_unlimited`
- 有效期
- 设备限制
- 是否包含双态
- 交付范围 `delivery_scope`
- 是否上架
- 是否允许在服务端代理中心展示或归因
- 最低客户端版本 `min_client_version`
- 灰度买家名单 `allowed_buyer_user_ids`

客户端只展示服务端返回内容。商品配置缺字段时，客户端必须跳过该商品，不能本地补默认价格或默认次数。不限次商品必须由服务端显式返回 `is_unlimited=true`，并允许 `remaining_uses=0`；如果没有 `is_unlimited`，`remaining_uses=0` 仍视为无效商品。

如果商品声明 `min_client_version`，低于该版本的客户端不得创建订单。如果商品声明 `allowed_buyer_user_ids`，不在名单内的买家不得创建订单；名单为空表示不启用灰度限制。旧客户端不能靠本地缓存商品或直接输入商品 ID 绕过这些服务端字段。

## 3. 商业部署清单签名

只要部署清单包含任一商业控制字段，例如 `products`、`entitlements`、`commercial`、`commercial_enabled` 或 `agent_center`，服务端必须同时返回：

- `manifest_signature`
- `manifest_issued_at`
- `manifest_signature_algorithm`
- `manifest_key_id`

签名算法使用 `ed25519`。签名载荷是去掉 `manifest_signature` 字段后的整份 manifest，按 JSON key 排序、紧凑分隔符和 UTF-8 编码生成。可用 `scripts/commercial_manifest_signer.py` 在离线环境生成密钥并签名 manifest。客户端只内置验签公钥，不保存私钥；私钥不得进入客户端源码、客户包、GitHub Release 或下载页。公钥通过构建环境变量 `PANGHU_COMMERCIAL_MANIFEST_PUBLIC_KEY_PEM` 写入生成模块 `src/commercial_manifest_public_key.py`，该生成模块不得提交到 git。缺字段、缺公钥、算法不支持或验签失败时，客户端会拒绝使用商业清单，避免用户通过本地修改 manifest 解锁商品、权益或 Agent 交付范围。不含商业控制字段的免费清单可以继续兼容。

## 4. 工具订单

工具订单由服务端创建，订单必须冻结下单时快照：

- 商品快照
- 价格快照
- 权益快照
- 代理链路快照
- 返佣规则快照
- `operator_context`
- `target_buyer_context`
- `diagnostic_code`

每个创建订单请求必须支持幂等键。重复点击、网络重试和客户端重启恢复都不能重复创建订单。

## 5. 支付回调

支付宝支付和支付回调验签只在服务端完成。客户端只负责创建订单和轮询支付状态，不保存支付密钥。

支付成功后服务端必须：

- 校验支付回调幂等
- 更新工具订单状态
- 创建权益
- 写入返佣账本待结算记录
- 支付成功但权益创建失败时进入人工处理状态

客户端不得因为“支付状态看起来成功”直接发放权益或扣次。

## 6. 权益

权益是配置前置条件，至少包含：

- 权益 ID
- 买家 ID
- 订单 ID
- Agent ID
- 模式 key
- 剩余次数
- 是否不限次 `is_unlimited`
- 有效期
- 设备限制
- 是否包含双态
- 是否允许在服务端代理中心展示或归因
- 当前状态

免费权益和付费权益必须分账，不能混成一个普通次数字段。设备超限、权益过期、次数不足、状态暂停都必须由服务端判断。

免费试用规则由服务端执行：

- 同一买家账号只能领取一次免费试用权益，不能按 Agent 或模式分别重复领取。
- 免费试用只允许基础直接 API 配置，不包含 `dual_state` 双态高级能力。
- 换设备重复领取必须按账号、设备和服务端领取记录联合拦截，不能只靠本地文件判断。
- 免费试用不创建付费订单，不生成返佣，不影响付费权益剩余次数。

不限次权益必须由服务端显式返回 `is_unlimited=true`，并允许 `remaining_uses=0`。客户端不得把负数次数或缺少 `is_unlimited` 的 0 次权益解释成不限次；不限次权益完成真实任务后不递减 `remaining_uses`。

设备策略由服务端维护绑定设备集合：

- 首次配置时把 `device_id` 绑定到该权益。
- 同一 `device_id` 重新配置或失败后重试，不新增设备占用。
- 新 `device_id` 超过 `device_limit` 时，配置会话不得预占成功，也不得扣次。
- 设备超限只返回可脱敏错误和诊断码，不把权益标记为失败或已消费。

## 7. API Key 归属校验

保存或配置 API Key 前，客户端必须调用服务端归属校验接口：

- `POST /api/deployer/api-keys/verify-owner`
- 请求体包含 `api_key`、`target_buyer_user_id` 和 `operator_user_id`
- 响应体至少返回 `owner_user_id`

服务端必须用真实 Key 查询结果确认归属，不能只按客户端传入字段信任。客户端只在 `owner_user_id == target_buyer_user_id` 时允许保存 Key 或继续配置；如果 Key 属于非当前买家账号或无法确认归属，必须阻断。该接口摘要、日志和客服诊断包不得输出明文 API Key 或完整用户 ID。

跳过普通接口连通测试不等于跳过商业归属校验。归属校验失败时，客户端不得写入 `profile.json`，不得进入环境检测、配置会话预占或扣次链路。

## 8. 配置会话和权益预占

配置前必须创建配置会话并完成权益预占。配置会话至少包含：

- `config_session_id`
- 权益 ID
- `operator_context`
- `target_buyer_context`
- Agent ID
- 模式 key
- 设备 ID
- `diagnostic_code`
- 状态
- 创建时间
- 完成时间

规则：

- 同一权益同一时刻只能有一个活跃配置会话。
- 配置前先权益预占。
- 设备超限时不能创建活跃配置会话。
- 真实任务验证通过后，客户端提交成功，服务端扣次。
- 失败提交必须释放权益预占，不扣次。
- 成功、失败和预占接口都必须支持幂等。
- `manual_review` 不自动重复扣次，并且在客服处理前继续冻结该权益，不能再创建新的配置会话。

## 9. 真实任务验证

真实任务验证是默认扣次门槛。文件写入成功、安装命令成功、客户端启动成功都不能单独视为商业交付成功。

服务端成功提交必须接收：

- `config_session_id`
- `diagnostic_code`
- `real_task_verified`

只有 `real_task_verified=true` 且配置会话仍有效时，才允许扣次并标记交付成功。

## 10. 五级代理

服务端必须支持五级代理关系：

- 代理等级 1 到 5 级
- 新买家通过邀请码或邀请链接绑定代理
- 已有上级邀请人不能被新代理覆盖
- 第 N 级代理最多拿往下 N 层的返佣
- 代理升级价格后台配置
- 默认不对代理升级费做上级返佣

客户端只展示代理介绍、升级入口和必要邀请入口。代理等级、升级价格、收益比例和展示开关全部由服务端控制。

服务端清单可返回 `agent_center` 快照供客户端展示。该快照属于商业控制字段，必须参与 manifest 签名验签：

```json
{
  "agent_center": {
    "enabled": true,
    "status": "active",
    "current_level": "L1",
    "invite_url": "https://aitokenapi.cc/register?invite=xxx",
    "join_page_url": "https://aitokenapi.cc/agent/join",
    "backend_url": "https://aitokenapi.cc/agent/center",
    "rules_url": "https://aitokenapi.cc/agent/rules",
    "summary": {
      "downstream_count": 0,
      "token_commission_cents": 0,
      "activation_commission_cents": 0,
      "agent_install_commission_cents": 0,
      "available_settlement_cents": 0,
      "pending_settlement_cents": 0,
      "frozen_cents": 0
    },
    "benefits": [],
    "boundaries": ["所有收益以后台结算账本为准"]
  }
}
```

客户端只显示这些客户可读字段。返佣比例、代理升级价格、结算规则、下游客户归因、token 返佣、激活返佣、安装返佣和账本明细必须继续由后台控制，不能由客户端写死或本地计算。

## 11. 返佣账本

返佣账本必须以订单和真实 token/API 消费为依据：

- token/API 真实消费返佣
- 下游客户付费激活返佣
- 付费安装 Agent 返佣
- 工具商品订单返佣
- 每笔订单只能结算一次
- 佣金比例使用订单快照
- 佣金状态可追踪
- 后台撤销订单时必须能反向冲正

客户端不得计算、保存或展示完整返佣账本权威数据。

## 12. 订单撤销和佣金冲正

前台不做退款申请入口。后台必须支持客服或管理员按精确订单撤销：

- 查找工具订单
- 撤销订单
- 回收订单对应权益
- 终止活跃配置会话
- 释放或作废权益预占
- 撤销该订单已经产生的佣金
- 写入佣金冲正记录

订单撤销必须幂等。同一订单重复撤销不能重复扣佣金。未提现或可自动追回的佣金可以自动标记为冲正；已提现、余额不足或状态不可自动追回的佣金必须进入 `manual_review`，不能硬改成已冲正。后台撤销后，客户端下一次查询权益或配置会话时必须立刻停止。

## 13. 客服诊断

后台必须能通过 `diagnostic_code` 查到：

- 工具订单
- 支付状态
- 权益
- 配置会话
- 设备 ID
- 代理链路
- 返佣账本和佣金冲正记录
- 客户端节点状态摘要

客户端日志和诊断包不得明文包含账号密码、加密密码 blob、手机号、邮箱、API Key、token、邀请码、订单号、权益 ID 或配置会话 ID。

客户端每次配置结束必须形成同一份客户交付报告，供弹窗、日志、客服诊断包和后端状态对齐使用：

- `diagnostic_code`
- 最终状态
- 是否允许扣次
- 配置会话终止动作：`complete`、`fail` 或 `none`
- 客户可读说明
- 固定节点状态摘要
- 已脱敏客服诊断包

只有交付报告同时满足真实任务通过、存在服务端配置会话且终止动作为 `complete` 时，才能作为付费交付成功口径；否则必须按失败或未预占处理，不扣次。

## 14. Agent 交付范围

服务端商品、代理话术、客户端按钮和成功页必须绑定 `delivery_scope`。

`ClaudeCode`、`OpenClaw`、`Hermes` 在没有完成 Agent Playbook、API 接入、重启验证和最小真实任务验证前，只能设置为：

- hidden
- paused
- 非收费说明入口

不能只下载 Agent 本体就作为付费完整配置交付。

`Gemini / agy` 当前只保留官方入口和待接入状态。未完成胖虎AI API Key 配置、启动检测、最小中文对话和功能验收矩阵前，不得作为付费完整配置交付。

## 15. 手机控制Agent独立服务合同

手机控制Agent是独立增值服务，固定 `service_type=mobile_control_agent`。它用于把已可用 Agent 接入 QQ、微信、飞书、钉钉、企业微信等手机通讯或办公通道。

它不得与基础 Agent 配置共用：

- 商品
- 订单
- 权益
- 配置会话
- 验收记录
- 扣费事件
- 返佣事件

基础 Agent 配置交付事件建议继续使用 `agent_install_delivered`。手机控制Agent交付事件必须单独使用 `mobile_control_agent_delivered`。

服务端数据模型至少应覆盖：

- `service_products`: `service_type`、名称、价格、状态、支持的 Agent、支持的平台通道、介绍文案和最低客户端版本。
- `service_orders`: 买家、服务商品、Agent、通道、订单状态、收费状态、创建时间、交付时间和取消时间。
- `mobile_control_sessions`: 订单、买家、Agent、通道、平台账号、聊天对象、网关模式、状态、最近探测时间和验收时间。
- `mobile_control_acceptance_records`: 入站平台消息 ID、出站平台消息 ID、测试提示词、Agent 响应摘要、证据链接、验收人、验收时间和唯一 `source_event_id`。
- `service_ledger_events`: `service_type`、订单、买家、金额、状态和唯一 `source_event_id`。

Agent 来源不能只限定为“本工具本次基础配置会话已完成”。服务端必须支持：

- 当前订单刚完成基础 Agent 交付。
- 买家历史订单已有基础 Agent 交付。
- 买家电脑本来已有可用 Agent，客户端检测或人工复核后进入手机控制Agent。
- 无法自动确认时进入 `manual_review`，而不是直接隐藏入口。

建议接口：

- `GET /api/mobile-control/offering`
- `POST /api/mobile-control/orders`
- `GET /api/mobile-control/orders/:id`
- `POST /api/mobile-control/sessions`
- `GET /api/mobile-control/sessions/:id`
- `POST /api/mobile-control/sessions/:id/test`
- `POST /api/mobile-control/sessions/:id/acceptance`
- `POST /api/mobile-control/sessions/:id/disable`
- `POST /api/mobile-control/callbacks/qq-bot`
- `POST /api/mobile-control/callbacks/feishu`
- `POST /api/mobile-control/callbacks/dingtalk`
- `POST /api/mobile-control/callbacks/wecom`
- `POST /api/mobile-control/callbacks/weixin`
- `GET/PUT /api/admin/mobile-control/products`
- `GET/PUT /api/admin/mobile-control/channel-policies`
- `GET /api/admin/mobile-control/sessions`
- `POST /api/admin/mobile-control/sessions/:id/freeze`
- `POST /api/admin/mobile-control/sessions/:id/release`
- `POST /api/admin/mobile-control/orders/:id/refund`
- `POST /api/admin/mobile-control/orders/:id/manual-review`

验收与扣费规则：

- 手机控制Agent必须记录入站平台消息、Agent 执行证据和出站平台回复证据。
- 未形成上述证据时，不得标记 `mobile_control_agent_delivered`。
- 已形成验收证据后，客户断网、禁用 API Key、取消平台授权、关闭机器人、删除群聊或阻断回调，只能进入暂停、重试或人工复核，不得自动判定为配置失败、自动退款或取消收费。
- 收费、返佣和结算必须基于不可重复的 `source_event_id` 幂等处理。
- 手机控制Agent退款、失败或人工复核不得自动撤销基础 Agent 配置交付。
- 如果手机控制Agent未来参与代理返佣，返佣事件也必须使用独立 `mobile_control_agent_delivered`，不得复用 `agent_install_delivered`。

## 16. 后端验收清单

- 商品配置由后台控制，客户端不写死价格、次数、有效期、设备数或上架状态。
- 商业部署清单必须返回 `manifest_signature`、`manifest_issued_at`、`manifest_signature_algorithm` 和 `manifest_key_id`，且能通过客户端内置 Ed25519 公钥验签；缺失或验签失败时客户端拒绝商业配置。
- 工具订单创建、支付回调、权益创建都具备幂等。
- 权益预占、配置成功、配置失败都具备幂等。
- 失败不扣次，真实任务验证后才扣次。
- API Key 归属校验必须由服务端确认，客户端只允许目标买家的 Key 进入保存和配置链路。
- 客户端配置只消耗当前登录买家的 `target_buyer_context` 权益；代理身份只用于服务端代理中心展示或归因，不作为客户端配置操作者。
- 订单撤销会回收权益、终止配置会话、释放预占并执行佣金冲正。
- 后台可通过 `diagnostic_code` 查到完整链路。
- 代理返佣比例、代理等级升级价格和展示开关全部由后台配置。
- 代理中心必须区分 token 返佣、下游付费激活返佣和付费安装 Agent 返佣，不能把三者混成一个普通推广返佣字段。
- 手机控制Agent必须作为独立 `service_type=mobile_control_agent` 处理，不能复用基础 Agent 配置的订单、权益、配置会话、验收记录或扣费事件。
- 手机控制Agent入口不能被“本工具本次基础配置会话是否完成”硬锁死；已有可用 Agent、历史交付或人工复核必须能进入单独配置链路。
- 手机控制Agent交付不能只以实时消息是否还能回传为准；验收证据已形成后，客户断网、禁 Key、取消平台授权或阻断回调不得自动免单。
- 后端或客户端商业合同变更后，必须先运行 `python scripts/commercial_flow_acceptance.py --json`，离线验收订单、支付、权益、配置会话、设备超限不扣次、失败不扣次、成功扣次和佣金冲正主链路。
- 商业版客户端、商业 manifest、构建脚本或客户包前置逻辑变更后，必须运行 `python scripts/commercial_release_acceptance.py --json` 做本地轻量验收；发布前深度验收或 CI 再运行 `python scripts/commercial_release_acceptance.py --with-exe-self-test --deep-scan --json`，验收三端客户包、Windows 包内自检、商业合同流、生成公钥模块、私钥材料和发布边界扫描。该脚本只读本地源码与 `release/`，不得作为 GitHub Release、下载页、`latest.json` 或生产服务器发布动作。

## 17. 代理业务管理

胖虎AI管理员账号必须新增一级菜单“代理业务管理”。该菜单是代理业务的唯一运营配置入口，至少包含：代理产品介绍、五级费用设置、返佣规则、代理审核、下游客户、佣金账本、结算提现、推广素材、风控冻结。桌面客户端不得复制这些配置规则，只能展示服务端快照和入口。

公开代理招募页为 `/agent/join`，用于招商而不是客户配置 Agent。页面内容由 `agent_marketing_content` 管理，必须讲清楚：卖什么、怎么赚钱、费用多少、适合谁、如何结算、风险边界、立即申请。该页必须能展示 L1 免费开通、L2-L5 审核或收费开通、三类收益来源、T+7 结算、退款冲正和后台账本为准的边界。

代理业务管理与结算系统在服务端包含以下核心表结构：

- `agent_products`: `id, level, name, price_cents, currency, validity_days, requires_review, status, intro_page_enabled`。`L1 可配置为 0 元`，L2-L5 可由后台隐藏、审核制、收费、年费、升级费或押金策略控制。
- `agent_profiles`: `user_id, level, status, product_id, activated_at, expires_at, invite_code`。代理身份只来自服务端权益。
- `referral_bindings`: `buyer_user_id, direct_agent_user_id, bound_at, source_invite_code`。绑定后不可覆盖，重复绑定直接返回原上级。
- `agent_chain_snapshots`: 每次订单、token 消费、激活或安装交付事件保存当时 1-5 级上级链路。
- `commission_policies`: 佣金政策主表，只允许后台启用、停用和发布新版本。
- `commission_policy_rules`: 按 `event_type + receiver_level + depth` 配置 `rate_bps`，只影响新事件，历史订单使用历史快照。
- `commission_events`: 基础事件类型限定为 `token_usage_settled`、`activation_paid`、`agent_install_delivered`；手机控制Agent如参与返佣，必须使用独立 `mobile_control_agent_delivered`。每个事件必须有唯一 `source_event_id` 防止重复返佣。
- `commission_ledger`: 佣金账本状态为 `pending`、`frozen`、`available`、`settled`、`reversed`、`manual_review`，金额字段统一使用 `commission_cents`。
- `settlement_requests`: 提现和结算申请表，记录申请金额、关联佣金、状态、审核人、放款流水和失败原因。
- `agent_marketing_content`: 招募页、FAQ、素材、话术、等级说明和风险边界。

代理业务相关接口如下：

- 公开页：`/agent/join`
- 客户端与内置网站接口：
  - GET `/api/agent/public/offering`: 返回公开代理产品、介绍页内容、可申请等级。
  - POST `/api/agent/apply`: 申请成为代理；0 元产品可直接开通或进入审核。
  - GET `/api/agent/center`: 当前代理总览、邀请链接、下游、三类佣金、结算状态。
  - GET `/api/agent/downstreams`: 当前代理的下游客户列表和分页游标。
  - GET `/api/agent/commissions`: 当前代理的佣金账本查询，支持状态、事件类型和分页。
  - POST `/api/agent/settlements`: 代理发起提现或结算申请，默认只能申请 `available` 金额。
  - POST `/api/referrals/bind`: 邀请码绑定；已有绑定直接返回原上级，不覆盖。
- 后台管理端接口：
  - GET/PUT `/api/admin/agent/products`
  - GET/PUT `/api/admin/agent/policies`
  - GET/PUT `/api/admin/agent/marketing-content`
  - GET/POST `/api/admin/agent/applications`
  - GET/POST `/api/admin/agent/settlements`
  - POST `/api/admin/agent/ledger/:id/freeze|release|reverse`

佣金结算与提现规则：

- 遵循纯五级代理模型，L1 只能拿 1 层，L5 最多拿 5 层；`receiver.level >= depth` 时才允许按规则返佣。
- 没有启用的 `commission_policy` 时，不产生佣金，只记录可诊断事件。
- 佣金默认 T+7 从 `pending` 转 `available`；退款、撤单、交付失败必须冲正。
- 未结算佣金可以转为 `reversed`；已经结算、提现或状态不可自动追回的佣金必须进入 `manual_review`。
- 管理员风控冻结只能把可处理账本项转为 `frozen`；解除冻结只能从 `frozen` 回到 `available`，不能绕过 T+7。
- 所有金额统一用 `price_cents`、`commission_cents` 和 `requested_cents`，币种默认 `CNY`。
