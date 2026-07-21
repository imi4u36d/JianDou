# 前端架构

## 概览

JianDou 前端是一个基于 Vue 3 + TypeScript + Vite 的单页应用，采用 npm workspace 管理的 monorepo 结构。

渐进式拆分规则、文件大小回退保护和后续批次见[可维护性指南](maintainability.md)。

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
│   │       ├── features/        # 功能 API、纯展示转换与领域前端逻辑
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
- `generation.ts` — 生成选项、媒体生成、探测与用量 HTTP 编排；纯目录/运行响应收窄和请求映射位于 `generation-normalizers.ts`
- `workflows.ts` — 阶段工作流
- `credits.ts` — 积分查询
- `health.ts` — 健康检查
- `material-assets.ts` — 素材管理
- `runtime-config.ts` — 运行时配置加载

### 状态管理

项目采用 Vue 3 原生响应式 API 管理状态，未引入 Vuex 或 Pinia：

- **`auth/session.ts`** — 全局登录态，通过 `reactive()` 存储，`useAuthSessionState()` 暴露计算属性
- **Composables** — 各模块通过 `use*` composable 管理局部状态与副作用

工作台生成表单由 `composables/home/useGenerationForm.ts` 管理输入状态、配置/积分加载和跨字段 watch；积分/时长/模型标签、种子能力提示、模式提交文案和提交就绪规则由 `useGenerationFormPresentation.ts` 管理；响应式模型目录派生、模型支持尺寸、可用画幅、视频时长和当前尺寸解析由 `useGenerationFormCatalog.ts` 管理。模型名称归一化、种子校验、尺寸解析、画幅匹配与质量标签等纯规则集中在 `generationFormOptions.ts`，以便脱离 Vue 生命周期进行单元测试。

首页参考图的读取、上传、重编号、`@图片N` 提及重映射和编辑器交互由 `useReferenceImages.ts` 管理；展开/收起卡片的投影间距、旋转、层级、底部补偿和添加卡位置属于无 Vue 依赖的 `referenceImageLayout.ts`，避免视觉数学与文件副作用交织。

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

大型视图只负责路由、页面级状态和功能组合。无副作用的状态标签、格式化和视图模型转换放在 `features/<domain>/*-presenters.ts`，交互状态与副作用放在 `composables/`，可独立交互的模板区域继续拆成子组件。

通用 `AppPreviewDialog.vue` 只保留 Teleport 模板和事件绑定；媒体加载、下载反馈、方向键导航、触摸滑动与焦点恢复状态位于 `components/common/useAppPreviewDialog.ts`，视觉样式位于 `components/common/app-preview-dialog.css`。素材库和任务详情共享该行为边界。

全局 `AuthDialog.vue` 只保留登录/激活表单模板和密码可见性绑定；会话提交、错误反馈、关闭保护、首字段聚焦和触发元素焦点恢复由可注入依赖的 `components/auth/useAuthDialog.ts` 管理，视觉样式位于 `components/auth/auth-dialog.css`。独立登录页与邀请码激活页共享 `AuthStandaloneForm.vue` 及 `auth-standalone-form.css`，页面自身只保留对应会话命令和路由编排；前台、管理端与路由守卫共同使用 `auth/redirect.ts` 校验站内跳转目标。

所有前台路由共享的 `WorkspaceShell.vue` 只维护导航项、路由高亮和内容插槽，整体布局样式位于 `workspace-shell.css`。积分读取、账户弹层、管理员入口、退出、路由同步和外部点击关闭由 `WorkspaceAccountMenu.vue` 及其同目录样式管理。

`CreditDetailsDialog.vue` 只维护积分摘要、分页加载、充值弹层和复制交互，完整视觉样式位于 `credit-details-dialog.css`；数值、时间、功能编码和交易类型展示规则统一位于 `features/credits/credit-details-presenters.ts`。

`StageWorkflowView` 已将项目导航及其搜索、筛选、滚动分页和观察器生命周期拆到 `WorkflowProjectDrawer.vue`。工作流标题、参数摘要和设置表单由 `WorkflowHeaderSettings.vue` 管理，字段变更通过不可变 `WorkflowSettingsDraft` 事件回传；草稿默认值、详情映射、校验和 API 请求组装统一位于 `features/workflows/workflow-settings.ts`，供现行页面与统一工作区复用。故事板、角色、关键帧、视频和最终成片区域均由独立组件管理；角色摘要与原图预览覆盖层分别位于 `CharacterSummaryDialog.vue` 和 `ImagePreviewOverlay.vue`。`useWorkflowStageReadiness.ts` 由现行页面与统一工作区共同使用，统一计算角色缺口、视频就绪度、五阶段状态和成片提示；`useWorkflowStagePreviews.ts` 由两套工作流详情共同维护跨阶段预览选择、镜头选择、分镜调整草稿及详情刷新后的选择修复。公共 `useWorkflowPreviewInteractions.ts` 统一管理角色摘要、关键帧画廊、失败图片状态和键盘生命周期；详情路由、请求、草稿同步和刷新由 `useStageWorkflowDetailLoader.ts` 管理；下载反馈、版本菜单定位及全局菜单关闭生命周期由 `useStageWorkflowInteractions.ts` 管理；`useWorkflowStageCommands.ts` 通过可注入 API 封装常规生成、选择、调整和成片命令；版本删除、阶段清空和素材复用与统一工作区共享 `useWorkflowVersionCommands.ts`；设置保存、缺失角色批量生成、角色素材选择及工作流删除由 `useStageWorkflowManagementCommands.ts` 管理。页面只保留展示状态和组合装配。

