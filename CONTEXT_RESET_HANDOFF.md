# 客户端与后端对齐重构阶段交接说明 (CONTEXT_RESET_HANDOFF)

**生成时间**：2026-06-26
**当前仓库主目录**：`C:\Users\Administrator\Documents\codex\panghu-codex-installer`
**当前分支**：`main` (比 `origin/main` 领先 3 个 commit，当前工作区是干净的，所有更改均已提交)

---

## 1. 本轮已完全落地的重构与修复

### 🎨 前端 UI 与视觉重构 (对齐 Apple HIG 极简规范)
* **登录门禁物理隔离**：未登录状态下彻底隐藏顶部导航、子导航、右侧面板、日志及 Trace 记录，仅暴露登录、自动登录/记住密码及注册入口。
* **11步配置 Agent 子导航**：扩展新增了“连接通讯软件”与“连接通讯软件交付验收”两个独立子步骤，并完美修正了进度条及 steps 状态，登录动作不占用配置步骤（登录作为前置门禁，登录后初始步骤为 step 1）。
* **代理中心 (8项子导航)**：增加了招商介绍 (`agent_join`) 子导航，且在服务端无返回值时均以“服务端接入中/占位”显示，决不写死佣金或代理等级。
* **设置菜单精简**：TopBar 设置菜单已精简为仅包含：**切换账号**、**切换主题**、**退出当前账号** 三个选项。
* **布局与冲突修复**：修复并清理了 `src/ui/index.html` 中的重复 `.btn-sm` CSS 规则（删除了 Line 1667 处冗余且带 `!important` 的冲突定义，统一使用 Line 1283 的标准高度）。
* **内置 WebView 连通与阻断**：充值、API Key、返佣等入口在内置 WebView 容器中打开；若缺失 `pywebview` 依赖时会触发“**未完成内嵌闭环**”明确阻断弹窗，不会自动跳出到系统浏览器。

### ⚙️ 后端逻辑与安全审计 (src/panghu_codex_installer.py)
* **自动登录与解密**：自动登录机制与记住密码严格绑定，无本机 Windows DPAPI 加密密码时，启动时不触发自动登录，且脱敏排除了所有模糊日志。
* **安全审计**：彻底屏蔽了 API Key 输出至日志，不保存第三方 key/部署 token/订单 ID/会话 ID 到 `profile.json` 中。
* **级联清除**：在删除历史保存账号时，同步清理该账号相关的本地加密密码、自动登录标记、记住密码标志以及 Web Profile 缓存和 Cookie。
* **Codex 三模式切换**：普通模式、双态模式和官方直登模式切换时，增加了基于 `~/.codex/panghu_modes/` 的模式快照机制，完美避免历史过期 API Key 被恢复。

---

## 2. 自动化与构建验证结果

1. **编译检查**：
   ```powershell
   python -m py_compile src\panghu_codex_installer.py scripts\agent_delivery_acceptance.py scripts\customer_web_entry_acceptance.py
   ```
   👉 **编译通过，无任何语法或解析错误。**

2. **UI 自检**：
   ```powershell
   python src\panghu_codex_installer.py --self-test
   ```
   👉 **输出：`UI self-test OK`**

3. **单元测试 (248 个用例)**：
   ```powershell
   pytest
   ```
   👉 **248/248 tests passed (100% PASS)。**

4. **客户端打包**：
   * 成功运行 `scripts\build-windows-exe.bat`（调用 PyInstaller 编译）。
   * 历史旧名生成可执行程序：`release\胖虎AI多Agent一键部署工具\胖虎AI多Agent一键部署工具.exe`
   * 历史旧名生成分发压缩包：`release\胖虎AI多Agent一键部署工具-Windows.zip` (已完成包内 exe 完整性与文件数校验)。当前产品名已改为“胖虎AI”，新一轮客户包需重新构建后才使用新包名。

5. **真机界面截图**：
   已通过 Headless Edge 浏览器真实渲染并捕获 **12 张全量核心场景截图**（包括登录、API key 填写、环境检测、模式选择、部署日志、代理/增值模块、亮/暗/钢铁主题及不同窗口尺寸布局），截图已放入以下图册：
   * 详细图册可见：[all_views_gallery.md](file:///C:/Users/Administrator/.gemini/antigravity/brain/bef0c7b3-c0c3-475d-be5d-6fd79464f2e7/all_views_gallery.md)
   * 交付验收报告：[walkthrough.md](file:///C:/Users/Administrator/.gemini/antigravity/brain/bef0c7b3-c0c3-475d-be5d-6fd79464f2e7/walkthrough.md)

---

## 3. 下一步工作建议与未完成项

由于真实环境依赖以及离线限制，以下功能在当前仓库以 Mock/合同守卫形态存在，建议在全新窗口中继续验证：
1. **内置浏览器 SSO 与真实免密登录**：需要实机使用真实买家会话以及 HttpOnly Cookie 方案进行验证。
2. **非 Codex Agent 的真实中文对话与矩阵状态**：
   * **ClaudeCode / OpenClaw / Hermes** 需使用真实客户 API Key 在对应运行环境下测试最小中文对话输出，确保功能验收矩阵能够记录通过。
   * **Gemini / agy** 模块当前仅包含官方下载与打开入口，其完整的配置部署与环境检测链路待后续版本开发。
3. **代理中心服务端对接**：需对接并验证真实服务端（`aitokenapi.cc`）返回的数据归因、返佣账本明细以及提现状态机，替换目前的离线契约。
4. **Communication Software Link Agent**：需对接真实平台通道消息 ID、消息中转 Adapter 以及防套利防卡扣费扣次逻辑。

---

## 4. 新窗口/新 Agent 启动引导指令

> [!TIP]
> 后面开启新窗口/新 Agent 任务时，请直接发送以下指令给它以快速载入上下文：

```text
你是“胖虎AI”的新执行窗口。当前项目的重构与本地构建已经完全完成且 248 项测试全数通过。
请不要进入 goal 模式，不要调用 create_goal。

你的真实项目主目录为：
C:\Users\Administrator\Documents\codex\panghu-codex-installer

请首先阅读以下关键交接与规范文件：
1. C:\Users\Administrator\Documents\codex\panghu-codex-installer\CONTEXT_RESET_HANDOFF.md (本文件)
2. C:\Users\Administrator\Documents\codex\panghu-codex-installer\docs\PRODUCT_MANUAL_SINGLE_SOURCE_OF_TRUTH.md
3. C:\Users\Administrator\Documents\codex\panghu-codex-installer\docs\TECHNICAL_MAINTENANCE_MANUAL.md
4. C:\Users\Administrator\Documents\codex\panghu-codex-installer\docs\COMMERCIAL_BACKEND_API_CONTRACT.md
5. C:\Users\Administrator\Documents\codex\panghu-codex-installer\ACCEPTANCE.md

启动前建议立即在工作区运行以核对环境状态：
git status
python -m py_compile src\panghu_codex_installer.py
python src\panghu_codex_installer.py --self-test
pytest
```
