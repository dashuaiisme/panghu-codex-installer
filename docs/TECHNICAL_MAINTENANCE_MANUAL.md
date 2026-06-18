# 多 Agent 一键配置工具技术维护手册

最后更新：2026-06-19

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
| Codex | 安装或检测官方客户端/CLI，并自动写入胖虎AI中转配置、中文规则、工作区说明 |
| ClaudeCode | 只安装，不写 Key，不改账号或配置 |
| OpenClaw | 只安装并生成中文说明，不强写未确认安全的配置 |
| Hermes | 只安装并生成中文说明，不强写未确认安全的配置 |

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

客户端使用 cookie jar 保存登录态。登录成功后，客户端保存必要的本地 profile 数据。

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

Codex 配置必须保留两条链路：

- 普通模式：默认路径，直接使用胖虎AI API Key。
- 双态模式：额外路径，只给需要 ChatGPT 登录态共存的客户使用。

普通模式无需登录 ChatGPT 账号，也可以正常使用 Codex。任何模式只要写入 Codex 配置，都必须提示客户完全退出 Codex 后重新打开。

普通模式写入 `auth.json`：

```json
{
  "OPENAI_API_KEY": "客户填写的胖虎AI API Key"
}
```

双态模式规则：

- 客户自己的 ChatGPT 账号负责登录态。
- 胖虎AI API Key 负责模型调用消耗。
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

客户操作提示必须保留：

```text
配置写完后，必须完全退出 Codex，再重新打开 Codex，新的配置才会生效。
双态模式需要客户重新打开后自行登录自己的 ChatGPT 账号。
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
- 更新只覆盖工具安装目录；`profile.json`、客户登录状态、API Key、Codex 配置、备份和工作区资料都在用户目录，不能被更新流程删除。

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
- 构建后执行 exe 的 `--self-test`。

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
- 构建后执行 app 内二进制 `--self-test`。
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
