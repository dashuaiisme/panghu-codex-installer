# 胖虎AI客户端 QA 收口报告 2026-06-28 R1

## 身份与范围

- RID：R3-QA-VISIBLE-001
- 角色：测试/交付经理
- 用户入口：`C:\Users\Administrator\Documents\codex\胖虎AI客户端`
- 真实 git root：`C:\Users\Administrator\Documents\codex\panghu-codex-installer`
- 范围：本地源码、后端合同、WebView 桥接、客户 Web 入口验收
- 禁止范围：源码/测试/文档修改、删除/移动/暂存/提交、发布包、生产服务器、数据库、支付、密钥

## 验收结果

| 验收项 | 命令 | 结果 |
| --- | --- | --- |
| 后端/桥接 focused 测试 | `python -m pytest tests\test_panghu_commercial_manifest.py tests\test_installer_backend.py -q` | 83 passed，11 subtests passed |
| 商业流本地合同验收 | `python scripts\commercial_flow_acceptance.py --json` | `status=PASS` |
| UI 自检 | `python src\panghu_codex_installer.py --self-test` | `UI self-test OK` |
| 全量 unittest | `python -m unittest discover -s tests -p "test_*.py"` | 300 tests OK |
| 客户 Web 入口验收 | `.\.venv\Scripts\python.exe scripts\customer_web_entry_acceptance.py` | `web_entry_status=ready`，`blocking_gaps=[]` |
| JS/Python 桥接静态检查 | AST + regex 脚本 | `JS calls not in WebviewApi: [none]`，WebviewApi callable count 38 |

## 本地交付判断

- 当前源码达到本地可修复交付基线。
- 未提交改动很多不等于后端未完成；QA 看到的问题是工作树混有源码、测试、文档、发布脚本、截图产物、依赖和临时目录。
- 本轮 QA 没有修改源码、测试、产品文档、发布脚本，也没有删除、移动、暂存、提交或发布。

## 未验证项

- 真实服务端、真实数据库、真实支付回调未验证。
- 真实 Agent Runtime Adapter 未验证。
- 真实 agent_center 服务端快照未验证。
- 真实客户账号/实机完整交付链路未验证。
- 三端发布包、签名、GitHub Release、下载页和 `latest.json` 未验证。
- `commercial_flow_acceptance.py` 输出仍明确包含 `offline_guarded` / `mock_guarded`，不能写成生产闭环。

## 下一步建议

1. 由版本治理经理把工作树拆成提交候选、暂缓发布、需用户确认清理、缓存/临时产物。
2. 在用户确认前，不删除 `node_modules/`、`scratch/`、未跟踪 `outputs/`。
3. 若要进入真实生产闭环，需另派服务端/生产负责人处理数据库、支付、Runtime Adapter、发布包和实机验收。