`MaterialLibraryView` 的 URL、媒体类型、宽高比、卡片样式和分镜预览转换位于 `features/materials/material-library-presenters.ts`。单张素材的预览降级、批量选择、收藏入口和操作菜单封装在 `MaterialAssetCard.vue`；收藏夹弹窗及其表单状态封装在 `MaterialFavoriteDialog.vue`。`useMaterialLibraryState.ts` 管理标签页、筛选、批量选择、收藏夹素材投影、查询参数和空状态文案；`useMaterialLibraryLifecycle.ts` 管理鉴权首屏加载、路由筛选初始化、选中项回收、无限滚动观察器和监听器清理；`useMaterialPreview.ts` 管理预览弹窗、媒体映射、前后导航和素材更新同步；`useMaterialPagination.ts` 管理并发请求失效、首屏替换、游标追加、去重和缓存回调；`useMaterialFavoriteCommands.ts` 管理收藏夹加载、创建、重命名、删除、单项/批量成员变更及缺失素材回填；`useMaterialAssetCommands.ts` 管理素材重命名、上传、单项/批量删除、复用、下载和鉴权反馈。页面只保留命令编排和功能组合。

图片任务侧栏 `ImageTaskListPanel.vue` 只组合搜索、状态筛选、列表项和空状态，视觉规则位于 `image-task-list-panel.css`。可视高度页容量计算、滚动触底、IntersectionObserver/ResizeObserver 装配与销毁统一由 `useImageTaskListViewport.ts` 管理，组件继续通过既有事件向页面请求分页和刷新。

`HomeView` 的页面级样式位于 `home-view.css`。品牌 SVG、交互状态类和动画关键帧作为整体封装在 `views/home/components/HomeBrandPlay.vue` 与同目录 CSS 中。类型、比例、模型、引用、数量和种子菜单由 `HomeComposerToolbar.vue` 通过显式 props/events 管理，专属响应式样式位于 `home-composer-toolbar.css`。任务提交提示和进行中任务列表分别由 `HomeTaskToast.vue`、`HomeActiveTasks.vue` 管理，任务进度、阶段和时间展示规则位于 `features/home/active-task-presenters.ts`。提示词模板合并、提交指纹及图片/视频请求构建位于 `features/home/home-submission.ts`，提交中、防重复和提示条计时状态位于 `useHomeSubmissionGuard.ts`；菜单、模式/比例选择、模板应用、积分入口、提交快照和成功后重置由可注入依赖的 `useHomeComposerControls.ts` 管理；鉴权、图片/视频分流、API、默认比例保存、Toast、错误反馈和路由事务由 `useHomeComposerSubmission.ts` 管理；编辑器外部同步、参考图桥接、积分刷新、全局菜单事件和卸载清理由 `useHomeComposerLifecycle.ts` 管理。`usePromptEditor.ts` 只管理 Vue 状态、IME 和输入事件编排，contenteditable 文本序列化、引用芯片 DOM、光标偏移恢复及选区插入属于 `prompt-editor-dom.ts`。页面只组合展示状态与功能协作者。

旧 `components/generate` 目录中的 `GenerateFormCard`、`TaskProgressCard` 和 `useTaskProgress` 已无任何路由、页面或组件消费者，且功能已由 `HomeView`、`ImageTaskView` 与统一任务视图接管，因此整组删除，避免为历史平行实现继续维护表单、轮询和样式契约。

`PromptTemplateGallery.vue` 只维护选中预览和应用事件；模板 ID、标题、标签、提示词和静态图片路径统一位于 `components/home/prompt-templates.ts`，画廊与预览布局样式位于 `components/home/prompt-template-gallery.css`，避免内容目录和视觉规则重新进入组件脚本。

