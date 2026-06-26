# Stage Packet

To: Claude Code / Hermes
From: Codex
Shared Hub:
- C:\Users\Administrator\.codex-claude-code-hermes-hub\

## One objective for this round
对 `C:\Users\Administrator\Documents\codex\panghu-codex-installer` 当前 Tkinter 前端主线改动做只读评审，重点看：
1. 顶部四个一级模块现在是否符合最新产品架构；
2. 胖虎AI网站 / 增值业务 / 代理中心 的左侧子导航与目标页面映射是否清晰；
3. 非 Agent 主工作区是否仍然显得拥挤、混乱，是否还有明显信息架构问题；
4. 是否还有和产品手册冲突的代码或文案；
5. 是否还有会导致用户误解“本地已闭环网站购买/代理功能”的风险文案。

## Required reads
- C:\Users\Administrator\.codex\进化.md
- C:\Users\Administrator\Documents\codex\panghu-codex-installer\docs\PRODUCT_MANUAL_SINGLE_SOURCE_OF_TRUTH.md
- C:\Users\Administrator\Documents\codex\panghu-codex-installer\docs\TECHNICAL_MAINTENANCE_MANUAL.md
- C:\Users\Administrator\Documents\codex\panghu-codex-installer\src\panghu_codex_installer.py

## Context
本轮已经完成这些真实改动：
- 顶部一级模块固定为：配置Agent / 胖虎AI网站 / 增值业务 / 代理中心
- 胖虎AI网站模块左侧改成：控制台 / 创建 API Key / 充值购买 / 推广返佣
- 代理中心模块左侧改成：代理总览 / 工具代理后端 / 代理规则
- 非 Agent 主工作区新增“客服指引 + 网站入口页”结构，而不是只有说明卡
- 新增真实截图脚本：C:\Users\Administrator\Documents\codex\panghu-codex-installer\outputs\capture_ui_preview.py
- 当前已通过：
  - python -m py_compile src\panghu_codex_installer.py
  - python src\panghu_codex_installer.py --self-test
  - python -m unittest discover -s tests -p "test_*.py"

## Constraints
- 只读评审，不改文件。
- 不碰生产服务器、数据库、GitHub Release、download、latest.json。
- 不跑重型发布验收。
- 不讨论 PanghuAI 主站其它仓库，只看本项目。

## Expected output
请按下面结构输出：
Verdict: accept_with_minor_notes | revise
P0:
- ...
P1:
- ...
P2:
- ...
Accepted strengths:
- ...
Residual risks:
- ...

请尽量引用具体文件和代码区域，不要泛泛而谈。
