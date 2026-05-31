# 胖虎AI Codex 图形界面配置助手说明

这是给客户使用的 UI 版工具。客户不用手动输入 PowerShell 命令，只需要打开中文窗口，填 API Key，点击“一键配置”。

## 要发给客户的文件

把下面两个文件放在同一个文件夹里发给客户：

```text
启动胖虎AI-Codex配置助手.cmd
panghu-codex-ui-installer.ps1
```

客户只需要打开：

```text
启动胖虎AI-Codex配置助手.cmd
```

注意：

- 不要用普通记事本重新保存这两个文件，避免中文编码被改坏。
- 如果后续修改脚本，必须保存为 `UTF-8 with BOM`。
- 当前版本已用 `启动胖虎AI-Codex配置助手.cmd --self-test` 复测通过。

## 客户看到的界面

窗口标题：

```text
胖虎AI Codex 一键配置助手
```

主要内容：

- 胖虎AI API Key 输入框
- 接口地址
- 模型选择
- 跳过接口测试
- 配置完成后打开 Codex App
- 一键配置
- 打开工作区
- 打开配置目录
- 配置日志

## 客户使用步骤

1. 双击 `启动胖虎AI-Codex配置助手.cmd`。
2. 在 `胖虎AI API Key` 输入框粘贴自己的 Key。
3. 接口地址保持默认：

```text
https://aitokenapi.cc
```

4. 模型保持默认：

```text
gpt-5.5
```

5. 点击 `一键配置`。
6. 日志里看到 `接口连通正常：HTTP 200`，说明配置成功。
7. 点击 `打开工作区` 或直接使用自动打开的 Codex App。

默认工作区：

```text
文档\胖虎AI-Codex工作区
```

## 工具会自动做什么

- 创建 Codex 配置目录：

```text
C:\Users\<客户名>\.codex
```

- 备份旧配置：

```text
config.toml.bak-时间
```

- 写入胖虎AI中转配置：

```text
base_url = "https://aitokenapi.cc"
wire_api = "responses"
```

- 写入客户的 API Key。
- 创建默认工作区：

```text
文档\胖虎AI-Codex工作区
```

- 写入中文回答规则。
- 测试胖虎AI接口。
- 尝试打开 Codex App。

## 成功标志

日志里出现：

```text
接口连通正常：HTTP 200
配置完成
```

就说明胖虎AI中转配置成功。

## 常见问题

### 双击后没有窗口

可能是 Windows 安全策略拦截。处理方法：

1. 右键 `启动胖虎AI-Codex配置助手.cmd`。
2. 选择 `以管理员身份运行`。

### 提示没有检测到 codex 命令

说明客户电脑可能还没安装 Codex App，或命令行找不到 Codex。

处理：

1. 先安装 Codex App。
2. 重新打开配置助手。
3. 再点 `一键配置`。

即使提示没有检测到 Codex，配置文件也会先写好。

### 接口测试失败

优先检查：

- API Key 是否填错。
- 账号余额是否足够。
- 胖虎AI后台是否给这个 Key 分配了账号池。
- 客户网络是否能访问 `https://aitokenapi.cc`。

### Codex App 菜单还是英文

这是官方 Codex App 的界面限制。

本工具能做到：

- 胖虎AI中转配置。
- 默认中文回答。
- 默认中文工作区规则。

本工具不能保证：

- 把官方 Codex App 所有菜单按钮强制改成中文。

## 后续封装成 exe

当前版本是最容易维护的 UI 脚本版。

后续可以封装成：

```text
胖虎AI-Codex配置助手.exe
```

封装后客户只需要双击一个 exe，不需要看到 `.ps1` 或 `.cmd` 文件。

建议封装前先用当前版本给 3 到 5 个客户测试，确认：

- Key 输入是否顺畅。
- 配置是否成功。
- 接口测试是否能覆盖常见问题。
- 客户是否还会卡在 Codex App 英文界面。

