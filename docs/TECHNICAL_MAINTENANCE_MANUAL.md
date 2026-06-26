# 多 Agent 一键配置工具技术维护手册

最后更新：2026-06-19

> 产品结构、界面规则、客户可见交付口径，以 `docs/PRODUCT_MANUAL_SINGLE_SOURCE_OF_TRUTH.md` 为准。
> 本手册负责技术维护、接口、构建、发布、脚本和限制说明。

## 1. 项目边界

本项目是独立的客户侧桌面工具，正式名称为“胖虎AI多 Agent 一键部署工具”。它的职责是让客户登录胖虎AI账号后，在 Windows 或 Mac 上安装和配置 Codex、ClaudeCode、OpenClaw、Hermes。

本项目不是“胖虎AI 本地源码仓”的一部分。它只对接胖虎AI的登录、部署授权、更新清单、API Key 和公开下载入口。胖虎AI网站、控制台、后端、数据库、支付、钱包等内容归另一个长期项目维护。

正式仓库：

```text
C:\Users\Administrator\Documents\codex\panghu-codex-installer
https://github.com/dashuaiisme/panghu-codex-installer
```

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
10. 如果服务端下发临时 OpenAI 官网访问窗口，工具短时间启用 PAC 系统代理，并到点恢复。
11. 后续用“检查更新”从公开清单下载新版包。

支持的 Agent：

| Agent | 当前策略 |
| --- | --- |
| Codex | 安装或检测官方客户端/CLI，并自动写入胖虎AI中转配置、中文规则、工作区说明；通过胖虎AI网关真实任务验证 |
| ClaudeCode | 覆盖官方 CLI 和客户端入口；写入 `~/.claude/settings.json` 的 `env`，配置 `ANTHROPIC_BASE_URL=https://aitokenapi.cc`、`ANTHROPIC_AUTH_TOKEN` / `ANTHROPIC_API_KEY` 和模型，并用 `claude --model <模型> -p <中文验收提示>` 最小中文对话验收。注意 Claude Code 会自行拼接 `/v1/messages`，这里不能写成 `/v1`，否则会变成 `/v1/v1/messages`。当前只读检测到 CLI，但独立客户端形态未稳定确认 |
| OpenClaw | 覆盖官方 CLI 和 Hub/客户端入口；安装优先使用官方 npm 包 `openclaw@latest`，写入 `~/.openclaw/openclaw.json` 的 `models.providers.panghuai` 自定义 OpenAI-compatible 提供商（`baseUrl=https://aitokenapi.cc/v1`、`api=openai-completions`、`apiKey=买家 Key`），并用 `openclaw infer model run --model panghuai/<模型> --prompt ... --json` 最小中文对话验收。未检测到 CLI、`openclaw config validate` 未通过或最小对话失败时，不能声明完整交付 |
| Hermes | 覆盖官方 CLI 和客户端入口；按官方文档写入 Hermes Home 下的 `config.yaml` 与 `.env`，配置 `custom_providers.panghuai`、`model.provider=custom:panghuai`、`PANGHUAI_API_KEY`，并用 `hermes --provider custom:panghuai --model <模型> -z <中文验收提示>` 最小中文对话验收。当前只读检测到 CLI，但独立客户端形态未稳定确认 |

当前状态说明：

- 以上三项表示“代码中已有配置写入和验收链路”，不等于所有客户机器已经完整打通。
- 完整交付必须以部署后生成的 `胖虎AI-Agent功能验收矩阵.txt` 为准。
- OpenClaw CLI 未检测到、`openclaw config validate` 未通过、Hermes `hermes config check` 未通过、客户端形态未确认或最小中文对话未返回有效内容时，不得扣次或包装成完整交付。测试 Key 返回 401 只能证明请求链路打到胖虎AI网关，不能证明客户交付已完成。

风险插件拦截：

- `ccswitch`
- `codex++`
- `CCR / Claude Code Router`

发现这些工具时，部署必须停止并提示客户先卸载或禁用。不要静默删除客户电脑上的程序。

## 3. 关键源码结构

```text
src/panghu_codex_installer.py
```

主程序。当前大部分逻辑集中在这一个文件中，包括：

- Tkinter 图形界面。
- 胖虎AI登录。
- 部署授权。
- Agent 清单解析。
- 环境检测。
- 风险插件检测。
- Codex 配置写入。
- 备份和恢复。
- 临时 OpenAI 官网访问窗口。
- 在线更新。
- 自检入口 `--self-test`。

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
docs/多Agent一键配置工具下载二维码.png
assets/deployer-download-qr.png
```

客户交付材料。

## 4. 关键常量

维护时优先检查 `src/panghu_codex_installer.py` 顶部常量：

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

### 登录

```text
POST https://aitokenapi.cc/api/user/login?turnstile=
```

客户端在本次运行内使用 cookie jar 和内存态完成登录、授权和部署。`profile.json` 只保存账号提示、API Key、模型和界面偏好，不保存可恢复登录态、部署 token、历史商业污染字段或第三方账号密码。重启工具后必须重新登录胖虎AI账号。

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
- 切换到目标模式时，允许读取目标快照作为历史基准，但 API Key、`experimental_bearer_token` 等动态字段必须按当前输入重新生成，不能把旧快照里的旧 Key 带回主配置。
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
- 更新只覆盖工具安装目录；`profile.json`、API Key、Codex 配置、备份和工作区资料都在用户目录，不能被更新流程删除。`profile.json` 不能被当作登录态恢复来源，更新后仍应要求客户重新登录胖虎AI账号。

维护重点：

- GitHub Release 有新包不等于客户已经能下载到新包。
- 必须同时更新 `https://aitokenapi.cc/deployer/latest.json` 和 `https://aitokenapi.cc/deployer/download`。
- 下载页上必须明显显示当前版本号。
- 旧包直链可能仍可访问，客户必须通过统一下载页拿当前包。
- 更新脚本必须等待当前进程退出后再覆盖，避免 Windows 文件锁导致覆盖失败。