统一工作区的 `TaskDetailPanel.vue` 只组合详情标题、失败提示、结果和弹窗；页面剩余样式位于 `task-detail-panel.css`。状态驱动的刷新、提示词、重试、暂停、继续、终止和删除操作入口由 `TaskDetailActions.vue` 及专属样式管理。任务阶段时间线由 `TaskStageTimeline.vue` 与 `task-stage-timeline.css` 管理，监控和产物摘要由 `TaskMonitoringSummary.vue` 与 `task-monitoring-summary.css` 管理。提示词弹窗由 `TaskPromptDialog.vue` 管理内容、焦点、Esc/遮罩关闭和响应式样式。`TaskResultPreview.vue` 管理参考图堆叠、图片/视频预览及预览/下载事件；`useTaskPreviewState.ts` 管理媒体加载状态、类型识别和预览弹窗。详情请求串行号、完成态预览补拉和轮询启停属于 `useTaskDetailLoader.ts`；鉴权、确认及重试/暂停/继续/终止/删除事务属于可注入依赖的 `useTaskDetailCommands.ts`。任务类型、阶段状态、阶段耗时、监控值、路径缩写和失败上下文等纯展示规则位于 `views/unified/features/task-detail-presenters.ts`，`useTaskDetail.ts` 只组合响应式展示状态和这些协作者。

无路由、无组件消费者且不属于待执行融合方案的 `WorkflowResultPanel.vue` 已删除。`CreateTaskDialog.vue`、`WorkflowDetailPanel.vue` 和 `useWorkflowDetail.ts` 虽尚未接入现行路由，但被 `merge-task-into-workflow.md` 明确列为后续统一任务系统的目标资产；在该方案启动前不得把它们误判为普通死代码。`CreateTaskDialog.vue` 只保留表单视图，焦点恢复、目录加载、鉴权与创建事务由 `useCreateTaskDialog.ts` 管理，模型和视频尺寸选择规则位于 `features/create-task-options.ts`，样式位于 `create-task-dialog.css`。`WorkflowDetailPanel.vue` 的页面样式位于 `workflow-detail-panel.css`，并与现行页面直接共享 `WorkflowStoryboardBoard.vue`、`WorkflowKeyframeBoard.vue`、`WorkflowVideoBoard.vue`、`WorkflowFinalBoard.vue`、`WorkflowHeaderSettings.vue`、`CharacterSummaryDialog.vue` 和 `ImagePreviewOverlay.vue`；角色素材搜索与结果网格仍由 `WorkflowCharacterAssetPicker.vue` 及专属样式管理。头部状态/进度投影与 AutoPilot 装配由 `useWorkflowDetailHeader.ts` 管理，自动执行状态条由 `WorkflowAutoPilotBar.vue` 及其专属样式管理。后端 AutoPilot 状态初始化、任务日志去重、工作流切换清理和轮询启停统一由 `useWorkflowAutoPilotSync.ts` 管理。`useWorkflowDetail.ts` 的跨阶段预览与镜头选择复用公共 `useWorkflowStagePreviews.ts`；错误摘要、关键帧预览帧、工作流状态和头部标签规则位于 `views/unified/features/workflow-detail-presenters.ts`；图片失败状态、角色摘要、关键帧画廊、键盘导航和版本菜单定位通过适配器复用公共 `composables/workflow/useWorkflowPreviewInteractions.ts`；详情请求、路由舞台同步、轮询合并和设置草稿由 `useWorkflowDetailLoader.ts` 管理，并通过单一预览同步端口修复刷新后的选择；需要鉴权与确认的版本删除、整阶段清空和素材复用事务由可注入依赖的 `useWorkflowVersionCommands.ts` 管理；设置更新、故事板/角色/关键帧/视频生成及版本选择由可注入依赖的 `useWorkflowGenerationCommands.ts` 管理。组合式函数只继续负责状态组合和生命周期装配。当前线上工作流仍由 `StageWorkflowView.vue` 及其 `views/workflow/components` 子组件提供。

### 管理后台

管理后台在路由器匹配到 `/admin` 路径时动态加载 Element Plus 及管理端样式，避免影响前台的包体积。管理端组件位于 `src/admin/` 目录下。

`DashboardView.vue` 只组合概览卡片、系统脉搏、队列和任务表格，页面样式位于 `dashboard-view.css`。概览与用户请求的并发加载、部分失败保留和刷新状态由可注入依赖的 `admin/composables/useAdminDashboard.ts` 管理；统计卡片、脉搏指标、状态标签、风险标签、日期和进度转换位于 `admin/features/dashboard/dashboard-presenters.ts`。

`TaskManagementView.vue` 的状态标签、时长/进度摘要、请求参数、执行信息、失败信息和产物目录展示统一由 `admin/features/tasks/task-management-presenters.ts` 生成。列表分页、筛选请求、详情缓存、展开状态、跨页选中项回收和加载错误由 `admin/composables/useAdminTaskList.ts` 管理；终止、删除、批量确认、部分失败选中项回收和成功提示由 `admin/composables/useAdminTaskCommands.ts` 管理。表格展开区由 `admin/components/AdminTaskDetailExpansion.vue` 及其同目录样式管理，页面样式位于 `task-management-view.css`；主页面只保留列表模板、表格交互和组合式函数装配。

