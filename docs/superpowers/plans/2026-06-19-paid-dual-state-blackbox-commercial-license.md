# 付费双态、黑箱保护与商业授权实施计划

> **历史/非权威说明：** 本文件是 2026-06-19 阶段的商业化方案草稿，不是当前产品规则来源。文中的价格、次数、有效期、设备数、套餐、版本、返佣比例、提现门槛、结算状态、上架状态和发布建议均不得作为当前交付口径使用；当前权威以 `docs/PRODUCT_MANUAL_SINGLE_SOURCE_OF_TRUTH.md`、`docs/TECHNICAL_MAINTENANCE_MANUAL.md`、`docs/COMMERCIAL_BACKEND_API_CONTRACT.md`、`FINAL_REPORT.md` 为准。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在原版“胖虎AI多 Agent 一键部署工具”基础上，增加双态模式 20 元付费解锁、客户端黑箱保护、商业传播/代安装授权三层产品能力。

**Architecture:** 以胖虎AI服务端作为授权和支付中心，客户端只负责登录、展示状态、发起支付、拉取权益清单、执行本机配置。普通一键配置保持现有免费/低门槛路径，双态模式和商业传播能力通过服务端权益决定是否放行。客户端打包做混淆、签名、完整性校验和关键逻辑服务端化，但不承诺绝对不可破解。

**Tech Stack:** Python/Tkinter 客户端、胖虎AI现有登录接口、胖虎AI支付宝官方支付配置、服务端部署授权接口、GitHub Actions 三端构建、Windows/Mac 打包脚本。

---

## 一、产品分层设计

### 1. 基础版：继续传播胖虎AI

基础版保留现有原版能力：

- 胖虎AI账号登录。
- 创建并填写胖虎AI API Key。
- 安装或配置 Codex、ClaudeCode、OpenClaw、Hermes。
- Codex 普通模式继续使用直接 API 配置。
- 不要求客户登录 ChatGPT。
- 不限制普通用户转发工具。

这一层的目的不是收费，而是让工具继续传播，让更多客户最终使用胖虎AI中转站、API 和 token。

### 2. 高级版：20 元解锁双态模式

双态模式定义为高级功能：

- 入口仍然叫“双态配置”。
- 未解锁时按钮可见，但状态显示“高级功能，20 元解锁”。
- 用户点击后，客户端向胖虎AI服务端查询权益。
- 未购买时弹出支付窗口，展示 20 元解锁说明和支付宝支付入口。
- 支付成功后，服务端给当前胖虎AI账号下发 `dual_state_pro` 权益。
- 客户端重新拉取 manifest 后放行双态配置。

双态模式不应混入普通部署链路。普通客户仍点“一键部署（普通）”；只有需要 ChatGPT 登录态共存的人才购买并使用双态模式。

### 3. 商业授权版：从代安装牟利者身上收费

商业授权不是限制所有人分享，而是限制商业化批量使用：

- 普通分享：允许，继续帮助胖虎AI传播。
- 个人自用：允许，不强制收费。
- 代安装、工作室、批量部署、客户服务：需要商业授权。

建议第一版提供三种授权：

| 授权类型 | 适合对象 | 控制方式 |
| --- | --- | --- |
| 个人版 | 自己电脑使用 | 默认登录授权即可 |
| 双态高级版 | 需要双态模式的个人用户 | 20 元一次性解锁 |
| 商业安装版 | 帮别人安装并收费的人 | 按设备数/次数/有效期授权 |

商业授权第一版建议不要做得太重，先做“设备额度包”：

- 30 元：10 次商业安装额度。
- 88 元：50 次商业安装额度。
- 188 元：200 次商业安装额度。

服务端根据设备指纹和账号记录已使用次数。客户端每次执行“一键部署（普通）”前上报设备指纹，如果检测到同一账号短时间部署多台新设备，则提示购买商业授权。

---

## 二、服务端设计

本工具当前已经有三类服务端接口：

