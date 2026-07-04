# 胖虎AI客户端技术维护手册

最后更新：2026-06-29

> 产品结构、界面规则、客户可见交付口径，以 `docs/PRODUCT_MANUAL_SINGLE_SOURCE_OF_TRUTH.md` 为准。
> 本手册负责技术维护、接口、构建、发布、脚本和限制说明。
> 当前真实状态和是否允许进入发布阶段，以 `FINAL_REPORT.md` 为准。

## 1. 项目边界

本项目是独立的客户侧桌面工具，正式名称为“胖虎AI客户端”。它的职责是让客户登录胖虎AI账号后，在 Windows 或 Mac 上进入一站式 AI 客户端服务流程：配置已接入完整链路的 Agent，打开胖虎AI中转站/网站入口，查看充值购买、增值业务、手机号/短信接码、GPT 会员服务、连接通讯软件和代理中心等服务端入口。Gemini / agy 当前只保留官方入口和待接入状态。

本项目不是“胖虎AI中转站”的子项目；相反，胖虎AI客户端是客户侧主产品和统一入口。胖虎AI中转站在客户端体系中只作为 API 网关分支服务承接，负责 API Token、余额扣费、模型调用、用量记录、模型价格、网关侧充值记账和必要的 token 返佣。手机接码、Plus 充值 / Plus 订阅、连接通讯软件和代理中心同样作为客户端内的功能区或分支服务接入。

本仓只实现客户侧桌面入口、WebView 状态桥接、服务目录解析、Agent 配置和本地交付验收。独立胖虎AI后台管理系统、胖虎AI网站、数据库、支付、钱包、商品上架、代充履约、接码平台结算和各分支服务生产编排由服务端源码项目维护。

文档权威顺序：

1. 产品结构、客户可见规则、交付边界：`docs/PRODUCT_MANUAL_SINGLE_SOURCE_OF_TRUTH.md`
2. 技术维护、接口、构建、发布、脚本：本文件
3. 商业版服务端合同：`docs/COMMERCIAL_BACKEND_API_CONTRACT.md`
4. 蓝图、验收、运行和状态：`PRODUCT.md`、`ACCEPTANCE.md`、`RUNBOOK.md`、`FINAL_REPORT.md`（2026-07-03 起 `PROJECT_BLUEPRINT.md` 并入 `PRODUCT.md`；`PLAN.md`、`TASKS.md`、`TASK_GRAPH.md` 并入 `FINAL_REPORT.md`）
5. `legacy/` 目录不作为当前产品判断依据。

当前本地仓库和远程仓库：

```text
C:\Users\Administrator\Documents\codex\胖虎AI客户端
https://github.com/dashuaiisme/panghu-ai-client
```

路径说明：

- `C:\Users\Administrator\Documents\codex\胖虎AI客户端` 是长期登记路径、用户可见入口和当前本地 git root。
- `panghu-ai-client` 是 GitHub 远程仓库 slug；本地项目名称和本地根目录仍统一为 `胖虎AI客户端`。
- 如果后续要把 GitHub 仓库 slug 也改掉，必须先确认新的英文仓库名，并同步更新远程地址、Release API、CI、下载页和维护登记。
- 旧路径 `C:\Users\Administrator\Documents\codex\胖虎AI` 当前不再作为权威入口。

统一下载入口：

```text
https://aitokenapi.cc/deployer/download
```

公开更新清单：

```text
https://aitokenapi.cc/deployer/latest.json
```

## 2. 当前产品能力

客户流程：

1. 客户打开工具。
2. 使用胖虎AI账号登录。
3. 客户端调用胖虎AI服务端申请部署授权。
4. 客户去胖虎AI控制台创建 API Key。
5. 工具检测系统环境、PATH、包管理器、已安装 Agent 和风险插件。
6. 客户选择要安装的 Agent。
7. 工具正式部署前再次拉取服务端授权清单。
8. 工具调用官方安装入口安装 Agent。
9. 对安全可写的 Codex 写入胖虎AI配置。
10. 登录后通过“胖虎AI网站”模块的内置浏览器入口打开控制台、创建 API Key、充值购买、推广返佣和代理中心等服务端页面。
11. 登录后可进入“配置Agent -> 连接通讯软件”配置独立增值服务。该入口不能只因为本次基础 Agent 配置会话未完成而锁死；已有可用 Agent、历史交付记录或人工复核通过时，都可以作为连接通讯软件的 Agent 来源。
12. 登录后可进入“增值业务”查看服务端下发的 Plus 订阅、账号服务、手机卡/云号码、手机号/短信接码、连接通讯软件和其他业务入口；其中接码入口挂载手机号接码控制中心，目标地址为胖虎AI现有域名的 `sim` 子域名；Plus 订阅履约关联 Plus session.脚本工具。客户端只展示服务端状态，不计算价格、库存、履约、卡密发放、号码分配或上架规则。
13. 如果服务端下发临时 OpenAI 官网访问窗口，工具短时间启用 PAC 系统代理，并到点恢复。
14. 后续用“检查更新”从公开清单下载新版包。

当前登录后主模块固定为：

- 配置Agent
- 胖虎AI网站
- 增值业务
- 代理中心

“代理中心”是登录后的独立代理业务模块。它不能只等同于胖虎AI网站推广返佣页；本工具代理中心需要服务端合同覆盖 token 返佣、下游付费激活返佣、付费安装 Agent 返佣、下游客户归因和结算状态。

支持的 Agent：

