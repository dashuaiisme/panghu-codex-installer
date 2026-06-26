# 后端 CC 分支交接包

最后更新：2026-06-26

## 角色

你负责“胖虎AI多 Agent 一键部署工具”的商业逻辑、服务端合同边界、内置网站闭环可行性、四 Agent 真实交付链路评审和补齐建议。

## 必读文件

1. `C:\Users\Administrator\.codex\进化.md`
2. `docs\PRODUCT_MANUAL_SINGLE_SOURCE_OF_TRUTH.md`
3. `docs\TECHNICAL_MAINTENANCE_MANUAL.md`
4. `docs\COMMERCIAL_BACKEND_API_CONTRACT.md`
5. `PROJECT_BLUEPRINT.md`
6. `ACCEPTANCE.md`
7. `SAFETY.md`

## 当前目标

判断并补齐客户真实功能闭环。不要把单元测试、模拟账本或 UI 文案当成真实交付完成。

## 必查问题

### 1. 胖虎AI网站内置闭环

核对：

- 注册账号是否能在工具内完成。
- 邀请码是否能在工具内填写或识别。
- 创建 API Key 是否能在工具内完成，并能返回工具继续填写。
- 充值购买是否能在工具内完成。
- 支付跳转、扫码、回调、失败态是否有明确路径。
- 代理中心是否只使用服务端数据，不本地计算返佣或等级。
- `pywebview` 不可用时是否明确回退，而不是声称完全内置。

### 2. Agent 真实交付

四个 Agent：

- Codex
- ClaudeCode（CC）
- OpenClaw
- Hermes

每个 Agent 分别核对：

- 安装状态
- 启动状态
- 对话状态
- 验收状态
- 交付状态

重点判断：

- CLI 安装是否真实可执行。
- 客户端安装是否只是打开官方文档，还是有真实安装流程。
- 配置写入文件是否正确。
- 最小中文对话是否能真实返回内容。
- 功能验收矩阵是否以真实结果写入。
- 未通过矩阵时是否会阻止扣次和完整交付。

### 3. 商业与安全边界

核对：

- API Key 不进日志。
- token、邀请码、订单号、权益 ID、配置会话 ID 不进客服日志。
- 不保存可恢复登录 token 或部署授权 token。
- `profile.json` 不写第三方账号密码、服务端授权 token、订单号、权益 ID 或配置会话 ID。
- 不硬编码价格、次数、有效期、设备数、返佣比例、商品状态。
- 商业 manifest 验签缺失时不会绕过。
- ClaudeCode、OpenClaw、Hermes 未完成真实链路时不能包装成完整付费交付。

## 禁止

- 不碰生产服务器、数据库、GitHub Release、下载页、`latest.json`。
- 不打包、不发布。
- 不删除 `release/`、客户包、`docs/superpowers/`。
- 不做 UI 美化。

## 验收输出

必须输出：

- 功能状态表：已完成 / 部分完成 / 未完成 / 阻塞。
- 具体文件和函数引用。
- 必须改的 bug。
- 可以后做的优化。
- 风险优先级。
- 建议测试命令。

## 当前特别提醒

当前不能默认认为“207 条测试通过”代表客户可交付。必须按真实业务链路判断。