- 登录：`POST https://aitokenapi.cc/api/user/login?turnstile=`
- 部署激活：`POST https://aitokenapi.cc/api/deployer/activate`
- 部署清单：`GET https://aitokenapi.cc/api/deployer/manifest`

新增付费能力时，不建议让客户端直接判断“是否付过钱”。正确做法是让胖虎AI服务端统一返回权益。

### 1. 新增权益模型

服务端为当前登录用户维护这些权益：

```json
{
  "entitlements": {
    "basic_deploy": {
      "enabled": true
    },
    "dual_state_pro": {
      "enabled": true,
      "source": "paid",
      "paid_amount_cents": 2000,
      "order_no": "DEPLOYER_DUAL_202606190001",
      "activated_at": "2026-06-19T12:00:00+08:00"
    },
    "commercial_deploy": {
      "enabled": true,
      "quota_total": 50,
      "quota_used": 3,
      "expires_at": null
    }
  }
}
```

### 2. 扩展部署清单接口

修改胖虎AI服务端的 `GET /api/deployer/manifest` 返回结构，新增：

```json
{
  "success": true,
  "data": {
    "agents": [
      {"id": "codex"},
      {"id": "claudecode"},
      {"id": "openclaw"},
      {"id": "hermes"}
    ],
    "features": {
      "basic_deploy": true,
      "dual_state_pro": false,
      "commercial_deploy": false
    },
    "products": {
      "dual_state_pro": {
        "name": "双态模式高级版",
        "price_cents": 2000,
        "currency": "CNY",
        "description": "保留 ChatGPT 登录态，模型消耗走胖虎AI API Key。"
      },
      "commercial_10": {
        "name": "商业安装 10 次包",
        "price_cents": 3000,
        "currency": "CNY",
        "quota": 10
      }
    },
    "commercial_usage": {
      "device_count_30d": 2,
      "quota_total": 0,
      "quota_used": 0,
      "needs_commercial_license": false
    }
  }
}
```

客户端只信任这个清单，不在本地硬编码用户是否已购买。

### 3. 新增订单创建接口

新增胖虎AI服务端接口：

```text
POST https://aitokenapi.cc/api/deployer/order/create
```

请求：

```json
{
  "product_id": "dual_state_pro",
  "device_fingerprint": "sha256:...",
  "app_version": "1.0.16",
  "platform": "windows"
}
```

响应：

```json
{
  "success": true,
  "data": {
    "order_no": "DEPLOYER_DUAL_202606190001",
    "amount_cents": 2000,
    "payment_provider": "alipay",
    "payment_url": "https://aitokenapi.cc/pay/alipay/...",
    "qr_code_url": "https://aitokenapi.cc/pay/alipay/qr/..."
  }
}
```

支付宝具体密钥、收款配置和回调继续沿用胖虎AI已有支付设置。工具客户端只拿支付链接或二维码，不保存支付宝密钥。

### 4. 新增订单状态接口

新增：

```text
GET https://aitokenapi.cc/api/deployer/order/status?order_no=DEPLOYER_DUAL_202606190001
```

响应：

```json
{
  "success": true,
  "data": {
    "order_no": "DEPLOYER_DUAL_202606190001",
    "status": "paid",
    "entitlement": "dual_state_pro"
  }
}
```

客户端轮询订单状态。状态为 `paid` 后，客户端重新拉取 `manifest`，确认 `features.dual_state_pro=true` 后再放行双态配置。

### 5. 支付回调处理

支付宝异步回调由胖虎AI服务端处理：

- 校验支付宝签名。
- 校验订单金额必须等于 20 元。
- 校验订单未重复处理。
- 将订单状态改为 `paid`。
- 给用户写入 `dual_state_pro` 权益。
- 记录设备指纹和来源。

客户端不要直接相信“浏览器支付成功页面”，必须以服务端订单状态为准。

---

## 三、客户端设计

当前客户端主文件：

```text
C:\Users\Administrator\Documents\codex\panghu-codex-installer\src\panghu_codex_installer.py
```

当前相关位置：

