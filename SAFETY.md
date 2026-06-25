# 安全与边界

最后更新：2026-06-25

## 0. 本文件职责

本文件只负责：

- 禁止事项
- 敏感信息边界
- 生产边界
- 删除与覆盖边界

## 1. 禁止事项

- 不碰生产服务器、数据库、GitHub Release、下载页、`latest.json`
- 不删除 `docs/superpowers/`
- 不删除 `release/`、Windows/Mac 客户 zip、exe/app 软件本体
- 不运行 `python scripts\commercial_release_acceptance.py --with-exe-self-test --deep-scan --json`
- 不硬编码价格、次数、有效期、设备数、返佣比例、上架状态
- 不把代理登录态写入 `profile.json`
- 不把可恢复买家登录 token 写入 `profile.json`
- 不把 ClaudeCode、OpenClaw、Hermes 未打通项包装成完整付费交付

## 2. 敏感信息边界

- API Key 不输出到日志
- token、Authorization、邀请码、订单号、权益 ID、配置会话 ID 不输出到客服日志或诊断包
- 不把真实密钥、账号密码、生产敏感日志发给网页端或其他 agent

## 3. 生产边界

当前阶段不做生产变更。

如果以后进入生产下载入口、服务器、数据库、支付或钱包改动，必须先按胖虎AI生产维护规则拿锁、记录计划、备份点和验证计划。

## 4. 删除与覆盖边界

- 不覆盖或回退用户现有未确认改动
- 不把历史文档静默删除为“清理”
- 不把客户本地资料、登录信息、工作区资料、备份文件当成普通缓存处理
