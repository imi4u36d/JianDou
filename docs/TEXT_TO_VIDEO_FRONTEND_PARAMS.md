# 文生视频前端参数分析

## 1. 目标

本文档用于说明当前项目里“文生视频”前端应该提供哪些参数、这些参数从哪里来、如何校验，以及当前实现里有哪些差异需要注意。

结论先说：

- 如果走直接生成接口 `/api/v1/generations/video`，前端核心只需要维护 6 个业务参数：
  - `prompt`
  - `version`
  - `providerModel`
  - `videoSize`
  - `videoDurationSeconds`
  - `stylePreset`（可选）
- 提交前还需要从 `videoSize` 派生出：
  - `width`
  - `height`
- 固定字段：
  - `kind = "video"`
- 如果走 Agent 工作台接口 `/api/v1/agents/text-media/runs`，还会额外用到：
  - `mediaKind = "video"`
  - `aspectRatio`

## 2. 当前代码入口

当前仓库里有两条“文生视频”前端链路：

### 2.1 直接生成页面

- 页面：`apps/web/src/views/TextGenerateView.vue`
- 接口封装：`apps/web/src/api/generation.ts`
- 后端接口：`POST /api/v1/generations/video`

这条链路的参数最完整，适合作为标准实现。

### 2.2 Studio / Agent 工作台

- 页面：`apps/web/src/views/StudioView.vue`
- Agent 请求封装：`apps/web/src/api/agents.ts`
- 后端接口：`POST /api/v1/agents/text-media/runs`

这条链路面向工作台能力，底层仍然调用文生视频生成逻辑，但当前参数透传不完全。

## 3. 参数来源

文生视频前端不应该把模型、尺寸、时长写死在页面里，应该优先从：

- `GET /api/v1/generations/versions`

获取以下配置：

| 字段 | 用途 |
| --- | --- |
| `versions` | 可选策略版本列表 |
| `versionDetails` | 版本名称、说明、默认项 |
| `videoModels` | 视频模型列表 |
| `videoSizes` | 视频尺寸列表 |
| `videoDurations` | 视频时长列表 |
| `defaultVersion` | 默认策略版本 |
| `defaultVideoModel` | 默认视频模型 |
| `defaultVideoSize` | 默认视频尺寸 |
| `defaultVideoDurationSeconds` | 默认视频时长 |

前端应该始终按“模型 -> 过滤可用尺寸/时长”的方式联动，而不是让用户随意组合。

## 4. 前端必备参数

以下为当前项目下，文生视频前端真正需要维护的参数。

### 4.1 业务表单参数

| 参数 | 必填 | 前端类型 | 示例 | 来源 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `prompt` | 是 | `string` | `"雨夜霓虹街头，一名女孩回头凝视镜头，电影感"` | 用户输入 | 文生视频主提示词 |
| `version` | 是 | `number` | `1` | `versions/defaultVersion` | 提示词策略版本，不是底层模型版本 |
| `providerModel` | 建议视为必填 | `string` | `"wan2.6-t2v"` | `videoModels/defaultVideoModel` | 选择具体视频模型 |
| `videoSize` | 是 | `string` | `"1080x1920"` | `videoSizes/defaultVideoSize` | 分辨率选择项 |
| `videoDurationSeconds` | 是 | `number` | `5` | `videoDurations/defaultVideoDurationSeconds` | 生成时长 |
| `stylePreset` | 否 | `string` | `"cinematic"` | `stylePresets` | 风格预设，没有可传空 |

### 4.2 提交时派生参数

| 参数 | 必填 | 前端类型 | 说明 |
| --- | --- | --- | --- |
| `kind` | 是 | `"video"` | 直接生成接口固定值 |
| `width` | 是 | `number` | 从 `videoSize` 解析 |
| `height` | 是 | `number` | 从 `videoSize` 解析 |
| `aspectRatio` | Agent 模式必填 | `"9:16" \| "16:9"` | 从 `width/height` 推导 |
| `mediaKind` | Agent 模式必填 | `"video"` | Agent 接口固定值 |

## 5. 后端约束

以后端模型 `GenerateTextMediaRequest` 和 `TextMediaAgentRunRequest` 为准，前端需要遵守以下规则：

### 5.1 通用规则

- `prompt`
  - 必填
  - 去首尾空格后不能为空
  - 长度 `1 ~ 5000`
- `version`
  - 必填
  - 范围 `1 ~ 10`
- `providerModel`
  - 当前后端允许为空，但对文生视频前端来说不应依赖为空
  - 为空时后端会落回默认模型
- `width / height`
  - 范围 `256 ~ 4096`
  - 总像素不能超过 `8_294_400`
- `durationSeconds`
  - 文生视频必填
  - 范围 `1 ~ 120`

### 5.2 模型联动规则

后端会根据模型自动规范化尺寸和时长。如果前端允许了不支持的组合，后端会“纠正”为最近可用值。

这意味着前端最好提前限制，而不是把修正交给后端，否则用户会遇到“我选的是 A，结果生成成了 B”的体验问题。

## 6. 当前模型与可选参数建议

基于当前代码里的模型目录，文生视频前端建议暴露如下组合：

| 模型 | 推荐用途 | 支持尺寸概况 | 支持时长概况 |
| --- | --- | --- | --- |
| `wan2.6-t2v` | 主文生视频模型 | 480p / 720p / 1080p，横竖屏均有 | 2-15 秒 |
| `wan2.6-t2v-us` | US 地域模型 | 720p / 1080p，横竖屏均有 | 5 / 10 / 15 秒 |
| `wan2.5-t2v-preview` | 兼容性模型 | 480p / 720p / 1080p | 5-10 秒 |
| `wan2.2-t2v-plus` | 质量稳定模型 | 480p / 1080p | 固定 5 秒 |
| `wanx2.1-t2v-turbo` | 速度优先 | 480p / 720p | 固定 5 秒 |
| `wanx2.1-t2v-plus` | 质量优先 | 720p | 固定 5 秒 |

