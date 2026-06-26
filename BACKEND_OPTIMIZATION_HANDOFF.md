# 后端优化窗口交接说明

最后更新：2026-06-26

## 1. 交接目标

你是专门负责本项目后端和商业合同优化的 Codex 窗口。

项目路径：

```text
C:\Users\Administrator\Documents\codex\panghu-codex-installer
```

你的目标是审计并优化本工具的后端合同、商业授权、配置会话、扣次、API Key 归属校验、Agent 交付边界和主程序分发逻辑。你不是前端窗口，不负责视觉重设计；也不是发布窗口，不负责打包、Release、下载页或 `latest.json`。

## 2. 必读顺序

开始前先读：

```text
C:\Users\Administrator\.codex\进化.md
C:\Users\Administrator\Documents\codex\工具项目目录\README.md
C:\Users\Administrator\Documents\codex\工具项目目录\PROJECTS.md
C:\Users\Administrator\Documents\codex\工具项目目录\projects\多 Agent 一键配置工具.md
```

然后读本项目文件：

```text
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
```

重点读源码：

```text
src\panghu_codex_installer.py
src\commercial_api.py
src\commercial_core.py
src\commercial_backend_contract.py
scripts\commercial_flow_acceptance.py
scripts\commercial_release_acceptance.py
scripts\agent_delivery_acceptance.py
tests\test_commercial_api.py
tests\test_commercial_core.py
tests\test_panghu_commercial_manifest.py
tests\test_agent_playbooks.py
tests\test_commercial_flow_acceptance.py
tests\test_commercial_release_acceptance.py
```

## 3. 当前真实状态

当前阶段：

```text
文档收束完成后的后端审计与功能闭环补齐阶段
```

已经有的基础：

- 商业 API 合同已形成：商品、订单、支付、权益、配置会话、扣次、撤销、返佣、诊断码。
- `profile.json` 持久化边界已收紧。
- 主程序商业链路已收束为当前登录买家上下文。
- 当前商业 API 请求构造只围绕当前登录买家上下文。
- manifest 商业字段需要 Ed25519 签名和客户端公钥验签。
- 配置成功必须以真实任务验证通过为扣次门槛。
- `scripts\commercial_flow_acceptance.py --json` 可跑离线商业流程验收。
- `scripts\commercial_release_acceptance.py --json` 可跑本地轻量发布前检查。
- 代理业务商业化合同已在本仓库离线层补齐：`src\commercial_backend_contract.py` 覆盖代理产品、营销内容、代理申请审核、五级链路、三类佣金事件、T+7 结算申请、管理员账本冻结/解冻/冲正。
- `src\commercial_api.py` 已新增代理公开招商、下游客户、佣金账本、结算申请、后台产品、政策、营销内容、审核、结算和账本动作请求构造。
- `agent_center` 已纳入商业 manifest 控制字段；只要 manifest 包含 `agent_center`，客户端必须要求服务端签名。

仍未完成：

- 后端合同与主程序实现还未逐项审计完成。
- 真实客户授权上下文和真实业务闭环验收未完成。
- Codex、ClaudeCode、OpenClaw、Hermes 使用真实客户 API Key 的最小中文对话闭环未完成；Gemini / agy 配置链路待开发。
- ClaudeCode、OpenClaw、Hermes 独立客户端形态未稳定确认。
- 当前 `src\panghu_codex_installer.py` 约 7820 行，UI、商业逻辑、Agent 安装、更新和验收高度耦合，后续应拆层。
- 真实胖虎AI后端数据库迁移、接口实现、管理员后台“代理业务管理”和公开招商页 `/agent/join` 尚未在本仓库验收；本仓库只提供合同、请求构造、离线模拟和测试守卫。

## 4. 优化边界

你可以处理：

- 商业 API 合同与客户端请求构造一致性。
- `operator_context`、`target_buyer_context`、当前登录买家身份的边界。
- API Key 归属校验。
- 配置会话预占、成功、失败、人工复核、幂等。
- 真实任务验证和扣次边界。
- manifest 商业签名、公钥注入和拒绝策略。
- Agent 交付矩阵、未完成项不扣次、不包装成交付。
- 后端模拟器与测试用例的准确性。

你不要处理：

- Tkinter / HTML UI 视觉重设计。
- 客户下载页生产更新。
- GitHub Release 上传。
- 三端重包。
- 胖虎AI网站、控制台、支付、钱包、数据库的生产实现。
- 本地代操作或第三方账号代登录能力。

## 5. 重点问题清单

### N-BE-01 当前买家上下文收口

合同要求：当前客户端只保留统一胖虎AI账号登录，商业接口围绕登录后的买家本人工作。

检查点：

