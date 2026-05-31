# 胖虎AI Codex 一键配置工具截图讲解版

这份说明给客户使用。客户只需要照着做，不需要理解配置文件。

重要说明：

- 这个工具用于一键配置胖虎AI中转，让 Codex 能使用胖虎AI API。
- 这个工具会让 Codex 默认用中文回答。
- 这个工具不能强制把官方 Codex App 的菜单、按钮、设置页全部改成中文。
- 如果客户需要官方插件模式，通常还需要客户自己登录 OpenAI/ChatGPT 账号；胖虎中转只负责模型接口。

---

## 第 1 步：准备文件

把这个文件发给客户：

```text
panghu-codex-oneclick-install.ps1
```

建议客户放到桌面，方便找到。

### 截图 1：桌面上看到脚本文件

客户应该能在桌面看到类似这个文件：

```text
桌面
┌──────────────────────────────────────────────┐
│  panghu-codex-oneclick-install.ps1            │
│  胖虎AI Codex 一键配置脚本                    │
└──────────────────────────────────────────────┘
```

如果客户看不到 `.ps1` 后缀，也没关系，只要文件名是 `panghu-codex-oneclick-install` 即可。

---

## 第 2 步：打开 PowerShell

在脚本所在文件夹空白处，按住 `Shift`，然后点鼠标右键，选择：

```text
在终端中打开
```

或者：

```text
在 PowerShell 中打开
```

### 截图 2：打开终端

客户看到黑色或蓝色窗口都正常：

```text
Windows PowerShell
版权所有 (C) Microsoft Corporation。

PS C:\Users\客户名\Desktop>
```

只要最后一行里有 `PS`，就说明已经打开成功。

---

## 第 3 步：运行一键配置命令

让客户复制下面这一行，粘贴到 PowerShell，然后按回车：

```powershell
powershell -ExecutionPolicy Bypass -File .\panghu-codex-oneclick-install.ps1
```

### 截图 3：输入运行命令

正常画面类似：

```text
PS C:\Users\客户名\Desktop> powershell -ExecutionPolicy Bypass -File .\panghu-codex-oneclick-install.ps1

胖虎AI Codex App 一键安装配置工具
用途：自动写入 Codex API 配置、中文规则，并做基础连通性检查。
请输入胖虎中转 API Key:
```

---

## 第 4 步：输入 API Key

客户把购买到的胖虎AI API Key 粘贴进去，然后按回车。

API Key 通常长这样：

```text
sk-xxxxxxxxxxxxxxxxxxxxxxxx
```

注意：

- 输入时屏幕上可能不显示内容，这是正常的。
- 不要手动加空格。
- 不要漏掉前面的 `sk-`。

### 截图 4：输入 Key

正常画面类似：

```text
请输入胖虎中转 API Key:
```

客户粘贴后按回车即可。看不到字符也不用担心。

---

## 第 5 步：等待自动配置

脚本会自动做这些事情：

1. 检查电脑是否安装了 Codex。
2. 创建 Codex 配置目录。
3. 备份旧配置。
4. 写入胖虎AI中转地址和 API Key。
5. 写入中文回答规则。
6. 测试胖虎AI接口是否连通。
7. 尝试打开 Codex App。

### 截图 5：配置过程

成功过程一般类似：

```text
== 检查 Codex ==
已检测到 Codex：codex-cli 0.xxx.x

== 准备目录 ==
Codex 配置目录：C:\Users\客户名\.codex
默认工作区：C:\Users\客户名\Documents\胖虎AI-Codex工作区

== 备份旧配置 ==
已备份：C:\Users\客户名\.codex\config.toml.bak-20260530-120000

== 写入 Codex API 配置 ==
已写入：C:\Users\客户名\.codex\config.toml
接口地址：https://aitokenapi.cc
模型：gpt-5.5
Key：sk-new...abcd
```

---

## 第 6 步：看接口测试结果

### 成功画面

如果看到：

```text
== 测试胖虎中转接口 ==
接口连通正常：HTTP 200
```

说明胖虎AI中转已经连通。

### 失败画面

如果看到：

```text
接口连通测试失败
```

不要慌，配置文件可能已经写好了。常见原因：

- API Key 复制错了。
- 账号余额不足。
- 客户网络访问不了胖虎AI接口。
- 中转后台没有给这个 Key 分配可用账号池。
- 胖虎AI后台临时维护。

