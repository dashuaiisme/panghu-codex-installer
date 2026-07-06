# 变更记录

## 2026-07-07（第二轮：多视角验收 + 全量修复 P0/P1/P2）

> 5 视角审查(买家端到端/跨仓合同/前端/客户端后端/服务端资金安全)后的全量修复。详见 `docs/交接说明_2026-07-07_Claude.md` 第 7 节。

- **P0（客户端）**：① 运行日志修复——后端推 `{t,c,m}` 对象、前端当字符串 → 满屏 `[object Object]`，买家点安装/写配置后看不到真实结果；现正确解析对象并把历史日志从 `state.logs` 接上。② Codex 二进制未真正装上(install_agent=False)时不再判"安装通过"、不再据网关探测扣次(杜绝"没装也扣次"假交付，+回归测试)。③ 软件内扫码付款不再写死 codex，按第 3 步所选 Agent 取商品(避免选 Claude 却买成 Codex 权益白花钱)。
- **P1（客户端）**：`start_install` 补并发护栏；第 7 步"连通测试"不再误调完整付费部署(改查看日志，避免重复预占/扣次)；增值业务服务端数据 XSS 转义 + URL 白名单；侧栏 agent 子导航走 `go_to_step` 门禁 + "已完成✓"改按真实完成信号(去假勾)。
- **P2（客户端）**：`success_count` 只在配置真正写入成功才+1；第 3 步模式小字按各 Agent 实际支持模式动态生成；第 2 步环境检测端口/网络改诚实文案(不再谎报"隧道已建立✓")。
- **服务端（本地改动，尚未部署，需走生产锁+批准）**：5 个创建接口(提现/下通讯软件单/平台授权/申请代理/提交验收)幂等键并发竞态加 `IntegrityError`/savepoint 兜底(重复提交返回既有结果而非 500)；3 个 admin 列表接口 `status` 参数加 membership 校验(非法值 422 而非 500)；订正 `commission.py`/README 里"T+30"旧注释→"结算等待期以管理员后台设置为准，默认 T+7"。
- 结论：按用户决策，"客户端模式装好即验收合格/不验网络""撤单走人工退款""结算周期后台可配"均为设计如此不改。客户端 **371 测试全绿**、服务端 **163 测试全绿**、index.html 内联 JS `node --check` 通过。**客户端仍未打包发布；服务端本轮改动待部署。**

## 2026-07-07（型号修正 + 安装/配置拆步 + 服务端 WAP/自动验收上线）

> 详细交接见 `docs/交接说明_2026-07-07_Claude.md`（后来 agent 先读它，含"别改回旧的"清单）。

