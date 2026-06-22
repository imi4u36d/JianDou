# 前端架构

## 概览

JianDou 前端是一个基于 Vue 3 + TypeScript + Vite 的单页应用，采用 npm workspace 管理的 monorepo 结构。

| 维度 | 选型 |
|------|------|
| 框架 | Vue 3 (Composition API + `<script setup>`) |
| 语言 | TypeScript 5.x |
| 构建 | Vite 4.x |
| 路由 | Vue Router 4 |
| UI 框架（管理后台） | Element Plus |
| 样式 | Tailwind CSS 3 + CSS 自定义属性 |
| 包管理 | npm workspaces |

## 项目结构

```
root/
├── frontends/
│   ├── web/                     # 用户前台 SPA（主入口）
│   │   └── src/
│   │       ├── api/             # API 调用层
│   │       ├── auth/            # 认证状态管理
│   │       ├── components/      # 共享组件
│   │       │   ├── auth/        #   认证相关组件
│   │       │   ├── common/      #   通用 UI 原子（对话框、选择器等）
│   │       │   ├── generate/    #   生成任务相关组件
│   │       │   ├── icons/       #   SVG 图标组件
│   │       │   ├── layout/      #   布局组件（左侧栏壳体）
│   │       │   └── ui/          #   基础 UI 元件（按钮等）
│   │       ├── composables/     # 可组合逻辑（use*）
│   │       ├── features/        # 功能模块索引
│   │       ├── router/          # 路由定义
│   │       ├── styles/          # 全局样式
│   │       ├── types/           # TypeScript 类型定义
│   │       ├── utils/           # 纯工具函数
│   │       ├── views/           # 页面视图
│   │       └── admin/           # 管理后台（延迟加载）
│   │           ├── api/
│   │           ├── components/
│   │           ├── features/
│   │           ├── layouts/
│   │           ├── styles/
│   │           └── views/
│   └── admin/                   # 管理后台独立部署产物
├── packages/
│   ├── api/                     # OpenAPI 生成的 TypeScript 客户端
│   ├── domain/                  # 领域模型与常量
│   └── ui/                      # 跨工作区共享 UI 组件
└── static/web/                  # 构建产物（由 npm run web:build 生成）
```

## 架构分层

### API 层 (`src/api/`)

基于 `packages/api` 提供的共享客户端，封装了各业务域的 HTTP 调用。每个 API 模块对应后端的一组端点：

- `client.ts` — 共享 API 客户端实例
- `auth.ts` — 登录 / 登出 / 激活
- `tasks.ts` — 任务 CRUD 与进度查询
- `generation.ts` — 生成选项与媒体生成
- `workflows.ts` — 阶段工作流
- `credits.ts` — 积分查询
- `health.ts` — 健康检查
- `showcase.ts` — 公开案例
- `material-assets.ts` — 素材管理
- `runtime-config.ts` — 运行时配置加载

### 状态管理

项目采用 Vue 3 原生响应式 API 管理状态，未引入 Vuex 或 Pinia：

- **`auth/session.ts`** — 全局登录态，通过 `reactive()` 存储，`useAuthSessionState()` 暴露计算属性
- **Composables** — 各模块通过 `use*` composable 管理局部状态与副作用

### 视图与路由

路由采用分层结构：

- `/` → `WorkspaceShell`（左侧栏壳）
  - `/workspace` — 工作台首页（HomeView）
  - `/workflows` — 阶段工作流列表
  - `/workflows/:workflowId` — 工作流详情
  - `/tasks` — 任务列表
  - `/materials` — 素材库
- `/login` — 登录
- `/activate` — 邀请码激活
- `/403` — 无权限
- `/admin/*` — 管理后台路由（Element Plus 延迟加载）

### 管理后台

管理后台在路由器匹配到 `/admin` 路径时动态加载 Element Plus 及管理端样式，避免影响前台的包体积。管理端组件位于 `src/admin/` 目录下。

## 关键约定

### 命名规范

- 文件名：PascalCase（Vue 组件）、kebab-case（工具函数、composables）
- 组件 Props：camelCase
- API 函数：`fetch*` / `create*` / `update*` / `delete*`

### 类型安全

所有 API 响应和请求体在 `src/types/index.ts` 中有对应的 TypeScript 接口定义。新增 API 调用时必须确保类型覆盖。

### 样式策略

- 全局变量（颜色、间距）通过 CSS 自定义属性定义在 `tailwind.css` 中
- 组件级样式使用 Vue 的 `<style scoped>` 块
- Tailwind 用于快速原型和布局，但不强制所有样式通过 utility class 表达

### 环境变量

| 变量 | 用途 | 默认值 |
|------|------|--------|
| `VITE_API_PROXY_TARGET` | Vite 代理的后端地址 | `http://127.0.0.1:8100` |

## 开发命令

```bash
# 启动开发服务器
cd frontends/web && npm run dev

# 类型检查
npm run web:typecheck

# 代码检查
npm run web:lint

# 代码格式化
npm run web:format

# 运行测试
npm run web:test

# 测试覆盖率
npm run web:test -- --coverage

# 构建生产包
npm run web:build
```

所有命令也可通过根目录 workspace 脚本调用：

```bash
npm run web:dev       # 启动前端开发服务器
npm run web:lint      # 代码检查
npm run web:format    # 代码格式化
npm run web:test      # 运行前端测试
npm run web:typecheck # 类型检查
npm run web:build     # 生产构建
```

## 包间依赖关系

```
frontends/web
  ├── @jiandou/api     (OpenAPI 客户端)
  ├── @jiandou/domain  (领域模型)
  └── @jiandou/ui      (共享 UI 组件)
```

三个共享包均位于 `packages/` 目录，通过 npm workspace 协议关联。Vite 在开发期直接引用源码（`src/index.ts`），构建期使用编译后的 `dist/` 产物。
