# Codex 双态模式退回 API / 官方直登交接

最后更新：2026-06-26

## 1. 本文目标

本文只说明一个问题：

客户当前处于双态模式时，后端代码应该如何切回：

1. 普通 API 模式 `direct_api`
2. 官方直登模式 `official_chatgpt`

重点是避免后端写脚本时误删 ChatGPT 登录态、误保留胖虎AI中转配置、或者把旧 Key 从快照恢复回来。

## 2. 双态模式当前长什么样

双态模式同时影响两个文件：

- `~/.codex/config.toml`
- `~/.codex/auth.json`

双态 `config.toml` 核心：

```toml
model_provider = "panghuAI"

[model_providers.panghuAI]
name = "panghuAI"
base_url = "https://aitokenapi.cc/v1"
wire_api = "responses"
experimental_bearer_token = "客户填写的胖虎AI API Key"
requires_openai_auth = true
```

双态 `auth.json` 核心：

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

双态含义：

- ChatGPT 登录态只负责登录态。
- 模型请求仍走胖虎AI中转站。
- 消耗胖虎AI API Key，不消耗 ChatGPT 账号额度。

## 3. 从双态退回普通 API 模式

目标：

- Codex 模型请求继续走胖虎AI中转站。
- 消耗胖虎AI API Key。
- 当前主 `auth.json` 改回 API Key 模式。
- 当前主 `config.toml` 不能再有 `experimental_bearer_token`。

正确目标模式：

```python
CodexConfigMode.DIRECT_API
```

正确代码路径：

```python
new_config = merge_config(base_config, api_key, base_url, model)
new_auth = build_direct_api_auth_json(base_auth, api_key)
```

最终 `config.toml` 应该类似：

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

最终 `auth.json` 应该是：

```json
{
  "OPENAI_API_KEY": "客户填写的胖虎AI API Key"
}
```

必须确认：

- `config.toml` 中没有 `experimental_bearer_token`。
- `auth.json` 中有 `OPENAI_API_KEY`。
- 这个模式需要胖虎AI API Key。
- 这个模式可以跑 `test_api(base_url, api_key)`。

不要做：

- 不要只把 `auth.json` 改成 API Key，却保留双态 `experimental_bearer_token`。
- 不要只删除 `experimental_bearer_token`，却让 `auth.json` 仍是 `OPENAI_API_KEY = null`。
- 不要把双态的 `auth_mode = "chatgpt"` 留成主 API 模式。

## 4. 从双态退回官方直登模式

目标：

- Codex 模型请求走官方 OpenAI / ChatGPT 账号体系。
- 消耗客户自己的 ChatGPT 账号额度。
- 保留客户已有 ChatGPT 登录态。
- 不再使用胖虎AI中转站 provider。

正确目标模式：

```python
CodexConfigMode.OFFICIAL_CHATGPT
```

正确代码路径：

```python
auth_base = old_auth if has_chatgpt_auth_state(old_auth) else base_auth
new_config = build_official_chatgpt_config(base_config, model)
new_auth = build_official_chatgpt_auth_json(auth_base)
```

最终 `config.toml` 应该类似：

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

最终 `auth.json` 应该保留 ChatGPT 登录态：

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

必须确认：

- `config.toml` 中没有 `[model_providers.panghuAI]`。
- `config.toml` 中没有 `experimental_bearer_token`。
- `config.toml` 中是 `model_provider = "openai"`。
- `auth.json` 中保留 ChatGPT `tokens`。
- `auth.json` 中 `OPENAI_API_KEY` 是 `null`。
- 这个模式不需要胖虎AI API Key。
- 这个模式不能跑 `test_api(base_url, api_key)`。
- 这个模式不能创建胖虎AI商业配置会话，也不能扣胖虎AI次数。

不要做：

- 不要把 `build_direct_api_auth_json(...)` 用到官方直登。
- 不要在官方直登里写胖虎AI `OPENAI_API_KEY`。
- 不要保留 `panghuAI` provider。
- 不要保留双态的 `experimental_bearer_token`。
- 不要覆盖或删除客户已有 ChatGPT `tokens`。

## 5. 为什么不要写“从双态退回”的特殊补丁

错误思路：

```python
if current_mode == DUAL_STATE and target_mode == DIRECT_API:
    手动删除 experimental_bearer_token
    手动改 auth.json
```