| Agent | 当前策略 |
| --- | --- |
| Codex | 安装或检测官方客户端/CLI，并自动写入胖虎AI中转配置、中文规则、工作区说明；通过胖虎AI网关真实任务验证 |
| ClaudeCode | 覆盖官方 CLI 和客户端入口；写入 `~/.claude/settings.json` 的 `env`，配置 `ANTHROPIC_BASE_URL=https://aitokenapi.cc`、`ANTHROPIC_AUTH_TOKEN` / `ANTHROPIC_API_KEY` 和模型，并用 `claude --model <模型> -p <中文验收提示>` 最小中文对话验收。注意 Claude Code 会自行拼接 `/v1/messages`，这里不能写成 `/v1`，否则会变成 `/v1/v1/messages`。当前只读检测到 CLI，但独立客户端形态未稳定确认 |
| OpenClaw | 覆盖官方 CLI 和 Hub/客户端入口；安装优先使用官方 npm 包 `openclaw@latest`，写入 `~/.openclaw/openclaw.json` 的 `models.providers.panghuai` 自定义 OpenAI-compatible 提供商（`baseUrl=https://aitokenapi.cc/v1`、`api=openai-completions`、`apiKey=买家 Key`），并用 `openclaw infer model run --model panghuai/<模型> --prompt ... --json` 最小中文对话验收。未检测到 CLI、`openclaw config validate` 未通过或最小对话失败时，不能声明完整交付 |
| Hermes | 覆盖官方 CLI 和客户端入口；按官方文档写入 Hermes Home 下的 `config.yaml` 与 `.env`，配置 `custom_providers.panghuai`、`model.provider=custom:panghuai`、`PANGHUAI_API_KEY`，并用 `hermes --provider custom:panghuai --model <模型> -z <中文验收提示>` 最小中文对话验收。当前只读检测到 CLI，但独立客户端形态未稳定确认 |
| Gemini / agy | 只保留 Google Antigravity 官方 CLI 和客户端入口；配置功能待开发，默认通过 Google 账号自行登录，不写入胖虎AI API Key 或网关配置，未接入前不算完整交付 |

当前状态说明：

- 以上三项表示“代码中已有配置写入和验收链路”，不等于所有客户机器已经完整打通。
- 完整交付必须以部署后生成的 `胖虎AI-Agent功能验收矩阵.txt` 为准。
- OpenClaw CLI 未检测到、`openclaw config validate` 未通过、Hermes `hermes config check` 未通过、客户端形态未确认或最小中文对话未返回有效内容时，不得扣次或包装成完整交付。测试 Key 返回 401 只能证明请求链路打到胖虎AI网关，不能证明客户交付已完成。
- 当前仓库处于“文档收束后的后端审计与功能闭环补齐阶段”，不等于最终交付完成状态；未完成真实客户闭环前，不进入三端打包、GitHub Release、下载页或 `latest.json` 更新。

风险插件拦截：

- `ccswitch`
- `codex++`
- `CCR / Claude Code Router`

发现这些工具时，部署必须停止并提示客户先卸载或禁用。不要静默删除客户电脑上的程序。

## 3. 关键源码结构

```text
src/panghu_ai_client.py
```

主程序。当前大部分逻辑集中在这一个文件中，包括：

- WebView 正式客户主界面（`src/ui/index.html`）和 Python 后端桥接。
- 胖虎AI登录。
- 部署授权。
- Agent 清单解析。
- 环境检测。
- 风险插件检测。
- Codex 配置写入。
- 备份和恢复。
- 临时 OpenAI 官网访问窗口。
- 在线更新。
- 内置网站入口与 pywebview 内置浏览器阻断提示；正式客户包必须包含 pywebview 和 WebView UI，缺失时视为启动/打包失败，不允许回退到旧 Tkinter 业务界面。
- 自检入口 `--self-test`。

```text
src/commercial_core.py
src/commercial_api.py
src/commercial_backend_contract.py
```

商业版核心、API 合同和后端合同模拟结构。维护重点：

- 不硬编码价格、次数、有效期、设备数、返佣比例或上架状态。
- 商业 manifest 必须走服务端签名和客户端验签。
- 当前客户端只围绕登录后的买家上下文工作；代理身份、下游客户、token 返佣、激活返佣、安装返佣和结算状态只由网站服务端和代理后端承载。
- `profile.json` 必须按白名单保存，只能保留账号提示、API Key、模型和界面偏好；买家登录态由独立会话 cookie 文件和内置浏览器 profile 持久化。历史登录账号和可选“记住密码”记录保存在独立 `login_accounts.json`，密码只允许系统级本机加密 blob，不得写入明文。不能把部署 token、订单号、权益 ID 或配置会话 ID 写入任一本地长期文件。
- 手机号接码控制中心负责手机卡、云号码、短信回传、真实设备 Agent、平台会话和审计；Plus session.脚本工具负责激活码兑换、Session Token 临时处理、Plus 自动化履约、取消续费和履约日志。客户端只打开服务端入口并展示摘要，不保存短信内容、接码设备 token、Plus Session Token 或激活服务密钥。跨项目集成主控说明见 `INTEGRATION.md`。

```text
scripts/run-windows.bat
scripts/run-mac.command
```

源码运行入口。

```text
scripts/build-windows-exe.ps1
scripts/build-windows-exe.bat
scripts/build-mac-app.command
```

本地打包入口。

```text
.github/workflows/build-mac-release.yml
```

GitHub Actions 三端发布工作流。虽然文件名叫 `build-mac-release.yml`，但里面同时构建 Windows、Mac AppleSilicon、Mac Intel。

```text
docs/发送客户说明.txt
docs/PRODUCT_MANUAL_SINGLE_SOURCE_OF_TRUTH.md
docs/COMMERCIAL_BACKEND_API_CONTRACT.md
docs/胖虎AI下载二维码.png
assets/deployer-download-qr.png
```

客户交付材料和产品 / 商业合同文档。

```text
PRODUCT.md
ACCEPTANCE.md
SECURITY.md
RUNBOOK.md
FINAL_REPORT.md
```

产品蓝图、验收标准、安全边界、运行手册和真实状态报告。2026-07-03 文档合并后：`PROJECT_BLUEPRINT.md` 并入 `PRODUCT.md`，`SAFETY.md` 并入 `SECURITY.md`，`PLAN.md` / `TASKS.md` / `TASK_GRAPH.md` 并入 `FINAL_REPORT.md`，`DEPLOYMENT.md` 并入 `RUNBOOK.md`，`BACKEND.md` / `FRONTEND.md` / `DESIGN.md` 并入 `ARCHITECTURE.md`。

## 4. 关键常量

维护时优先检查 `src/panghu_ai_client.py` 顶部常量：

```python
APP_VERSION = "1.0.15"
DEFAULT_BASE_URL = "https://aitokenapi.cc"
CODEX_BASE_URL = "https://aitokenapi.cc/v1"
PUBLIC_UPDATE_MANIFEST_URL = "https://aitokenapi.cc/deployer/latest.json"
LOGIN_URL = "https://aitokenapi.cc/api/user/login?turnstile="
DEPLOYER_ACTIVATE_URL = "https://aitokenapi.cc/api/deployer/activate"
DEPLOYER_MANIFEST_URL = "https://aitokenapi.cc/api/deployer/manifest"
```

