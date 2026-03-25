# API 文档

本文档描述首版后端 API 规划。实际接口以代码实现为准。

## 1. 健康检查

### `GET /health`

返回服务状态与基础依赖信息。

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

## 4. 创建任务

### `POST /api/v1/tasks`

请求示例：

```json
{
  "title": "第12集高能转化版",
  "sourceAssetId": "video_xxx",
  "sourceFileName": "episode12.mp4",
  "platform": "douyin",
  "aspectRatio": "9:16",
  "minDurationSeconds": 15,
  "maxDurationSeconds": 30,
  "outputCount": 3,
  "introTemplate": "hook",
  "outroTemplate": "brand",
  "creativePrompt": "优先保留冲突和反转"
}
```

响应内容包含：

- 任务 ID
- 当前状态
- 任务配置
- 已生成结果列表

## 5. 任务详情

### `GET /api/v1/tasks/{taskId}`

查询单个任务详情、状态、错误信息和输出列表。

## 6. 任务重试

### `POST /api/v1/tasks/{taskId}/retry`

对失败任务发起重试。

## 7. 输出结果

任务详情中的 `outputs` 应包含：

- 素材 ID
- 片段序号
- 片段开始/结束时间
- 时长
- 预览地址
- 下载地址
- 推荐原因

## 8. 未来补充

- 删除任务
- 取消任务
- WebSocket / SSE 任务进度推送
- 任务日志查询
- 模板管理