- 常量：文件顶部 `APP_VERSION`、`LOGIN_URL`、`DEPLOYER_ACTIVATE_URL`、`DEPLOYER_MANIFEST_URL`
- 登录：`login_panghuai`
- 部署激活：`activate_deployer`
- 部署清单：`fetch_deployer_manifest`
- 双态按钮：`self.dual_state_button`
- 双态执行：`start_dual_state_config`
- 普通部署：`start_deploy`
- 自检：`--self-test`

### 1. 增加产品和权益解析

建议新增数据解析函数：

```python
def manifest_features(manifest: dict) -> dict:
    features = manifest.get("features") or {}
    return features if isinstance(features, dict) else {}


def feature_enabled(manifest: dict, feature_id: str) -> bool:
    return bool(manifest_features(manifest).get(feature_id))


def manifest_products(manifest: dict) -> dict:
    products = manifest.get("products") or {}
    return products if isinstance(products, dict) else {}
```

这些函数只解析服务端清单，不做本地破解式判断。

### 2. 双态按钮状态

客户端进入第四步时：

- 如果 `dual_state_pro=true`：按钮显示“已解锁：双态配置”。
- 如果 `dual_state_pro=false`：按钮显示“20 元解锁双态模式”。
- 点击未解锁按钮时，不直接写配置，而是进入支付流程。

界面说明文案建议：

```text
普通一键配置：适合大多数客户，直接使用胖虎AI API Key，无需 ChatGPT 登录。
双态模式：高级功能，20 元解锁。适合需要保留自己 ChatGPT 登录态，同时模型消耗走胖虎AI API Key 的客户。
```

### 3. 支付弹窗流程

新增客户端流程：

1. 用户点击“20 元解锁双态模式”。
2. 客户端调用 `POST /api/deployer/order/create`。
3. 弹出支付窗口，展示金额、说明、二维码或“打开支付宝支付”按钮。
4. 客户端每 3 秒查询一次订单状态。
5. 最长等待 5 分钟。
6. 支付成功后刷新 manifest。
7. `dual_state_pro=true` 后，按钮切换为“已解锁：双态配置”。
8. 自动继续或提示用户再次点击双态配置。

失败提示：

- 订单创建失败：提示“支付订单创建失败，请稍后重试或联系胖虎AI客服。”
- 支付超时：提示“未检测到支付成功，订单可稍后继续查询。”
- 订单已支付但权益未刷新：提示“支付已成功，权益同步中，请点击刷新授权。”

### 4. 商业使用识别

客户端每次准备部署前上报：

- 当前胖虎AI用户 ID。
- 设备指纹。
- 系统平台。
- 应用版本。
- 选择的 Agent。
- 是否为修复配置。

服务端判断是否属于商业使用迹象：

- 同一账号 30 天内绑定多台新设备。
- 同一账号短时间多次部署。
- 同一设备多账号频繁切换。
- 部署目标明显超过个人自用范围。

第一版不要强拦截普通用户，只在超过阈值时提示：

```text
检测到该账号近期已为多台设备执行部署。如果这是代安装或商业服务，请购买商业安装额度后继续。个人自用不受影响。
```

当服务端返回 `needs_commercial_license=true` 时，客户端才强制购买商业授权。

---

## 四、黑箱保护设计

必须先明确边界：客户端下载安装到用户电脑后，不存在绝对不可破解。目标是提高盗版和逆向成本，并把真正值钱的授权逻辑放服务端。

### 1. 第一层：关键逻辑服务端化

不要把这些逻辑完全放本地：

- 是否已购买双态模式。
- 是否还有商业安装额度。
- 是否允许部署某个 Agent。
- 是否允许临时 OpenAI 访问窗口。
- 是否允许当前设备继续使用高级功能。

客户端只负责：

- 登录。
- 展示权益。
- 请求支付。
- 拉取 manifest。
- 执行本机安装和配置。

即使别人逆向客户端，也无法凭本地代码伪造服务端权益。

### 2. 第二层：客户端打包保护

Windows 和 Mac 包都做：

