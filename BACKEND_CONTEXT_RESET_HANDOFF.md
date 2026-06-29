# 后端上下文重置交接说明

生成时间：2026-06-26

适用对象：
- 主控窗口：审查并收口当前后端窗口已经落到主树的改动。
- 新后端任务窗口：从本文件继续，不继承当前窗口污染上下文。

## 1. 当前仓库状态

真实项目主目录：

`C:\Users\Administrator\Documents\codex\panghu-codex-installer`

当前 `git rev-parse --show-toplevel` 已确认是：

`C:/Users/Administrator/Documents/codex/panghu-codex-installer`

当前分支：

`main`

重要说明：

- 本窗口后期已经直接在主树改动，不再是独立 backend worktree 的孤立成果。
- 主控不要再从旧 backend worktree 反向覆盖主目录，避免把前端窗口或本窗口后续改动覆盖掉。
- 主控要做的是在当前主树审查、分组、暂存和提交这些改动。
- 未跟踪目录 `scratch/` 默认不应纳入提交，除非主控确认里面有必须保留的审计材料。

## 2. 本窗口已改动范围

当前工作树主要包含这些已修改文件：

- `src/panghu_codex_installer.py`
- `src/ui/index.html`
- `src/commercial_api.py`
- `src/commercial_backend_contract.py`
- `tests/test_installer_backend.py`
- `tests/test_commercial_api.py`
- `tests/test_commercial_backend_contract.py`
- `tests/test_commercial_backend_contract_docs.py`
- `tests/test_panghu_commercial_manifest.py`
- `docs/PRODUCT_MANUAL_SINGLE_SOURCE_OF_TRUTH.md`
- `docs/TECHNICAL_MAINTENANCE_MANUAL.md`
- `docs/COMMERCIAL_BACKEND_API_CONTRACT.md`
- `ACCEPTANCE.md`
- `README.md`
- `RUNBOOK.md`
- `SAFETY.md`
- `PLAN.md`
- `TASK_GRAPH.md`
- `FINAL_REPORT.md`
- 多个已有 handoff 文档和 `outputs/panghu-installer-*.png` 截图

当前未跟踪项：

- `outputs/ui-all-20260626-correct/`
- `outputs/ui-all-20260626/`
- `outputs/ui-review-20260626-round2/`
- `scratch/`

主控合并建议：

- 源码、测试、权威文档必须一起审查，避免代码和手册口径不一致。
- `outputs/` 截图是否提交由主控决定；它们是验收证据，但不是运行必需文件。
- `scratch/` 默认不要提交。
- 不要删除 `docs/superpowers/`、`release/`、Windows/Mac 客户 zip、exe/app 软件本体。

## 3. 已落地的后端/业务功能

登录门禁与账号保存：

- 未登录只暴露登录页，主界面、Agent 配置、商业权益、状态矩阵继续在登录后展示。
- 增加买家账号本地保存框架：账号邮箱列表、记住密码、自动登录、删除已保存账号。
- 密码只走本机保护存储字段，UI 初始状态不回传解密密码。
- 登录信息和运行 profile 分离；删除保存账号会同步清理相关登录提示/会话痕迹。
- 主界面设置入口保留：切换账号、切换主题、退出当前账号；不再做“退出软件”按钮。

胖虎AI内置浏览器：

- 胖虎AI首页/控制台/API Key/充值购买/推广返佣入口改为优先走软件内置 WebView/内置浏览器。
- 对 `aitokenapi.cc` 白名单客户页面，若当前环境缺少 pywebview 或内置窗口打开失败，会返回 `embedded_webview_blocked`，不再自动跳系统浏览器。
- 外部非白名单链接仍可按普通外部链接处理。
- 文档已同步说明：不能把系统浏览器 fallback 包装成“已完全内嵌”。

Agent 矩阵与 Gemini/agy：

