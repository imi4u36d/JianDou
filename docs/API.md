# API 文档

## 1. 基础信息

- Base URL（开发默认）：`http://127.0.0.1:8000`
- API 前缀：`/api/v2`
- 返回格式：JSON

## 2. 健康检查

### `GET /api/v2/health`

返回服务与运行时信息。

## 3. 上传接口

### `POST /api/v2/uploads/videos`

- `multipart/form-data`
- 字段：`file`

### `POST /api/v2/uploads/texts`

- `multipart/form-data`
- 字段：`file`（TXT）

上传成功返回：

```json
{
  "assetId": "asset_xxx",
  "fileName": "demo.txt",
  "fileUrl": "/storage/uploads/xxx.txt",
  "sizeBytes": 1024
}
```

## 4. 任务接口

### `POST /api/v2/tasks/generation`

创建文本生成任务。

请求示例：

```json
{
  "title": "都市短剧预告片",
  "aspectRatio": "9:16",
  "videoDurationSeconds": "auto",
  "creativePrompt": "情绪递进、冲突高频、结尾留悬念",
  "textAnalysisModel": "gpt-5.4",
  "videoModel": "wan2.6-i2v",
  "videoSize": "720*1280",
  "transcriptText": "这里是输入文本"
}
```

说明：

- `aspectRatio` 仅支持 `9:16` 或 `16:9`
- `videoDurationSeconds` 支持整数秒或 `"auto"`
- 若不用 `"auto"`，需保证时长约束可被解析

### `POST /api/v2/tasks/generate-prompt`

根据任务元信息生成创意提示词。

### `GET /api/v2/tasks`

查询任务列表，支持参数：

- `q`
- `status`
- `platform`

### `GET /api/v2/tasks/{task_id}`

任务详情。

### `GET /api/v2/tasks/{task_id}/trace`

任务追踪事件，支持 `limit`。

### `GET /api/v2/tasks/{task_id}/status-history`

任务状态变更历史。

### `GET /api/v2/tasks/{task_id}/model-calls`

模型调用记录。

### `GET /api/v2/tasks/{task_id}/results`

任务输出结果列表。

### `GET /api/v2/tasks/{task_id}/materials`

任务关联素材列表。

### `GET /api/v2/tasks/{task_id}/logs`

任务日志（结构同 trace）。

### `GET /api/v2/tasks/seeddance/{remote_task_id}`

查询远端 SeedDance 任务状态。

### `POST /api/v2/tasks/{task_id}/retry`

重试任务。

### `POST /api/v2/tasks/{task_id}/pause`

暂停任务。

### `POST /api/v2/tasks/{task_id}/continue`

继续已暂停任务。

### `POST /api/v2/tasks/{task_id}/terminate`

终止任务。

### `DELETE /api/v2/tasks/{task_id}`

删除任务（进行中的任务不可直接删除）。

## 5. 生成能力接口

### `GET /api/v2/generation/catalog`

获取模型目录、尺寸、时长等可选项。

### `POST /api/v2/generation/runs`

统一创建生成运行任务，`kind` 支持：

- `image`
- `video`
- `script`
- `probe`

视频请求示例：

```json
{
  "kind": "video",
  "input": {
    "prompt": "雨夜街头追逐，电影感",
    "width": 720,
    "height": 1280,
    "minDurationSeconds": 8,
    "maxDurationSeconds": 12
  },
  "model": {
    "providerModel": "wan2.6-i2v",
    "textAnalysisModel": "gpt-5.4"
  },
  "options": {
    "stylePreset": "cinematic"
  }
}
```

### `GET /api/v2/generation/runs/{run_id}`

查询运行任务详情。

### `GET /api/v2/generation/usage`

查询视频模型额度使用情况。

## 6. 管理端接口

管理端统一前缀：`/api/v2/admin`

### `GET /api/v2/admin/overview`
### `GET /api/v2/admin/tasks`
### `GET /api/v2/admin/tasks/{task_id}`
### `GET /api/v2/admin/tasks/{task_id}/trace`
### `GET /api/v2/admin/traces`
### `POST /api/v2/admin/tasks/{task_id}/retry`
### `POST /api/v2/admin/tasks/{task_id}/terminate`
### `DELETE /api/v2/admin/tasks/{task_id}`
### `POST /api/v2/admin/tasks/bulk-delete`
### `POST /api/v2/admin/tasks/bulk-retry`

## 7. 错误码约定

常见 HTTP 状态：

- `400`：请求参数错误
- `404`：资源不存在
- `409`：状态冲突（如任务不可继续/不可暂停）
- `502`：上游模型调用失败