- Python 源码不以 `.py` 明文分发。
- 使用 PyInstaller one-folder 或 one-file，并启用字节码优化。
- 增加混淆步骤，优先保护业务授权、支付、manifest 解析和配置执行相关模块。
- 把客户界面文案和非敏感配置保留可维护，不把密钥写死在客户端。

建议后续把当前单文件拆成模块后再混淆：

```text
src/panghu_codex_installer/
  app.py
  auth_client.py
  entitlement_client.py
  payment_client.py
  license_guard.py
  codex_config.py
  packaging_guard.py
```

### 3. 第三层：完整性校验

客户端启动时做轻量完整性检查：

- 校验自身版本号。
- 校验核心资源文件 hash。
- 校验更新清单签名。
- 检测是否运行在明显被篡改目录。

如果检测到异常：

```text
当前工具文件可能已被修改。为保护账号和配置安全，请从胖虎AI官方下载页重新下载最新版。
```

### 4. 第四层：签名和发布可信度

Windows：

- 后续购买代码签名证书。
- 对 exe 签名。
- 下载页提示只认胖虎AI官方域名。

Mac：

- 配置 Apple Developer ID。
- 做签名和 notarization 公证。
- 减少客户安装拦截。

这一步不仅防破解，也降低别人二次打包冒充官方工具的风险。

### 5. 第五层：水印和审计

每个安装包或登录账号下发唯一客户端标识：

- 工具日志里隐藏敏感信息，但保留授权流水号。
- 服务端记录账号、设备、版本、部署次数。
- 如果发现盗版包，可从请求特征定位来源账号或版本。

---

## 五、文件级实施计划

### Task 1: 固化产品方案文档

**Files:**

- Create: `C:\Users\Administrator\Documents\codex\panghu-codex-installer\docs\PAID_DUAL_STATE_AND_COMMERCIAL_LICENSE.md`
- Modify: `C:\Users\Administrator\Documents\codex\panghu-codex-installer\docs\TECHNICAL_MAINTENANCE_MANUAL.md`
- Modify: `C:\Users\Administrator\Documents\codex\panghu-codex-installer\README.md`

- [ ] **Step 1: 新增产品方案文档**

写入四个固定章节：

```markdown
# 付费双态与商业授权方案

## 产品分层

- 基础版：普通一键配置，继续传播胖虎AI。
- 高级版：20元解锁双态模式。
- 商业授权版：代安装、批量部署、工作室使用需购买商业安装额度。

## 授权原则

所有付费权益以胖虎AI服务端为准；客户端只展示和执行，不在本地硬编码已购买状态。

## 支付原则

支付宝密钥、收款账号和回调只存在胖虎AI服务端；客户端只拿订单链接、二维码和订单状态。

## 黑箱原则

客户端做混淆、签名、完整性校验；关键授权逻辑服务端化。不承诺绝对不可破解，只提高盗版和逆向成本。
```

- [ ] **Step 2: 更新维护手册项目边界**

在维护手册“胖虎AI服务端接口”后补充：

```markdown
### 付费权益和商业授权

双态模式不再只是本地按钮能力，而是胖虎AI服务端下发的高级权益。客户端必须先拉取部署清单，确认 `features.dual_state_pro=true` 后才能写入双态配置。

商业安装能力由服务端统计设备指纹和部署次数。客户端不得在本地伪造商业额度，也不得绕过服务端清单继续部署。
```

- [ ] **Step 3: 更新 README 客户说明**

在“客户流程”里补充：

```markdown
双态模式是高级功能。未解锁时工具会提示通过胖虎AI支付宝官方支付 20 元解锁；支付成功并刷新授权后才可使用。普通一键配置不受影响。
```

- [ ] **Step 4: 验证文档**

Run:

```powershell
rg -n "20元|双态模式|商业授权|dual_state_pro" C:\Users\Administrator\Documents\codex\panghu-codex-installer\README.md C:\Users\Administrator\Documents\codex\panghu-codex-installer\docs
```

Expected: 能看到新方案、README 和维护手册里都提到付费双态和商业授权。

