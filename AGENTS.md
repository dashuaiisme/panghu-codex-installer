# 胖虎AI客户端

Codex / Agent 协作规则

最后更新：2026-07-03

## 1. 项目身份

- 用户可见入口 / 本地 git root：`C:\Users\Administrator\Documents\codex\胖虎AI客户端`
- GitHub 远程仓库：`https://github.com/dashuaiisme/panghu-ai-client`

`panghu-ai-client` 是 GitHub 远程仓库 slug；本地项目名称和本地根目录仍统一为 `胖虎AI客户端`。

## 2. 文档权威顺序（唯一维护处）

本顺序只在本文件维护，其他文档一律引用本文件，不得另写一份：

1. Agent 入口与本机规则：本文件、`C:\Users\Administrator\.codex\进化.md`
2. 仓库入口摘要：`README.md`
3. 产品权威：`docs/PRODUCT_MANUAL_SINGLE_SOURCE_OF_TRUTH.md`
4. 技术维护权威：`docs/TECHNICAL_MAINTENANCE_MANUAL.md`
5. 商业服务端合同：`docs/COMMERCIAL_BACKEND_API_CONTRACT.md`
6. 产品摘要与蓝图：`PRODUCT.md`
7. 架构与工程边界：`ARCHITECTURE.md`
8. 验收标准：`ACCEPTANCE.md`；验证记录：`TESTING.md`
9. 运行与发布：`RUNBOOK.md`；安全边界：`SECURITY.md`
10. 跨项目集成：`INTEGRATION.md`
11. 当前真实状态、任务与阻塞：`FINAL_REPORT.md`
12. 交接与工程盘点：`HANDOFF.md`

历史废弃材料、过期 handoff、历史截图和聊天上下文不能替代长期权威文档。

## 3. 开工前必读

开始任何严肃修改前先读：

1. `C:\Users\Administrator\.codex\进化.md`
2. 本文件
3. `README.md`
4. `docs/PRODUCT_MANUAL_SINGLE_SOURCE_OF_TRUTH.md`
5. `docs/TECHNICAL_MAINTENANCE_MANUAL.md`
6. `PRODUCT.md`
7. `ACCEPTANCE.md`
8. `RUNBOOK.md`
9. `FINAL_REPORT.md`

涉及服务端合同时，再读 `docs/COMMERCIAL_BACKEND_API_CONTRACT.md`。
涉及跨项目集成或产品树主控时，再读 `INTEGRATION.md` 和 `HANDOFF.md`。

## 4. 执行边界

- 产品结构、客户可见规则、交付边界：以 `docs/PRODUCT_MANUAL_SINGLE_SOURCE_OF_TRUTH.md` 为准。
- 技术维护、接口、构建、发布、脚本：以 `docs/TECHNICAL_MAINTENANCE_MANUAL.md` 为准。
- 当前运行和验证命令：以 `RUNBOOK.md` 和 `TESTING.md` 为准；验证数字只在 `TESTING.md` 维护。
- 当前真实可交付状态、任务和阻塞：以 `FINAL_REPORT.md` 为准。
- 工程化盘点、文件分类和整理边界：以 `HANDOFF.md` 为准。

## 5. 禁止事项

- 不要 `git reset --hard`、`git checkout --`、`git clean` 或回退他人改动。
- 当前仓库经常有其他窗口留下的未提交工作；修改前必须先看 `git status --short`。
- 删除、移动、重命名、归档文件前，必须先给出清单并获得用户明确确认。
- 不要编辑 `release/`、`build/`、`.venv/`、`.pytest_cache/` 这类生成目录，除非任务明确进入打包或清理阶段。
- 不要把本地截图、单元测试或离线 mock 验收写成真实客户闭环完成。

## 6. 前端规则

正式客户 UI 入口是 `src/ui/index.html`。必须保留：

- `#loginGate`
- `#consoleLayout`
- `window.updatePythonState(data)`
- `window.appendPythonLog(line)`
- `window.renderLogs()`

登录前只能显示登录闸口；登录后一级模块必须覆盖：

- 配置Agent
- 胖虎AI网站
- 增值业务
- 代理中心

客户端不得本地硬编码商品价格、购买次数、有效期、设备数、返佣比例、返佣金额、代理等级、下游客户数、结算金额、商品上架状态或真实交付成功。

## 7. 发布规则

当前普通开发和源码整理不等于发布。进入发布前必须先确认：

- `ACCEPTANCE.md` 允许进入发布前阶段。
- `commercial_release_acceptance.py --json` 不再只是 WARN。
- 三端客户包新鲜且命名正确。
- 商业清单生产公钥已注入。
- GitHub Release、下载页和 `latest.json` 的操作计划已明确。

完整发布前条件和顺序见 `RUNBOOK.md`。