规则：

- 每次发新版必须同步修改 `APP_VERSION`。
- 面向客户的默认域名必须使用 `https://aitokenapi.cc`。
- 客户界面的“接口地址”只能只读展示，不能让客户编辑；保存 profile、Key 测试、部署和仅修复配置都必须强制使用 `DEFAULT_BASE_URL`。
- 不要写入内部域名、私有上游域名、管理域名。
- `HTTP_USER_AGENT` 必须保持 ASCII，不要把中文软件名写进请求头。

## 5. 胖虎AI服务端接口

商业版服务端合同以 `docs/COMMERCIAL_BACKEND_API_CONTRACT.md` 为准。本节只列客户端必须对接或不能绕过的关键接口和技术边界。

### 登录

```text
POST https://aitokenapi.cc/api/user/login?turnstile=
```

客户端使用持久化 cookie jar 保存胖虎AI买家会话，并在启动时用该会话重新向服务端申请本次运行的部署授权。`profile.json` 只保存账号提示、API Key、模型和界面偏好；`buyer_session.json` 只保存非敏感买家标识，`buyer_session_cookies.txt` 保存胖虎AI站点 cookie。历史账号列表保存在 `login_accounts.json`，只保存邮箱、记住密码标记、自动登录标记和系统加密后的密码 blob；用户未勾选“记住密码”时不得保存密码，自动登录必须依赖可解密密码记录。WebView 初始状态和账号下拉只允许接收邮箱、记住密码标记、自动登录标记和“是否存在已保存密码”，不得接收全部账号的明文密码；自动登录由后端按选中账号本机解密后提交。客户端不得保存明文账号密码、第三方账号密码、部署 token、订单号、权益 ID 或配置会话 ID；如果服务端返回 401/403、用户主动退出，或用户删除当前账号记录，则清理对应保存会话并回到登录门禁。

### 部署激活

```text
POST https://aitokenapi.cc/api/deployer/activate
```

请求中包含：

- 用户信息。
- 客户端设备指纹。
- 系统平台。
- 应用版本。

服务端返回短期部署令牌。

### 部署清单

```text
GET https://aitokenapi.cc/api/deployer/manifest
```

请求头必须包含：

```text
New-Api-User: 用户 id
X-Panghu-Deployer-Token: 部署令牌
```

返回内容决定：

- 当前账号允许安装哪些 Agent。
- 是否下发 `temporary_openai_access`。

如果服务端接口未上线或返回 401/403，客户端应停止部署，不要绕过授权。

### 商业 API 合同

商业能力必须由服务端控制，客户端只做展示、入口、校验请求和结果记录。当前固定边界：

- 商品价格、次数、有效期、设备数、返佣比例、代理等级、上架状态和灰度规则只能来自服务端。
- token 返佣、下游付费激活返佣、付费安装 Agent 返佣、下游客户归因和结算状态只能来自服务端或代理后端，不能由客户端计算。
- 所有商业接口必须围绕当前登录买家 token 工作；客户端不得建立本地代操作会话，也不得让代理身份作为本地配置操作者。
- API Key 归属校验必须由服务端确认；归属失败时不得保存 Key、不得进入配置会话、不得扣次。
- 配置会话预占、成功、失败必须支持幂等；失败释放预占且不扣次，真实任务验证通过后才允许扣次。
- 客户端日志、诊断包和客服摘要不得输出完整 API Key、token、Authorization、邀请码、订单号、权益 ID 或配置会话 ID。
- 修改商业合同、权益、配置会话、扣次、撤销、返佣、manifest 验签或客户包前置逻辑后，必须跑对应商业验收脚本。

### 增值业务服务目录

胖虎AI服务端应下发统一 `value_added_services` 快照，客户端从该快照展示 Plus 订阅、手机卡/云号码、接码控制台、连接通讯软件等入口。当前 `src/ui/index.html` 内的静态 URL 只能作为过渡默认值，不能作为生产可售或已履约依据。

建议字段：

- `service_id`：稳定服务 ID，例如 `gpt_plus`、`phone_card`、`sms_code`、`communication_software_link`。
- `title`：客户可见名称。
- `target_project`：关联项目，例如“手机号接码控制中心”或“Plus session.脚本工具”。
- `status`：服务端判断的状态，例如 `available`、`paused`、`pending_production`、`manual_review`。
- `entry_url`：服务端入口 URL。接码控制台生产目标为 `sim` 子域名；Plus 购买入口由服务端下发。
- `entitlement_status`：当前买家权益状态，例如 `not_purchased`、`active`、`pending_activation`、`manual_review`。
- `requires_webview_session`：是否要求客户端桥接当前胖虎AI买家会话。
- `summary_url`：客户可读状态摘要接口。
- `unverified_reason`：服务未上线或未验收时的客户/客服可读原因。

客户端展示规则：

- 服务端未返回、返回 `pending_production` 或带 `unverified_reason` 时，只能展示待接入或待生产验收。
- 客户端不得保存短信内容、接码设备 token、Plus Session Token、激活服务密钥、支付密钥或后台履约密钥。
- Plus 激活码发放、Session Token 处理、续费取消、日志回写和人工复核都属于 Plus 执行器与服务端职责。
- 接码号码分配、短信回传、设备 Agent、平台会话、多手机/白卡绑定和审计都属于手机号接码控制中心职责。

### 连接通讯软件服务合同

连接通讯软件是独立增值服务，不得复用基础 Agent 配置订单、配置会话、验收记录或扣费事件。

全链路命名统一为“连接通讯软件”；技术接口、事件名、表名、UI 文案和交付话术都使用 `communication-software-link` / `communication_software_link` 这一组新命名。

服务端合同至少要能表达：

- `service_type=communication_software_link`
- 独立商品、订单、配置会话、验收记录和账本事件
- Agent 来源：本次基础交付、历史基础交付、本机已有 Agent 检测、人工复核
- 平台通道：`qq_bot`、`weixin`、`feishu`、`dingtalk`、`wecom`
- 平台授权会话：服务端创建授权链接或二维码，客户端打开给买家扫码/确认，并轮询服务端回填平台账号、聊天对象和网关模式
- 验收证据：入站平台消息 ID、Agent 调用证据、出站平台消息 ID、响应摘要、验收时间、`source_event_id`
- 状态区分：待配置、等待平台授权、已连接、测试中、验收通过、失败、暂停、人工复核
- 创建连接通讯软件配置会话前，服务端订单必须已支付，或明确进入人工预售/人工复核；未支付订单不得写入平台账号或聊天对象。
- 客户端不得保存机器人密钥、个人微信密码、平台 access token 或长期授权密钥；这些凭据只能由服务端平台授权回调、安全凭据库或人工复核链路处理。