### Task 2: 胖虎AI服务端扩展权益和订单接口

**Files:**

- Modify: 胖虎AI服务端 deployer manifest 相关路由文件
- Create/Modify: 胖虎AI服务端 deployer order 相关路由文件
- Modify: 胖虎AI支付宝官方支付回调处理文件
- Test: 服务端 deployer 支付和权益测试

- [ ] **Step 1: 给 manifest 增加 features/products/commercial_usage**

目标返回结构：

```json
{
  "features": {
    "basic_deploy": true,
    "dual_state_pro": false,
    "commercial_deploy": false
  },
  "products": {
    "dual_state_pro": {
      "name": "双态模式高级版",
      "price_cents": 2000,
      "currency": "CNY"
    }
  },
  "commercial_usage": {
    "device_count_30d": 1,
    "quota_total": 0,
    "quota_used": 0,
    "needs_commercial_license": false
  }
}
```

- [ ] **Step 2: 新增订单创建接口**

接口：

```text
POST /api/deployer/order/create
```

只允许这些产品：

```json
[
  {"product_id": "dual_state_pro", "price_cents": 2000},
  {"product_id": "commercial_10", "price_cents": 3000},
  {"product_id": "commercial_50", "price_cents": 8800},
  {"product_id": "commercial_200", "price_cents": 18800}
]
```

校验规则：

- 必须登录。
- 必须有用户 ID。
- `product_id` 必须在白名单。
- 金额由服务端白名单决定，不能相信客户端传来的金额。
- 返回支付宝官方支付链接或二维码。

- [ ] **Step 3: 新增订单状态接口**

接口：

```text
GET /api/deployer/order/status?order_no=...
```

状态：

```text
created
paying
paid
expired
failed
```

只有 `paid` 才能给客户端放行。

- [ ] **Step 4: 支付回调写入权益**

支付宝回调成功后：

- 校验签名。
- 校验订单号存在。
- 校验金额和产品白名单一致。
- 幂等处理重复回调。
- `dual_state_pro` 写一次性永久权益。
- 商业安装包写入对应额度。

- [ ] **Step 5: 服务端测试**

测试用例：

```text
未购买用户 manifest 返回 dual_state_pro=false
创建 dual_state_pro 订单金额固定为 2000 分
支付回调成功后 manifest 返回 dual_state_pro=true
重复回调不会重复加商业额度
商业额度不足时 needs_commercial_license=true
```

### Task 3: 客户端新增权益解析和支付客户端

**Files:**

- Modify: `C:\Users\Administrator\Documents\codex\panghu-codex-installer\src\panghu_codex_installer.py`
- Test: `--self-test`

- [ ] **Step 1: 新增接口常量**

在顶部常量区新增：

```python
DEPLOYER_ORDER_CREATE_URL = f"{DEFAULT_BASE_URL}/api/deployer/order/create"
DEPLOYER_ORDER_STATUS_URL = f"{DEFAULT_BASE_URL}/api/deployer/order/status"
```

- [ ] **Step 2: 新增 manifest 权益解析函数**

加入：

```python
def manifest_features(manifest: dict) -> dict:
    features = manifest.get("features") or {}
    return features if isinstance(features, dict) else {}


def feature_enabled(manifest: dict, feature_id: str) -> bool:
    return bool(manifest_features(manifest).get(feature_id))


def manifest_products(manifest: dict) -> dict:
    products = manifest.get("products") or {}
    return products if isinstance(products, dict) else {}
```

- [ ] **Step 3: 新增订单创建函数**

加入：