- 固定 Agent 扩展为：Codex、ClaudeCode/CC、OpenClaw、Hermes、Gemini/agy。
- 每个 Agent 维持五维状态：安装状态、启动状态、对话状态、验收状态、交付状态。
- 新增 Gemini/agy 安装/官方入口；配置功能明确为“开发中/待开发”，不得显示完整交付。
- 未真实打通的 Agent 不再包装成完整付费交付。

代理中心：

- 已按新产品口径调整：代理中心不是登录前入口，也不等同于胖虎AI网站推广返佣页。
- 代理中心作为买家登录后的独立服务端权益模块，范围包括 token 返佣、下游客户激活返佣、付费安装 Agent 返佣等。
- 客户端只展示服务端返回的代理身份、下游、佣金和状态，不在本地硬编码等级、比例、金额或上架状态。

增值业务与 Communication Software Link Agent：

- 删除“带配置服务/代配置服务”多余入口。
- 保留 Plus 代充值、国外手机卡、短信接码等基础框架，状态以服务端为准。
- 新增 Communication Software Link Agent 后端合同、请求分发、订单/会话/验收/禁用链路框架。
- Communication Software Link Agent 是独立增值服务，不绑定当前基础 Agent 安装流程。

商业后端合同：

- 增加/同步商业账号、代理中心、移动控制、订单、权益、佣金和状态字段合同。
- 商业权益、次数、有效期、设备数、价格、返佣比例、上架状态都要求来自服务端或配置，不允许客户端硬编码。
- 所有请求继续以公共域名 `https://aitokenapi.cc` 为准。

安全与审计：

- API Key 不输出到日志。
- 不保存第三方账号密码、部署授权 token、订单号、权益 ID、配置会话 ID 到 `profile.json`。
- 文档已删除旧“代理登录态”口径，保留买家自己的胖虎AI会话持久化目标。
- 未通过功能验收矩阵不得包装成完整交付。

## 4. 不能夸大的未完成/阻塞

这些点必须交给新后端窗口继续，不得对主控或用户说“已完全完成”：

1. 内置浏览器真实免登录仍需实机验证。
   - 当前已改为内置 WebView 优先和系统浏览器 fallback 阻断。
   - 但胖虎AI网站的真实 SSO/会话桥接还要用真实登录链路验证。
   - 如果站点会话依赖 HttpOnly Cookie，仅靠前端 JS 注入无法完整桥接，需要服务端 SSO 或 pywebview profile 持久会话方案。

2. Gemini/agy 只做安装入口和官方入口。
   - 配置按钮必须保持灰色/开发中。
   - 不得写成已经接入用户 API 或完整验收。

3. ClaudeCode/CC、OpenClaw、Hermes 的真实最小中文对话和功能验收仍要按官方文档/CLI help 继续核验。
   - 本地残留配置不能当事实。
   - 接入官方工具时优先查官方文档、官方 GitHub/npm/CLI help。

4. 代理中心客户端框架和服务端合同已做，但真实服务端字段和数据仍需 `aitokenapi.cc` 对接确认。

5. Communication Software Link Agent 目前是后端合同、客户端请求和 UI 入口框架。
   - 真实供应商/接码/移动端控制服务未在本窗口完整打通。
   - 不能作为完整交付功能宣传。

6. 未跟踪截图目录和 `scratch/` 需要主控决定是否保留，不要自动提交临时材料。

## 5. 已运行验证

已通过：

```powershell
python -m py_compile src\panghu_codex_installer.py
```

已通过：

```powershell
node -e "const fs=require('fs'); const s=fs.readFileSync('src/ui/index.html','utf8'); const m=s.match(/<script>([\s\S]*)<\/script>/); if(!m) throw new Error('script not found'); new Function(m[1]); console.log('ui script syntax ok');"
```

已通过：

```powershell
python src\panghu_codex_installer.py --self-test
```

结果：

`UI self-test OK`

已通过：

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

结果：

`Ran 246 tests ... OK`

明确未运行：

```powershell
python scripts\commercial_release_acceptance.py --with-exe-self-test --deep-scan --json
```

原因：用户明确禁止运行该深度商业发布验收命令。

## 6. 主控合并注意事项

主控处理顺序建议：