## 10. 本地开发流程

进入仓库：

```powershell
cd C:\Users\Administrator\Documents\codex\panghu-codex-installer
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
python src\panghu_codex_installer.py --self-test
```

如果使用项目虚拟环境：

```powershell
.venv\Scripts\python.exe src\panghu_codex_installer.py --self-test
```

注意：

- 当前仓库可能已有用户或上一轮 Agent 未提交改动。不要随意回退。
- 修改前先看 `git diff`。
- 文档、客户说明、主程序改动要分清楚。

## 11. Windows 打包

命令：

```powershell
scripts\build-windows-exe.bat
```

本地打包会生成 `release/` 目录。`build/`、`.venv/` 和缓存属于可重建环境；`release/` 里的三端 zip 属于本地客户交付物，不能在普通清理中删除。正式客户发布包以 GitHub Release 和 `https://aitokenapi.cc/deployer/download` 为准，本地 zip 不提交进源码仓。

工作流上传到 GitHub Release 的公开 asset 名称：

```text
AI.Agent.-Windows.zip
```

本地客户包应保留为：

```text
release/胖虎AI多Agent一键部署工具-Windows.zip
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

报告里的 `non_codex_full_config_delivery_found` 必须为 `false`。该扫描用于防止 ClaudeCode、OpenClaw、Hermes 等 Agent 在未完成配置写入、启动检测、最小对话验证前，被主程序静态包装成无条件完整付费交付。真实交付状态必须以部署后生成的 `胖虎AI-Agent功能验收矩阵.txt` 为准；矩阵未通过时必须 fail 配置会话、不扣次。

若报告为 `WARN`，需要人工确认警告项后再进入发版步骤；生产商业构建必须注入 `PANGHU_COMMERCIAL_MANIFEST_PUBLIC_KEY_PEM`，否则商业清单保持拒绝状态是预期结果。

## 12. Mac 打包

本地命令必须在 Mac 上执行：

```bash
chmod +x scripts/build-mac-app.command
scripts/build-mac-app.command
```

输出：

```text
release/胖虎AI多Agent一键部署工具-Mac-AppleSilicon.zip
release/胖虎AI多Agent一键部署工具-Mac-Intel.zip
```

这两个 Mac zip 也是本地客户交付物；即使本机是 Windows，清理项目时也必须从 GitHub Release 或统一下载入口补齐后再收尾。

工作流公开 asset 名称：

```text
AI.Agent.-Mac-AppleSilicon.zip
AI.Agent.-Mac-Intel.zip
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
   - `AI.Agent.-Windows.zip`
   - `AI.Agent.-Mac-AppleSilicon.zip`
   - `AI.Agent.-Mac-Intel.zip`
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
- `python src\panghu_codex_installer.py --self-test` 通过。
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
- 下载页是否还指向旧版。
- Mac 包是否包含 certifi 数据。
- 主程序是否仍使用 trusted HTTPS helper。

### 用户重新下载仍是旧版

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

- 不要把本项目当成胖虎AI源码仓。
- 不要把胖虎AI控制台、后端、支付、钱包逻辑写进本仓。
- 不要把 OpenAI/Codex、ClaudeCode、OpenClaw、Hermes 本体提交进源码仓。
- 不要使用内部域名作为客户默认接口。
- 不要绕过胖虎AI服务端部署授权。
- 不要把临时 OpenAI 官网访问窗口改成常驻代理。
- 不要静默删除客户电脑上的第三方程序。
- 不要让 ClaudeCode/OpenClaw/Hermes 自动写入未确认安全的配置。
- 不要只发布 GitHub Release 就说客户入口已上线。

## 18. 后续 Agent 接手顺序

每次接手先做：

1. 读本手册。
2. 读 `README.md`。
3. 读工具项目登记文件：

```text
C:\Users\Administrator\Documents\codex\工具项目目录\projects\多 Agent 一键配置工具.md
```

4. 查看 `git status --short`。
5. 查看 `git diff`，不要覆盖已有未提交改动。
6. 搜索当前任务涉及的函数或常量。
7. 修改前明确是本地源码改动、GitHub 发布，还是生产下载入口改动。
8. 修改后跑自检。
9. 需要发版时按 Release 流程走完三端包和线上下载入口验证。

如果用户问“有没有上线”“客户下载是不是新版”，必须用公网证据回答，不要只看本地代码或 GitHub Release。