`TaskDetailView.vue` 的创建参数、时长诊断、监控目录、诊断严重度和 Trace 摘要由 `admin/features/tasks/admin-task-detail-presenters.ts` 统一生成。任务概览、创建参数、监控、时长诊断、产物目录和计划表由 `AdminTaskOverviewCard.vue` 及专属样式承载；页面样式位于 `task-detail-view.css`，页面只编排详情、Trace、诊断加载以及重试/删除路由动作。

`UserManagementView.vue` 只组合用户表格、分页和弹窗，列表样式位于 `user-management-view.css`，日期和模型类型展示转换由 `admin/features/users/user-management-presenters.ts` 管理。用户编辑、密码重置和模型 Key 三类表单由 `admin/components/UserManagementDialogs.vue` 及其同目录样式统一管理，并通过更新事件回传表单快照，避免子组件直接修改 props。列表加载、筛选分页、弹窗状态以及用户、密码、状态和模型 Key 命令统一由可注入依赖的 `admin/composables/useUserManagement.ts` 管理。

`CreditManagementView.vue` 只组合用户、规则和流水模板；页面样式位于 `credit-management-view.css`。加载、弹窗、校验、调整和规则更新状态由可注入依赖的 `admin/composables/useCreditManagement.ts` 管理，管理端专属日期、金额和流水标签规则位于 `admin/features/credits/credit-management-presenters.ts`。

`InviteManagementView.vue` 只组合统计卡片、邀请表格与创建弹窗；加载、创建、复制、撤销确认和刷新状态由可注入依赖的 `admin/composables/useInviteManagement.ts` 管理，统计、时间、操作人和状态标签转换位于 `admin/features/invites/invite-management-presenters.ts`，页面样式位于 `invite-management-view.css`。

## 关键约定

### 命名规范

- 文件名：PascalCase（Vue 组件）、kebab-case（工具函数、composables）
- 组件 Props：camelCase
- API 函数：`fetch*` / `create*` / `update*` / `delete*`

### 类型安全

所有 API 响应和请求体都必须有 TypeScript 接口定义。`src/types/index.ts` 是纯兼容 barrel，不承载领域契约；`generation.ts` 也是生成领域 barrel，其任务与上传、选项目录、媒体调用、管理端模型配置契约分别位于对应子文件。`task.ts` 统一导出任务列表与规划、产物素材、执行诊断、详情快照四个子领域。`workflow.ts` 是工作流兼容 barrel，工作流聚合、素材库、阶段版本契约分别由 `workflow-core.ts`、`workflow-material.ts`、`workflow-stage.ts` 承载。认证、管理端、积分、健康检查和素材请求分别位于同名领域文件。新增类型应优先进入对应文件，再由 barrel 统一导出，避免恢复单体类型文件。

通用选择器 `AppSelect.vue` 只保留可访问模板和 props/events 装配；弹层定位、全局监听器生命周期、禁用项跳过、键盘状态机和选项状态位于 `useAppSelectInteraction.ts`，公开选项/变体类型位于 `app-select.ts`。视觉规则位于同目录 `app-select.css`，并通过 scoped 外部样式接入。点击选择和键盘跳过禁用项均由独立组件测试覆盖，后续变体不应重新堆回单文件。

### 样式策略

- 全局变量（颜色、间距）通过 CSS 自定义属性定义在 `tailwind.css` 中
- 组件级样式使用 Vue 的 `<style scoped>` 块；大型视图可以使用带 `scoped` 的外部 `src` 样式文件，并在子组件拆分时同步迁移对应样式
- 工作流画布按舞台拆分组件；`WorkflowStoryboardBoard.vue` 已独立承载分镜版本预览、选择和调整交互，页面层只保留 API 编排与共享状态
- `WorkflowCharacterBoard.vue` 独立承载角色版本、三视图、素材检索与选择界面；工作流页面仅处理生成、选用和详情刷新等跨舞台编排
- `WorkflowKeyframeBoard.vue` 独立承载镜头导航、关键帧版本、首尾帧预览与单帧操作，页面层继续统一处理 API 调用和工作流刷新
- `WorkflowVideoBoard.vue` 独立承载视频就绪度、镜头导航、输入关键帧、视频版本与播放/下载操作；页面层保留跨舞台拼接条件和副作用编排
- `WorkflowFinalBoard.vue` 与 `WorkflowMissingClips.vue` 独立承载成片播放、拼接就绪度、缺失镜头导航与下载操作
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