1. 先读本文件、`git status --short`、`git diff --stat`。
2. 审查源码/测试/权威文档是否同批进入提交。
3. 排除 `scratch/`，再决定是否纳入 `outputs/ui-*` 截图目录。
4. 不要从任何旧 backend worktree 覆盖当前主树。
5. 不要碰生产服务器、数据库、GitHub Release、下载页、`latest.json`。
6. 不要删除 release 包、客户 zip、exe/app、本体文件和 `docs/superpowers/`。
7. 提交说明里必须标明：Gemini/agy 配置待开发；Communication Software Link Agent、代理中心、内置浏览器 SSO 仍需真实服务端/实机验证。

## 7. 新后端窗口启动提示

请把下面这段作为新后端任务窗口的启动说明：

```text
你是“胖虎AI”的新后端执行窗口。不要进入 goal 模式，不要调用 create_goal。

真实项目主目录：
C:\Users\Administrator\Documents\codex\panghu-codex-installer

你必须先读：
1. C:\Users\Administrator\.codex\进化.md
2. C:\Users\Administrator\Documents\codex\panghu-codex-installer\BACKEND_CONTEXT_RESET_HANDOFF.md
3. C:\Users\Administrator\Documents\codex\panghu-codex-installer\docs\TECHNICAL_MAINTENANCE_MANUAL.md
4. C:\Users\Administrator\Documents\codex\panghu-codex-installer\docs\PRODUCT_MANUAL_SINGLE_SOURCE_OF_TRUTH.md
5. C:\Users\Administrator\Documents\codex\panghu-codex-installer\docs\COMMERCIAL_BACKEND_API_CONTRACT.md
6. C:\Users\Administrator\Documents\codex\panghu-codex-installer\CODEX_THREE_MODES_HANDOFF.md
7. 当前源码、测试、git status

当前主树已经包含上一后端窗口的大量改动，请不要从旧 backend worktree 覆盖主树。你的任务是在当前主树继续排查和补齐后端真实链路，不做前端整体视觉重设计，不碰生产服务器、数据库、GitHub Release、下载页、latest.json，不运行被禁止的商业深度发布验收命令。

重点继续：
- 核验登录门禁、记住密码、自动登录、账号下拉删除、退出当前账号、切换账号是否和产品文档一致。
- 核验胖虎AI内置浏览器：必须是软件内置浏览器；客户页面缺 pywebview 或打开失败时应阻断并标记未完成，不得自动跳系统浏览器；真实免登录/SSO 需要实机验证或补服务端桥接方案。
- 核验 Agent 五维矩阵：Codex、ClaudeCode/CC、OpenClaw、Hermes、Gemini/agy；Gemini/agy 只保留安装入口，配置必须开发中。
- 继续按官方文档/官方 GitHub/npm/CLI help 检查 ClaudeCode/CC、OpenClaw、Hermes、Gemini/agy，不要用本机残留配置当事实。
- 核验代理中心是登录后的独立服务端权益模块，覆盖 token 返佣、下游激活返佣、付费安装 Agent 返佣，不等同于胖虎AI网站推广返佣页。
- 核验 Communication Software Link Agent 的后端合同、订单、会话、验收、禁用链路，不能包装成已完整打通。
- 继续清理旧“登录前代理模式/买家模式分流”和旧“代理登录态”残留。
- 所有商业权益、次数、有效期、设备数、价格、返佣比例、上架状态必须来自服务端或配置，不得硬编码。
- API Key 不输出日志；不保存第三方账号密码、部署授权 token、订单号、权益 ID、配置会话 ID 到 profile.json。

建议先运行：
git status --short
git diff --stat
python -m py_compile src\panghu_codex_installer.py
python src\panghu_codex_installer.py --self-test
python -m unittest discover -s tests -p "test_*.py"

交付时必须说明：
- 修改了哪些文件
- 修了哪些后端功能
- 哪些 Agent 链路真实打通，哪些仍是未完成/阻塞
- 运行了哪些验证命令和结果
- 给主控的合并注意事项
```
