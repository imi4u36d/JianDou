# 使用文档

## 1. 项目目标

AI Cut 用于根据原始短剧视频和配置参数，自动生成可用于投放的短视频素材。

当前版本重点支持：

- 视频上传
- 剪辑任务创建
- 任务状态跟踪
- 素材预览与下载
- 本地开发部署

## 2. 本地环境

建议准备：

- Node.js 14.18+ 或更高
- Python 3.11+ 或更高
- Docker Desktop
- FFmpeg / FFprobe
- 本地 MySQL 和 Redis

## 3. 配置文件

后端主配置：

- [config/app.toml](/Users/wangzhuo/codexProjects/ai_cut/config/app.toml)

前端运行时配置：

- [runtime-config.json](/Users/wangzhuo/codexProjects/ai_cut/apps/web/public/runtime-config.json)

主要可调项：

- MySQL 连接串
- Redis 连接串
- 本地存储目录
- Qwen 模型 endpoint / api_key / model_name
- 默认画幅比例
- 默认片头片尾模板

## 4. 启动本地依赖

在项目根目录执行：

```bash
docker compose up -d mysql redis
```

## 5. 启动前端

```bash
npm install
npm --prefix apps/web install
npm run web:dev
```

## 6. 启动后端

```bash
cd apps/api
pip install -e ../../packages/backend_core -e .
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 7. 基本使用流程

1. 打开前端页面。
2. 进入“新建任务”。
3. 上传原始视频。
4. 配置时长范围、产出数量、平台方向、片头片尾模板、创意补充。
5. 提交任务并等待处理。
6. 在任务详情页查看进度和生成结果。
7. 预览并下载输出素材。

## 8. 当前注意事项

- 现阶段优先保证本地可跑通与工程结构完整。
- 投放平台对接暂未实现。
- 模型 provider 首版按 Qwen 接入，后续可继续扩展。
- 如果需要真实生成效果，必须保证本机 FFmpeg / FFprobe 可用。
