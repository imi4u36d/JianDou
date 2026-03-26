# API 文档

本文档描述首版后端 API 规划。实际接口以代码实现为准。

## 1. 健康检查

### `GET /api/v1/health`

返回服务状态与基础依赖信息。

当前会额外返回：

- 模型主规格 / 回退规格
- endpoint host
- API Key 是否已配置
- 是否具备带时间戳字幕规划能力
- 配置缺失项列表

该接口只做配置与能力检查，不会发起真实模型生成请求。

## 2. 视频上传

### `POST /api/v1/uploads/videos`

上传原始视频到本地存储。

请求：

- `multipart/form-data`
- 字段：`file`

响应示例：

```json
{
  "assetId": "video_xxx",
  "fileName": "demo.mp4",
  "fileUrl": "http://127.0.0.1:8000/storage/uploads/demo.mp4",
  "sizeBytes": 1024000
}
```

## 3. 任务列表

### `GET /api/v1/tasks`

查询任务列表。

支持 query 参数：

- `q`：按任务标题、源文件名、创意补充模糊搜索
- `status`：按任务状态过滤
- `platform`：按投放平台过滤

## 4. 创建任务

### `POST /api/v1/tasks`

请求示例：

```json
{
  "title": "第12集高能转化版",
  "sourceAssetId": "video_xxx",
  "sourceAssetIds": ["video_xxx"],
  "sourceFileName": "episode12.mp4",
  "sourceFileNames": ["episode12.mp4"],
  "editingMode": "drama",
  "mixcutEnabled": false,
  "mixcutContentType": "generic",
  "mixcutStylePreset": "director",
  "platform": "douyin",
  "aspectRatio": "9:16",
  "minDurationSeconds": 15,
  "maxDurationSeconds": 30,
  "outputCount": 3,
  "introTemplate": "flash_hook",
  "outroTemplate": "suspense_hold",
  "creativePrompt": "优先保留冲突和反转",
  "transcriptText": "1\n00:00:02,000 --> 00:00:06,000\n你居然背着我把合同签了？"
}
```

模式约束：

- `editingMode=drama`：仅允许 1 条 `sourceAssetIds`
- `editingMode=mixcut`：至少 2 条 `sourceAssetIds`

响应内容包含：

- 任务 ID
- 当前状态
- 任务配置
- 已生成结果列表

## 5. 任务详情

### `GET /api/v1/tasks/{taskId}`

查询单个任务详情、状态、错误信息、规划方案、素材摘要和输出列表。

新增字段包括：

- `plan`
- `source`
- `startedAt`
- `finishedAt`
- `retryCount`
- `completedOutputCount`
- `transcriptPreview`
- `hasTranscript`
- `hasTimedTranscript`

## 6. 任务重试

### `POST /api/v1/tasks/{taskId}/retry`

对失败任务发起重试。

## 7. 任务日志追踪

### `GET /api/v1/tasks/{taskId}/trace`

返回任务级 trace 事件列表，覆盖：

- API 创建
- 调度与执行开始
- 素材探测
- 规划开始与完成
- 大模型请求尝试、回退、错误、响应摘录
- FFmpeg 渲染开始与每个片段完成
- 失败与结束状态

支持 query 参数：

- `limit`：限制返回事件数，默认 `500`

## 8. 任务复制

### `POST /api/v1/tasks/{taskId}/clone`

返回一个任务草稿，用于前端预填新建任务表单，不直接创建新任务。

草稿中会包含原任务的 `transcriptText`，便于继续复用字幕/台词语义输入。

## 9. 任务预设

### `GET /api/v1/presets`

返回预定义的任务模板列表，用于快速填充平台、画幅、时长、片头片尾和创意补充。

## 10. 输出结果

任务详情中的 `outputs` 应包含：

- 素材 ID
- 片段序号
- 片段开始/结束时间
- 时长
- 预览地址
- 下载地址
- 推荐原因

## 11. 未来补充

- 删除任务
- 取消任务
- WebSocket / SSE 任务进度推送
- 任务日志查询
- 模板管理