这时把报错截图发给售后即可。

---

## 第 7 步：打开 Codex App

脚本最后会尝试自动打开 Codex App。

### 截图 6：完成画面

正常会看到：

```text
== 启动 Codex App ==
已尝试打开 Codex App。

完成。以后客户只需要在这个工作区使用 Codex：
C:\Users\客户名\Documents\胖虎AI-Codex工作区
```

如果没有自动打开，让客户手动打开 Codex App。

---

## 第 8 步：选择工作区

打开 Codex App 后，客户进入这个文件夹：

```text
Documents\胖虎AI-Codex工作区
```

### 截图 7：选择工作区

如果 Codex App 让客户选择文件夹，选择：

```text
此电脑
  文档
    胖虎AI-Codex工作区
```

这个工作区里已经写好了中文规则。

---

## 第 9 步：发第一句话测试

在 Codex App 输入：

```text
你好，测试一下胖虎AI中转是否正常。以后请全部用中文回答。
```

如果 Codex 能正常回复中文，说明基本配置成功。

### 截图 8：测试成功

正常效果：

```text
用户：
你好，测试一下胖虎AI中转是否正常。以后请全部用中文回答。

Codex：
你好，胖虎AI中转已可以正常使用。后续我会默认使用简体中文回答。
```

---

## 常见问题截图判断

### 问题 1：提示找不到脚本

画面类似：

```text
无法找到路径 .\panghu-codex-oneclick-install.ps1
```

原因：PowerShell 当前目录不是脚本所在目录。

处理：

1. 确认脚本在桌面。
2. 在桌面空白处右键打开 PowerShell。
3. 重新运行命令。

---

### 问题 2：提示没有检测到 codex 命令

画面类似：

```text
没有检测到 codex 命令。
如果你已经安装 Codex App，可以继续；如果还没安装，请先安装 Codex App 后重新运行本脚本。
```

含义：

- 电脑可能还没安装 Codex。
- 或者安装了 Codex App，但命令行里找不到 `codex`。

处理：

1. 先安装 Codex App。
2. 重启电脑或重新打开 PowerShell。
3. 再运行脚本。

脚本仍然会先写好配置，客户后面安装 Codex 后也可能直接生效。

---

### 问题 3：接口连通测试失败

画面类似：

```text
接口连通测试失败
```

优先检查：

1. API Key 是否完整。
2. API Key 是否填错。
3. 胖虎AI账户是否有余额。
4. 胖虎中转后台是否给这个 Key 分配账号池。
5. 客户电脑网络是否能访问 `https://aitokenapi.cc`。

售后最需要客户发这张截图。

---

### 问题 4：Codex App 菜单还是英文

这是正常情况。

这个工具能做到：

- 配置胖虎AI中转。
- 让 Codex 默认中文回答。
- 创建中文规则工作区。

这个工具不能保证：

- 把官方 Codex App 的所有菜单、按钮、设置页改成中文。

如果客户看不懂英文界面，让客户只记住两个操作：

1. 打开 `Documents\胖虎AI-Codex工作区`。
2. 在输入框里直接用中文提问。

---

## 售后人员快速判断表

| 客户截图内容 | 含义 | 处理 |
| --- | --- | --- |
| `接口连通正常：HTTP 200` | 胖虎中转可用 | 让客户打开 Codex 测试 |
| `API Key 不能为空` | 没输入 Key | 重新运行脚本并粘贴 Key |
| `找不到脚本` | 目录错了 | 在脚本所在文件夹打开 PowerShell |
| `没有检测到 codex 命令` | Codex 未安装或命令不可用 | 安装 Codex App 后重试 |
| `接口连通测试失败` | Key、余额、网络或账号池问题 | 查 Key 和后台账号池 |
| Codex 菜单英文 | 官方 App UI 未汉化 | 不影响胖虎中转，按中文教程使用 |

---

## 给客户的最短话术

你只需要做三件事：

1. 把脚本放到桌面。
2. 运行一键配置命令。
3. 输入胖虎AI API Key。

看到 `接口连通正常：HTTP 200` 就说明配置成功。

以后打开 Codex，选择：

```text
Documents\胖虎AI-Codex工作区
```

然后直接用中文提问即可。

