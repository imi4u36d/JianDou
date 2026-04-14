# 使用文档

## 1. 环境准备

- JDK `17`
- Maven `3.9+`
- Node.js `>=18`
- Docker / Docker Compose（推荐）
- MySQL 8.x（本地直跑时需要）

## 2. 配置说明

1. 使用示例配置：

```bash
cp config/app.example.yml config/app.yml
```

2. 打开 `config/app.yml`，替换所有模型相关 Key。  
3. 如需覆盖配置，可使用 `JIANDOU_*` 环境变量（例如 `JIANDOU_DATABASE_URL`）。

## 3. Docker 一键启动（推荐）

```bash
docker compose up --build
```

默认地址：

- 前端：`http://127.0.0.1:5173`
- 后端：`http://127.0.0.1:8000`
- MySQL：`127.0.0.1:3306`

说明：

- 项目默认后端为 `apps/api-spring`
- `apps/api/app/**` 下的 FastAPI API 入口已移除，不再作为启动方式

停止服务：

```bash
docker compose down
```

清空数据卷：

```bash
docker compose down -v
```

## 4. 本地开发启动

### 4.1 安装前端依赖

```bash
npm --prefix apps/web install
```

### 4.2 准备 Spring Boot 后端依赖

```bash
/opt/homebrew/opt/maven@3.9/bin/mvn -f apps/api-spring/pom.xml -DskipTests compile
```

### 4.3 同时启动 Spring API 和前端

```bash
npm run dev
```

该命令会调用 `scripts/dev-spring.sh`，自动启动：

- Spring Boot API：`http://127.0.0.1:8000`
- Vite：`http://127.0.0.1:5173`

## 5. 典型使用流程

1. 进入前端 `http://127.0.0.1:5173`
2. 在“创建任务”页面填写标题、比例、模型、时长限制
3. 可上传 TXT 或直接粘贴文本
4. 提交任务后在“任务”页面查看实时状态与日志
5. 完成后在任务详情中查看输出并下载结果

## 6. 常见问题

### 6.1 启动时报 Key 或模型错误

- 检查 `config/app.yml` 中 Key 是否已替换
- 检查模型 endpoint 与 provider 是否匹配

### 6.2 前端请求失败

- 检查后端是否在 `8000` 端口启动
- 检查 `apps/web/public/runtime-config.json` 的 `apiBaseUrl`

### 6.3 任务长时间停留在 `PENDING`

- 当前默认模式为 `queue`
- 请确认 Spring 进程正常运行，且未被旧进程占用 `8000` 端口
- 当前 Spring worker 已内嵌在 API 进程内，不需要再单独启动 Python worker
- `apps/api/app/**` 下的 FastAPI API 入口已移除，如仍有旧脚本引用请切换到 `apps/api-spring`
