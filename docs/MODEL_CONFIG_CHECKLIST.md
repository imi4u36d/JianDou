# 大模型配置清单

本文整理当前项目中与大模型接入相关的配置项，重点覆盖 `provider`、`endpoint/base_url`、`task_base_url`、`api_key`、模型映射、环境变量覆盖规则，以及当前仓库里已经声明和实际启用的模型。

## 1. 配置入口

- 主配置文件默认位于 `config/app.yml`
- Spring 后端会在运行时读取该文件中的 `model` 节点
- 前端不直接配置 `provider`、`key`、`endpoint`
- 前端只传业务层模型名，例如 `qwen3.6-plus`、`Doubao-Seedream-4.5`、`seedance-1.5-pro`

## 2. 配置文件结构

当前核心结构如下：

```yaml
model:
  timeout_seconds: 120
  temperature: 0.15
  max_tokens: 2000
  vision_frame_count: 6
  providers:
    qwen:
      provider: "qwen"
      api_key: ""
      base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
      extras:
        use_responses_api: true
        timeout_seconds: 300
    seedream:
      provider: "seedream"
      api_key: ""
      base_url: "https://ark.cn-beijing.volces.com/api/v3/images/generations"
    seedance:
      provider: "seedance"
      api_key: ""
      base_url: "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks"
      extras:
        task_base_url: "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks"
        poll_interval_seconds: 8
        poll_timeout_seconds: 600
        camera_fixed: false
        watermark: false
  models:
    "qwen3.6-plus":
      provider: "qwen"
      kind: "text"
    "Doubao-Seedream-4.5":
      provider: "seedream"
      kind: "image"
    "seedance-1.5-pro":
      provider: "seedance"
      kind: "video"
```

## 3. 必填参数清单

### 3.1 文本模型

适用于 `text`、`vision` 类型模型。

必填项：

- `model.models.<模型名>.provider`
- `model.models.<模型名>.kind`
- `model.providers.<provider>.api_key`
- `model.providers.<provider>.base_url`

常用可选项：

- `model.models.<模型名>.fallback_model`
- `model.models.<模型名>.supports_seed`
- `model.models.<模型名>.vision_use_chat_completions`
- `model.models.<模型名>.timeout_seconds`
- `model.models.<模型名>.temperature`
- `model.models.<模型名>.max_tokens`
- `model.providers.<provider>.extras.use_responses_api`
- `model.providers.<provider>.extras.timeout_seconds`

说明：

- 文本模型只有在 `api_key` 和 `base_url` 都存在时才算 ready
- `base_url` 这里配置的是基地址，不是最终接口地址
- 运行时会自动拼接成 `/responses` 或 `/chat/completions`

### 3.2 图片模型

适用于 `image` 类型模型。

必填项：

- `model.models.<模型名>.provider`
- `model.models.<模型名>.kind=image`
- `model.providers.<provider>.api_key`
- `model.providers.<provider>.base_url`

常用可选项：

- `model.models.<模型名>.supports_seed`
- `model.models.<模型名>.timeout_seconds`

说明：

- 当前仓库实际实现的图片 provider 是 `seedream`
- 图片模型要求 `api_key` 和 `base_url` 都存在
- 图片模型的 `base_url` 是实际提交图片生成请求的地址，不会自动补 `/responses`

### 3.3 视频模型

适用于 `video` 类型模型。

必填项：

- `model.models.<模型名>.provider`
- `model.models.<模型名>.kind=video`
- `model.providers.<provider>.api_key`
- `model.providers.<provider>.base_url`
- `model.providers.<provider>.extras.task_base_url`

常用可选项：

- `model.models.<模型名>.supports_seed`
- `model.models.<模型名>.generation_mode`
- `model.models.<模型名>.supported_sizes`
- `model.models.<模型名>.supported_durations`
- `model.providers.<provider>.extras.poll_interval_seconds`
- `model.providers.<provider>.extras.poll_timeout_seconds`
- `model.providers.<provider>.extras.prompt_extend`
- `model.providers.<provider>.extras.camera_fixed`
- `model.providers.<provider>.extras.watermark`
- `model.providers.<provider>.extras.timeout_seconds`

说明：