入口规则：

- 主入口固定在“配置Agent -> 连接通讯软件”。
- 增值业务模块只做销售卡片和介绍入口。
- 代理中心不得承载连接通讯软件配置入口。
- 不允许用“基础 Agent 是否由本工具本次配置完成”作为唯一解锁条件。已有 Agent 或历史交付可通过检测和人工复核进入连接通讯软件链路。

扣费与防套利规则：

- `agent_install_delivered` 只代表基础 Agent 配置交付。
- `communication_software_link_delivered` 只代表连接通讯软件交付。
- 两个事件必须进入各自服务账本和验收记录，不能用连接通讯软件验收去补基础 Agent 交付，也不能用基础 Agent 验收去触发连接通讯软件扣费。
- 连接通讯软件交付不能只看当前是否还能收到消息。配置完成并形成验收证据后，客户断网、禁用 Key、关闭平台授权、删除机器人或阻断回调，应进入暂停、重试或人工复核，不得自动失败、自动退款或取消收费。
- 如果从未形成入站消息、Agent 调用和出站回复证据，不能标记连接通讯软件交付完成。
- 客户端本地 Runtime 测试和一键连接只能作为本地预检；不得自动调用真实验收接口，不得把本地 evidence URL、离线 mock 或静态报告写成连接通讯软件交付完成。
- 所有交付和账本事件必须用唯一 `source_event_id` 幂等处理，防止重复扣费、重复返佣和重复回调伪造交付。

### 胖虎AI网站内置入口

注册、邀请码、创建 API Key、充值购买、推广返佣、代理中心和增值业务入口都属于胖虎AI网站、工具代理后端或服务端页面。客户端规则：

- 通过 `pywebview` 在软件内打开服务端页面；正式客户包必须内置该运行时。
- 未登录闸口允许客户填写代理邀请码或代理邀请链接；客户端只把它规范化为 `https://aitokenapi.cc/register?invite=<code>` 并通过内置浏览器打开注册页，不在本地保存邀请码、不本地绑定代理身份、不计算返佣。
- WebView 必须使用 `private_mode=False` 和买家专属 `storage_path` 保存 cookie/localStorage，打开前优先桥接当前持久 cookie jar，让客户重启工具后不需要在系统浏览器里二次登录胖虎AI。
- `pywebview` 不可用或 `src/ui/index.html` 缺失时属于客户包启动/打包失败，不得回退到旧 Tkinter 业务界面。cookie 桥接失败或运行环境阻止嵌入时，必须明确提示内置浏览器未完成/不可用；客户站点入口不得自动打开系统浏览器，也不得算完成内嵌网页闭环。
- 入口 URL 必须使用 `https://aitokenapi.cc`。
- 不能把网站购买、返佣、代理等级、套餐、钱包规则、下游客户归因或三类返佣规则复制到本地硬编码。
- 内置入口和 WebView 前提通过，不等于真实网页登录、充值、支付、创建 Key 或代理中心闭环已完成。

## 6. HTTPS 证书处理

Mac 打包后的 Python 运行环境可能找不到系统可信 CA，导致登录时报：

```text
SSL: CERTIFICATE_VERIFY_FAILED
unable to get local issuer certificate
```

当前修复方式：

- `requirements-build.txt` 包含 `certifi>=2024.8.30`。
- 主程序优先使用 `certifi.where()` 创建 SSL context。
- Windows 打包脚本用 `--add-data "$certifiData;certifi"` 带上 certifi 数据。
- Mac 打包脚本用 `--collect-data certifi` 带上 certifi 数据。
- 所有登录、授权、清单、更新、下载相关 HTTPS 请求必须使用 trusted helper，不要直接回到裸 `urlopen` 默认上下文。

维护时重点检查这些函数：

```python
trusted_ssl_context()
trusted_urlopen()
build_trusted_opener()
download_with_trusted_certs()
```

## 7. Codex 配置模式

Codex 配置必须保留三条链路：

- 普通模式：默认路径，Codex 只走胖虎AI中转站 API，消耗胖虎AI额度。
- 双态模式：付费高级路径，保留客户自己的 ChatGPT 登录态，但模型请求仍走胖虎AI中转站 API，消耗胖虎AI额度。
- 官方直登：免费切换路径，Codex 使用客户自己的 ChatGPT 账号登录态，模型请求走官方账号额度，不写入胖虎AI中转站 Key。

胖虎AI账号只用于登录本工具和胖虎AI网站，不是 Codex 登录账号，不能写成“胖虎AI账号登录 Codex”。普通模式无需登录 ChatGPT 账号，也可以正常使用 Codex。任何模式只要写入 Codex 配置，都必须提示客户完全退出 Codex 后重新打开。

普通模式写入 `auth.json`：

```json
{
  "OPENAI_API_KEY": "客户填写的胖虎AI API Key"
}
```

普通模式 `config.toml` 使用 `model_provider = "panghuAI"` 和 `[model_providers.panghuAI]`，不写 `experimental_bearer_token`。

双态模式规则：

- 客户自己的 ChatGPT 账号只负责登录态。
- 胖虎AI API Key 负责模型调用消耗，消耗的是胖虎AI额度，不是 ChatGPT 账号额度。
- 工具不代替客户登录 ChatGPT 账号。
- 工具不保存 ChatGPT 账号密码。

双态模式写入的 `config.toml` 关键段：

```toml
model_provider = "panghuAI"
model = "gpt-5.4"
review_model = "gpt-5.4"
model_reasoning_effort = "xhigh"
disable_response_storage = true
network_access = "enabled"
windows_wsl_setup_acknowledged = true
model_context_window = 1000000
model_auto_compact_token_limit =600000

[model_providers.panghuAI]
name = "panghuAI"
base_url = "https://aitokenapi.cc/v1"
wire_api = "responses"
experimental_bearer_token = "客户填写的胖虎AI API Key"
requires_openai_auth = true
```