这种写法容易漏字段。

正确思路：

永远按“目标模式”重建主配置：

```python
if target_mode == CodexConfigMode.DIRECT_API:
    new_config = merge_config(base_config, api_key, base_url, model)
    new_auth = build_direct_api_auth_json(base_auth, api_key)

elif target_mode == CodexConfigMode.OFFICIAL_CHATGPT:
    auth_base = old_auth if has_chatgpt_auth_state(old_auth) else base_auth
    new_config = build_official_chatgpt_config(base_config, model)
    new_auth = build_official_chatgpt_auth_json(auth_base)
```

原因：

- 目标模式决定最终文件形态。
- 当前模式只用于切换前保存快照。
- 不需要为“从双态退回”单独写一套 patch。
- 单独 patch 最容易出现半双态、半 API、半官方直登的坏配置。

## 6. 快照机制在退回时怎么用

切换前必须先保存当前双态快照：

```python
current_mode = detect_codex_config_mode(old_config, old_auth)
save_codex_mode_snapshot(current_mode, config_path, auth_path, global_agents, workspace_agents, log)
```

如果当前是双态，会保存到：

```text
~/.codex/panghu_modes/dual_state/
```

然后读取目标模式快照作为基准：

```python
snapshot = load_codex_mode_snapshot(target_mode)
base_config = snapshot["config"] if snapshot else old_config
base_auth = snapshot["auth"] if snapshot else old_auth
```

注意：

- 快照是历史基准，不是最终主配置。
- API Key 和 `experimental_bearer_token` 必须按当前输入重新生成。
- 官方直登和双态要优先继承当前主 `auth.json` 里的最新 ChatGPT 登录态。
- 当前主 `auth.json` 没有登录态时，才从目标快照读取登录态。

## 7. 最小伪代码

```python
def switch_codex_mode(target_mode, api_key, model):
    old_config = read(config_path)
    old_auth = read(auth_path)

    current_mode = detect_codex_config_mode(old_config, old_auth)
    save_codex_mode_snapshot(current_mode, ...)

    snapshot = load_codex_mode_snapshot(target_mode)
    base_config = snapshot["config"] if snapshot else old_config
    base_auth = snapshot["auth"] if snapshot else old_auth

    if target_mode == CodexConfigMode.DIRECT_API:
        require_panghu_key(api_key)
        new_config = merge_config(base_config, api_key, DEFAULT_BASE_URL, model)
        new_auth = build_direct_api_auth_json(base_auth, api_key)
        should_test_panghu_api = True

    elif target_mode == CodexConfigMode.OFFICIAL_CHATGPT:
        auth_base = old_auth if has_chatgpt_auth_state(old_auth) else base_auth
        new_config = build_official_chatgpt_config(base_config, model)
        new_auth = build_official_chatgpt_auth_json(auth_base)
        should_test_panghu_api = False

    write(config_path, new_config)
    write(auth_path, new_auth)
```

## 8. 退回后的验收

从双态退 API 后，检查：

```text
config.toml 有 model_provider = "panghuAI"
config.toml 没有 experimental_bearer_token
auth.json 有 OPENAI_API_KEY = 胖虎AI Key
胖虎AI API Key 测试通过
```

从双态退官方直登后，检查：

```text
config.toml 有 model_provider = "openai"
config.toml 没有 model_providers.panghuAI
config.toml 没有 experimental_bearer_token
auth.json 有 auth_mode = "chatgpt"
auth.json 有 tokens
auth.json 的 OPENAI_API_KEY 是 null
不跑胖虎AI API Key 测试
```

共同检查：

```text
写入前有本次备份
写入前有模式快照
失败时能回滚
写完提示客户完全退出 Codex 再重新打开
```

## 9. 后端接手提醒

如果用户说“从双态退回普通 API”，后端应该理解为：

- 目标模式是 `DIRECT_API`。
- 重新生成胖虎AI普通配置。
- `auth.json` 改回胖虎AI API Key。

如果用户说“从双态退回账号直登 / 官方直登”，后端应该理解为：

- 目标模式是 `OFFICIAL_CHATGPT`。
- `config.toml` 改回官方 `openai` provider。
- `auth.json` 保留 ChatGPT 登录态。
- 不再使用胖虎AI中转站 Key。

不要根据“当前是双态”写特殊逻辑；根据“目标模式是什么”写统一逻辑。