- 视频模型除了提交任务，还要轮询任务状态，所以通常需要两类端点
- `base_url` 用于提交任务
- `task_base_url` 用于查询任务状态
- 对 `wan` 这类 DashScope 视频接口，如果未手动配置 `task_base_url`，代码会尝试从 `base_url` 推导
- 对 `seedance`，建议明确写死 `task_base_url`

## 4. 当前仓库已声明的 provider

在 `config/app.yml` 中已声明：

- `openai`
- `qwen`
- `ark`
- `wan`
- `seedream`
- `seedance`

说明：

- “已声明 provider” 不等于“已在前端可选模型目录中启用”
- 是否会出现在前端模型列表，取决于 `model.models` 下是否挂了具体模型

## 5. 当前仓库已挂载到模型目录的模型

### 文本模型

- `qwen3.6-plus`
- `qwen-plus`
- `qwen3.5-flash`

### 视觉模型

- `qwen3-vl-flash-2026-01-22`

### 图片模型

- `Doubao-Seedream-4.5`

### 视频模型

- `seedance-1.5-pro`

说明：

- 当前 `openai`、`ark`、`wan` 虽然已经有 provider 配置段，但还没有在 `model.models` 里挂出对应模型
- 这意味着当前前端目录默认不会直接出现这些 provider 的模型选项

## 6. 当前项目建议优先配置的参数

如果你只想让当前项目先跑起来，按现在仓库里的模型目录，至少需要准备下面这些 key：

- `JIANDOU_MODEL_QWEN_API_KEY`
- `JIANDOU_MODEL_SEEDREAM_API_KEY`
- `JIANDOU_MODEL_SEEDANCE_API_KEY`

如果你同时要覆盖端点，还需要：

- `JIANDOU_MODEL_QWEN_BASE_URL`
- `JIANDOU_MODEL_SEEDREAM_BASE_URL`
- `JIANDOU_MODEL_SEEDANCE_BASE_URL`
- `JIANDOU_MODEL_SEEDANCE_TASK_BASE_URL`

## 7. 环境变量覆盖规则

### 7.1 配置文件路径

支持以下环境变量指定配置文件位置：

- `JIANDOU_CONFIG_FILE`
- `JIANDOU_CONFIG_PATH`
- `JIANDOU_CONFIG_DIR`
- `SPRING_CONFIG_LOCATION`
- `SPRING_CONFIG_ADDITIONAL_LOCATION`

如果不指定，默认会优先查找当前工作目录及上级目录下的 `config/app.yml` 或同类配置文件。

### 7.2 文本模型全局覆盖

文本模型支持以下全局环境变量：

- `JIANDOU_MODEL_PROVIDER`
- `JIANDOU_MODEL_FALLBACK`
- `JIANDOU_MODEL_API_KEY`
- `JIANDOU_MODEL_BASE_URL`
- `JIANDOU_MODEL_ENDPOINT`
- `JIANDOU_MODEL_ENDPOINT_HOST`
- `JIANDOU_MODEL_TIMEOUT`
- `JIANDOU_MODEL_TEMPERATURE`
- `JIANDOU_MODEL_MAX_TOKENS`

说明：

- 这些全局变量会影响文本/视觉模型解析
- 如果设置了全局值，会优先于 `config/app.yml` 中的 provider 配置

### 7.3 按 provider 覆盖

所有 provider 都支持按名字覆盖，格式是：

```text
JIANDOU_MODEL_<PROVIDER>_API_KEY
JIANDOU_MODEL_<PROVIDER>_BASE_URL
JIANDOU_MODEL_<PROVIDER>_ENDPOINT
JIANDOU_MODEL_<PROVIDER>_TASK_BASE_URL
JIANDOU_MODEL_<PROVIDER>_TIMEOUT_SECONDS
```

例如：

- `JIANDOU_MODEL_QWEN_API_KEY`
- `JIANDOU_MODEL_QWEN_BASE_URL`
- `JIANDOU_MODEL_OPENAI_API_KEY`
- `JIANDOU_MODEL_WAN_TASK_BASE_URL`
- `JIANDOU_MODEL_SEEDANCE_TASK_BASE_URL`

说明：

- provider 名会自动转成大写并用下划线拼接
- 例如 `seedance` 会变成 `JIANDOU_MODEL_SEEDANCE_*`

## 8. 文本接口协议规则

文本模型底层统一按 OpenAI 兼容协议调用，但有两种传输方式：

