# 胖虎AI Codex App 一键安装配置方案

## 客户怎么用

把 `panghu-codex-oneclick-install.ps1` 发给客户，让客户右键用 PowerShell 运行，或在脚本所在目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\panghu-codex-oneclick-install.ps1
```

脚本会提示客户输入胖虎中转 API Key。客户不需要手动改配置文件。

如果你想把 Key 直接做成一键命令：

```powershell
powershell -ExecutionPolicy Bypass -File .\panghu-codex-oneclick-install.ps1 -ApiKey "sk-xxxx"
```

## 脚本会做什么

1. 检查电脑上是否能找到 `codex` 命令。
2. 创建 `C:\Users\<客户名>\.codex` 配置目录。
3. 自动备份旧的 `config.toml`。
4. 写入胖虎中转地址、API Key、模型名和 Responses 协议配置。
5. 写入中文优先规则，减少 Codex App 回答英文的问题。
6. 创建默认工作区 `Documents\胖虎AI-Codex工作区`。
7. 测试 `https://aitokenapi.cc/v1/models` 是否能连通。
8. 尝试打开 Codex App。

## 默认配置

- 中转地址：`https://aitokenapi.cc`
- 模型：`gpt-5.5`
- 协议：`responses`
- 默认工作区：`Documents\胖虎AI-Codex工作区`

需要换模型或地址时：

```powershell
powershell -ExecutionPolicy Bypass -File .\panghu-codex-oneclick-install.ps1 -ApiKey "sk-xxxx" -BaseUrl "https://aitokenapi.cc" -Model "gpt-5.5"
```

## 给客户的最短说明

1. 先安装 Codex App。
2. 运行这个脚本。
3. 输入你购买的胖虎AI API Key。
4. 打开 Codex App 后，进入 `Documents\胖虎AI-Codex工作区` 使用。

## 常见问题

### 配置好后还是不能用

优先检查：

- API Key 是否复制完整。
- 胖虎AI账户余额是否足够。
- 客户网络是否能访问 `https://aitokenapi.cc`。
- 中转后台是否给这个 Key 分配了可用账号池。

### Codex App 不显示中文

脚本已经写入：

- `C:\Users\<客户名>\.codex\AGENTS.md`
- `Documents\胖虎AI-Codex工作区\AGENTS.md`

如果仍然偶发英文，让客户第一句话输入：

```text
以后全部用简体中文回答。
```

### 客户已经有自己的 Codex 配置

脚本会先备份旧配置，备份文件类似：

```text
config.toml.bak-20260524-220000
```

恢复时把备份文件改回 `config.toml` 即可。

## 后续可以继续升级

更适合批量客户的版本是做成 `.exe` 或 `.msi` 安装器，界面只保留三个输入：

- API Key
- 模型选择
- 是否强制中文

安装器内部仍然复用这个 PowerShell 逻辑。