需要特别注意：

- `wan2.6-i2v` 是图生视频模型，不适合作为“纯文生视频”入口的默认模型。
- 如果前端页面是“文本生成视频”，建议默认模型改为 `wan2.6-t2v`，而不是 `wan2.6-i2v`。

## 7. 推荐的前端表单结构

推荐将文生视频表单控制在下面这个结构：

```ts
type TextToVideoForm = {
  prompt: string;
  version: number;
  providerModel: string;
  videoSize: string;
  videoDurationSeconds: number;
  stylePreset: string;
};
```

提交前再派生：

```ts
type VideoSubmitPayload = {
  prompt: string;
  version: number;
  kind: "video";
  providerModel: string;
  videoSize: string;
  width: number;
  height: number;
  durationSeconds: number;
  stylePreset?: string;
};
```

如果走 Agent：

```ts
type VideoAgentPayload = {
  prompt: string;
  mediaKind: "video";
  version: number;
  providerModel: string;
  aspectRatio: "9:16" | "16:9";
  width: number;
  height: number;
  durationSeconds: number;
  stylePreset?: string;
};
```

## 8. 推荐交互与校验

### 8.1 表单顺序

建议前端表单顺序如下：

1. `prompt`
2. `version`
3. `providerModel`
4. `videoSize`
5. `videoDurationSeconds`
6. `stylePreset`

### 8.2 联动逻辑

建议联动规则如下：

1. 页面加载时先拉 `GET /generations/versions`
2. 设置默认 `version`
3. 设置默认 `providerModel`
4. 根据 `providerModel` 过滤 `videoSizes`
5. 根据 `providerModel` 过滤 `videoDurations`
6. 如果当前已选尺寸或时长不再可用，自动切到该模型的默认值或首项

### 8.3 前端校验

提交前至少做以下校验：

- `prompt.trim()` 不能为空
- `version` 必须在接口返回范围内
- `providerModel` 必须在当前 `videoModels` 内
- `videoSize` 必须在当前模型可支持的 `videoSizes` 内
- `videoDurationSeconds` 必须在当前模型可支持的 `videoDurations` 内

## 9. 推荐请求示例

### 9.1 直接生成接口

```json
{
  "prompt": "暴雨夜的高架桥下，红色尾灯在积水中拉出反光，镜头缓慢推进，电影感",
  "version": 1,
  "kind": "video",
  "providerModel": "wan2.6-t2v",
  "videoSize": "1080x1920",
  "width": 1080,
  "height": 1920,
  "durationSeconds": 5,
  "stylePreset": "cinematic"
}
```

### 9.2 Agent 工作台接口

```json
{
  "prompt": "暴雨夜的高架桥下，红色尾灯在积水中拉出反光，镜头缓慢推进，电影感",
  "mediaKind": "video",
  "version": 1,
  "providerModel": "wan2.6-t2v",
  "aspectRatio": "9:16",
  "width": 1080,
  "height": 1920,
  "durationSeconds": 5,
  "stylePreset": "cinematic"
}
```

## 10. 当前实现差异与风险

### 10.1 `TextGenerateView.vue` 基本符合预期

当前直接生成页已经具备：

- `prompt`
- `version`
- `providerModel`
- `videoSize`
- `videoDurationSeconds`
- `stylePreset`

并在提交时派生出：

- `kind`
- `width`
- `height`

这条链路可以视为“标准参考实现”。

### 10.2 `StudioView.vue` 当前漏传视频模型和视频尺寸

当前 `StudioView.vue` 调 `runVisualAgent()` 时，视频模式只传了：

- `prompt`
- `mediaKind`
- `version`
- `stylePreset`
- `imageSize`
- `videoDurationSeconds`

没有显式传：

- `providerModel`
- `videoSize`

影响：

- 页面上虽然让用户选择了“视频模型”，但请求里未必带出去
- 最终可能回退到后端默认模型
- UI 选择和实际生成模型可能不一致

### 10.3 Agent 链路没有把 `stylePreset` 原样透传到生成请求

当前 Agent 执行时把 `stylePreset` 写进了 `extras.styleHint` / `extras.cameraHint`，但没有作为顶层 `stylePreset` 传给文生视频生成请求。

影响：

- 直接生成链路和 Agent 链路的参数行为不完全一致
- 后续如果后端对 `stylePreset` 做强约束，Agent 链路会和直连接口出现偏差

### 10.4 默认视频模型不适合“纯文生视频”页面

当前多个 fallback/default 把：

- `wan2.6-i2v`

作为默认视频模型。

问题：

- 该模型是图生视频模型
- 对“文本生成视频”页面来说，默认模型应该是 `wan2.6-t2v`

## 11. 结论

如果只是做一套清晰、可维护的文生视频前端，建议把参数分成三层：

### 11.1 用户可编辑

- `prompt`
- `version`
- `providerModel`
- `videoSize`
- `videoDurationSeconds`
- `stylePreset`

### 11.2 前端派生

- `kind`
- `mediaKind`
- `width`
- `height`
- `aspectRatio`

### 11.3 后端决定

- 实际模型归一化后的尺寸
- 实际模型归一化后的时长
- 实际执行链路和产物地址

按这个边界来拆，前端职责会比较清晰，也便于后续新增高级参数，比如：

- `negativePrompt`
- `seed`
- `cameraMotion`
- `shotType`
- `audio`
- `batchCount`

这些高级参数当前项目还没有稳定接口定义，暂时不建议直接开放到正式表单。