双态模式 `auth.json` 规则：

- 保留已有登录 token。
- 写入 `auth_mode=chatgpt`。
- 将 `OPENAI_API_KEY` 置为 `null`。

官方直登规则：

- 只用于客户明确要消耗自己 ChatGPT 账号额度的场景。
- 不写 `experimental_bearer_token`。
- 不保留 `[model_providers.panghuAI]`。
- `config.toml` 应恢复官方 provider：

```toml
model_provider = "openai"
model = "gpt-5.4"
review_model = "gpt-5.4"
model_reasoning_effort = "xhigh"
disable_response_storage = true
network_access = "enabled"
windows_wsl_setup_acknowledged = true
model_context_window = 1000000
model_auto_compact_token_limit =600000
```

- `auth.json` 必须保留客户自己的 ChatGPT 登录态：

```json
{
  "auth_mode": "chatgpt",
  "OPENAI_API_KEY": null,
  "tokens": {
    "access_token": "客户本机已有 token",
    "refresh_token": "客户本机已有 refresh token"
  }
}
```

- 如果本机没有 ChatGPT 登录态，工具不能伪造，也不能要求客户提供账号密码；只能提示客户完全退出并重开 Codex 后自行登录 ChatGPT 账号。
- 官方直登不执行胖虎AI API Key 测试，不创建商业配置会话，不扣胖虎AI配置次数。

模式切换机制：

- 切换前必须保存当前 `~/.codex/config.toml`、`~/.codex/auth.json`、全局 `AGENTS.md` 和工作区 `AGENTS.md`。
- 模式快照目录固定为 `~/.codex/panghu_modes/`。
- 已识别模式写入对应目录：`direct_api/`、`dual_state/`、`official_chatgpt/`。
- 未识别模式写入 `history/<timestamp>/`，作为人工恢复线索。
- 切换到目标模式时，允许读取目标快照作为恢复基准，但 API Key、`experimental_bearer_token` 等动态字段必须按当前输入重新生成，不能把快照里的过期 Key 带回主配置。
- 官方直登和双态模式优先继承当前主 `auth.json` 中最新 ChatGPT 登录态；当前主文件没有登录态时，才从目标模式快照读取登录态。
- 写入失败时必须使用原有 `backup_file()` / `restore_backup()` 回滚到本次写入前状态。

客户操作提示必须保留：

```text
配置写完后，必须完全退出 Codex，再重新打开 Codex，新的配置才会生效。
普通模式和双态模式都消耗胖虎AI中转站额度；官方直登消耗客户自己的 ChatGPT 账号额度。
双态模式和官方直登都需要客户在 Codex 内使用自己的 ChatGPT 账号登录，本工具不接收、不保存 ChatGPT 账号密码。
```

## 8. 临时 OpenAI 官网访问窗口

用途：客户网络短期无法访问 OpenAI / Codex 官方页面时，临时辅助登录或访问官方页面。

服务端清单字段：

```json
{
  "temporary_openai_access": {
    "enabled": true,
    "proxy": "aitokenapi.cc:80",
    "duration_seconds": 600
  }
}
```

客户端规则：

- 未拿到字段时，不改系统代理。
- 只在 Windows 和 Mac 启用。
- 使用 PAC，只放行 OpenAI/Codex 登录相关域名。
- 启用前保存原系统代理。
- 到点自动恢复原系统代理。
- 不要改成常驻代理。
- 不要在胖虎AI网页里反代 OpenAI 登录页。
- 不接收、不保存客户 OpenAI 官网账号密码。

## 9. 在线更新机制

客户端检查：

```text
https://aitokenapi.cc/deployer/latest.json
```

清单必须包含：

- `version`
- `download_page_url`
- Windows 包 URL、SHA256、size
- Mac AppleSilicon 包 URL、SHA256、size
- Mac Intel 包 URL、SHA256、size
- 兼容旧客户端的 `download_url`、`sha256`、`size`

Mac 包选择：

- `arm64` 使用 `mac_apple_silicon_zip_url`。
- `x86_64` 使用 `mac_intel_zip_url`。

客户端行为：

- 登录成功后自动检查一次新版。
- 手动点击“检查更新”也使用同一套检查逻辑。
- 有新版时弹窗提示客户在线更新。
- 客户确认后下载对应系统 zip，启动独立更新脚本，退出当前工具，解压覆盖当前程序目录，再重新打开新版。
- 更新只覆盖工具安装目录；账号提示、用户显式保存的本机加密密码记录、API Key、Codex 配置、买家会话 cookie、内置浏览器 profile、备份和工作区资料都在用户目录，不能被更新流程删除。胖虎AI网站入口优先复用保存的买家会话；客户端不把部署授权写入 `profile.json` 或买家会话文件，会话失效时按登录门禁处理。

维护重点：

- GitHub Release 有新包不等于客户已经能下载到新包。
- 必须同时更新 `https://aitokenapi.cc/deployer/latest.json` 和 `https://aitokenapi.cc/deployer/download`。
- 下载页上必须明显显示当前版本号。
- 旧包直链可能仍可访问，客户必须通过统一下载页拿当前包。
- 更新脚本必须等待当前进程退出后再覆盖，避免 Windows 文件锁导致覆盖失败。

## 10. 本地开发流程

进入仓库：

```powershell
cd C:\Users\Administrator\Documents\codex\胖虎AI客户端
```

查看当前状态：

```powershell
git status --short
```

运行源码：

```powershell
scripts\run-windows.bat
```

运行自检：

```powershell
python src\panghu_ai_client.py --self-test
```

代码健康检查：

```powershell
python -m py_compile src\panghu_ai_client.py src\commercial_core.py src\commercial_api.py src\commercial_backend_contract.py
python -m unittest discover -s tests -p "test_*.py"
```

网站入口前提检查：

```powershell
python scripts\customer_web_entry_acceptance.py
```

Agent 交付只读检查：

```powershell
python scripts\agent_delivery_acceptance.py
```

Agent 真实对话验收必须使用临时隔离配置，不能读取或污染维护机已有 ClaudeCode、OpenClaw、Hermes 配置。只有拿到当前买家的真实胖虎AI API Key 后，才允许在当前 PowerShell 会话中临时设置 `PANGHU_AGENT_ACCEPTANCE_API_KEY` 并运行：