- 客户端请求不能让代理身份成为本地配置操作者。
- `operator_context` 和 `target_buyer_context` 在客户端侧应等于当前登录买家。
- 服务端必须用 Authorization token 校验 operator，不能信任请求体。
- 离线模拟脚本中若使用 `operator_user_id="agent-1"`，需要明确它是服务端代理归因模拟，不是客户端真实操作者口径；建议拆分或改名，避免误导。

相关文件：

```text
docs\COMMERCIAL_BACKEND_API_CONTRACT.md
src\commercial_api.py
src\commercial_core.py
src\commercial_backend_contract.py
scripts\commercial_flow_acceptance.py
tests\test_commercial_api.py
tests\test_commercial_core.py
```

### N-BE-02 profile 持久化白名单复核

必须保持：

- 保留胖虎AI买家会话 cookie 和内置浏览器 profile，重启后优先自动恢复买家登录态。
- 不保存部署 token。
- 不保存账号密码或第三方账号密码。
- 不保存订单号、权益 ID、配置会话 ID、邀请码等商业污染字段。
- 启动恢复时不能把旧部署 token 当成当前授权，必须用保存的买家会话重新向服务端申请。

相关函数：

```text
build_persistent_profile_payload
save_profile_data
load_saved_profile
```

### N-BE-03 API Key 归属校验强制化

合同要求：

- 保存或配置 API Key 前必须调用服务端归属校验。
- `owner_user_id == target_buyer_user_id` 才允许保存和继续配置。
- 跳过普通接口测试不等于跳过商业归属校验。
- 归属校验失败不得写入 `profile.json`，不得进入配置会话预占或扣次。

相关文件：

```text
src\commercial_api.py
src\commercial_core.py
src\panghu_codex_installer.py
tests\test_commercial_api.py
tests\test_panghu_commercial_manifest.py
```

### N-BE-04 配置会话和扣次边界

必须保持：

- 配置前先预占权益。
- 失败释放预占且不扣次。
- 真实任务验证通过后才 complete 和扣次。
- 设备超限不能创建活跃配置会话。
- `manual_review` 不自动重复扣次，并冻结该权益。
- 成功、失败、预占都要幂等。

相关文件：

```text
src\commercial_api.py
src\commercial_core.py
src\commercial_backend_contract.py
scripts\commercial_flow_acceptance.py
```

### N-BE-05 Agent 交付边界

当前不能把 ClaudeCode、OpenClaw、Hermes 包装成无条件完整付费交付；Gemini / agy 未接入前只能作为官方入口或待接入状态。

必须做到：

- 安装、配置写入、启动检测、最小中文对话、验收状态、交付状态分开记录。
- 未通过最小对话验收时 fail 配置会话，不扣次。
- CLI 能检测到不等于客户端形态稳定。
- 401 只能证明请求打到网关，不证明客户交付完成。

相关文件：

```text
src\panghu_codex_installer.py
scripts\agent_delivery_acceptance.py
tests\test_agent_playbooks.py
tests\test_panghu_commercial_manifest.py
```

### N-BE-06 manifest 商业签名和公钥策略

必须保持：

- 只要 manifest 包含商业控制字段，就必须有签名字段。
- 商业控制字段包括 `products`、`entitlements`、`commercial`、`commercial_enabled` 和 `agent_center`。
- 签名算法为 Ed25519。
- 客户端只内置公钥，不保存私钥。
- 缺公钥、缺签名、验签失败时拒绝商业清单。
- 生产客户包必须注入 `PANGHU_COMMERCIAL_MANIFEST_PUBLIC_KEY_PEM`。
- `src\commercial_manifest_public_key.py` 是生成文件，不得提交。

相关文件：

```text
src\commercial_core.py
src\panghu_codex_installer.py
scripts\commercial_manifest_signer.py
scripts\commercial_release_acceptance.py
scripts\build-windows-exe.ps1
scripts\build-mac-app.command
.github\workflows\build-mac-release.yml
```

### N-BE-07 代理业务商业化合同落地

必须按 `docs\COMMERCIAL_BACKEND_API_CONTRACT.md` 第 16 节实现真实服务端能力：

- 胖虎AI管理员后台新增一级菜单“代理业务管理”。
- 菜单至少包含代理产品介绍、五级费用设置、返佣规则、代理审核、下游客户、佣金账本、结算提现、推广素材、风控冻结。
- 公开招商页固定为 `/agent/join`，必须讲清楚“卖什么、怎么赚钱、费用多少、适合谁、如何结算、风险边界、立即申请”。
- L1 可配置为 0 元开通；L2-L5 可由后台改为隐藏、审核制、收费、年费、升级费或押金。
- 邀请码绑定后不可覆盖，重复绑定直接返回原上级。
- 三类佣金事件固定为 `token_usage_settled`、`activation_paid`、`agent_install_delivered`，每个事件必须有唯一 `source_event_id`。
- 佣金状态固定为 `pending`、`frozen`、`available`、`settled`、`reversed`、`manual_review`。
- 默认 T+7 从 `pending` 转 `available`，退款、撤单、安装失败和重复回调必须冲正。
- `agent_center` 只下发客户可读快照；客户端不得计算费用、等级、返佣比例、下游归因或结算结果。

