# 功能开发记录

## 记录规范

每次迭代建议至少记录以下内容：

- 背景与目标
- 主要改动点
- 风险与回滚方案
- 验证方式
- 后续待办

## 2026-04-09 文档恢复

### 背景

根 `README.md` 已引用文档文件缺失，导致文档入口失效。

### 改动

- 新增缺失文档文件：
  - `docs/ARCHITECTURE.md`
  - `docs/API.md`
  - `docs/USER_GUIDE.md`
  - `docs/ROADMAP.md`
  - `docs/CHANGELOG.md`
  - `docs/DEVELOPMENT_LOG.md`
- 更新根 `README.md` 文档导航
- 增加 QQ 交流群信息

### 验证

- 检查 README 中所有文档链接目标文件存在
- 核对 API 文档与当前 `apps/api/app/routers/*` 路由一致

### 后续待办

- 补充接口请求/响应样例的自动化校验
- 在 CI 增加文档链接可用性检查

