# 胖虎AI多 Agent 一键部署工具

这是一个跨平台图形界面工具，用来给客户一键部署和配置常用 AI Agent。客户必须先用胖虎AI注册账号登录软件，并通过胖虎AI服务端部署授权后，才能按向导创建并填写 API Key，再选择系统、Agent 和安装方式。

## 项目状态

- 规范源码目录：`C:\Users\Administrator\Documents\codex\panghu-codex-installer`
- 原客户发布包位置：`J:\桌面收纳\工具\codex一键安装工具\release\PanghuAI-Codex-Installer-Windows.zip`
- 新版推荐发布包名：`PanghuAI-Agent-Deployer-Windows.zip`
- GitHub 仓库：`https://github.com/dashuaiisme/panghu-codex-installer`
- GitHub Release：`https://github.com/dashuaiisme/panghu-codex-installer/releases/latest`
- 公开更新清单：`https://aitokenapi.cc/deployer/latest.json`
- 仓库只保存源码、脚本和说明；`build/`、`release/`、缓存和 exe/zip 发布产物不提交。

## 客户流程

1. 登录胖虎AI账号；没有账号时点击注册链接去 `https://aitokenapi.cc/register`。
2. 软件向胖虎AI服务端申请部署授权；未授权账号不能进入后续部署。
3. 打开 `https://aitokenapi.cc/login?next=/console/token` 创建 API Key，粘贴到工具里并测试。
4. 选择或确认当前系统，检测环境、PATH、包管理器、已安装 Agent 和第三方配置插件。
5. 选择 Agent 和安装方式：`Codex`、`ClaudeCode`、`OpenClaw`、`Hermes`，支持 CLI / 客户端入口。
6. 点击“一键部署”，工具先拦截 `ccswitch`、`codex++`、`CCR` 等可能改坏配置的第三方工具，再拉取服务端授权清单、调用官方在线安装入口，并对安全可写的 Agent 应用胖虎AI配置。
7. 如果客户已经安装过 Agent，只是 Codex 配置坏了，可点击“仅修复 Codex 配置”，不会重新安装 Agent。
8. 后续软件有新版时，点击“检查更新”下载最新 Windows 更新包；更新后会继续读取客户本机已保存的登录授权、账号名和 API Key，不要求重新填写。

## 服务端授权

- 客户端登录成功后调用 `POST https://aitokenapi.cc/api/deployer/activate` 申请短期部署令牌。
- 真正开始安装前调用 `GET https://aitokenapi.cc/api/deployer/manifest` 获取当前账号允许安装的 Agent 清单。
- 如果服务端拒绝授权、令牌过期、清单不包含所选 Agent，客户端会停止部署。
- 这套强安全模式必须先把胖虎AI后端接口上线到生产站；接口未上线时，新包会在部署授权阶段失败，这是预期的拦截行为。

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

Codex 配置按 `panghuAI` provider 写入，接口固定为：

```text
https://aitokenapi.cc/v1
```

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
  build-mac-app.command          Mac 打包 app
legacy/
  旧版 PowerShell 工具备份
docs/
  客户发送说明和维护说明
```

## Windows 开发运行

```bat
scripts\run-windows.bat
```

## Windows 打包

```bat
scripts\build-windows-exe.bat
```

打包后发送：

```text
release\PanghuAI-Agent-Deployer-Windows.zip
```

客户解压后双击里面的：

```text
PanghuAI-Agent-Deployer.exe
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

打包后发送 `release` 里的 `.app` 或 `.dmg`。

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
- 胖虎AI默认公开客户域名固定为 `https://aitokenapi.cc`，不要改成内部或私有上游域名。
- ClaudeCode 只安装，不做配置。
- OpenClaw / Hermes 只有在官方配置路径明确且安全时才允许自动写入；本版默认只生成中文配置说明。
- 官方客户端菜单、按钮、设置页是否中文，仍取决于对应官方产品自身。
