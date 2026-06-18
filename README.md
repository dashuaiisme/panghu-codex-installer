# 胖虎AI多 Agent 一键部署工具

这是一个跨平台图形界面工具，用来给客户一键部署和配置常用 AI Agent。客户必须先用胖虎AI注册账号登录软件，并通过胖虎AI服务端部署授权后，才能按向导创建并填写 API Key，再选择系统、Agent 和安装方式。

## 项目状态

- 规范源码目录：`C:\Users\Administrator\Documents\codex\panghu-codex-installer`
- 新版推荐发布包名：
  - Windows：`胖虎AI多Agent一键部署工具-Windows.zip`
  - Mac Apple 芯片：`胖虎AI多Agent一键部署工具-Mac-AppleSilicon.zip`
  - Mac Intel 芯片：`胖虎AI多Agent一键部署工具-Mac-Intel.zip`
- GitHub 仓库：`https://github.com/dashuaiisme/panghu-codex-installer`
- GitHub Release：`https://github.com/dashuaiisme/panghu-codex-installer/releases/latest`
- 统一下载入口：`https://aitokenapi.cc/deployer/download`
- 下载二维码：`docs/多Agent一键配置工具下载二维码.png`
- 纯二维码素材：`assets/deployer-download-qr.png`
- 公开更新清单：`https://aitokenapi.cc/deployer/latest.json`
- 技术维护手册：`docs/TECHNICAL_MAINTENANCE_MANUAL.md`
- 仓库只保存源码、脚本和说明；`build/`、缓存和 exe/zip 发布产物不提交。`release/` 虽然不提交，但里面的三端 zip 是本地客户交付物，清理项目前必须保留或先确认已有可恢复的正式包。

## 下载二维码

平台不方便发送明文链接时，直接发送下面这张二维码图片给客户。二维码指向统一下载入口，客户扫码后选择自己的电脑系统下载 Windows、Mac Apple 芯片或 Mac Intel 版本。

![多 Agent 一键配置工具下载二维码](docs/多Agent一键配置工具下载二维码.png)

## 客户流程

1. 登录胖虎AI账号；没有账号时点击注册链接去 `https://aitokenapi.cc/register`。
2. 软件向胖虎AI服务端申请部署授权；未授权账号不能进入后续部署。
3. 打开 `https://aitokenapi.cc/login?next=/console/token` 创建 API Key，粘贴到工具里并测试。新注册账号需要先充值或确保账户有余额，否则 Key 可能无法通过测试。
4. 选择或确认当前系统，检测环境、PATH、包管理器、已安装 Agent 和第三方配置插件。
5. 选择 Agent 和安装方式：`Codex`、`ClaudeCode`、`OpenClaw`、`Hermes`，支持 CLI / 客户端入口。
6. 点击“一键部署（普通）”，工具先拦截 `ccswitch`、`codex++`、`CCR` 等可能改坏配置的第三方工具，再拉取服务端授权清单、调用官方在线安装入口，并对安全可写的 Agent 应用普通直接 API 配置。
7. 如果服务端清单给当前账号下发 `temporary_openai_access` 授权，工具会在打开 Codex 前临时启用 OpenAI 官网访问窗口；默认 10 分钟，到点自动恢复客户原系统代理。
8. 如果客户已经安装过 Agent，只是 Codex 配置坏了，可点击“仅修复 Codex 配置”，不会重新安装 Agent。配置写完后必须完全退出 Codex，再重新打开 Codex，新的配置才会生效。
9. 如果客户需要“保持 ChatGPT 登录态，同时模型消耗胖虎AI API Key”，点击“双态配置”。不需要登录态共存的客户不要点这个模式。
10. 登录成功后软件会自动联网检查新版；有新版时提示在线更新。客户确认后，工具会下载当前系统对应的 Windows / Mac 更新包，退出当前程序，自动覆盖程序目录并重新打开新版。客户手动点击“检查更新”也走同一套在线更新流程。更新只覆盖工具本体，不清空客户本机已保存的登录授权、账号名、API Key、Codex 配置和工作区资料。

## 服务端授权

