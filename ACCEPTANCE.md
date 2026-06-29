# 产品验收标准

最后更新：2026-06-28

## 0. 本文件职责

本文件只负责 Definition of Done：

- 什么叫通过
- 什么叫未通过
- 进入下一阶段前必须满足什么

本文件不负责记录当前状态、过程流水或执行方法。

## 1. A 级：代码健康验收

必须通过：

- `python -m py_compile src\panghu_codex_installer.py scripts\agent_delivery_acceptance.py scripts\customer_web_entry_acceptance.py`
- `python src\panghu_codex_installer.py --self-test`
- `python -m unittest discover -s tests -p "test_*.py"`

说明：

- A 级通过只代表代码健康通过，不代表产品可交付。
- 本轮结果：`py_compile OK`、`self-test OK`、`unittest 306 OK`。
- 本轮旧前端删除 / 商业 manifest / 发布脚本 focused pytest 为 `98 passed, 11 subtests passed`；商业后端 focused pytest 为 `158 passed, 11 subtests passed`。

## 2. B 级：客户界面验收

当前旧前端已按最新指令删除，B 级客户界面验收暂停，不再引用旧 WebView shell、旧截图脚本或旧截图目录作为当前证据。

新前端重做前，本级状态为 `deferred`。后续新 UI 重新接入后，必须重新生成截图证据并覆盖：

- 未登录登录闸口
- 登录页自动登录 / 记住密码勾选项、账号下拉切换和账号删除入口
- 登录后设置菜单：切换账号、切换主题、退出当前账号
- 登录后配置Agent模块
- 胖虎AI网站模块
- 增值业务模块
- 代理中心模块
- 普通窗口
- 全屏窗口

新 UI 必须满足：

- 登录前不暴露完整控制台
- 顶部、左侧、中间、右侧、底部结构稳定
- 左侧只展示当前模块子导航
- 中间区域不堆满所有步骤
- 右侧账号 / 权益 / Agent 交付状态清晰

说明：历史截图不得作为新前端或当前上线判断证据。

## 3. C 级：胖虎AI网站入口验收

必须逐项验证：

- 注册页面入口正确
- 邀请码 / 注册入口正确
- 创建 API Key 页面入口正确
- 充值购买页面入口正确
- 代理中心入口正确
- `pywebview` 可用时优先内置打开
- `pywebview` 不可用时明确阻断并提示内置浏览器未完成；客户站点入口不得自动打开系统浏览器

说明：

- 入口和依赖前提通过，不等于真实业务闭环通过。
- 本轮 `.venv\Scripts\python.exe scripts\customer_web_entry_acceptance.py` 返回 `web_entry_status=ready`。
- 系统 Python 返回 `blocked` 是因为没有 `webview`，不代表项目运行环境失败；C 级入口前提以项目 `.venv` 结果为准。

## 4. D 级：代理中心业务验收

代理中心是登录后的独立代理业务模块。必须逐项验证：

- 代理身份来自服务端，不来自本地身份分流或本地代操作会话。
- 服务端能区分 token 返佣、下游付费激活返佣和付费安装 Agent 返佣。
- 下游客户归因、代理等级、返佣比例、结算状态和账本明细都来自服务端。
- 客户端只展示服务端返回的代理中心摘要、入口和状态，不本地计算返佣、等级、价格或次数。
- 没有服务端合同时，代理中心只能显示待接入或占位状态，不能写成已完成。

## 5. E 级：Agent 交付验收

完整配置交付验收对象：

- Codex
- ClaudeCode（CC）
- OpenClaw
- Hermes

交付范围必须绑定 `delivery_scope`：

- `cli`：只验收官方 CLI 安装、配置写入、启动检查和最小中文对话。
- `client`：只验收官方客户端或独立客户端形态。
- `both`：CLI 和客户端都必须分别验收通过。

CLI 和客户端是独立付费、独立交付范围。只购买 CLI 时，不得因为客户端未确认阻断 CLI 交付；购买 `client` 或 `both` 时，客户端入口、启动、配置和真实任务必须单独验收。

每个已接入 Agent 必须分别验收五维状态：

- 安装状态
- 启动状态
- 对话状态
- 验收状态
- 交付状态

最低通过条件：

- 所购 `delivery_scope` 对应的官方 CLI 或客户端入口真实可用
- 配置写入目标文件正确
- 重开或启动检查通过
- 最小中文对话返回有效内容
- 功能验收矩阵记录通过

