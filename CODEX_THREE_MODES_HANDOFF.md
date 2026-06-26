# Codex 三模式切换交接说明

最后更新：2026-06-26

## 1. 给接手窗口的结论

本轮已经在本地代码里新增 Codex 第三种模式：`official_chatgpt` 官方直登。

当前 Codex 配置模式必须按三种理解：

1. 普通模式 `direct_api`
2. 双态模式 `dual_state`
3. 官方直登 `official_chatgpt`

重点边界：

- 胖虎AI账号只用于登录本工具和胖虎AI网站，不能登录 Codex。
- 普通模式和双态模式消耗胖虎AI中转站额度。
- 官方直登消耗客户自己的 ChatGPT 账号额度。
- 双态模式不是消耗 ChatGPT 账号额度；双态只是保留 ChatGPT 登录态，模型请求仍走胖虎AI中转站。
- 所有 Codex 配置写入后，都必须完全退出 Codex 再重新打开，配置才会生效。

## 2. 本轮已改代码

主要文件：

- `src/panghu_codex_installer.py`
- `src/commercial_core.py`

关键代码点：

- `CodexConfigMode` 新增 `OFFICIAL_CHATGPT = "official_chatgpt"`。
- 新增 Codex 模式检测：`detect_codex_config_mode(...)`。
- 新增本机模式快照目录：`~/.codex/panghu_modes/`。
- 新增模式快照保存：`save_codex_mode_snapshot(...)`。
- 新增模式快照读取：`load_codex_mode_snapshot(...)`。
- 新增官方直登配置生成：`build_official_chatgpt_config(...)`。
- 新增官方直登 auth 生成：`build_official_chatgpt_auth_json(...)`。
- 新增 Key 需求判断：`codex_config_mode_requires_panghu_key(...)`。
- `install_codex_config(...)` 已接入三模式分支。
- UI 第五步已新增“官方直登”按钮。
- `commercial_core.py` 的 `MODE_LABELS` 已新增 `official_chatgpt: 官方直登`。

## 3. 三种模式的写入规则

### 普通模式 `direct_api`

用途：默认客户路径。

消耗：胖虎AI中转站额度。

`auth.json`：

```json
{
  "OPENAI_API_KEY": "客户填写的胖虎AI API Key"
}
```

`config.toml`：

- 使用 `model_provider = "panghuAI"`。
- 使用 `[model_providers.panghuAI]`。
- 使用 `base_url = "https://aitokenapi.cc/v1"`。
- 不写 `experimental_bearer_token`。

### 双态模式 `dual_state`

用途：客户需要保留 ChatGPT 登录态，同时模型请求仍走胖虎AI中转站。

消耗：胖虎AI中转站额度。

`auth.json`：

- 保留已有 ChatGPT 登录 token。
- 写入 `auth_mode = "chatgpt"`。
- 写入 `OPENAI_API_KEY = null`。

`config.toml`：

- 使用 `model_provider = "panghuAI"`。
- 使用 `[model_providers.panghuAI]`。
- 写入 `experimental_bearer_token = "客户填写的胖虎AI API Key"`。

### 官方直登 `official_chatgpt`

用途：客户明确要消耗自己 ChatGPT 账号额度。

消耗：客户自己的 ChatGPT 账号额度。

`auth.json`：

- 必须保留客户自己的 ChatGPT 登录态。
- 写入 `auth_mode = "chatgpt"`。
- 写入 `OPENAI_API_KEY = null`。
- 如果本机没有 ChatGPT 登录态，工具不能伪造，只能提示客户打开 Codex 自行登录 ChatGPT 账号。

`config.toml`：

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

禁止：

- 不写 `experimental_bearer_token`。
- 不保留 `[model_providers.panghuAI]`。
- 不执行胖虎AI API Key 测试。
- 不创建商业配置会话。
- 不扣胖虎AI配置次数。

## 4. 模式快照机制

目标：三种模式可以来回切换，不把 `config.toml` / `auth.json` 搞乱。

快照目录：

```text
~/.codex/panghu_modes/
  direct_api/
  dual_state/
  official_chatgpt/
  history/<timestamp>/
```

切换流程：

1. 读取当前 `config.toml` 和 `auth.json`。
2. 用 `detect_codex_config_mode(...)` 判断当前模式。
3. 切换前保存当前模式快照。
4. 读取目标模式快照作为恢复基准。
5. 重新生成目标模式的动态字段。
6. 写入主 `config.toml`、`auth.json`、`AGENTS.md`。
7. 失败时用原有 `backup_file(...)` / `restore_backup(...)` 回滚本次写入。

重要规则：

- 目标模式快照可以作为基准，但不能直接把快照原样恢复到主配置。
- 普通/双态里的 API Key 和 `experimental_bearer_token` 必须用当前输入重新生成，不能把快照里的过期 Key 带回来。
- 双态和官方直登优先继承当前主 `auth.json` 里的最新 ChatGPT 登录态；当前没有登录态时，才从目标模式快照取登录态。
- 未识别模式保存到 `history/<timestamp>/`，作为人工恢复线索。

## 5. 已同步文档

本轮已同步：

- `README.md`
- `docs/TECHNICAL_MAINTENANCE_MANUAL.md`
- `docs/PRODUCT_MANUAL_SINGLE_SOURCE_OF_TRUTH.md`
- `docs/发送客户说明.txt`
- `ACCEPTANCE.md`
- `RUNBOOK.md`
- `FINAL_REPORT.md`

这些文档已经写清楚：

- 胖虎AI账号不是 Codex 登录账号。
- 普通/双态消耗胖虎AI中转站额度。
- 官方直登消耗 ChatGPT 账号额度。
- 所有模式写完都要完全退出 Codex 再重新打开。
- 模式切换前保存快照。

## 6. 已跑验证

已跑：

```powershell
python src/panghu_codex_installer.py --self-test
```

结果：

```text
UI self-test OK
```

已跑：

```powershell
python -m pytest tests/test_panghu_commercial_manifest.py tests/test_commercial_core.py tests/test_agent_playbooks.py -q
```

结果：

```text
138 passed, 9 subtests passed
```

另跑过：

```powershell
python -m py_compile src/panghu_codex_installer.py src/commercial_core.py
```

无报错。

## 7. 当前未收尾事项

这些改动目前仍在本地工作树，尚未提交、未推送、未重新打包、未发布。

其他窗口如果要读到这份代码，必须打开真实仓库：

```powershell
cd C:\Users\Administrator\Documents\codex\panghu-codex-installer
```

不要打开这个空目录：

```powershell
C:\Users\Administrator\Documents\胖虎ai codex一键配置
```

后续收尾建议：

1. 先确认工作树中哪些改动属于三模式，哪些是之前已有商业版/文档/发布改动。
2. 重新跑上面的三条验证命令。
3. 提交到 Git。
4. 推送 GitHub。
5. 如要给客户使用，再重新打包、更新 Release、下载页和 `latest.json`。

## 8. 接手时不要改错的点

- 不要把胖虎AI网站账号写成 Codex 登录账号。
- 不要把双态模式说成消耗 ChatGPT 账号额度。
- 不要让官方直登走胖虎AI API Key 测试。
- 不要让官方直登创建商业配置会话或扣胖虎AI次数。
- 不要直接恢复快照里的过期 API Key。
- 不要删客户本机已有的 ChatGPT 登录态。
- 不要忘记所有模式都要求完全退出 Codex 后重开。