- 客户端登录成功后调用 `POST https://aitokenapi.cc/api/deployer/activate` 申请短期部署令牌。
- 真正开始安装前调用 `GET https://aitokenapi.cc/api/deployer/manifest` 获取当前账号允许安装的 Agent 清单。
- 如果服务端拒绝授权、令牌过期、清单不包含所选 Agent，客户端会停止部署。
- 这套强安全模式必须先把胖虎AI后端接口上线到生产站；接口未上线时，新包会在部署授权阶段失败，这是预期的拦截行为。

### OpenAI 官网临时访问窗口

该能力只用于客户网络运营商短期异常时辅助打开 OpenAI / Codex 官方页面，不是长期代理功能。

服务端部署清单可选下发：

```json
{
  "temporary_openai_access": {
    "enabled": true,
    "proxy": "aitokenapi.cc:80",
    "duration_seconds": 600
  }
}
```

客户端行为：

- 未拿到该字段时，不改动系统代理。
- 只在 Windows 和 Mac 客户机上启用。
- 通过 PAC 只把 `openai.com`、`chatgpt.com`、`oaistatic.com`、`oaiusercontent.com` 等 OpenAI/Codex 登录相关域名走指定代理，其它网站保持直连。
- 启用前保存客户原系统代理设置；10 分钟到点后自动恢复并删除临时 PAC 文件。
- Mac 客户机启用时会弹出 macOS 系统管理员授权提示；授权只用于短时间写入和恢复系统自动代理配置。
- 如果检测到已有临时窗口仍在运行，不会重复覆盖系统代理。
- 不在胖虎AI网页里反代 OpenAI 登录页，不接收、不保存客户 OpenAI 官网账号密码。

## Agent 规则

- `Codex`：支持 CLI 和客户端安装；保留官方签名离线包、Microsoft Store/winget、官方下载页兜底；可自动写入胖虎AI API Key、接口、模型、中文规则和默认工作区。
- `ClaudeCode`：只安装 Agent，不写 Key，不改 ClaudeCode 账号或配置；客户后续按 ClaudeCode 官方流程自行配置。
- `OpenClaw`：优先走官方在线安装；本版先安装并生成中文配置说明，不强写未确认安全的客户端配置。
- `Hermes`：优先走官方在线安装；本版先安装并生成中文配置说明，不强写未确认安全的客户端配置。

## 第三方插件拦截

- 第二步环境检测会检查 `ccswitch`、`codex++`、`CCR / Claude Code Router` 等第三方配置切换工具。
- 正式部署前会再次检查；发现后直接停止安装，要求客户先卸载或禁用。
- 原因：这类工具可能接管或改写 Codex / ClaudeCode 配置，导致胖虎AI写入的 API Key、接口、模型或中文规则被改坏。
- 工具不会静默删除客户电脑上的程序；日志和弹窗会给出卸载/禁用建议，客户处理完成后重新打开工具再部署。

## 配置写入位置

Codex 配置写入当前用户目录：

```text
~/.codex/config.toml
~/.codex/auth.json
~/.codex/AGENTS.md
~/Documents/胖虎AI-Agent工作区/AGENTS.md
```

普通模式会先备份旧文件，再用下面这段完整覆盖 `config.toml`：

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
requires_openai_auth = true
```

普通模式的 `auth.json` 会写入客户填写的 `OPENAI_API_KEY`，适合只需要直接 API 配置的客户。

普通配置方式无需登录 ChatGPT 账号，也可以正常使用 Codex。无论使用普通模式、仅修复配置，还是双态模式，只要工具写入了 Codex 配置，都必须完全退出 Codex 后重新打开，新的配置才会生效。

双态模式是额外入口，只有客户需要登录态共存时才使用。双态模式会在 `config.toml` 里额外写入：

```toml
experimental_bearer_token = "客户填写的胖虎AI API Key"
```

双态模式的 `auth.json` 会自动创建或更新 `auth_mode=chatgpt`，并把 `OPENAI_API_KEY` 置为 `null`。如果客户已经在 Codex 里登录过，本工具会保留已有登录 token；如果客户还没有登录，配置完成后需要客户完全退出 Codex、重新打开 Codex，并自行登录自己的 ChatGPT 账号。

双态模式生效后：

- 登录态来自客户自己的 ChatGPT 账号。
- 模型请求走胖虎AI中转 provider。
- 模型消耗使用客户填写的胖虎AI API Key。
- 本工具不代替客户登录 ChatGPT 账号，也不保存 ChatGPT 账号密码。

通用说明文件写入：

```text
~/Documents/胖虎AI-Agent工作区/胖虎AI-Agent配置说明.txt
```

## 目录说明

```text
src/
  panghu_codex_installer.py      图形界面源码，主要实现都在这里