```powershell
$env:PANGHU_AGENT_ACCEPTANCE_API_KEY="<current-buyer-panghuai-api-key>"
python scripts\agent_delivery_acceptance.py --run-dialogue --isolated-config-from-env --run-codex-gateway-probe --dialogue-timeout 60
Remove-Item Env:\PANGHU_AGENT_ACCEPTANCE_API_KEY
```

报告中 Codex、ClaudeCode/CC、OpenClaw、Hermes 的最小中文对话必须为 `pass` 才能计入完整交付；Gemini / agy 当前只保留官方安装入口，报告为 `not_supported` 或“配置待开发”时是预期状态，不能包装成完整配置交付。

商业合同离线验收：

```powershell
python scripts\commercial_flow_acceptance.py --json
```

商业版本地轻量发布前检查：

```powershell
python scripts\commercial_release_acceptance.py --json
```

如果使用项目虚拟环境：

```powershell
.venv\Scripts\python.exe src\panghu_ai_client.py --self-test
```

注意：

- 当前仓库可能已有用户或上一轮 Agent 未提交改动。不要随意回退。
- 修改前先看 `git diff`。
- 文档、客户说明、主程序改动要分清楚。
- 当前阶段不要运行 `python scripts\commercial_release_acceptance.py --with-exe-self-test --deep-scan --json`，除非明确进入发布前深度验收或 CI 场景。
- 自动化测试通过只代表代码健康和已有回归通过，不代表客户可交付。

## 11. Windows 打包

命令：

```powershell
scripts\build-windows-exe.bat
```

本地打包会生成 `release/` 目录。`build/`、`.venv/` 和缓存属于可重建环境；`release/` 里的三端 zip 属于本地客户交付物，不能在普通清理中删除。正式客户发布包以 GitHub Release 和 `https://aitokenapi.cc/deployer/download` 为准，本地 zip 不提交进源码仓。

工作流上传到 GitHub Release 的公开 asset 名称：

```text
胖虎AI客户端-Windows.zip
```

本地客户包应保留为：

```text
release/胖虎AI客户端-Windows.zip
```

Windows 构建要求：

- 使用 `.venv`。
- 安装 `requirements-build.txt`。
- PyInstaller 必须打包 `assets`。
- PyInstaller 必须打包 `certifi` 数据。
- 商业版生产构建必须设置 `PANGHU_COMMERCIAL_MANIFEST_PUBLIC_KEY_PEM`，构建脚本会生成 `src/commercial_manifest_public_key.py`；该生成文件不得提交。
- 构建后执行 exe 的 `--self-test`。

商业 manifest 签名工具：

```powershell
python scripts\commercial_manifest_signer.py generate-keypair --private-key C:\secure\manifest-private.pem --public-key C:\secure\manifest-public.pem
python scripts\commercial_manifest_signer.py sign --manifest manifest.json --private-key C:\secure\manifest-private.pem --key-id prod-2026-06 --output manifest.signed.json
```

私钥只能放在后端或离线签名环境，不能写入客户端源码、客户包、GitHub Release、下载页或 `latest.json`。生产构建只注入公钥。

商业流程离线验收：

```powershell
python scripts\commercial_flow_acceptance.py --json
```

凡是修改订单、支付、权益、配置会话、扣次、撤销或返佣合同，都必须先跑这个脚本。该脚本只使用本地模拟账本，不访问生产服务器。

商业版本地发布验收：

```powershell
python scripts\commercial_release_acceptance.py --json
```

凡是修改商业版客户端、商业 manifest、构建脚本或客户包前置逻辑，都必须先跑这个轻量脚本。它只读取本地源码和 `release/` 包，校验三端客户包是否存在、每个客户包是否早于当前源码或构建脚本、客户包 zip 内容、商业合同离线主链路、生成公钥模块、私钥材料和客户 App 运行面硬边界；不会执行 GitHub Release、下载页、`latest.json` 或生产服务器操作。

发布前深度验收或 CI 才运行：

```powershell
python scripts\commercial_release_acceptance.py --with-exe-self-test --deep-scan --json
```

`--with-exe-self-test` 会把 Windows 客户 zip 解压到临时目录并运行包内 exe 自检，容易触发 Windows Defender 和索引器扫描 PyInstaller 文件树；本地日常开发不要反复跑。`--deep-scan` 会额外扫描 `docs/`、`tests/` 和 `.github/` 里的发布边界提示；本地快速回归默认保持轻量扫描。

报告里的 `release_artifacts` 会给 Windows、Mac AppleSilicon、Mac Intel 三个客户包分别输出 `freshness`：

- `fresh`：客户包时间不早于当前源码和构建脚本，可作为当前本地构建结果继续验收。
- `stale`：客户包早于当前源码或构建脚本，需要重包；Mac AppleSilicon 或 Mac Intel 出现 `stale` 时，不能把三端本地客户包视为已收口。
- `missing`：本地缺少客户包，需要从构建产物、GitHub Release 或统一下载入口补齐后再验收。

报告里的 `packaged_artifact_contents` 会打开每个本地 zip 做黑箱扫描。`internal_file_hits` 必须为空，避免客户包里带出内部维护、测试、源码或签名资料；正常第三方依赖文件不应被当作内部泄露。

报告里的 `release_temp_files` 会检查 `release/` 下是否残留 `.tmp`、`*.tmp.zip`、`zip-validation-*` 等本地验证临时文件。若出现 `release 目录存在临时验证残留` 警告，只能删除已经确认属于验证残留的临时文件；不得删除 Windows、Mac 客户 zip，也不得删除 `release/` 下的软件本体目录。

报告里的 `packaged_app_source_files_scanned` 是客户包商业源码扫描清单，只代表客户 App 运行面。该清单至少应包含主界面、商业核心和商业 API 模块，用于确认商业价格、返佣比例、次数、有效期、设备数、上架状态等参数没有被写死在客户侧源码里；这些值只能来自服务端商品、权益或 manifest。

后端合约模拟器、商业流程验收脚本、商业发布验收脚本、签名脚本、维护手册和测试用例属于内部验收面，不属于客户 App 运行面。它们可以作为本地和 CI 验收依据，但不得进入客户包；如果 `packaged_artifact_contents.internal_file_hits` 命中这些文件，必须重包并排查打包规则。

