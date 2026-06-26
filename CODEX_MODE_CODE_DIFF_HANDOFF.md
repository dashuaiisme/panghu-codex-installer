# Codex 三种模式代码差异交接

最后更新：2026-06-26

## 1. 本文只解决一个问题

给后端接手者说明：Codex 的三种模式在代码上到底差在哪里，后续改脚本时应该改哪条分支，不能混用哪些代码。

本文不讨论 UI 设计、不讨论发布、不讨论产品宣传。

## 2. 三种模式总览

当前枚举在 `src/panghu_codex_installer.py`：

```python
class CodexConfigMode(str, Enum):
    DIRECT_API = "direct_api"
    DUAL_STATE = "dual_state"
    OFFICIAL_CHATGPT = "official_chatgpt"
```

三种模式含义：

| 模式 | 代码枚举 | 模型请求走哪里 | 消耗谁的额度 | 是否需要胖虎AI Key | 是否需要 ChatGPT 登录态 |
|---|---|---|---|---|---|
| 普通 API 模式 | `DIRECT_API` | 胖虎AI中转站 | 胖虎AI额度 | 需要 | 不需要 |
| 双态模式 | `DUAL_STATE` | 胖虎AI中转站 | 胖虎AI额度 | 需要 | 需要，用于登录态 |
| 官方直登 | `OFFICIAL_CHATGPT` | OpenAI 官方 | 客户 ChatGPT 账号额度 | 不需要 | 需要 |

关键边界：

- 胖虎AI网站账号不是 Codex 登录账号。
- 普通模式和双态模式都是胖虎AI中转站消耗。
- 官方直登才是客户自己的 ChatGPT 账号额度消耗。

## 3. 普通 API 模式代码

### 3.1 config.toml 生成

函数：

```python
build_config(api_key, base_url, model)
merge_config(existing, api_key, base_url, model)
```

输出核心：

```toml
model_provider = "panghuAI"
model = "gpt-5.4"
review_model = "gpt-5.4"

[model_providers.panghuAI]
name = "panghuAI"
base_url = "https://aitokenapi.cc/v1"
wire_api = "responses"
requires_openai_auth = true
```

注意：

- 普通 API 模式使用 `panghuAI` provider。
- 普通 API 模式不写 `experimental_bearer_token`。
- 额度走胖虎AI中转站。

### 3.2 auth.json 生成

函数：

```python
build_direct_api_auth_json(existing, api_key)
```

输出：

```json
{
  "OPENAI_API_KEY": "客户填写的胖虎AI API Key"
}
```

注意：

- 这条路径会把 `auth.json` 写成纯 API Key 形态。
- 如果切换前有 ChatGPT 登录态，必须依赖快照机制先保存，不能直接覆盖后又说还能恢复。

### 3.3 install_codex_config 分支

```python
else:
    new_config = merge_config(base_config, api_key, base_url, model)
    new_auth = build_direct_api_auth_json(base_auth, api_key)
```

测试：

```python
test_api(base_url, api_key)
```

普通模式必须跑胖虎AI API Key 测试，除非用户主动跳过。

## 4. 双态模式代码

### 4.1 config.toml 生成

函数：

```python
build_dual_state_config(api_key, base_url, model)
```

它基于普通模式 `build_config(...)`，额外插入：

```toml
experimental_bearer_token = "客户填写的胖虎AI API Key"
```

输出核心：

```toml
model_provider = "panghuAI"

[model_providers.panghuAI]
name = "panghuAI"
base_url = "https://aitokenapi.cc/v1"
wire_api = "responses"
experimental_bearer_token = "客户填写的胖虎AI API Key"
requires_openai_auth = true
```

注意：

- 双态模式仍然是 `panghuAI` provider。
- 双态模式模型请求仍走胖虎AI中转站。
- `experimental_bearer_token` 是胖虎AI API Key，不是 ChatGPT token。

### 4.2 auth.json 生成

函数：

```python
build_dual_state_auth_json(existing, api_key)
```

逻辑：

```python
payload = json.loads(existing) if existing.strip() else {}
payload["auth_mode"] = "chatgpt"
payload["OPENAI_API_KEY"] = None
```

输出形态：

```json
{
  "auth_mode": "chatgpt",
  "OPENAI_API_KEY": null,
  "tokens": {
    "access_token": "保留已有登录态",
    "refresh_token": "保留已有刷新 token"
  }
}
```

注意：

- 它保留 `existing` 里的其它字段，尤其是 `tokens`。
- 它不把胖虎AI Key 写进 `auth.json`。
- 胖虎AI Key 在 `config.toml` 的 `experimental_bearer_token` 里。
- 双态登录态来自 ChatGPT，但模型消耗不是 ChatGPT 账号额度。

### 4.3 install_codex_config 分支

```python
if mode == CodexConfigMode.DUAL_STATE:
    auth_base = old_auth if has_chatgpt_auth_state(old_auth) else base_auth
    new_config = build_dual_state_config(api_key, base_url, model)
    new_auth = build_dual_state_auth_json(auth_base, api_key)
```

测试：

```python
test_api(base_url, api_key)
```

双态模式也必须跑胖虎AI API Key 测试，除非用户主动跳过。

## 5. 官方直登代码

### 5.1 config.toml 生成

函数：

```python
build_official_chatgpt_config(existing, model)
```

逻辑：

```python
lines = remove_sections(lines, {"model_providers.panghuAI"})
lines = update_top_level_keys(lines, CODEX_OFFICIAL_TOP_LEVEL_CONFIG, CODEX_MANAGED_TOP_LEVEL_KEYS)
```

输出核心：

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

注意：