```python
def create_deployer_order(
    user: dict,
    cookie_jar: http.cookiejar.CookieJar,
    deployer_token: str,
    product_id: str,
) -> tuple[bool, str, dict]:
    user_id = str(user.get("id") or user.get("user_id") or "").strip()
    if not user_id or not deployer_token:
        return False, "缺少登录授权，请重新恢复或登录胖虎AI账号。", {}
    try:
        payload = open_json_with_cookies(
            DEPLOYER_ORDER_CREATE_URL,
            cookie_jar,
            {
                "product_id": product_id,
                "device_fingerprint": device_fingerprint(),
                "app_version": APP_VERSION,
                "platform": current_platform_id(),
            },
            {"New-Api-User": user_id, "X-Panghu-Deployer-Token": deployer_token},
        )
    except urllib.error.HTTPError as exc:
        return False, f"支付订单创建失败：HTTP {exc.code}", {}
    except urllib.error.URLError as exc:
        return False, f"支付订单连接失败：{exc.reason}", {}
    except json.JSONDecodeError:
        return False, "支付订单返回内容无法解析。", {}
    except Exception as exc:
        return False, f"支付订单创建失败：{exc}", {}
    if not payload.get("success"):
        return False, str(payload.get("message") or "支付订单创建失败。"), {}
    return True, "支付订单已创建。", payload.get("data") or {}
```

- [ ] **Step 4: 新增订单查询函数**

加入：

```python
def fetch_deployer_order_status(
    user: dict,
    cookie_jar: http.cookiejar.CookieJar,
    deployer_token: str,
    order_no: str,
) -> tuple[bool, str, dict]:
    user_id = str(user.get("id") or user.get("user_id") or "").strip()
    if not user_id or not deployer_token or not order_no:
        return False, "缺少订单或登录授权。", {}
    url = f"{DEPLOYER_ORDER_STATUS_URL}?order_no={urllib.parse.quote(order_no)}"
    try:
        payload = open_json_with_cookies(
            url,
            cookie_jar,
            None,
            {"New-Api-User": user_id, "X-Panghu-Deployer-Token": deployer_token},
        )
    except urllib.error.HTTPError as exc:
        return False, f"订单状态查询失败：HTTP {exc.code}", {}
    except urllib.error.URLError as exc:
        return False, f"订单状态连接失败：{exc.reason}", {}
    except json.JSONDecodeError:
        return False, "订单状态返回内容无法解析。", {}
    except Exception as exc:
        return False, f"订单状态查询失败：{exc}", {}
    if not payload.get("success"):
        return False, str(payload.get("message") or "订单状态查询失败。"), {}
    return True, "订单状态已更新。", payload.get("data") or {}
```

- [ ] **Step 5: 更新自检**

在 `--self-test` 中增加：

```python
assert feature_enabled({"features": {"dual_state_pro": True}}, "dual_state_pro")
assert not feature_enabled({"features": {"dual_state_pro": False}}, "dual_state_pro")
assert manifest_products({"products": {"dual_state_pro": {"price_cents": 2000}}})["dual_state_pro"]["price_cents"] == 2000
```

Run:

```powershell
python C:\Users\Administrator\Documents\codex\panghu-codex-installer\src\panghu_codex_installer.py --self-test
```

Expected: self-test passed.

### Task 4: 客户端双态付费入口

**Files:**

- Modify: `C:\Users\Administrator\Documents\codex\panghu-codex-installer\src\panghu_codex_installer.py`
- Test: `--self-test` 和手动 UI 验证

- [ ] **Step 1: 拉取 manifest 后刷新双态按钮**

新增 UI 方法：

```python
def refresh_dual_state_button(self) -> None:
    manifest = self.deployer_manifest or {}
    if feature_enabled(manifest, "dual_state_pro"):
        self.dual_state_button.configure(text="已解锁：双态配置")
    else:
        self.dual_state_button.configure(text="20元解锁双态模式")
```

- [ ] **Step 2: 修改 `start_dual_state_config` 前置判断**

逻辑：

```python
if not feature_enabled(self.deployer_manifest or {}, "dual_state_pro"):
    self.start_dual_state_payment()
    return
```

只有权益已解锁才走现有双态写配置逻辑。

- [ ] **Step 3: 新增支付弹窗**

弹窗必须包含：

```text
双态模式高级版
价格：20元
用途：保留 ChatGPT 登录态，模型消耗走胖虎AI API Key
按钮：打开支付宝支付
按钮：我已支付，刷新授权
按钮：取消
```

