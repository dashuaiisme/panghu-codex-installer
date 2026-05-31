# 胖虎AI Codex 一键安装工具

这是一个跨平台图形界面工具，用来给客户一键配置 Codex 使用胖虎AI中转。

## 项目状态

- 规范源码目录：`C:\Users\Administrator\Documents\codex\panghu-codex-installer`
- 原客户发布包位置：`J:\桌面收纳\工具\codex一键安装工具\release\PanghuAI-Codex-Installer-Windows.zip`
- GitHub 仓库：`https://github.com/dashuaiisme/panghu-codex-installer`
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

- 输入胖虎AI API Key
- 默认接口 `https://aitokenapi.cc`
- 默认模型 `gpt-5.5`
- 一键写入 Codex 配置
- 自动备份旧配置
- 自动创建工作区
- 自动写入中文回答规则
- 自动测试 `/v1/models`
- 自动尝试打开 Codex App

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

## 重要限制

- 本工具负责配置胖虎AI中转和中文回答规则。
- 本工具不能强制把官方 Codex App 的菜单、按钮、设置页全部汉化。
- 官方插件市场/插件模式可能仍依赖客户自己登录 OpenAI/ChatGPT 账号。