- 官方直登必须移除 `[model_providers.panghuAI]`。
- 官方直登必须移除 `experimental_bearer_token`。
- 官方直登使用 `model_provider = "openai"`。
- 官方直登不写胖虎AI中转站 URL。

### 5.2 auth.json 生成

函数：

```python
build_official_chatgpt_auth_json(existing)
```

逻辑：

```python
if not has_chatgpt_auth_state(...):
    raise ValueError(...)
payload["auth_mode"] = "chatgpt"
payload["OPENAI_API_KEY"] = None
```

输出形态：

```json
{
  "auth_mode": "chatgpt",
  "OPENAI_API_KEY": null,
  "tokens": {
    "access_token": "客户已有 ChatGPT 登录态",
    "refresh_token": "客户已有 ChatGPT 刷新 token"
  }
}
```

注意：

- 官方直登必须检测本机已有 ChatGPT 登录态。
- 没有登录态时，工具不能伪造，必须报错提示客户先打开 Codex 登录 ChatGPT。
- 官方直登不需要胖虎AI API Key。

### 5.3 install_codex_config 分支

```python
elif mode == CodexConfigMode.OFFICIAL_CHATGPT:
    auth_base = old_auth if has_chatgpt_auth_state(old_auth) else base_auth
    new_config = build_official_chatgpt_config(base_config, model)
    new_auth = build_official_chatgpt_auth_json(auth_base)
```

测试：

```python
if mode == CodexConfigMode.OFFICIAL_CHATGPT:
    log("官方直登模式不执行胖虎AI接口测试...")
```

官方直登禁止跑 `test_api(base_url, api_key)`。

## 6. 模式检测代码

函数：

```python
detect_codex_config_mode(config_text, auth_text)
```

判断顺序：

```python
if "model_provider = \"panghuAI\"" in config_text or "[model_providers.panghuAI]" in config_text:
    if "experimental_bearer_token" in config_text:
        return CodexConfigMode.DUAL_STATE
    return CodexConfigMode.DIRECT_API
if has_chatgpt_auth_state(auth_text):
    return CodexConfigMode.OFFICIAL_CHATGPT
if auth 有 OPENAI_API_KEY:
    return CodexConfigMode.DIRECT_API
return None
```

注意：

- 只要配置里还有 `panghuAI`，就不能判断成官方直登。
- 有 `panghuAI + experimental_bearer_token` 是双态。
- 有 `panghuAI` 但没有 `experimental_bearer_token` 是普通 API。
- 没有 `panghuAI` 且有 ChatGPT 登录态，才是官方直登。

## 7. Key 需求代码

函数：

```python
codex_config_mode_requires_panghu_key(mode)
```

当前规则：

```python
return mode in (CodexConfigMode.DIRECT_API, CodexConfigMode.DUAL_STATE)
```

含义：

- 普通 API 需要胖虎AI Key。
- 双态需要胖虎AI Key。
- 官方直登不需要胖虎AI Key。

后端脚本不要把官方直登挡在“请先填写胖虎AI API Key”这一步。

## 8. 模式快照与动态字段

快照目录：

```text
~/.codex/panghu_modes/
  direct_api/
  dual_state/
  official_chatgpt/
  history/<timestamp>/
```

当前切换流程：

```python
old_config = safe_read_text(config_path)
old_auth = safe_read_text(auth_path)
current_mode = detect_codex_config_mode(old_config, old_auth)
save_codex_mode_snapshot(current_mode, ...)

snapshot = load_codex_mode_snapshot(mode)
base_config = snapshot["config"] if snapshot else old_config
base_auth = snapshot["auth"] if snapshot else old_auth
```

关键原则：

- 快照只能作为恢复基准。
- 不能把目标模式快照原样复制回主配置。
- API Key 和 `experimental_bearer_token` 必须根据当前输入重新生成。
- ChatGPT 登录态优先使用当前主 `auth.json`，当前没有时才从快照取。

## 9. 后端改代码时的红线

不要做这些事：

1. 不要把胖虎AI账号写成 Codex 登录账号。
2. 不要把双态模式说成或改成消耗 ChatGPT 账号额度。
3. 不要让官方直登保留 `[model_providers.panghuAI]`。
4. 不要让官方直登写 `experimental_bearer_token`。
5. 不要让官方直登写胖虎AI `OPENAI_API_KEY`。
6. 不要让官方直登跑 `test_api(base_url, api_key)`。
7. 不要让官方直登创建商业配置会话或扣胖虎AI次数。
8. 不要把普通 API 模式的 `build_direct_api_auth_json` 用到官方直登。
9. 不要把快照里的过期 Key 原样恢复到主配置。
10. 不要覆盖客户已有的 ChatGPT `tokens`。

## 10. 本轮相关验证

已经跑过：

```powershell
python src/panghu_codex_installer.py --self-test
python -m pytest tests/test_panghu_commercial_manifest.py tests/test_commercial_core.py tests/test_agent_playbooks.py -q
python -m py_compile src/panghu_codex_installer.py src/commercial_core.py
```

最近结果：

```text
UI self-test OK
138 passed, 9 subtests passed
py_compile 无报错
```

## 11. 给接手后端的最短检查清单

改任何 Codex 配置脚本前，先回答：

- 这次改的是普通 API、双态，还是官方直登？
- 目标模式是否需要胖虎AI Key？
- 目标模式的 `model_provider` 应该是 `panghuAI` 还是 `openai`？
- 目标模式是否允许出现 `experimental_bearer_token`？
- 目标模式是否应该保留 ChatGPT `tokens`？
- 目标模式是否应该跑胖虎AI API Key 测试？
- 切换前是否已经保存当前模式快照？

这些问题回答不清楚时，不要改 `install_codex_config(...)`。
