# AI Cut

AI 短剧剪辑平台首版工程，目标是根据上传视频和配置参数自动生成用于投放的短剧素材。

当前版本聚焦：

- 本地视频上传
- 剪辑任务创建与状态跟踪
- 任务预设模板与历史任务参数复制
- 任务列表搜索、状态/平台筛选与工作台指标
- 基于启发式 / Qwen 规划的片段方案
- 规划方案、素材摘要、时间信息的详情可视化
- FFmpeg 裁切与简单片头片尾拼接
- 素材预览与下载
- 本地 MySQL / Redis / 本地文件存储配置化

详细文档见：

- [架构说明](./docs/ARCHITECTURE.md)
- [API 文档](./docs/API.md)
- [使用文档](./docs/USER_GUIDE.md)
- [路线图](./docs/ROADMAP.md)
- [版本记录](./docs/CHANGELOG.md)
- [功能开发记录](./docs/DEVELOPMENT_LOG.md)