- **模型型号修正（用真实中转站 key 实测）**：`gpt-5.4`→**`gpt-5.5`**（codex/openclaw/hermes，`d2299d1`）、`claude-opus-4.8`(点)→**`claude-opus-4-8`**(中划线，`d76eb90`）。旧型号在中转站均 `model_not_found`。全仓已无旧型号。⚠️ 别再填回旧型号。
- **「安装」与「写入配置」拆成两个真步骤（`0e548e3`）**：第4步「安装」= 仅安装（新增 `start_install`/`_install_worker`，不写配置、不预占/扣次）；第5步「写入配置」= 真写配置+验收（按钮调 `start_deploy`），下方保留配置健康面板。**扣费时机不变、`_deploy_worker` 计费零改动**。修掉了"安装步偷偷写配置、写配置步不写配置"的错位。
- **配套服务端（panghu-admin，另一仓）已上线**镜像 `panghu-admin:20260707-wap-autoaccept`：#5 支付宝 WAP 工具订单支付、#4 通讯软件服务端自动验收。真实 ¥0.10 支付闭环 + 模拟签名平台回调自动验收均生产验证通过。回滚镜像 `panghu-admin:20260705-r6`。
- **已知限制**：`build_config`/`merge_config` 仍忽略传入 model、恒写死型号（现 gpt-5.5），"按买家选择写型号"留作后续增强；撤单 `reverse_tool_order` 只置 refund_pending、不自动退支付宝。
- 客户端 **370 测试全绿**。客户端仍未打包发布，本轮改动随下次发布生效。

## 2026-07-04（第四轮：五 Agent 商业链路全通 + 代理中心真数据 + 佣金第 4 类事件）

- **五个 Agent 全部真机走通完整商业链路**（本地联调栈，沙箱 USERPROFILE/LOCALAPPDATA/APPDATA）：Codex、ClaudeCode、OpenClaw、Hermes、Gemini/agy 均完成 权益门禁→会话预占→安装检测→快照→配置写入→启动检测→**真实 CLI 最小中文对话"胖虎AI配置验证成功"→扣次→交付矩阵"完整交付"**；Gemini 首次失败时"不扣次"守卫正确生效。扣次真实反映到顶栏算力（25→14 次）。
- **修复 agy 探针命令**：agy CLI 无 `-m` 短参（报 flags provided but not defined），改 `--model`。
- **联调网关补三种模型接口格式**：/v1/messages（Anthropic，ClaudeCode 用）、/v1beta/models/*:generateContent|streamGenerateContent（Gemini，agy 用）、/v1/chat/completions 补 SSE 流式；三格式均返回验收文本。
- **沙箱隔离修正**：Hermes 配置走 LOCALAPPDATA 而非 USERPROFILE，首轮联调误写真实 `AppData\Local\hermes`（客户端自动备份机制生效），已用备份恢复原配置；联调启动脚本现在同时沙箱 USERPROFILE/LOCALAPPDATA/APPDATA。注意：npm install -g 全局升级了 openclaw 2026.6.10→2026.6.11（真实环境，无害）。
- **后台佣金引擎补第 4 类事件 tool_order_paid**（合同歧义点 #1 决议）：与 paid_activation 同构、比例独立配置、默认 0 未配置不允许启用、五级归因/幂等互斥/T+N/冲正全套；管理页同步。后台 **77 测试全绿**。其余 4 个歧义点维持已实现口径（提现账号可空人工补充、放款流水号 payout_reference 优先 reason 兜底、回调平台+聊天对象匹配、账本动作 freeze/release/reverse）。
- **代理中心真数据打通**：后台 seed 默认产品/四类佣金比例（ready_to_enable=true）→ 买家经联调网关 /api/agent/apply 申请 → 管理员审批 → 客户端"代理中心"同步真实云端快照：L1 等级、邀请码、四项账本金额、同步检查全绿、网络在线。截图 outputs/integration_14_agent_center.png。
- 客户端 **359 测试全绿**。遗留：增值业务目录走签名清单同步已有底座、待服务端提供目录数据；生产部署待用户批准 + PRODUCTION_LOCK 流程。

## 2026-07-04（第三轮：本地联调打通完整买家链路 + 后台合同对齐 + 两个真机级 bug）

- **后台管理系统对齐客户端合同**：后台按需求草稿实现的路由（/api/agent/applications、/api/agent-business/* 等）全部改为合同路径（/api/agent/apply、/api/admin/agent/* 等），补齐 commlink offering/platform-auth/回调复数等缺失路由，响应统一 {success,data} 信封；新增 tests/test_client_contract_integration.py（16 项，直接用客户端 build_* 构造器打后台 TestClient）；后台 69 测试全绿（另修 requirements.txt 缺 cryptography）。5 个合同歧义点见后台交接报告（tool_order_paid 事件未实现等）。
- **客户端真机级 bug 两个**：① save_key/log 等把 urlopen 当自定义 opener 传（timeout 被当 data），Key 归属校验对真实服务器也必炸 → 改 trusted_urlopen；② 同步 bridge 处理器内调 log/sync（js_api 回调里 evaluate_js）重入死锁整窗卡死 → 新增异步 JS 推送队列（_push_js + 专用线程），log/sync_webview_state/push_webview_toast 全部队列化；前端 saveApiKey 改为显示成败 toast。
- **本地联调环境**：scripts/local_integration_server.py（8299）——mock 登录/激活/Ed25519 签名清单（agents 白名单+full_config 能力+7 条权益）/config-sessions/verify-owner/支付状态//v1 对话 mock，其余 /api/* 反代本地后台(8300)并注入 X-Panghu-User。客户端新增联调开关：PANGHU_DEV_BASE_URL_OVERRIDE（窗口标题醒目提示）、PANGHU_DEV_MANIFEST_PUBLIC_KEY_FILE；生产不设环境变量行为不变。
- **完整买家链路真机贯通**（沙箱 USERPROFILE，不碰真实配置）：登录→签名清单验签→权益 35 次→Key 校验+归属门禁→环境检测→商业门禁→会话预占→Codex 安装检测→快照→配置写入→连通 200→**最小中文对话"胖虎AI配置验证成功"→交付成功提交扣次→验收矩阵"Codex(CLI)：完整交付"**。截图 outputs/integration_*.png。
- 客户端 359 测试全绿。遗留：其余四 Agent 的同链路联调、代理中心/增值业务模块接本地后台真数据、生产部署（待用户批准+锁流程）。

## 2026-07-04（第二轮：登录后链路全面打通 + 登录失败中文映射）

用户真实账号登录后反馈"很多链路没打通"，真机（CDP 接入真实 WebView2）逐链路排查，找到并修复五类断链：

1. **busy 状态泄漏（伞形根因）**：`_restore_saved_session_worker` 恢复会话后从不 `set_busy(False)`，`worker_running` 永远为 True → 检查更新/保存 Key/部署等所有带 `if self.worker_running: return` 守卫的动作**静默失效**。→ 补 `finally: set_busy(False)`（与 `_login_worker` 对齐）。
2. **Tk messagebox 全军覆没**：43 处 `messagebox.showwarning/showinfo/showerror` 在 webview 模式必抛 RuntimeError 被吞 →"点了无反应"（如无 Key 点环境诊断）。→ 新增 `notify_user/notify_info/notify_warning/notify_error` 统一提示出口（webview 走日志+前端 toast），全量替换；`prompt_online_update` 的 askyesno 在 webview 模式改为提示不自动更新（打包发布叫停中）；`run_environment_check` 的 Tk `env_text` 控件加 webview 守卫；模块级 `open_url` 白名单告警改走 log 回调。
3. **evaluate_js 与页面加载竞态锁死**：启动时会话恢复线程在前端加载完成前调 `evaluate_js`（无超时），竞态输了就永久锁死 bridge → 窗口"未响应"、会话恢复"失灵"（复现过一次）。→ 新增 `webview_ready` 门闩：前端首次拉取 `get_initial_state` 前禁止一切 evaluate_js 推送（`log`/`sync_webview_state`/`push_webview_toast` 三个出口全部加闩，log 推送补 try/except）；就绪前状态与日志随首次拉取整体带给前端，不丢失。
4. **toast 登录后不可见**：`window.showToast` 只写登录页状态条 → 登录后所有 Python 推送提示全部不可见。→ 前端改为全局 toast：登录页走状态条，登录后右上角浮动提示（自动消失、最多堆叠 5 条）。
5. **算力"待刷新"误导**：清单已从服务端刷新但账号无活跃权益时仍显示"待刷新"。→ 改为如实显示"无可用权益"（"待刷新"只用于尚未拉到清单阶段）。

其他：`_login_worker` 的 `user_label`（webview 不存在的 Tk 控件）加 hasattr 守卫；服务端登录失败英文 message 增加中文映射 `localize_server_message`（登录/部署授权两处接入，未收录原文透传，新增单测）；删除沙箱遗留 `_probe_big.txt`（用户批准）。

**真机验证（假账号+真实会话）**：登录失败中文提示；会话恢复后自动更新检查跑通（"当前已是最新版本：1.0.16"）；手动检查更新 4 秒出 toast；无 Key 点环境诊断弹提示并跳回第一步；Codex 模式检测（官方直登+ChatGPT 登录态保留）、配置健康巡检（真实红黄判定+一键修复入口）、网关测速（主线路 200/约 1.2s）、快照列表四条链路后端+UI 全通。全量测试 **359 passed + 187 subtests**。

遗留：更新的"发现新版本"路径在 webview 模式只提示不自动更新（待接前端确认框）；买家购买/扣次/部署链路因该账号无活跃权益无法真机走通（需服务端权益或测试权益）。

## 2026-07-04（Claude Code CLI 接手：登录真机彻底修复 + 全量测试 Windows 复验）

接手 `docs/CLI交接文档_2026-07-03.md`，在 Windows 真机定位并修复登录"无反应"的两个真正根因：

1. **前端重复函数覆盖**：`src/ui/index.html` 存在两个 `submitLogin` 声明——07-03 修复版（带 loginStatus 反馈）在前，Codex 遗留的旧版（alert 版、无反馈）在后；JS 函数声明后者覆盖前者，导致修复版从未生效。→ 删除旧版，全文件扫描确认无其他重复函数声明。
2. **Tk 变量跨线程崩溃（真机根因，沙箱不可见）**：webview 模式主线程阻塞在 `webview.start()`，Tk mainloop 永远不运行；任何 pywebview bridge 线程/登录后台线程访问 `tk.StringVar` 都抛 `RuntimeError: main thread is not in main loop`——`_login_bridge_worker` 第一行 `login_username.set()` 即死，except 块里 `status.set()` 再次抛异常，线程无声死亡，登录结果永远推不回前端；连 `get_initial_state` 等所有 js_api 调用也一直在真机上失败。→ 新增线程安全 `WebviewVar/WebviewStringVar/WebviewBooleanVar/WebviewIntVar`（支持 trace_add），全量替换 `tk.StringVar/BooleanVar/IntVar` 构造点（35 处），bridge/后台线程不再触碰任何 Tk 对象。
3. 测试同步（scope 口径遗留）：`_agent_mode_label` 对已移除 client 模式的 CLI-only Agent 回退到中文标签"客户端"（客户可见矩阵不再出现英文 mode id）；`test_panghu_commercial_manifest.py` 旧文案断言更新为新口径"只销售 CLI 交付；client scope 不适用"。

**真机验证（CDP 接入真实 WebView2 窗口，假账号走完整登录链路）**：点击登录 → 立即黄条"正在登录胖虎AI，请稍候……" → 全程界面响应正常（无卡死）→ 约 2 秒后红条显示服务端真实原因"登录失败：Username or password is incorrect, or user has been banned" → 按钮恢复可点。截图证据 `outputs/login_fake_cred_test.png`。

**Windows 全量复验**：`python -m pytest tests -q` → **358 passed, 187 subtests passed**（含 07-03 所有标"需 Windows 复验"的批次：快照/漂移/测速/scope/合同审计）；`--self-test` OK。

遗留：① 真实账号登录成功路径（切进配置流程）待用户用真实账号验证一次；② pywebview 启动时对 js_api 的 `app` 公开属性做深度反射产生递归告警日志（不致命，建议后续把 `WebviewApi.app` 改为 `_app` 消除）；③ 服务端登录失败 message 为英文原文透传，如需中文可加映射。

## 2026-07-03（修复：登录无反应 + 登录卡死未响应）

两个连环 bug：

1. 登录按钮无反应：`src/ui/index.html` 按钮 `onclick="submitLogin()"` 但 `submitLogin` 从未定义（Codex 遗留），点击 JS 抛 ReferenceError 静默失败。→ 补齐 `submitLogin()`（读表单+勾选、调 `pywebview.api.login`、空字段拦截、失败日志提示）。
2. 修好按钮后登录卡死（窗口"未响应"）：`WebviewApi.login` 同步执行，内含 20s 网络请求，阻塞了 WebView GUI 线程。→ 重构为后台线程：`login` 立即返回 `{pending:true}`，真实登录在 `_login_bridge_worker` 线程跑，结果经 `self.app.log` 日志推送 + `sync_webview_state` 切界面反映；新增 `push_webview_toast` 从后台线程弹提示。
- 需 Windows 复验：完全重启客户端，点登录——界面不再卡死；成功进配置流程，失败在日志区显示原因（账号密码错/连接失败等）。

## 2026-07-03（Codex 模式一键切换+检测面板）

用户反馈三模式验证要手动翻/改配置文件、容易改错。切换本就是一键（按钮已存在），补上"免翻文件的检测"：

- `WebviewApi.get_codex_mode_status`：读 config.toml + auth.json，一键返回当前模式、ChatGPT 登录态是否保留、网关是否正常，免手动核对文件。
- `src/ui/index.html` 配置健康面板新增"Codex 模式一键切换"卡：当前模式徽章 + ChatGPT 登录态标记 + 三个一键切换按钮（普通/双态/官方直登，复用现有 start_config_only/start_dual_state_config/start_official_chatgpt_config）+ 检测按钮；切换后自动重新检测。浏览器预览 stub 补齐。
- `docs/Codex三模式真机验证清单` 改为全程点按钮：切换→退出重开→发中文测→点检测确认，不再要求手动打开 config.toml/auth.json。
- 需 Windows 复验前端结构检查 + self-test。

## 2026-07-03（开源对标补足 第四批：网关线路测速）

依据方案 P1（对标 cc-switch 延迟测速）：

- `measure_gateway_latency`：对胖虎网关候选线路（`GATEWAY_ENDPOINT_CANDIDATES`，当前仅主域名）做 HEAD/GET 轻量探测，返回各线路延迟、可达性，按延迟排序，推荐延迟最低的可达线路。复用现有 `trusted_urlopen`。服务端下发备用线路后可扩展候选列表，为多线路自动选优打基础。
- `WebviewApi.measure_gateway_latency` bridge + 配置健康面板新增"网关线路测速"卡片（延迟着色、推荐标记）+ 浏览器预览 stub。
- 测试：`tests/test_gateway_latency.py`（mock 探测，不打真实网络：推荐最低延迟、排序、不可达置底、全不可达无推荐、默认候选含主线路）。沙箱等价逻辑已验证全绿；需 Windows 复验。
- 用量面板（P1 另一项）仍依赖中转站开放统计接口，接口就绪前不做。

## 2026-07-03（开源对标补足 第三批：配置健康 UI 接入前端）

把第一、二批的后端能力接入 WebView 界面，客户可见可点：

- `WebviewApi` 新增 5 个 bridge 方法：`list_config_snapshots` / `restore_config_snapshot` / `restore_original_config` / `inspect_config_drift` / `repair_config_drift`（异常统一包成 {success, message}）。
- `src/ui/index.html`：配置Agent 模块步骤 5 新增"配置健康"面板 `renderConfigHealth()`——
  - 配置健康巡检：一键巡检五个 Agent，红/黄/正常三色状态；红色（网关被改/缺 Key）直接给"一键修复"按钮；检测到风险切换工具时醒目提示。
  - 配置快照与恢复：按 Agent 查看快照列表（含🔒官方初始），一键回滚到任意快照（带二次确认），一键恢复官方初始配置。
  - 浏览器预览模式补齐对应 stub，isBrowser 下有演示数据。
- 沙箱挂载对大 HTML 文件有截断，node 结构检查不可靠；需 Windows 本机复验：`node` 前端结构检查 + `python src\panghu_ai_client.py --self-test`。
- 至此开源对标 P0 三项（快照/恢复/漂移巡检）后端+UI 全部完成。

## 2026-07-03（开源对标补足 第二批：配置漂移巡检 + 一键修复）

依据方案 P0（对标 cc-switch 漂移检测），实现配置被外部工具篡改的主动发现与修复：

- `inspect_agent_config_drift`：逐 Agent 比对当前配置与胖虎期望值，分级——red（网关地址被改/缺 Key，影响计费、把买家切走）、yellow（模型被改）、ok。覆盖五个 Agent 各自的配置文件与字段；Key 只判存在性，报告不含任何明文。
- `agent_expected_gateway`：各 Agent 期望网关映射（Claude=根域名、Codex/OpenClaw/Hermes=/v1、Gemini=根域名）。
- `inspect_all_config_drift`：全量巡检 + 与 `detect_risk_plugins` 联动——检测到 ccswitch/codex++ 等风险插件时整体升红。
- `repair_agent_config_drift`：一键修复，用当前买家 Key/模型经 `apply_agent_config` 重写配置（自动带快照保护），修复后复检仍红则提示有工具在持续改写。
- 测试：`tests/test_config_drift.py`（红/黄/ok、未配置、缺 Key、期望网关、风险插件升红、修复往返、无明文泄露）。沙箱无 tkinter，已用等价脚本验证核心分级逻辑全绿；需 Windows 复验 `python -m pytest tests/test_config_drift.py -q`。
- UI 巡检面板（红黄灯 + 一键修复按钮）与第一批快照面板同批接前端。

## 2026-07-03（开源对标补足 第一批：统一配置快照 + 一键恢复）

依据 `docs/开源对标功能补足方案_2026-07-03.md`（对标 cc-switch Profile 机制 / Codex++ 官方切回），实现 P0 快照能力：

- 新增统一配置快照层（`~/.panghu_config_snapshots/<agent>/`，可用 `PANGHU_SNAPSHOT_ROOT` 覆盖）：
  - `create_config_snapshot`：写配置前自动快照，含 meta.json（reason/时间/文件清单/缺失清单），保留最近 `SNAPSHOT_KEEP_COUNT=10` 份（用户决策）。
  - `ensure_original_config_snapshot`：首次接管前留存 `original` 初始快照，永不被轮转清理。
  - `list_config_snapshots` / `restore_config_snapshot`：快照列表与回滚；回滚前自动生成 pre-restore 快照（支持"回滚的回滚"）；快照时不存在的文件在回滚时会被移除，精确还原。
  - `restore_original_config`：一键恢复官方初始配置（交付回收 / 客户自修复场景，配合服务端"只补次数"退款政策）。
  - `apply_agent_config` 统一接入：写任何 Agent 配置前先 ensure_original + create 快照；Codex 三模式快照与本层统一。
- 覆盖 5 个 Agent 的真实配置文件路径（Codex config.toml+auth.json、Claude settings.json、OpenClaw json、Hermes config.yaml+.env、Gemini/agy .env）。
- 测试：`tests/test_config_snapshots.py`（original 永久、10 份轮转、回滚往返、缺失文件移除、一键恢复、异常路径）。沙箱无 tkinter 无法跑主程序测试，已用等价独立脚本验证算法全绿；需 Windows 本机复验 `python -m pytest tests/test_config_snapshots.py -q`。
- UI 快照历史/一键恢复按钮为下一批（需接前端）。

## 2026-07-03（客户端 scope 口径修正轮 —— 撤销上一轮错误实现）

用户纠错：正确口径是"官方提供客户端安装的做客户端交付，没有提供的只做 CLI 交付"，上一轮的"CLI 回退顶替客户端交付"属于理解错误，已全部撤销并按正确口径重做：

- `AGENTS_WITH_OFFICIAL_CLIENT = {codex, claude_code, gemini_agy}`：做真实客户端交付。新增 Claude Desktop 检测（`%LOCALAPPDATA%\AnthropicClaude`、`/Applications/Claude.app` 等）和 Google Antigravity 检测（`%LOCALAPPDATA%\Programs\Antigravity`、`/Applications/Antigravity.app` 等）；`verify_agent_client_scope` 检测到官方客户端时通过安装项，最终交付仍以客户端内最小中文任务和验收矩阵为准。
- `CLI_ONLY_DELIVERY_AGENTS = {openclaw, hermes}`：官方无客户端，只销售 CLI；AgentSpec 移除 client 模式，playbook `client_supported=False`，UI 模式选择只留 CLI，验收脚本对 client scope 明确报"不适用"。
- 删除 `CLIENT_SCOPE_CLI_FALLBACK_AGENTS` 及全部回退逻辑；测试重写为新口径（含 Claude Desktop 检测通过/未检测两种路径断言）。
- `ACCEPTANCE.md` E 级、`docs/产品决策清单` §三 同步修正口径并记录本次纠错。
- 需 Windows 本机复验全量 pytest。

## 2026-07-03（客户端 scope 回退口径实现轮）【已撤销，见上一条】

- ~~按用户决策实现客户端 scope 回退~~（误解用户需求，当日修正）。

## 2026-07-03（Gemini/agy 完整配置链路接入轮）

- Gemini / agy（Google Antigravity，`agy` CLI）从"官方入口/待接入"升级为完整配置链路，与其他四个 Agent 同一验收矩阵门控：
  - 配置写入：`install_gemini_agy_config` 写 `~/.gemini/.env` 的 `GOOGLE_GEMINI_BASE_URL=https://aitokenapi.cc`（Gemini 格式服务根地址）、`GEMINI_API_KEY=买家 Key`、`GEMINI_MODEL=<模型>`；保留用户已有其他 env 行，带备份/恢复。依据：agy 继承 Gemini CLI 环境变量；中转站按 `x-goog-api-key` 自动识别 Gemini 格式（docs/openapi/relay.json）。
  - 最小中文对话验收：`agy -m <模型> -p <中文验收提示>`，纳入 `run_agent_dialogue_probe` 通用链路。
  - `AgentSpec.supports_config=True`（cli/client）、playbook 真实化、配置计划真实化；UI 默认勾选 gemini_agy，移除"暂不计入完整配置交付"特殊文案。
  - `agent_delivery_acceptance.py` 移除 gemini 全部 not_supported 特判；隔离验收环境注入 GEMINI 环境变量。
  - 测试同步：test_agent_playbooks（env 构造、合并保留、探针命令）、test_agent_delivery_acceptance_script（标准 CLI 门控、隔离环境断言、探针超时传递）、self-test 断言更新。
  - APP_VERSION 1.0.15 → 1.0.16。
- 文档同步：产品手册、技术维护手册、PRODUCT.md、ACCEPTANCE.md E 级从"待接入"改为"已接入完整配置链路；未通过最小中文对话验收前不计完整交付"。
- 边界保持：配置链路实现 ≠ 已交付；真实客户机器上的 agy 安装、重开启动检测和最小中文对话验收仍未执行。
- 本轮改动需在 Windows 本机复验：全量 pytest + self-test。

## 2026-07-03（N03 合同审计收尾轮）

- 完成后端商业合同（`docs/COMMERCIAL_BACKEND_API_CONTRACT.md`）与客户端实现的逐项对照审计：27/27 路由覆盖、字段名一致、敏感字段过滤完整（SENSITIVE_FIELDS + VALUE_ADDED_FORBIDDEN_KEYS）、所有创建类操作有幂等键、主程序 22 个商业 API 调用点全部经由 `commercial_api.py` 构造器，无绕过手拼请求。审计结论 A 级，无阻塞性偏差。
- 修复 `build_payment_poll_request` 缺少操作者校验：新增 `operator_user_id` 参数与 `_require_current_buyer_operator` 校验，与其余全部请求构造器对齐；同步主程序 `payment_poll` 调用点和 `tests/test_commercial_api.py` 断言（含不匹配操作者抛 ValueError 的负例）。
- 确认商业清单生产公钥注入机制已完备（构建脚本 + CI Secret + signer 脚本），"未注入"是运维步骤而非代码缺口。
- 遗留待澄清（记入 FINAL_REPORT 待决策）：`delivery_scope` 默认值 `codex_agent_config` 不在合同允许值内；通讯软件回调是否需携带 scope 标记。
- 本轮改动需在 Windows 本机复验：`python -m pytest tests\test_commercial_api.py -q` 及全量 pytest。

## 2026-07-03（R5-DOCS-ROBOT-GUIDE-01 文档收尾）

- 记录买家机器人创建/注册/凭证填写引导：客户端 UI `src/ui/index.html` 新增引导卡片，提供官方入口，并提示需要回填 `platform_account_id`、`platform_chat_id`、`gateway_mode`、回调地址和验签密钥。
- 记录防回归范围：`tests/test_panghu_commercial_manifest.py` 增加对应客户 UI 断言，防止后续窗口把引导卡片误删或改成真实接通声明。
- 记录验证结果：focused `28 passed, 74 deselected`；全量 `338 passed, 187 subtests passed`；release acceptance 仍为 `WARN`，阻塞仍是三端包缺失和生产公钥未注入。
- 保留边界：这只是连接通讯软件真实接入前置条件和买家填表链路，不代表真实平台回调、Runtime Adapter 或服务端验收闭环已完成。

## 2026-07-03（R3-DOCS-01 文档收尾）

- 记录 R3 连接通讯软件守卫完成项：服务端合同新增平台回调跨会话隔离和入站消息匹配守卫，防止其它会话或不匹配消息污染验收。
- 记录客户端状态刷新修正：服务端返回 `False` 时覆盖本地旧 `True`，避免旧完成态残留。
- 记录 focused 验证：`python -m pytest tests\test_commercial_backend_contract.py tests\test_installer_backend.py -q -k "communication_software_link" -p no:cacheprovider` -> `24 passed, 54 deselected`。
- 保留未完成边界：这仍不是生产真实闭环；真实平台、Runtime Adapter 生产接入、支付/账本生产记录仍未完成。

## 2026-07-03（团队模式代码推进轮）

- 修正 `src/ui/index.html` 客户运行资产：默认非 preview 状态不再携带示例买家/代理账号，不再硬编码演示次数、设备数、授权日期或全量通过的 Agent 矩阵。
- 修正代理中心和通用服务入口假成功态：将“通道激活”“已连接”“已完成检验”“服务端快照已返回”等客户可误解为真实闭环的文案改为等待服务端确权和同步。
- 修正连接通讯软件一键流程边界：客户端一键连接现在只执行订单/会话/测试/本地预检，不再自动提交真实验收；客户 UI 和 bridge 文案同步改为“一键连接并本地预检”，明确本地预检不能替代平台回调。
- 补强连接通讯软件本地合同闭环：离线合同层要求验收必须绑定已接受的平台回调、Agent Runtime Adapter 成功结果和唯一 `source_event_id`；API 解析新增真实服务、平台回调、Runtime Adapter、验收状态和服务端显式完成声明字段；客户端只展示这些服务端字段，不本地推断真实交付完成。
- 新增 WebView 客户资产静态守卫测试，防止示例账号、演示商业数值和假成功态重新进入 `src/ui/index.html`。
- 补齐前端键盘焦点态、减少动画媒体查询，并把部分裸色值收敛到 CSS token，使 Gemini 风格审计从 FAIL 降为 PASS（仍有设计债级 warning）。
- 本轮重新执行本地验证：全量 pytest `330 passed, 187 subtests passed`，客户端自检通过，商业流程离线验收 `PASS`，前端结构检查通过，Gemini 风格审计 `PASS`。
- 轻量发布前检查仍为 `WARN`：三端客户包缺失，商业清单生产公钥未注入；本轮未打包、未发布、未提交。

## 2026-07-03（第二轮：文档结构合并）

经用户批准执行文档结构合并，根目录文档从 23 个收敛为 12 个。只动文档，未改源码、脚本、测试或版本控制状态。

合并映射：

- `PROJECT_BLUEPRINT.md` → 并入 `PRODUCT.md`（产品说明与项目蓝图）。
- `BACKEND.md`、`FRONTEND.md`、`DESIGN.md` → 并入 `ARCHITECTURE.md`（架构与工程边界）。
- `PLAN.md`、`TASKS.md`、`TASK_GRAPH.md` → 并入 `FINAL_REPORT.md`（当前状态、任务节点、阻塞、下一步的唯一归口）。
- `DEPLOYMENT.md` → 并入 `RUNBOOK.md`（运行、验证与发布手册）。
- `SAFETY.md` → 并入 `SECURITY.md`（安全与边界）。
- `ENGINEERING_CLOSEOUT.md`、`PRODUCT_TREE_MASTER_CONTROL_HANDOFF_2026-06-30.md` → 并入 `HANDOFF.md`（交接与工程盘点，含产品树主控指引）。

同轮修正：

- 文档权威顺序改为只在 `AGENTS.md` 维护，`README.md` 改为文档地图并引用。
- 修正 `ACCEPTANCE.md` 重复的“## 0”章节和“进入 F 级”笔误（应为发布前阶段 I 级）。
- 修正 `FINAL_REPORT.md` 章节乱序（原 6/7 倒置）和“本轮返回”时态（统一为“最近记录”）。
- 修正 `INTEGRATION.md` 章节乱序（8.3/8.4 倒置）。
- 更新 `docs/TECHNICAL_MAINTENANCE_MANUAL.md` 三处对已合并文件的引用。
- 更新 `RUNBOOK.md` 连接通讯软件回归 rg 命令的文件清单为合并后文件。
- 合并前已确认 `tests/`、`scripts/`、`.github/` 对被合并文档无路径依赖；`tests/test_commercial_backend_contract_docs.py` 要求的 README 关键短语全部保留。

## 2026-07-03

- 文档一致性修正：重写 `文档梳理报告_2026-07-03.md`，删除源码缺失/目录失真口径；验证数字统一归口到 `TESTING.md` 的历史记录表。
- 收敛当前状态口径：`FINAL_REPORT.md`、`TASKS.md`、`RUNBOOK.md`、`HANDOFF.md`、`PLAN.md`、`TASK_GRAPH.md`、`ACCEPTANCE.md` 不再重复维护 pytest/unittest 具体数量。
- 明确当前未见 `outputs/` 和 `.venv`；历史截图和 `.venv` 网站入口检查只作为历史记录，复验需重建环境或重新运行截图脚本。
- 修正前端状态：当前客户 UI 入口仍是 `src/ui/index.html`；已清理的是旧 WebView shell、旧截图和旧输出证据，B 级视觉验收待用当前脚本复验。
- 修正代理中心和连接通讯软件口径：本仓可控范围限于文档合同、离线守卫、请求构造和测试边界；真实服务端、平台通道、生产闭环仍未完成。
- 新增 `ENGINEERING_CLOSEOUT.md`，集中记录项目身份、权威材料顺序、根目录文件分类、工程化闭环八类职责、混乱点和待确认问题。
- 新增 `HANDOFF.md`，作为后续窗口接手入口，记录当前目标、已完成、未完成、阻塞、验证结果和下一步。
- 新增 `FRONTEND.md` 和 `DESIGN.md`，记录当前 WebView UI 入口、Python bridge 契约、四个一级模块、设计 token、截图验收和 UI 禁止改动区。
- 在 `README.md` 和 `AGENTS.md` 增加工程化盘点入口，便于后续 Codex / 其他 agent 接手时先确认文件边界。
- 更新 `TASKS.md` 和 `FINAL_REPORT.md`，把本轮工程化整理与仍待确认的删除标记、缓存/输出清理、发布边界分开。
- 收紧 `.gitignore`，补充更多本地缓存、覆盖率、日志和输出目录规则；未删除、移动、重命名任何项目文件。
- 用户确认后清理本地可重建内容：`.pytest_cache/`、`.venv/`、`outputs/`、空 `legacy/` 目录和源码/脚本/测试下的 `__pycache__/`。这些不是项目交付材料；后续 pywebview / 打包相关检查需要先重建 `.venv`。
- 全仓扫描并统一旧名称口径：客户可见应用名、发布包名、CI artifact、验收脚本和旧计划文档统一为 `胖虎AI客户端` / `胖虎AI客户端-*.zip`；移除历史英文包名前缀、历史多 Agent 工具名和旧 release alias。
- 纠正项目身份残留口径：本地用户入口和本地 git root 统一为 `C:\Users\Administrator\Documents\codex\胖虎AI客户端`；`panghu-ai-client` 是 GitHub 远程仓库 slug。

## 2026-06-30

影响范围：仓库入口文档、运行手册和源码整理基线。

- 建立源码仓整理基线：补齐仓库入口级 `AGENTS.md`、`PRODUCT.md`、`ARCHITECTURE.md`、`BACKEND.md`、`TESTING.md`、`SECURITY.md`、`DEPLOYMENT.md`。
- 记录本轮本地验证结果：前端结构、自检、Gemini 风格审计、商业硬编码扫描、商业流程离线验收和 pytest 均通过。
- 明确当前不能发布：轻量发布验收仍为 WARN，三端客户包陈旧，Mac 包仍为旧名历史包，商业清单生产公钥未注入。
- 按用户授权清理旧客户包、历史构建产物、临时日志、历史截图、候选图和历史 handoff；后续客户包必须重新打包。
- 新增 `INTEGRATION.md`，把手机号接码控制中心和 Plus session.脚本工具纳入胖虎AI客户端增值业务集成图；同步服务目录合同、验收标准、状态报告和客户端入口文案。
- 按中转站产品边界交接口径统一主从关系：胖虎AI客户端是主产品；胖虎AI中转站、手机接码、Plus 充值 / Plus 订阅、连接通讯软件、代理中心都是客户端功能区或分支服务；中转站只作为 API 网关分支，不写作平台主后台或客户端后台。
- 增加 `value_added_services` 客户端底座：服务目录纳入商业 manifest 签名控制，客户端解析时过滤敏感字段，并把安全目录同步到 WebView；前端在有服务端目录时优先用服务端入口，没有目录时继续使用过渡静态入口。
- 删除 `legacy/` 下旧一键安装脚本、旧 UI 安装脚本和旧客户说明；这些文件属于历史废弃客户端材料，不再参与当前源码交付。
- 重新生成当前 WebView UI 本地截图证据：登录闸口、配置 Agent、胖虎AI网站、增值业务、代理中心和 1365 宽度配置页。
- 明确跨项目分工：`sim.aitokenapi.cc` 生产 HTTPS 收尾由手机号接码控制中心窗口负责；本仓继续处理客户端入口、服务目录和 Plus 对接口径。
- 保留发布边界：本轮未 stage、未 commit、未发布。

回滚：如需撤销本轮文档整理，只回滚本轮新增入口文档和 `RUNBOOK.md` / `README.md` / `ACCEPTANCE.md` 的新增说明，不触碰其他窗口留下的业务代码改动。

残留风险：三端客户包已清空，发布前必须重新构建并重新验收；当前仍未注入商业清单生产公钥；手机号接码控制中心和 Plus session.脚本工具仍未完成生产端到端验收。
