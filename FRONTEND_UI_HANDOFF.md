# 胖虎AI多 Agent 一键部署工具——前端视觉与交互融合交接说明

本文档专为**主控 Agent (Codex)** 编写，用于指导如何将已完成的前端 UI 样式与交互布局安全地合并至主线源码中，确保 Python Tkinter 客户端在视觉表现上与 [enterprise-light.html](file:///C:/Users/Administrator/Documents/codex/2026-06-23/panghu-installer-ui-style-options/outputs/panghu-installer-style-enterprise-light.html) 设计稿高度一致，防止合并出现偏差。

---

## 📌 核心结论与免除偏差准则

> [!IMPORTANT]
> **主控 Codex 请注意**：
> 1. **无需手动将 HTML 翻译为 Python**：吉米（Gemini）已将 HTML 中的所有边距、色彩、圆角和页面切换逻辑直接用 Python Tkinter 语言重写，并应用在 [panghu_codex_installer.py](file:///C:/Users/Administrator/Documents/codex/panghu-codex-installer/src/panghu_codex_installer.py) 中。
> 2. **主控融合动作**：主控只需要直接合并工作区中的 `src/panghu_codex_installer.py` 物理文件，千万不要尝试根据 HTML 自行重构 Python UI，否则会导致严重的界面对齐偏差。
> 3. **验证口径**：运行 `python src/panghu_codex_installer.py --self-test` 返回 `UI self-test OK` 即为逻辑融合成功。

---

## 🎨 视觉规范对齐矩阵（Tkinter 源码 vs HTML 规范）

在 [panghu_codex_installer.py](file:///C:/Users/Administrator/Documents/codex/panghu-codex-installer/src/panghu_codex_installer.py) 中，已完全实现以下苹果风钛金白浅色控制台视觉规范：

### 1. 配色系统 (Color Palette)
在 Python 源码第 157-180 行已定义统一色值，禁止漂移：
* `APP_BG = "#e8e8ed"` （窗口底色，低饱和灰白）
* `SURFACE_BG = "#f5f5f7"` （工作区背景）
* `SIDEBAR_BG = "#ebebec"` （左侧导航栏背景）
* `CARD_BG = "#ffffff"` （内容卡片纯白底）
* `PRIMARY = "#0071e3"` （苹果商业蓝，主操作及选中态）
* `BORDER = "#d2d2d7"` （面板及输入框标准边框线）
* `SUCCESS = "#1a7f37"` （成功绿）

### 2. 布局架构 (Layout Structure)
登录后的客户端界面被严格划分为六个网格区块，以 `grid` 稳定布局：
1. **TopBar (顶部栏)**：高 `50px`，左侧含胖虎头像及版本标识，右侧为脱敏账号与剩余额度。
2. **一级模块导航 (Module Nav)**：位于 TopBar 下方，由“配置Agent、胖虎AI网站、增值业务、代理中心”组成，具有清晰的选中态下划线。
3. **左侧子导航 (Sidebar Nav)**：宽度 `240px`，动态监听一级模块的切换。
4. **中间主内容区 (Center Container)**：配置 Agent 时呈单步骤卡片，切换至其他模块时渲染为 WebView 浏览器直达提示卡。
5. **右侧状态与商业矩阵 (Right Panel)**：宽度 `300px`，用于展示账号状态和固定的 4 Agent 5维验收矩阵。
6. **底部执行追踪日志 (Execution Log)**：精简设计，以黑底白字小字体显示，用于开发人员排障。

---

## 📂 关键代码块合并位置与比对

### A. 一级模块定义与子导航切换
在 `src/panghu_codex_installer.py` 中，定义了 `TOP_MODULES` 常量，取消了登录前分流：
```python
MODULE_AGENT = "agent"
MODULE_SITE = "site"
MODULE_VALUE_ADDED = "value_added"
MODULE_AGENT_CENTER = "agent_center"

TOP_MODULES = [
    (MODULE_AGENT, "配置Agent", "部署与验证多Agent"),
    (MODULE_SITE, "胖虎AI网站", "内置控制台与在线购买"),
    (MODULE_VALUE_ADDED, "增值业务", "云手机与接码服务"),
    (MODULE_AGENT_CENTER, "代理中心", "代理总览及收益管理"),
]
```
主控合并时请确保 `TOP_MODULES` 保持为以上 4 个，顺序与文案不得更改。

### B. 子导航状态圆圈渲染 (Canvas-based Sidebar Dot)
为解决 HTML 中圆角导航点的对齐，在 Python 中使用 `tk.Canvas` 实现高质量的自绘圆点（`_render_agent_step_nav` 中）：
```python
fill = PRIMARY if active else SUCCESS if dot_color == SUCCESS else WAIT_BG
outline = PRIMARY if active else SUCCESS if dot_color == SUCCESS else WAIT_BORDER
text_color = "#ffffff" if active or dot_color == SUCCESS else MUTED if locked else SECONDARY

dot.itemconfigure("circle", fill=fill, outline=outline)
dot.itemconfigure("label", fill=text_color, text=str(idx))
```
此渲染规避了原生 Tkinter 圆角锯齿问题，请保留此 Canvas 重绘逻辑。

---

## 🚀 主控 Codex 执行合并的命令顺序

请主控 Codex 在其终端窗口中完全遵循以下指令执行：

1. **核对修改**：
   ```powershell
   git status
   ```
   确保只有 `src/panghu_codex_installer.py` 被修改，没有不相关的代码噪音。

2. **运行编译自检**：
   ```powershell
   python -m py_compile src/panghu_codex_installer.py
   python src/panghu_codex_installer.py --self-test
   ```
   若输出 `UI self-test OK` 则表明前端代码结构在 Python 层面已完全融合无误。

3. **运行合约测试**：
   ```powershell
   python -m unittest discover -s tests -p "test_*.py"
   ```
   确保 219 个商业账本和 Manifest 合约测试 100% 通过（OK）。

4. **正式融合源码树**：
   ```powershell
   git add src/panghu_codex_installer.py
   git commit -m "feat: merge polished enterprise light UI and module nav"
   ```

请用户将此说明直接发给主控 Codex，Codex 读取该说明后，即可完全消除合并偏差。