未完成真实对话验收前，不得标记为完整付费交付。

CLI-only 通过不等于客户端 scope 通过，也不等于三端客户包发布完成。

待接入或入口型 Agent：

- Gemini / agy 当前只保留官方安装或打开入口；未接入胖虎AI API Key 配置、启动检测、最小中文对话和功能验收矩阵前，不得计入完整配置交付。

Codex 额外必须验收三种配置模式：

- 普通模式：写入胖虎AI中转站 provider 和 API Key，消耗胖虎AI额度。
- 双态模式：保留 ChatGPT 登录态，写入胖虎AI中转站 token，消耗胖虎AI额度。
- 官方直登：写入官方 `openai` provider，保留 ChatGPT 登录态，不写胖虎AI中转站 Key，消耗客户自己的 ChatGPT 账号额度。

Codex 模式切换必须验收：

- 切换前已保存当前配置快照。
- `auth.json` 中已有 ChatGPT 登录态不会被普通/双态/官方直登来回切换误删。
- 模式快照里的过期 API Key 不会被恢复到当前主配置。
- 任何模式写入后，都提示客户完全退出 Codex 再重新打开。

## 6. F 级：安全与商业边界验收

必须满足：

- API Key 不输出到日志
- 保留胖虎AI买家会话 cookie 和内置浏览器 profile，重启后优先自动恢复买家登录态
- 服务端部署授权 token 不写入 `profile.json` 或买家会话文件，启动恢复时必须重新向服务端申请
- 胖虎AI买家密码只有用户勾选“记住密码”时才允许本机系统加密保存；不得保存明文密码；自动登录必须依赖可解密密码记录
- WebView 初始状态和账号下拉不得接收全部账号的明文密码，只能显示账号、勾选标记和是否存在保存密码
- 不保存第三方账号密码、部署授权 token、订单号、权益 ID 或配置会话 ID
- 所有客户默认请求走 `https://aitokenapi.cc`
- 不硬编码价格、次数、有效期、设备数、返佣比例、商品上架状态
- 不硬编码 token 返佣、激活返佣、安装返佣、下游客户归因、代理等级或结算状态
- 未通过功能验收矩阵不得扣次或包装成交付完成
- 胖虎AI账号不能被写成 Codex 登录账号。
- 官方直登不应创建胖虎AI商业配置会话，不应扣胖虎AI配置次数。

## 7. G 级：连接通讯软件增值服务验收

连接通讯软件必须与基础 Agent 配置分开验收：

- 基础 Agent 配置交付通过，不自动代表连接通讯软件通过。
- 连接通讯软件失败，不自动回滚基础 Agent 配置交付。
- 连接通讯软件必须有独立订单、独立配置会话、独立验收记录和独立收费事件。
- 入口不能被“本工具本次基础配置会话已完成”硬锁死；已有可用 Agent、历史交付或人工复核必须能进入检测和单独配置链路。

最低通过条件：

- 平台通道配置成功。
- 通讯软件聊天窗口（手机或电脑端）发送指定测试消息。
- 服务端记录入站平台消息 ID。
- Agent Runtime Adapter 成功执行请求。
- 平台聊天窗口收到 Agent 回复。
- 服务端记录出站消息 ID、响应摘要、验收时间和唯一 `source_event_id`。

防卡扣费验收：

- 已形成验收证据后，客户断网、禁用 API Key、取消平台授权、关闭机器人、删除群聊或阻断回调，不得自动判定为配置失败、自动退款或不收费。
- 未形成入站消息、Agent 调用和出站回复证据时，不得标记连接通讯软件交付完成。
- 重复平台回调或重复验收提交不得重复扣费、重复返佣。

## 8. H 级：发布前验收

只有 A 到 G 全部通过，才允许进入：

- Windows 打包
- Mac 打包
- GitHub Release
- 下载页和 `latest.json` 更新

当前是否允许进入 F 级，不在本文件判断，由 `FINAL_REPORT.md` 判断。

本轮发布前相关判定：

- `commercial_flow_acceptance.py --json` 返回 `status=PASS`，但属于 `offline_only` / `offline_guarded` / `mock_guarded` 范围。
- `commercial_release_acceptance.py --json` 返回 `status=WARN`，原因是只有旧名历史客户包、三端包 `stale`、未注入商业清单生产公钥。
- 只要轻量发布前检查仍为 `WARN`，不得进入 Windows/Mac 打包、GitHub Release、下载页或 `latest.json` 更新流程。