- Responses API
- Chat Completions API

默认规则：

- `openai` 默认支持 Responses API
- `qwen` 默认支持 Responses API
- `ark` / `volc` 默认支持 Responses API
- 如果是视觉模型，且 provider 是 `qwen` 或模型名包含 `-vl-`，默认更倾向走 Chat Completions

可通过以下配置干预：

- `model.providers.<provider>.extras.use_responses_api`
- `model.models.<模型名>.vision_use_chat_completions`
- `model.providers.<provider>.extras.vision_use_chat_completions`

## 9. 当前文件中存在但暂未看到实际消费的字段

下列字段目前在 `config/app.yml` 中存在，但在当前代码中没有看到明确使用逻辑，现阶段更像预留项：

- `model.aliyun_billing_access_key_id`
- `model.aliyun_billing_access_key_secret`
- `model.volcengine_billing_access_key_id`
- `model.volcengine_billing_access_key_secret`
- `model.video_model_usage_quota`
- `model.vision_frame_count`
- `model.providers.seedance.extras.image_base_url`

如果后续你准备精简配置，这几个字段可以先视为非必需。

## 10. 最小可用示例

### 10.1 仅通过环境变量注入 key

```bash
export JIANDOU_MODEL_QWEN_API_KEY="你的QWEN_KEY"
export JIANDOU_MODEL_SEEDREAM_API_KEY="你的SEEDREAM_KEY"
export JIANDOU_MODEL_SEEDANCE_API_KEY="你的SEEDANCE_KEY"
```

### 10.2 同时覆盖端点

```bash
export JIANDOU_MODEL_QWEN_API_KEY="你的QWEN_KEY"
export JIANDOU_MODEL_QWEN_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"

export JIANDOU_MODEL_SEEDREAM_API_KEY="你的SEEDREAM_KEY"
export JIANDOU_MODEL_SEEDREAM_BASE_URL="https://ark.cn-beijing.volces.com/api/v3/images/generations"

export JIANDOU_MODEL_SEEDANCE_API_KEY="你的SEEDANCE_KEY"
export JIANDOU_MODEL_SEEDANCE_BASE_URL="https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks"
export JIANDOU_MODEL_SEEDANCE_TASK_BASE_URL="https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks"
```

### 10.3 `config/app.yml` 最小参考

```yaml
model:
  timeout_seconds: 120
  temperature: 0.15
  max_tokens: 2000
  providers:
    qwen:
      provider: "qwen"
      api_key: ""
      base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
      extras:
        use_responses_api: true
    seedream:
      provider: "seedream"
      api_key: ""
      base_url: "https://ark.cn-beijing.volces.com/api/v3/images/generations"
    seedance:
      provider: "seedance"
      api_key: ""
      base_url: "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks"
      extras:
        task_base_url: "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks"
        poll_interval_seconds: 8
        poll_timeout_seconds: 600
        camera_fixed: false
        watermark: false
  models:
    "qwen3.6-plus":
      provider: "qwen"
      kind: "text"
      label: "Qwen 3.6 Plus"
    "qwen3-vl-flash-2026-01-22":
      provider: "qwen"
      kind: "vision"
      label: "Qwen 3 VL Flash 2026-01-22"
    "Doubao-Seedream-4.5":
      provider: "seedream"
      kind: "image"
      label: "Doubao Seedream 4.5"
    "seedance-1.5-pro":
      provider: "seedance"
      kind: "video"
      label: "Seedance 1.5 Pro"
      generation_mode: "i2v"
      supported_sizes: "480*854,854*480,720*1280,1280*720"
      supported_durations: "4,6,8,10,12"
```

## 11. 快速检查清单

启动前建议逐项确认：

- `config/app.yml` 已被正确加载
- `model.models` 中存在你要在前端选择的模型
- 模型的 `provider` 能在 `model.providers` 中找到对应段
- 文本模型已配置 `api_key` 和 `base_url`
- 图片模型已配置 `api_key` 和 `base_url`
- 视频模型已配置 `api_key`、`base_url`、`task_base_url`
- 如果用了环境变量覆盖，变量名和 provider 名完全一致
- 若视觉模型请求异常，检查是否需要切换为 Chat Completions
- 若视频任务能提交但查不到状态，优先检查 `task_base_url`

