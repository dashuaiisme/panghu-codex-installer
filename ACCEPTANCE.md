# 产品验收标准

最后更新：2026-06-25

## 0. 本文件职责

本文件只负责 Definition of Done：

- 什么叫通过
- 什么叫未通过
- 进入下一阶段前必须满足什么

本文件不负责记录当前状态、历史过程或执行方法。

## 1. A 级：代码健康验收

必须通过：

- `python -m py_compile src\panghu_codex_installer.py scripts\agent_delivery_acceptance.py scripts\customer_web_entry_acceptance.py`
- `python src\panghu_codex_installer.py --self-test`
- `python -m unittest discover -s tests -p "test_*.py"`

说明：

- A 级通过只代表代码健康通过，不代表产品可交付。

## 2. B 级：客户界面验收

必须具备截图证据：

- 未登录登录闸口
- 登录后配置Agent模块
- 胖虎AI网站模块
- 增值业务模块
- 开发中模块
- 普通窗口
- 全屏窗口

必须满足：

- 登录前不暴露完整控制台
- 顶部、左侧、中间、右侧、底部结构稳定
- 左侧只展示当前模块子导航
- 中间区域不堆满所有步骤
- 右侧账号 / 权益 / 四 Agent 五维状态清晰

## 3. C 级：胖虎AI网站入口验收

必须逐项验证：

- 注册页面入口正确
- 邀请码 / 注册入口正确
- 创建 API Key 页面入口正确
- 充值购买页面入口正确
- 代理中心入口正确
- `pywebview` 可用时优先内置打开
- `pywebview` 不可用时明确回退外部浏览器

说明：

- 入口和依赖前提通过，不等于真实业务闭环通过。

## 4. D 级：Agent 交付验收

固定 Agent：

- Codex
- ClaudeCode（CC）
- OpenClaw
- Hermes

每个 Agent 必须分别验收五维状态：

- 安装状态
- 启动状态
- 对话状态
- 验收状态
- 交付状态

最低通过条件：

- 官方 CLI 或客户端入口真实可用
- 配置写入目标文件正确
- 重开或启动检查通过
- 最小中文对话返回有效内容
- 功能验收矩阵记录通过

未完成真实对话验收前，不得标记为完整付费交付。

Codex 额外必须验收三种配置模式：

- 普通模式：写入胖虎AI中转站 provider 和 API Key，消耗胖虎AI额度。
- 双态模式：保留 ChatGPT 登录态，写入胖虎AI中转站 token，消耗胖虎AI额度。
- 官方直登：写入官方 `openai` provider，保留 ChatGPT 登录态，不写胖虎AI中转站 Key，消耗客户自己的 ChatGPT 账号额度。

Codex 模式切换必须验收：

- 切换前已保存当前配置快照。
- `auth.json` 中已有 ChatGPT 登录态不会被普通/双态/官方直登来回切换误删。
- 旧快照里的旧 API Key 不会被恢复到当前主配置。
- 任何模式写入后，都提示客户完全退出 Codex 再重新打开。

## 5. E 级：安全与商业边界验收

必须满足：

- API Key 不输出到日志
- 不保存代理登录态
- 代理登录态不写入 `profile.json`
- 不保存可恢复买家登录 token，重启后必须重新登录胖虎AI账号
- 所有客户默认请求走 `https://aitokenapi.cc`
- 不硬编码价格、次数、有效期、设备数、返佣比例、商品上架状态
- 未通过功能验收矩阵不得扣次或包装成交付完成
- 胖虎AI账号不能被写成 Codex 登录账号。
- 官方直登不应创建胖虎AI商业配置会话，不应扣胖虎AI配置次数。

## 6. F 级：发布前验收

只有 A 到 E 全部通过，才允许进入：

- Windows 打包
- Mac 打包
- GitHub Release
- 下载页和 `latest.json` 更新

当前是否允许进入 F 级，不在本文件判断，由 `FINAL_REPORT.md` 判断。