相关文件：

```text
docs\COMMERCIAL_BACKEND_API_CONTRACT.md
docs\PRODUCT_MANUAL_SINGLE_SOURCE_OF_TRUTH.md
src\commercial_api.py
src\commercial_backend_contract.py
src\commercial_core.py
src\panghu_codex_installer.py
scripts\commercial_flow_acceptance.py
tests\test_commercial_api.py
tests\test_commercial_backend_contract.py
tests\test_commercial_core.py
tests\test_panghu_commercial_manifest.py
tests\test_commercial_flow_acceptance.py
tests\test_commercial_backend_contract_docs.py
```

## 6. 架构优化建议

当前最大结构问题是 `src\panghu_codex_installer.py` 过大，建议分阶段拆分，不要一次大重构。

建议目标结构：

```text
src\panghu_codex_installer.py          # 只保留应用入口和 UI 编排
src\commercial_api.py                  # 商业接口请求、脱敏、幂等 key
src\commercial_core.py                 # 商业规则纯函数、manifest、权益、交付报告
src\agent_adapters\codex.py            # Codex 安装/配置/验收
src\agent_adapters\claude_code.py      # ClaudeCode 安装/配置/验收
src\agent_adapters\openclaw.py         # OpenClaw 安装/配置/验收
src\agent_adapters\hermes.py           # Hermes 安装/配置/验收
src\web_bridge.py                      # pywebview、外部浏览器回退、页面入口
src\update_flow.py                     # 在线更新、包选择、替换脚本
src\diagnostics.py                     # 客服诊断包、日志脱敏、验收矩阵
```

拆分原则：

- 先抽纯函数和无 UI 依赖模块。
- 每抽一层必须保留测试。
- 不在同一轮同时改 UI、商业合同、Agent 配置和发布。
- 保持现有行为不变，再做优化。

## 7. 建议验证命令

基础健康检查：

```powershell
python src\panghu_codex_installer.py --self-test
python -m pytest tests\test_commercial_api.py tests\test_commercial_core.py tests\test_panghu_commercial_manifest.py tests\test_agent_playbooks.py -q
```

商业合同检查：

```powershell
python scripts\commercial_flow_acceptance.py --json
python -m pytest tests\test_commercial_api.py tests\test_commercial_backend_contract.py tests\test_commercial_core.py tests\test_panghu_commercial_manifest.py tests\test_commercial_flow_acceptance.py tests\test_commercial_backend_contract_docs.py -q
```

发布边界轻量检查，只读本地源码和 release：

```powershell
python scripts\commercial_release_acceptance.py --json --artifact-scope windows
```

Agent 只读盘点：

```powershell
python scripts\agent_delivery_acceptance.py
```

注意：

- 不要默认运行 `--run-dialogue`，除非明确有真实客户 API Key 和授权。
- 不要默认运行 `--with-exe-self-test --deep-scan`，除非进入发布前深度验收或 CI 场景。
- 不要打包或发布。

## 8. 验收标准

完成后必须说明：

- 后端合同和实现是否一致。
- 哪些接口/函数存在偏差。
- 哪些偏差已修正。
- 哪些仍需服务端配合或真实客户授权。
- 哪些 Agent 能完整交付，哪些只能显示为未完成或非收费入口。
- 使用过的测试命令和结果。
- `git status --short` 当前状态。

不能说：

- “目标 Agent 已完整交付”，除非对应 Agent 的真实最小中文对话和功能验收矩阵都通过；Gemini / agy 未接入前只能写官方入口或待接入。
- “内置浏览器闭环完成”，除非 pywebview 和真实网页登录/充值/Key 创建闭环都验证。
- “可以发布”，除非三端包、公钥、Release、下载页、`latest.json` 全部按发布门禁通过。

## 9. 禁止事项

- 不提供本地代操作会话或第三方账号代登录能力。
- 不把代理身份写成本地客户端操作者。
- 不把胖虎AI账号写成 Codex 登录账号。
- 不硬编码价格、次数、有效期、设备数、返佣比例、商品上架状态。
- 保留买家会话，但不保存部署 token、账号密码或第三方账号密码。
- 不把未完成真实任务验证的配置会话提交成功。
- 不改生产服务器、数据库、下载页或 GitHub Release。