- [ ] **Step 4: 支付成功后刷新 manifest**

支付状态为 `paid` 后：

- 调用 `fetch_deployer_manifest`
- 更新 `self.deployer_manifest`
- 调用 `refresh_dual_state_button`
- 提示“已解锁双态模式，现在可以继续配置”

- [ ] **Step 5: UI 手动验证**

验证三个状态：

```text
未购买：按钮显示 20元解锁双态模式，点击进入支付
已购买：按钮显示 已解锁：双态配置，点击直接写配置
支付后：刷新授权后按钮从未购买切换为已解锁
```

### Task 5: 商业授权识别和额度入口

**Files:**

- Modify: `C:\Users\Administrator\Documents\codex\panghu-codex-installer\src\panghu_codex_installer.py`
- Modify: `C:\Users\Administrator\Documents\codex\panghu-codex-installer\README.md`

- [ ] **Step 1: 解析 commercial_usage**

新增：

```python
def manifest_commercial_usage(manifest: dict) -> dict:
    usage = manifest.get("commercial_usage") or {}
    return usage if isinstance(usage, dict) else {}


def needs_commercial_license(manifest: dict) -> bool:
    return bool(manifest_commercial_usage(manifest).get("needs_commercial_license"))
```

- [ ] **Step 2: 普通部署前判断商业授权**

在 `start_deploy` 拉取 manifest 后：

```python
if needs_commercial_license(manifest) and not feature_enabled(manifest, "commercial_deploy"):
    self.show_commercial_license_dialog()
    return
```

- [ ] **Step 3: 商业授权弹窗**

文案：

```text
检测到该账号近期已为多台设备执行部署。如果这是代安装、批量部署或商业服务，请购买商业安装额度后继续。

个人自用不受影响。如判断有误，请联系胖虎AI客服处理。
```

按钮：

```text
购买10次额度
购买50次额度
购买200次额度
取消
```

- [ ] **Step 4: 复用订单流程**

商业授权使用同一套订单创建和查询函数，产品 ID 分别为：

```text
commercial_10
commercial_50
commercial_200
```

支付成功后刷新 manifest，确认 `commercial_deploy=true` 或商业额度充足后继续部署。

### Task 6: 黑箱保护和打包增强

**Files:**

- Modify: `C:\Users\Administrator\Documents\codex\panghu-codex-installer\scripts\build-windows-exe.ps1`
- Modify: `C:\Users\Administrator\Documents\codex\panghu-codex-installer\scripts\build-mac-app.command`
- Modify: `C:\Users\Administrator\Documents\codex\panghu-codex-installer\.github\workflows\build-mac-release.yml`
- Create: `C:\Users\Administrator\Documents\codex\panghu-codex-installer\docs\CLIENT_PROTECTION_NOTES.md`

- [ ] **Step 1: 先记录保护边界**

新增文档：

```markdown
# 客户端保护说明

本工具下载安装到客户电脑后，不能承诺绝对不可破解。保护目标是提高逆向和盗版成本，并把授权、支付、商业额度和高级功能开关放在胖虎AI服务端。

客户端不得包含支付宝密钥、服务端私钥、管理员账号、内部域名或可绕过服务端授权的本地开关。
```

- [ ] **Step 2: 打包脚本增加混淆开关**

先加可关闭的保护开关：

```text
PANGHU_PROTECT_BUILD=1
```

当开关启用时：

- 构建前复制源码到临时目录。
- 对核心模块做混淆。
- PyInstaller 从临时目录打包。
- 构建结束删除临时目录。

- [ ] **Step 3: 完整性校验**

生成 release 包时写入：

```text
build-manifest.json
```

包含：

```json
{
  "app_version": "1.0.16",
  "built_at": "2026-06-19T12:00:00+08:00",
  "files": {
    "胖虎AI多Agent一键部署工具.exe": "sha256:..."
  }
}
```

客户端启动时如果发现 manifest 存在但 hash 不匹配，提示重新下载官方包。

- [ ] **Step 4: 发布包签名规划**

Windows 暂时保留 unsigned 包，但文档记录后续需要：