scripts/
  run-windows.bat                Windows 源码运行入口
  run-mac.command                Mac 源码运行入口
  build-windows-exe.bat          Windows 打包 exe
  build-mac-app.command          Mac 打包 app，按当前构建机器生成 Apple 芯片版或 Intel 版
  generate-download-qr.py        生成统一下载入口二维码
docs/
  客户发送说明、二维码和技术维护手册
```

## Windows 开发运行

```bat
scripts\run-windows.bat
```

## Windows 打包

```bat
scripts\build-windows-exe.bat
```

本地打包会生成 `release/` 目录。`build/` 和 `.venv/` 属于可重建环境；`release/` 里的三端 zip 属于客户交付物，不能在普通清理中删除。正式给客户分发时，以 GitHub Release 和统一下载入口为准；客户解压后双击里面的：

```text
胖虎AI多Agent一键部署工具.exe
```

## Mac 开发运行

```bash
chmod +x scripts/run-mac.command
scripts/run-mac.command
```

## Mac 打包

必须在 Mac 上执行：

```bash
chmod +x scripts/build-mac-app.command
scripts/build-mac-app.command
```

打包脚本会按当前构建机器自动区分 Apple 芯片或 Intel 芯片，生成对应 zip：

```text
release/胖虎AI多Agent一键部署工具-Mac-AppleSilicon.zip
release/胖虎AI多Agent一键部署工具-Mac-Intel.zip
```

客户解压后打开：

```text
胖虎AI多Agent一键部署工具.app
```

### Mac 正式分发要求

客户正式分发包最好经过 Apple Developer ID 签名和 notarization 公证，否则 macOS 可能因为无法验证开发者而拦截打开。当前公开下载页为了先保证客户能稳定下载，已经提供未公证的两种芯片包：

- `AI.Agent.-Mac-AppleSilicon.zip`：M1/M2/M3/M4 等 Apple 芯片 Mac。
- `AI.Agent.-Mac-Intel.zip`：Intel Mac。

如果仓库 secrets 未配置 Apple 开发者证书，工作流会生成临时自签包。当前业务策略允许先公开提供该包下载，安装拦截由客户按 macOS 安全提示自行处理。

正式签名和公证需要在 GitHub 仓库配置这些 secrets：

```text
MACOS_CERTIFICATE_BASE64
MACOS_CERTIFICATE_PASSWORD
MACOS_KEYCHAIN_PASSWORD
MACOS_CODESIGN_IDENTITY
APPLE_ID
APPLE_APP_SPECIFIC_PASSWORD
APPLE_TEAM_ID
```

## Codex 官方安装策略

本工具不把 OpenAI/Codex 本体文件打包进源码仓库，也不修改或伪装 Codex 官方文件。

Windows 客户机选择 Codex 客户端时，工具按这个顺序执行：

1. 分开检测 `codex --version` 和 Windows `OpenAI.Codex` 应用包。
2. 查找官方签名离线包，支持放在工具同目录、`offline/`、`codex-official/`。
3. 如果找到 `.msixbundle`、`.msix`、`.appx`、`.appxbundle` 或 `.appinstaller`，先校验 Windows 签名发布者，再调用 Windows 官方 `Add-AppxPackage` 安装。
4. 如果没有离线包，调用：

```powershell
winget install Codex -s msstore
```

5. 自动安装失败时打开官方 Codex 下载页让客户继续。

## 打包环境

打包脚本会在项目目录创建 `.venv`，并从 `requirements-build.txt` 安装构建依赖，避免污染开发机全局 Python 环境。

## 重要限制

- 本工具只走官方在线安装入口，不内置、不修改、不伪装第三方 Agent 本体。
- 胖虎AI默认公开客户域名固定为 `https://aitokenapi.cc`，客户界面只读展示，不能编辑；不要改成内部或私有上游域名。
- ClaudeCode 只安装，不做配置。
- OpenClaw / Hermes 只有在官方配置路径明确且安全时才允许自动写入；本版默认只生成中文配置说明。
- 官方客户端菜单、按钮、设置页是否中文，仍取决于对应官方产品自身。