报告里的 `non_codex_full_config_delivery_found` 必须为 `false`。该扫描用于防止 ClaudeCode、OpenClaw、Hermes 等 Agent 在未完成配置写入、启动检测、最小对话验证前，被主程序静态包装成无条件完整付费交付；Gemini / agy 未接入前也只能显示官方入口或待接入状态。真实交付状态必须以部署后生成的 `胖虎AI-Agent功能验收矩阵.txt` 为准；矩阵未通过时必须 fail 配置会话、不扣次。

报告里的 `communication_link_real_delivery_claim_found` 必须为 `false`。该扫描用于防止客户包主程序把连接通讯软件写成客户端可自行声明真实交付完成；连接通讯软件最终交付只能以服务端真实验收记录为准，本地状态、离线报告或 mock 守卫不能替代真实平台回调、Agent Runtime Adapter、支付和账本闭环。

若报告为 `WARN`，视为发布阻塞，必须修复警告项或重跑到 `PASS` 后才允许进入打包、GitHub Release、下载页或 `latest.json` 步骤；生产商业构建必须注入 `PANGHU_COMMERCIAL_MANIFEST_PUBLIC_KEY_PEM`，否则商业清单保持拒绝状态是预期结果。

## 12. Mac 打包

本地命令必须在 Mac 上执行：

```bash
chmod +x scripts/build-mac-app.command
scripts/build-mac-app.command
```

输出：

```text
release/胖虎AI客户端-Mac-AppleSilicon.zip
release/胖虎AI客户端-Mac-Intel.zip
```

这两个 Mac zip 也是本地客户交付物；即使本机是 Windows，清理项目时也必须从 GitHub Release 或统一下载入口补齐后再收尾。

工作流公开 asset 名称：

```text
胖虎AI客户端-Mac-AppleSilicon.zip
胖虎AI客户端-Mac-Intel.zip
```

Mac 构建要求：

- AppleSilicon runner 产出 arm64 包。
- Intel runner 产出 x86_64 包。
- PyInstaller 必须使用 `--collect-data certifi`。
- 商业版生产构建必须设置 `PANGHU_COMMERCIAL_MANIFEST_PUBLIC_KEY_PEM`，构建脚本会生成 `src/commercial_manifest_public_key.py`；该生成文件不得提交。
- 构建后执行 app 内二进制 `--self-test`。
- workflow 里的 `Test final Mac zip` 必须在公证和可能的重新压包后执行；最终 Mac zip 必须先解压到临时目录，再运行解压出来的 `.app` 内二进制 `--self-test`。
- 当前允许未 Apple Developer ID 公证的包公开下载，但页面必须提示 macOS 可能拦截。

如果后续要减少 macOS 安装拦截，需要配置 GitHub secrets：

```text
MACOS_CERTIFICATE_BASE64
MACOS_CERTIFICATE_PASSWORD
MACOS_KEYCHAIN_PASSWORD
MACOS_CODESIGN_IDENTITY
APPLE_ID
APPLE_APP_SPECIFIC_PASSWORD
APPLE_TEAM_ID
```

## 13. GitHub Release 发布流程

商业版 CI 硬要求：

- GitHub Actions 必须配置 `PANGHU_COMMERCIAL_MANIFEST_PUBLIC_KEY_PEM` secret。
- Windows 和 Mac 构建步骤都必须注入该 secret，生成的客户包才会内置商业 manifest 验签公钥。
- 构建脚本每次都覆盖生成 `src/commercial_manifest_public_key.py`；CI 和生产构建缺少该 secret 时必须快速失败，不能生成可上传客户包。本地未设置强制开关的测试包会写入空公钥并保持商业清单拒绝状态，不能沿用旧公钥文件。
- workflow 必须运行 `commercial_release_acceptance.py --with-exe-self-test --deep-scan --json`，先在 CI 中确认商业主链路、客户包自检、公钥生成、私钥隔离和发布边界扫描结果。
- CI 单平台验收必须使用 `--artifact-scope` 和 `--strict`；本地人工验收默认看三端包，CI 里 Windows、Mac AppleSilicon、Mac Intel 各自只验刚构建出的平台包，避免还未构建的其它平台包造成误判，同时让商业公钥缺失、包自检失败或商业链路失败直接中断 workflow。
- Mac 公证后如果重新压 zip，必须在 `Prepare release asset` 前再次运行商业发布验收，确保最终上传的 zip 仍通过内容扫描、freshness、公钥和硬边界检查。
- Mac 的 `Test final Mac zip` 必须在最终商业发布验收之前执行，确认最终 Mac zip 必须先解压到临时目录，且解压出来的 `.app` 内二进制 `--self-test` 通过后，才能改名为公开 Release asset。

推荐流程：

1. 修改代码。
2. 更新 `APP_VERSION`。
3. 更新 README、客户说明、维护手册中对应版本或行为。
4. 运行自检。
5. 提交代码并推送。
6. 创建 tag，例如 `v1.0.15`。
7. 推送 tag。
8. 等 GitHub Actions 构建 Windows、Mac AppleSilicon、Mac Intel。
9. 确认 Release 下有三个 asset：
   - `胖虎AI客户端-Windows.zip`
   - `胖虎AI客户端-Mac-AppleSilicon.zip`
   - `胖虎AI客户端-Mac-Intel.zip`
10. 记录三个包的 SHA256 和 size。
11. 更新生产下载清单和下载页。
12. 验证客户统一下载入口。

如果 Mac 未公证且业务上允许先公开未公证包，可手动触发工作流：

```powershell
gh workflow run build-mac-release.yml -f tag=vX.Y.Z -f allow_unnotarized_upload=true
```

不要只看 GitHub Release。客户真正走的是 `aitokenapi.cc/deployer/download` 和 `latest.json`。

## 14. 生产下载入口更新流程

生产入口属于胖虎AI服务器静态文件。改它之前必须按胖虎AI生产维护规则拿锁并记录。

目标文件：

```text
/opt/newapi/weai-home/deployer/latest.json
/opt/newapi/weai-home/deployer/download.html
```

必须备份：

```text
/opt/newapi/backups/<日期>-deployer-<版本>-downloads/
```

只改静态文件时：

- 不需要重启 Docker。
- 不需要 reload Nginx。
- 不要动后端二进制。
- 不要动 protected-console。
- 不要动数据库、支付、钱包、用户数据。

验证命令方向：