```text
Windows Authenticode 代码签名证书
Apple Developer ID Application 证书
Apple notarization
```

Mac 当前未公证状态继续写清楚，不把未公证说成已签名。

### Task 7: 版本、发布和验收

**Files:**

- Modify: `C:\Users\Administrator\Documents\codex\panghu-codex-installer\src\panghu_codex_installer.py`
- Modify: `C:\Users\Administrator\Documents\codex\panghu-codex-installer\README.md`
- Modify: `C:\Users\Administrator\Documents\codex\panghu-codex-installer\docs\TECHNICAL_MAINTENANCE_MANUAL.md`
- Modify: `C:\Users\Administrator\Documents\codex\工具项目目录\PROJECTS.md`
- Modify: `C:\Users\Administrator\Documents\codex\工具项目目录\projects\多 Agent 一键配置工具.md`

- [ ] **Step 1: 升级版本**

把：

```python
APP_VERSION = "1.0.15"
```

改为：

```python
APP_VERSION = "1.0.16"
```

同步更新 self-test 里的版本断言。

- [ ] **Step 2: 本地自检**

Run:

```powershell
python C:\Users\Administrator\Documents\codex\panghu-codex-installer\src\panghu_codex_installer.py --self-test
```

Expected:

```text
self-test passed
```

- [ ] **Step 3: Windows 打包验证**

Run:

```powershell
cd C:\Users\Administrator\Documents\codex\panghu-codex-installer
scripts\build-windows-exe.bat
```

Expected:

```text
release\胖虎AI多Agent一键部署工具-Windows.zip
```

存在，并且 exe 能打开登录页。

- [ ] **Step 4: 三端发布验证**

通过 GitHub Actions 构建：

```text
Windows
Mac AppleSilicon
Mac Intel
```

三端包都上传 Release 后，再更新：

```text
https://aitokenapi.cc/deployer/latest.json
https://aitokenapi.cc/deployer/download
```

- [ ] **Step 5: 业务验收清单**

必须验证：

```text
普通一键配置未受影响
未购买用户点击双态进入20元支付
支付成功后双态模式解锁
双态模式仍保留 ChatGPT 登录态共存逻辑
未触发商业阈值的个人用户可正常部署
触发商业阈值的账号会进入商业授权购买
客户端不包含支付宝密钥
客户端不包含内部私有域名
release 三端包都存在
README、维护手册、项目登记都更新
```

---

## 六、推荐实施顺序

1. 先做服务端权益和订单接口。
2. 再改客户端双态按钮和支付弹窗。
3. 再加商业授权提醒和额度包。
4. 最后做黑箱保护、签名和发布增强。

不要先做本地黑箱再做服务端授权。因为如果授权仍在本地判断，混淆只能拖延破解，不能真正保护商业模式。

---

## 七、风险和取舍

### 风险 1：支付接入复杂度高于客户端改造

支付宝回调、订单幂等、权益写入都在胖虎AI服务端。客户端只是展示支付入口。实际开工时应把胖虎AI服务端作为第一阶段。

### 风险 2：黑箱不能绝对防破解

必须坚持服务端授权。客户端混淆、签名、完整性校验只是提高成本，不是根本防线。

### 风险 3：商业授权太重会影响传播

第一版只对明显批量部署或服务端判断为商业行为的账号弹出商业授权。普通用户和正常分享不要被卡住。

### 风险 4：不要破坏普通模式

普通一键配置是传播入口，必须保持原样。双态模式只能作为高级入口，不能替换默认部署。

---

## 八、完成定义

本升级完成时，必须同时满足：

- 普通一键配置继续可用。
- 双态模式变成 20 元高级功能。
- 支付使用胖虎AI服务端已有支付宝官方配置和回调。
- 支付成功后由服务端权益解锁，不靠本地标记。
- 商业代安装有购买额度入口。
- 客户端关键权益判断服务端化。
- 发布包不明文分发核心 Python 源码。
- 文档、维护手册、项目登记和三端发布包同步更新。
