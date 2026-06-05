# 胖虎AI Codex 一键安装工具

这是一个跨平台图形界面工具，用来给客户一键配置 Codex 使用胖虎AI中转。

## 项目状态

- 规范源码目录：`C:\Users\Administrator\Documents\codex\panghu-codex-installer`
- 原客户发布包位置：`J:\桌面收纳\工具\codex一键安装工具\release\PanghuAI-Codex-Installer-Windows.zip`
- GitHub 仓库：`https://github.com/dashuaiisme/panghu-codex-installer`
- GitHub Release：`https://github.com/dashuaiisme/panghu-codex-installer/releases/tag/v0.1.0`
- 仓库只保存源码、脚本和说明；`build/`、`release/`、缓存和 exe/zip 发布产物不提交。

## 目录说明

```text
src/
  panghu_codex_installer.py      图形界面源码，后续优化主要改这里
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

## 客户看到的功能

- 检测 Codex 本体是否已经安装
- 支持安装/修复 Codex 本体：
  - 优先识别同目录、`offline/`、`codex-official/` 下的官方签名离线包
  - 找不到离线包时调用 Microsoft Store/winget 官方安装
  - 自动安装失败时打开官方 Codex 下载页
- 输入胖虎AI API Key
- 默认接口 `https://aitokenapi.cc`
- 默认模型 `gpt-5.5`
- 一键写入 Codex 配置
- 自动备份旧配置和旧中文规则
- 接口测试失败时自动恢复本次写入前的配置
- 自动创建工作区
- 自动合并中文回答规则，不覆盖客户原有规则
- 自动测试 `/v1/models`
- 自动尝试通过 Codex App 官方链接打开工作区
- 可恢复最近一次配置备份
- 可一键复制日志，方便客户发回排查

## 配置写入位置

Windows 和 Mac 都写入当前用户目录：

```text
~/.codex/config.toml
~/.codex/AGENTS.md
~/Documents/胖虎AI-Codex工作区/AGENTS.md
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
release\PanghuAI-Codex-Installer-Windows.zip
```

客户解压后双击里面的：

```text
PanghuAI-Codex-Installer.exe
```

## Codex 本体安装策略

本工具不把 OpenAI/Codex 本体文件打包进源码仓库，也不修改或伪装 Codex 官方文件。

Windows 客户机点击“安装/修复 Codex 本体”时，工具按这个顺序执行：

1. 分开检测 `codex --version` 和 Windows `OpenAI.Codex` 应用包；只有 CLI 不代表桌面 App 本体已安装。
2. 查找官方签名离线包，支持放在：
   - 工具 exe 同目录
   - `offline/`
   - `codex-official/`
3. 如果找到 `.msixbundle`、`.msix`、`.appx`、`.appxbundle` 或 `.appinstaller`，先校验 Windows 签名发布者，再调用 Windows 官方 `Add-AppxPackage` 安装。
4. 如果没有离线包，调用：

```powershell
winget install Codex -s msstore
```

5. 安装后必须重新检测到 Windows `OpenAI.Codex` 应用包才算本体就绪。
6. 如果自动安装失败，打开官方 Codex 下载页让客户按提示继续。

客户发送包可以采用这种结构：

```text
PanghuAI-Codex-Installer/
  PanghuAI-Codex-Installer.exe
  _internal/
  offline/
    OpenAI-Codex-官方签名安装包.msixbundle
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

## 打包环境

打包脚本会在项目目录创建 `.venv`，并从 `requirements-build.txt` 安装构建依赖，避免污染开发机全局 Python 环境。

## 重要限制

- 本工具负责配置胖虎AI中转和中文回答规则。
- Windows 上，本工具只支持安装官方签名 Codex 包或打开官方安装入口，不提供私自重打包的 Codex 本体。
- Mac 上，本工具只负责配置胖虎AI中转；Codex 本体需要客户按官方入口手动安装。
- 本工具不能强制把官方 Codex App 的菜单、按钮、设置页全部汉化。
- 官方插件市场/插件模式可能仍依赖客户自己登录 OpenAI/ChatGPT 账号。