```powershell
Invoke-WebRequest -UseBasicParsing -Uri 'https://aitokenapi.cc/deployer/latest.json'
Invoke-WebRequest -UseBasicParsing -Uri 'https://aitokenapi.cc/deployer/download'
Invoke-WebRequest -UseBasicParsing -Uri 'https://aitokenapi.cc/api/status'
```

检查点：

- `latest.json` 的 `version` 是新版本。
- 三个包 URL 都指向新版本。
- 三个 SHA256 和 size 与 GitHub Release asset 一致。
- 下载页标题或按钮明确显示当前版本。
- 三个按钮都指向新版本。
- `/api/status`、`/`、`/console/` 不受影响。

## 15. 每次迭代的最小验收清单

代码类改动：

- `git diff` 已审过。
- `APP_VERSION` 已按需更新。
- `python src\panghu_ai_client.py --self-test` 通过。
- 相关 README / 客户说明 / 本手册已更新。
- Windows 或 Mac 打包脚本未破坏。

发布类改动：

- GitHub Release 三个包都存在。
- 本地 `release/` 三个客户 zip 都存在，且 SHA256/size 与 Release 或 `latest.json` 一致。
- 三个包 SHA256 和 size 已记录。
- `latest.json` 已更新。
- 下载页已更新。
- 统一下载入口显示当前版本。
- 客户说明仍能解释清楚如何下载、安装、登录、重开 Codex。

生产下载入口改动：

- 已读生产维护规则。
- 已拿生产锁。
- 已备份旧文件。
- 已只改 `latest.json` / `download.html`。
- 已验证公网响应。
- 已写 `PANGHUAI_CHANGE_LOG.md`、`STATUS.md`、`PRODUCTION_LOCK.md`。
- 如机制变化，已更新 `PANGHUAI_OFFICIAL_DOCS.md`。

## 16. 常见故障处理

### Mac 登录时报 SSL 证书错误

现象：

```text
SSL: CERTIFICATE_VERIFY_FAILED
unable to get local issuer certificate
```

检查：

- 客户下载的是否是 `v1.0.15` 或更高版本。
- 下载页是否还指向过期版本。
- Mac 包是否包含 certifi 数据。
- 主程序是否仍使用 trusted HTTPS helper。

### 用户重新下载仍是过期版本

常见原因：

- GitHub Release 已有新包，但 `aitokenapi.cc/deployer/latest.json` 没更新。
- 下载页按钮仍指向旧 tag。
- 用户点的是旧 ZIP 直链，不是统一下载页。

处理：

- 检查公网 `latest.json`。
- 检查下载页 HTML 里的 `releases/download/v...`。
- 让客户从统一下载页重新下载。

### 配置写完 Codex 仍不生效

常见原因：

- 客户没有完全退出 Codex。
- Codex 进程仍在后台。
- 风险插件接管了配置。

处理：

- 提示客户完全退出 Codex，再重新打开。
- 重新打开后登录自己的 ChatGPT 账号。
- 用“仅修复 Codex 配置”重写配置。
- 检查 `ccswitch`、`codex++`、`CCR`。

### Mac 打包成功但 Release 没有 Mac 包

常见原因：

- Apple 公证 secrets 未配置。
- 工作流阻止未公证包公开上传。

处理：

- 如果业务允许未公证包，手动触发 workflow 并设置 `allow_unnotarized_upload=true`。
- 否则配置 Apple Developer ID 和 notarization secrets。

## 17. 不允许做的事

- 不要把本项目当成胖虎AI中转站源码仓。
- 不要把胖虎AI控制台、后端、支付、钱包逻辑写进本仓。
- 不要把 OpenAI/Codex、ClaudeCode、OpenClaw、Hermes、Gemini / agy 本体提交进源码仓。
- 不要使用内部域名作为客户默认接口。
- 不要绕过胖虎AI服务端部署授权。
- 不要把临时 OpenAI 官网访问窗口改成常驻代理。
- 不要静默删除客户电脑上的第三方程序。
- 不要让 ClaudeCode/OpenClaw/Hermes 自动写入未确认安全的配置。
- 不要只发布 GitHub Release 就说客户入口已上线。
- 不要提供登录前身份分流、本地代操作会话或第三方账号代登录能力。
- 不要把注册、邀请码、创建 Key、充值购买、代理中心、返佣规则或套餐规则硬编码进客户端。
- 不要把代理中心写成已完成业务闭环；没有服务端合同时只能显示待接入状态。
- 不要把 `profile.json` 当成登录态或密码恢复来源；它只保存账号提示、API Key、模型和界面偏好。买家登录态恢复只来自独立会话 cookie 文件和内置浏览器 profile；可选记住密码只来自 `login_accounts.json` 中的系统加密 blob。
- 不要把连接通讯软件写成基础 Agent 配置的一部分；它必须独立订单、独立配置会话、独立验收和独立收费。不要把客户断网、禁 Key、取消平台授权后的实时不可达自动解释为配置失败。
- 不要把未完成真实客户闭环的状态写成最终交付完成。

## 18. 后续 Agent 接手顺序

每次接手先做：

1. 读 `C:\Users\Administrator\.codex\进化.md`。
2. 读 `README.md`。
3. 读产品单一事实源 `docs\PRODUCT_MANUAL_SINGLE_SOURCE_OF_TRUTH.md`。
4. 读本手册。
5. 读商业后端合同 `docs\COMMERCIAL_BACKEND_API_CONTRACT.md`。
6. 读 `PRODUCT.md`、`ACCEPTANCE.md`、`SECURITY.md`、`RUNBOOK.md`、`FINAL_REPORT.md`、`HANDOFF.md`。
7. 读工具项目登记文件：

```text
C:\Users\Administrator\Documents\codex\工具项目目录\projects\胖虎AI客户端.md
```

其它历史兼容登记入口只作为旧自动化线索，不作为当前接手权威登记。

8. 查看 `git status --short`。
9. 查看 `git diff`，不要覆盖已有未提交改动。
10. 搜索当前任务涉及的函数或常量。
11. 修改前明确是本地源码改动、GitHub 发布，还是生产下载入口改动。
12. 修改后跑对应自检和验收命令。
13. 需要发版时按 Release 流程走完三端包和线上下载入口验证。

如果用户问“有没有上线”“客户下载是不是新版”，必须用公网证据回答，不要只看本地代码或 GitHub Release。
