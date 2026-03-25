# 功能开发记录

## 2026-03-25

### 阶段

项目启动与首版骨架搭建

### 本次开发目标

- 确认 MVP 边界
- 建立前后端工程结构
- 落地统一配置方式
- 为本地开发准备 MySQL、Redis、本地存储方案
- 建立文档体系

### 已落实内容

1. 工程结构初始化
- 创建 `apps/web`、`apps/api`、`apps/worker`、`packages/*`、`docs`、`config`、`storage`

2. 配置体系
- 使用 `config/app.toml` 管理应用、数据库、Redis、本地存储、模型、流水线配置
- 使用 `apps/web/public/runtime-config.json` 管理前端运行时 API 地址

3. 前端首版页面
- 任务列表页
- 新建任务页
- 任务详情页
- 基础状态轮询与上传/创建任务交互

4. 并行协作
- 已启用需求、架构、UI/UX、前端、后端、测试 6 个 agent 并行推进

### 待继续

- 后端任务模型与 API
- 本地视频上传和素材输出
- FFmpeg 裁切与片头片尾拼接
- Qwen provider 接入层
- 完整使用文档和接口文档

## 2026-03-25（二次迭代）

### 阶段

多 agent 协同迭代与工作台升级

### 本次开发目标

- 用产品、UI、前端、后端四个角色并行推进连续 3 个版本
- 在不引入数据库迁移的前提下增强任务可见性、可复用性和建单效率
- 统一前后端对“任务工作台”的表达

### 已落实内容

1. 产品迭代链路
- V1：任务详情增强，暴露规划方案、素材摘要、时间信息
- V2：任务筛选与参数复制，支持从历史任务快速复用配置
- V3：预设模板与工作台指标，降低建单门槛

2. 后端增强
- 新增 `GET /api/v1/presets`
- 新增 `POST /api/v1/tasks/{taskId}/clone`
- `GET /api/v1/tasks` 支持 `q`、`status`、`platform`
- `TaskDetail` / `TaskListItem` 增加更多工作台字段

3. 前端升级
- 重做全局视觉基底与工作台头部
- 任务列表增加搜索、筛选、指标卡、分组展示
- 新建页支持预设模板、参数摘要和历史任务复制
- 详情页增加规划方案区、素材信息区和更清晰的阶段状态

4. 并行协作
- 产品 agent 负责连续版本需求
- UI agent 负责工作台视觉与布局方向
- 前端 / 后端 agent 分别落地实现
- 主 agent 负责集成、校验和文档同步

### 验证

- `npm --prefix apps/web run typecheck`
- `npm --prefix apps/web run build`
- `python3 -m py_compile apps/api/app/main.py apps/api/app/routers/tasks.py apps/api/app/routers/presets.py packages/backend_core/backend_core/*.py`
- `./.venv/bin/python -c "from apps.api.app.main import app; ..."`

## 2026-03-25（三次迭代）

### 阶段

V4-V8 路线规划与模型就绪层补强

### 本次开发目标

- 在不额外消耗模型 token 做自检的前提下，确保模型配置与规划能力可见
- 把字幕 / 台词输入体验提升为真正的语义规划入口
- 为后续五个版本建立清晰的版本路线

### 已落实内容

1. 模型就绪层
- 健康检查返回更丰富的运行时模型信息
- 前端全局头部展示主模型、回退模型、配置是否就绪和规划能力

2. 字幕驱动输入
- 新建页支持导入 `.srt/.vtt/.txt`
- 新建页展示语义输入质量与时间戳模式提示
- 详情页展示字幕输入摘要和时间轴片段数

3. 五个后续版本路线
- V4：模型就绪层
- V5：字幕驱动切片
- V6：批量运营工作台
- V7：人工审核与微调
- V8：策略复盘台

## 2026-03-25（四次迭代）

### 阶段

全链路任务日志追踪

### 本次开发目标

- 为每个任务建立可查询的 trace 事件流
- 覆盖 API 创建、任务调度、素材分析、规划、Qwen 调用、渲染和失败
- 尤其增强大模型调用细节，方便排查 prompt、回退和响应问题

### 已落实内容

1. 后端 trace 能力
- 为每个任务写入 `storage/temp/task_trace/<task_id>.jsonl`
- 新增 `GET /api/v1/tasks/{taskId}/trace`
- 记录 API 创建、调度、分析、规划、LLM 尝试、回退、HTTP/网络错误、响应摘录、渲染片段开始/完成、任务完成/失败

2. 大模型细节
- 记录主模型 / 回退模型尝试过程
- 记录 prompt 长度和 prompt 摘录
- 记录响应摘录和解析出的 clip 数量
- 不记录 API Key

3. 前端可视化
- 任务详情页新增“全链路日志追踪”面板
- 用 stage / level 分组显示任务事件
- `llm` 阶段会直接显示模型调用相关上下文
