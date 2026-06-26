<template>
  <section class="task-page">
    <div class="task-page__summary">
      <el-card
        v-for="item in summaryCards"
        :key="item.label"
        class="surface-card task-page__summary-card"
        shadow="never"
      >
        <p>{{ item.label }}</p>
        <strong>{{ item.value }}</strong>
        <span>{{ item.note }}</span>
      </el-card>
    </div>

    <div v-if="initialLoading" class="task-page__summary">
      <div v-for="n in 4" :key="n" class="skeleton-card">
        <el-skeleton :rows="3" animated />
      </div>
    </div>

    <transition name="fade" mode="out-in">
      <div v-show="!initialLoading" key="content">
        <el-card class="surface-card" shadow="never">
          <template #header>
            <div class="task-page__toolbar">
              <div class="task-page__toolbar-spacer" aria-hidden="true"></div>
              <div class="task-page__toolbar-actions">
                <el-button plain @click="resetFilters">重置</el-button>
                <el-button
                  plain
                  type="danger"
                  :disabled="selectedTerminableIds.length === 0 || actionLoading"
                  :loading="actionLoading"
                  @click="terminateSelected"
                >
                  批量终止
                </el-button>
                <el-button
                  plain
                  type="danger"
                  :disabled="selectedTasks.length === 0 || actionLoading"
                  :loading="actionLoading"
                  @click="deleteSelected"
                >
                  批量删除
                </el-button>
                <el-button :icon="Refresh" plain @click="loadTasks">刷新</el-button>
              </div>
            </div>
          </template>

          <el-form class="task-page__filters" inline @submit.prevent="loadTasks">
            <el-form-item label="关键词">
              <el-input v-model.trim="filters.q" clearable placeholder="任务或素材" />
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="filters.status" clearable placeholder="全部状态" style="width: 180px">
                <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
            <el-form-item label="排序">
              <el-select v-model="filters.sort" placeholder="排序方式" style="width: 180px">
                <el-option v-for="item in sortOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
            <el-form-item class="task-page__filters-action">
              <el-button :loading="refreshing" native-type="submit" type="primary">查询</el-button>
            </el-form-item>
          </el-form>

          <el-alert
            v-if="successMessage"
            :closable="false"
            class="task-page__alert"
            show-icon
            type="success"
            :title="successMessage"
          />

          <el-table
            ref="taskTable"
            v-loading="refreshing"
            :data="tasks"
            :expand-row-keys="expandedTaskIds"
            class="task-page__table"
            row-key="id"
            @expand-change="handleExpandChange"
            @row-click="handleRowClick"
            @selection-change="handleSelectionChange"
          >
            <el-table-column type="selection" width="48" />
            <el-table-column type="expand" width="48">
              <template #default="{ row }">
                <div class="task-page__detail-panel">
                  <div v-if="detailLoading[row.id]" class="task-page__detail-loading">
                    <el-skeleton :rows="4" animated />
                  </div>
                  <el-alert
                    v-else-if="detailErrors[row.id]"
                    :closable="false"
                    show-icon
                    type="error"
                    :title="detailErrors[row.id]"
                  />
                  <div v-else-if="expandedDetail(row)" class="task-page__detail-grid">
                    <section class="task-page__detail-section">
                      <div class="task-page__detail-section-head">
                        <h3>执行进度</h3>
                        <el-tag
                          :type="statusTagType(expandedDetail(row)?.status || row.status)"
                          effect="light"
                          size="small"
                        >
                          {{ statusLabel(expandedDetail(row)?.status || row.status) }}
                        </el-tag>
                      </div>
                      <div class="task-page__detail-progress">
                        <div class="task-page__detail-progress-head">
                          <strong>{{ detailProgressValue(row) }}%</strong>
                          <span>{{ progressHint(expandedDetail(row) || row) }}</span>
                        </div>
                        <el-progress :percentage="detailProgressValue(row)" :stroke-width="10" />
                      </div>
                      <dl class="task-page__detail-list">
                        <div v-for="item in executionRows(row)" :key="item.label">
                          <dt>{{ item.label }}</dt>
                          <dd>{{ item.value }}</dd>
                        </div>
                      </dl>
                    </section>

                    <section class="task-page__detail-section">
                      <div class="task-page__detail-section-head">
                        <h3>失败原因</h3>
                        <el-tag :type="failureTagType(row)" effect="light" size="small">{{
                          failureStateLabel(row)
                        }}</el-tag>
                      </div>
                      <el-alert
                        v-if="failureMessage(row)"
                        :closable="false"
                        show-icon
                        type="error"
                        :title="failureMessage(row)"
                      />
                      <div v-else class="task-page__detail-empty">暂无失败信息</div>
                      <dl class="task-page__detail-list task-page__detail-list--compact">
                        <div v-for="item in failureRows(row)" :key="item.label">
                          <dt>{{ item.label }}</dt>
                          <dd>{{ item.value }}</dd>
                        </div>
                      </dl>
                    </section>

                    <section class="task-page__detail-section task-page__detail-section--wide">
                      <div class="task-page__detail-section-head">
                        <h3>任务参数</h3>
                        <el-tag effect="plain" size="small">{{ requestDurationMode(row) }}</el-tag>
                      </div>
                      <dl class="task-page__detail-list task-page__detail-list--params">
                        <div v-for="item in requestRows(row)" :key="item.label">
                          <dt>{{ item.label }}</dt>
                          <dd>{{ item.value }}</dd>
                        </div>
                      </dl>
                      <div v-if="creativePrompt(row)" class="task-page__detail-text">
                        <strong>创意提示</strong>
                        <p>{{ creativePrompt(row) }}</p>
                      </div>
                      <div v-if="transcriptPreview(row)" class="task-page__detail-text">
                        <strong>正文预览</strong>
                        <p>{{ transcriptPreview(row) }}</p>
                      </div>
                      <el-collapse v-if="requestSnapshotJson(row)" class="task-page__detail-json">
                        <el-collapse-item title="原始请求参数" name="request">
                          <pre>{{ requestSnapshotJson(row) }}</pre>
                        </el-collapse-item>
                      </el-collapse>
                    </section>

                    <section class="task-page__detail-section task-page__detail-section--wide">
                      <div class="task-page__detail-section-head">
                        <h3>产物与监控</h3>
                        <el-tag effect="plain" size="small">{{ renderedClipLabel(expandedDetail(row) || row) }}</el-tag>
                      </div>
                      <dl class="task-page__detail-list task-page__detail-list--params">
                        <div v-for="item in outputRows(row)" :key="item.label">
                          <dt>{{ item.label }}</dt>
                          <dd>{{ item.value }}</dd>
                        </div>
                      </dl>
                    </section>
                  </div>
                  <div v-else class="task-page__detail-empty">点击展开后读取任务详情</div>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="任务信息" min-width="260">
              <template #default="{ row }">
                <div class="task-page__task-cell">
                  <strong>{{ row.title || "未命名任务" }}</strong>
                  <span>{{ row.id }}</span>
                  <span>{{ row.sourceFileName || "未记录素材文件" }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="创建人" min-width="180">
              <template #default="{ row }">
                <div class="task-page__owner-cell">
                  <strong>{{ row.ownerUsername }}</strong>
                  <el-tag v-if="row.ownerRole === 'ADMIN'" effect="plain" size="small" type="warning">管理员</el-tag>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="状态" min-width="120">
              <template #default="{ row }">
                <div class="task-page__status-cell">
                  <el-tag :type="statusTagType(row.status)" effect="light">{{ statusLabel(row.status) }}</el-tag>
                  <span>{{ row.currentStage || "等待处理" }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="进度" min-width="180">
              <template #default="{ row }">
                <div class="task-page__progress-cell">
                  <div class="task-page__progress-head">
                    <strong>{{ row.progress ?? 0 }}%</strong>
                    <span>{{ progressHint(row) }}</span>
                  </div>
                  <el-progress :percentage="row.progress ?? 0" :show-text="false" :stroke-width="8" />
                </div>
              </template>
            </el-table-column>
            <el-table-column label="任务参数" min-width="170">
              <template #default="{ row }">
                <div class="task-page__meta-cell">
                  <span>{{ row.aspectRatio || "比例未记录" }}</span>
                  <span>{{ durationLabel(row) }}</span>
                  <span>重试 {{ row.retryCount ?? 0 }} 次</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="素材 / 结果" min-width="150">
              <template #default="{ row }">
                <div class="task-page__meta-cell">
                  <span>素材 {{ row.sourceAssetCount ?? 0 }}</span>
                  <span>成片 {{ row.completedOutputCount ?? 0 }}</span>
                  <span>镜头 {{ renderedClipLabel(row) }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="创建时间" min-width="180">
              <template #default="{ row }">
                {{ formatDateTime(row.createdAt) }}
              </template>
            </el-table-column>
            <el-table-column label="更新时间" min-width="180">
              <template #default="{ row }">
                {{ formatDateTime(row.updatedAt) }}
              </template>
            </el-table-column>
            <el-table-column fixed="right" label="操作" min-width="160">
              <template #default="{ row }">
                <div class="task-page__action-cell">
                  <el-button
                    v-if="terminableStatus(row.status)"
                    link
                    type="warning"
                    :disabled="actionLoading"
                    @click.stop="terminateSingle(row)"
                  >
                    终止
                  </el-button>
                  <el-button link type="danger" :disabled="actionLoading" @click.stop="deleteSingle(row)">
                    删除
                  </el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>

          <div class="task-page__pagination">
            <el-pagination
              v-model:current-page="currentPage"
              v-model:page-size="pageSize"
              :total="totalTasks"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next, jumper"
              background
              @size-change="handleSizeChange"
              @current-change="handlePageChange"
            />
          </div>
        </el-card>
      </div>
    </transition>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Refresh } from "@element-plus/icons-vue";
import {
  bulkDeleteAdminTasks,
  bulkTerminateAdminTasks,
  deleteAdminTask,
  fetchAdminTask,
  fetchAdminTasks,
  terminateAdminTask,
} from "@/admin/features/tasks/services/taskService";
import type { AdminTaskListItem, AdminTaskSortMode, TaskDetail, TaskStatus } from "@/types";

const initialLoading = ref(true);
const refreshing = ref(false);
const actionLoading = ref(false);
const successMessage = ref("");
const taskTable = ref();
const tasks = ref<AdminTaskListItem[]>([]);
const selectedTasks = ref<AdminTaskListItem[]>([]);
const expandedTaskIds = ref<string[]>([]);
const taskDetails = reactive<Record<string, TaskDetail | undefined>>({});
const detailLoading = reactive<Record<string, boolean>>({});
const detailErrors = reactive<Record<string, string>>({});
const totalTasks = ref(0);
const currentPage = ref(1);
const pageSize = ref(20);
const filters = reactive({
  q: "",
  status: "" as TaskStatus | "",
  sort: "updated_desc" as AdminTaskSortMode,
});

const statusOptions: Array<{ label: string; value: TaskStatus }> = [
  { label: "排队中", value: "PENDING" },
  { label: "已暂停", value: "PAUSED" },
  { label: "分析中", value: "ANALYZING" },
  { label: "编排中", value: "PLANNING" },
  { label: "渲染中", value: "RENDERING" },
  { label: "已完成", value: "COMPLETED" },
  { label: "失败", value: "FAILED" },
];

const sortOptions: Array<{ label: string; value: AdminTaskSortMode }> = [
  { label: "最近更新", value: "updated_desc" },
  { label: "最新创建", value: "created_desc" },
  { label: "进度优先", value: "progress_desc" },
  { label: "状态优先", value: "status_desc" },
];

const summaryCards = computed(() => [
  { label: "全部任务", value: totalTasks.value, note: "当前筛选" },
  { label: "当前页", value: tasks.value.length, note: `每页 ${pageSize.value}` },
]);

const selectedTerminableIds = computed(() =>
  selectedTasks.value.filter((task) => terminableStatus(task.status)).map((task) => task.id),
);

function formatDateTime(value?: string | null) {
  if (!value) {
    return "未记录";
  }
  return new Date(value).toLocaleString();
}

function statusLabel(status: TaskStatus) {
  switch (status) {
    case "PENDING":
      return "排队中";
    case "PAUSED":
      return "已暂停";
    case "ANALYZING":
      return "分析中";
    case "PLANNING":
      return "编排中";
    case "RENDERING":
      return "渲染中";
    case "COMPLETED":
      return "已完成";
    case "FAILED":
      return "失败";
    default:
      return status;
  }
}

function statusTagType(status: TaskStatus) {
  switch (status) {
    case "COMPLETED":
      return "success";
    case "FAILED":
      return "danger";
    case "RENDERING":
    case "ANALYZING":
    case "PLANNING":
      return "warning";
    case "PAUSED":
      return "info";
    default:
      return "primary";
  }
}

function durationLabel(task: AdminTaskListItem) {
  if (task.minDurationSeconds && task.maxDurationSeconds) {
    return `${task.minDurationSeconds}-${task.maxDurationSeconds} 秒`;
  }
  if (task.minDurationSeconds) {
    return `${task.minDurationSeconds} 秒`;
  }
  if (task.maxDurationSeconds) {
    return `${task.maxDurationSeconds} 秒`;
  }
  return "时长未记录";
}

function renderedClipLabel(task: AdminTaskListItem | TaskDetail) {
  const rendered = task.renderedClipCount ?? 0;
  const planned = task.plannedClipCount ?? 0;
  if (planned > 0) {
    return `${rendered}/${planned}`;
  }
  return `${rendered}`;
}

function progressHint(task: AdminTaskListItem | TaskDetail) {
  if (task.status === "FAILED") {
    return task.diagnosisHint || "任务执行失败";
  }
  if (task.status === "COMPLETED") {
    return `已产出 ${task.completedOutputCount ?? 0} 个结果`;
  }
  if (task.queuePosition && task.queuePosition > 0) {
    return `队列第 ${task.queuePosition} 位`;
  }
  return task.currentStage || "等待处理";
}

function terminableStatus(status: TaskStatus) {
  return ["PENDING", "ANALYZING", "PLANNING", "RENDERING"].includes(status);
}

function expandedDetail(task: AdminTaskListItem) {
  return taskDetails[task.id];
}

function requestSnapshot(task: AdminTaskListItem) {
  const detail = expandedDetail(task);
  return (detail?.requestSnapshot ?? detail ?? task) as Record<string, unknown>;
}

function formatDetailValue(value: unknown, fallback = "暂无") {
  if (value == null) return fallback;
  if (typeof value === "boolean") return value ? "是" : "否";
  if (typeof value === "number") return Number.isFinite(value) ? String(value) : fallback;
  const text = String(value).trim();
  return text || fallback;
}

function formatSecondsValue(value: unknown) {
  if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) return "暂无";
  return `${Number.isInteger(value) ? value : value.toFixed(1)} 秒`;
}

function formatModelValue(value: unknown) {
  return formatDetailValue(value, "未指定");
}

function formatOutputCount(snapshot: Record<string, unknown>) {
  const count = snapshot.outputCount;
  if (count === "auto") return "自动";
  if (typeof count === "number" && count > 0) return String(count);
  if (count && typeof count === "object") {
    const value = count as { auto?: boolean; count?: number | string | null };
    if (value.auto) return "自动";
    return formatDetailValue(value.count, "默认");
  }
  return "默认";
}

function formatRequestedDuration(snapshot: Record<string, unknown>) {
  const value = snapshot.videoDurationSeconds;
  if (value === "auto") return "自动";
  if (typeof value === "number" && value > 0) return `${value} 秒`;
  return "未指定";
}

function formatSeed(task: AdminTaskListItem) {
  const detail = expandedDetail(task);
  const snapshot = requestSnapshot(task);
  const seed = detail?.taskSeed ?? task.taskSeed ?? snapshot.seed;
  if (typeof seed === "number" && Number.isFinite(seed)) return String(Math.trunc(seed));
  return "未设置";
}

function detailProgressValue(task: AdminTaskListItem) {
  const progress = expandedDetail(task)?.progress ?? task.progress ?? 0;
  return Math.min(100, Math.max(0, Math.trunc(progress)));
}

function requestDurationMode(task: AdminTaskListItem) {
  const mode = requestSnapshot(task).durationMode;
  return `时长模式 ${formatDetailValue(mode, "auto")}`;
}

function executionRows(task: AdminTaskListItem) {
  const detail = expandedDetail(task);
  const monitoring = detail?.monitoring;
  return [
    {
      label: "当前阶段",
      value: formatDetailValue(monitoring?.currentStage ?? detail?.currentStage ?? task.currentStage, "等待处理"),
    },
    { label: "Attempt 状态", value: formatDetailValue(monitoring?.activeAttemptStatus) },
    {
      label: "Worker",
      value: formatDetailValue(
        monitoring?.activeWorkerInstanceId ?? detail?.activeWorkerInstanceId ?? task.activeWorkerInstanceId,
      ),
    },
    {
      label: "队列位置",
      value:
        detail?.isQueued || task.isQueued
          ? formatDetailValue(detail?.queuePosition ?? task.queuePosition, "排队中")
          : "未排队",
    },
    { label: "恢复阶段", value: formatDetailValue(monitoring?.resumeFromStage) },
    { label: "恢复镜头", value: formatDetailValue(monitoring?.resumeFromClipIndex) },
    { label: "开始时间", value: formatDateTime(detail?.startedAt ?? task.startedAt) },
    { label: "结束时间", value: formatDateTime(detail?.finishedAt ?? task.finishedAt) },
  ];
}

function failureMessage(task: AdminTaskListItem) {
  const detail = expandedDetail(task);
  return formatDetailValue(detail?.failureReason || detail?.errorMessage || task.failureReason || "", "");
}

function failureStateLabel(task: AdminTaskListItem) {
  return failureMessage(task) ? "已记录" : "暂无";
}

function failureTagType(task: AdminTaskListItem) {
  return failureMessage(task) ? "danger" : "info";
}

function failureRows(task: AdminTaskListItem) {
  const detail = expandedDetail(task);
  return [
    { label: "错误消息", value: formatDetailValue(detail?.errorMessage || task.failureReason) },
    { label: "失败阶段", value: formatDetailValue(detail?.failureStage ?? task.failureStage) },
    { label: "失败镜头", value: formatDetailValue(detail?.failureClipIndex ?? task.failureClipIndex) },
    { label: "诊断提示", value: formatDetailValue(detail?.diagnosisHint ?? task.diagnosisHint) },
    { label: "推荐动作", value: formatDetailValue(detail?.recommendedAction ?? task.recommendedAction) },
  ];
}

function requestRows(task: AdminTaskListItem) {
  const detail = expandedDetail(task);
  const snapshot = requestSnapshot(task);
  return [
    { label: "任务类型", value: formatDetailValue(snapshot.taskType ?? detail?.taskType ?? task.taskType) },
    { label: "素材类型", value: formatDetailValue(snapshot.assetType) },
    { label: "画幅比例", value: formatDetailValue(snapshot.aspectRatio ?? detail?.aspectRatio ?? task.aspectRatio) },
    { label: "图片尺寸", value: formatModelValue(snapshot.imageSize) },
    { label: "视频清晰度", value: formatModelValue(snapshot.videoSize) },
    { label: "文本模型", value: formatModelValue(snapshot.textAnalysisModel) },
    { label: "关键帧模型", value: formatModelValue(snapshot.imageModel) },
    { label: "视频模型", value: formatModelValue(snapshot.videoModel) },
    { label: "输出数量", value: formatOutputCount(snapshot) },
    { label: "请求时长", value: formatRequestedDuration(snapshot) },
    { label: "生效时长", value: durationLabel(detail || task) },
    { label: "任务 Seed", value: formatSeed(task) },
    { label: "提前停止视频生成", value: snapshot.stopBeforeVideoGeneration ? "已启用" : "否" },
    { label: "文本输入", value: snapshot.transcriptText || detail?.transcriptPreview ? "已提供" : "无文本输入" },
  ];
}

function creativePrompt(task: AdminTaskListItem) {
  const detail = expandedDetail(task);
  return formatDetailValue(detail?.creativePrompt ?? requestSnapshot(task).creativePrompt, "");
}

function transcriptPreview(task: AdminTaskListItem) {
  const detail = expandedDetail(task);
  const text = formatDetailValue(detail?.transcriptPreview ?? requestSnapshot(task).transcriptText, "");
  return text.length > 220 ? `${text.slice(0, 220)}...` : text;
}

function requestSnapshotJson(task: AdminTaskListItem) {
  const snapshot = requestSnapshot(task);
  if (!Object.keys(snapshot).length) return "";
  return JSON.stringify(snapshot, null, 2);
}

function outputRows(task: AdminTaskListItem) {
  const detail = expandedDetail(task);
  const monitoring = detail?.monitoring;
  const directories = detail?.artifactDirectories ?? monitoring?.artifactDirectories;
  return [
    {
      label: "素材数量",
      value: formatDetailValue(detail?.sourceAssetCount ?? task.sourceAssetCount ?? detail?.sourceAssets?.length ?? 0),
    },
    {
      label: "结果数量",
      value: formatDetailValue(
        detail?.completedOutputCount ?? task.completedOutputCount ?? detail?.outputs?.length ?? 0,
      ),
    },
    {
      label: "计划镜头",
      value: formatDetailValue(monitoring?.plannedClipCount ?? detail?.plannedClipCount ?? task.plannedClipCount),
    },
    {
      label: "已生成镜头",
      value: formatDetailValue(monitoring?.renderedClipCount ?? detail?.renderedClipCount ?? task.renderedClipCount),
    },
    { label: "连续完成镜头", value: formatDetailValue(monitoring?.contiguousRenderedClipCount) },
    { label: "最新片段", value: formatDetailValue(monitoring?.latestRenderedClipIndex) },
    { label: "最新拼接", value: formatDetailValue(monitoring?.latestJoinName) },
    { label: "任务目录", value: formatDetailValue(directories?.baseRelativeDir ?? directories?.baseAbsoluteDir) },
    { label: "运行目录", value: formatDetailValue(directories?.runningRelativeDir ?? directories?.runningAbsoluteDir) },
    { label: "脚本文件", value: formatDetailValue(directories?.storyboardFileName) },
    { label: "源文件", value: formatDetailValue(detail?.sourceFileName ?? task.sourceFileName) },
    { label: "源文件列表", value: formatDetailValue(detail?.sourceFileNames?.join("、")) },
    {
      label: "输出时长",
      value: formatSecondsValue(
        (monitoring?.latestVideoOutput as { durationSeconds?: number } | undefined)?.durationSeconds,
      ),
    },
  ];
}

async function loadTaskDetail(taskId: string) {
  if (taskDetails[taskId] || detailLoading[taskId]) return;
  detailLoading[taskId] = true;
  detailErrors[taskId] = "";
  try {
    taskDetails[taskId] = await fetchAdminTask(taskId);
  } catch (error) {
    detailErrors[taskId] = error instanceof Error ? error.message : "读取任务详情失败";
  } finally {
    detailLoading[taskId] = false;
  }
}

function handleExpandChange(row: AdminTaskListItem, expandedRows: AdminTaskListItem[]) {
  expandedTaskIds.value = expandedRows.map((task) => task.id);
  if (expandedTaskIds.value.includes(row.id)) {
    void loadTaskDetail(row.id);
  }
}

function handleRowClick(row: AdminTaskListItem, column?: { type?: string; label?: string }) {
  if (column?.type === "selection" || column?.type === "expand" || column?.label === "操作") {
    return;
  }
  const expanding = !expandedTaskIds.value.includes(row.id);
  taskTable.value?.toggleRowExpansion(row, expanding);
  if (expanding) {
    void loadTaskDetail(row.id);
  }
}

function clearTaskDetails() {
  expandedTaskIds.value = [];
  Object.keys(taskDetails).forEach((key) => delete taskDetails[key]);
  Object.keys(detailLoading).forEach((key) => delete detailLoading[key]);
  Object.keys(detailErrors).forEach((key) => delete detailErrors[key]);
}

function handleSelectionChange(selection: AdminTaskListItem[]) {
  selectedTasks.value = selection;
}

async function loadTasks() {
  refreshing.value = true;
  successMessage.value = "";
  try {
    const offset = (currentPage.value - 1) * pageSize.value;
    const result = await fetchAdminTasks({
      ...filters,
      offset,
      limit: pageSize.value,
    });
    clearTaskDetails();
    tasks.value = result?.items ?? [];
    totalTasks.value = result?.total ?? 0;
    selectedTasks.value = selectedTasks.value.filter((selected) => tasks.value.some((task) => task.id === selected.id));
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "读取任务列表失败");
  } finally {
    if (initialLoading.value) {
      initialLoading.value = false;
    }
    refreshing.value = false;
  }
}

function handlePageChange() {
  void loadTasks();
}

function handleSizeChange() {
  currentPage.value = 1;
  void loadTasks();
}

async function terminateSingle(task: AdminTaskListItem) {
  try {
    await ElMessageBox.confirm(`确认终止任务"${task.title || task.id}"吗？终止后任务会进入失败状态。`, "终止任务", {
      confirmButtonText: "终止",
      cancelButtonText: "取消",
      type: "warning",
    });
    actionLoading.value = true;
    successMessage.value = "";
    await terminateAdminTask(task.id);
    selectedTasks.value = selectedTasks.value.filter((item) => item.id !== task.id);
    await loadTasks();
    successMessage.value = "任务已终止。";
    ElMessage.success("任务已终止");
  } catch (error) {
    if (error === "cancel") {
      return;
    }
    ElMessage.error(error instanceof Error ? error.message : "终止任务失败");
  } finally {
    actionLoading.value = false;
  }
}

async function terminateSelected() {
  const taskIds = selectedTerminableIds.value;
  if (taskIds.length === 0) {
    ElMessage.warning("请选择排队或执行中的任务");
    return;
  }
  try {
    await ElMessageBox.confirm(
      `确认终止选中的 ${taskIds.length} 个任务吗？已完成、失败或暂停任务不会被提交。`,
      "批量终止任务",
      {
        confirmButtonText: "批量终止",
        cancelButtonText: "取消",
        type: "warning",
      },
    );
    actionLoading.value = true;
    successMessage.value = "";
    const result = await bulkTerminateAdminTasks(taskIds);
    const failedIds = new Set(result.failed.map((item) => item.taskId));
    selectedTasks.value = result.failed.length ? selectedTasks.value.filter((task) => failedIds.has(task.id)) : [];
    await loadTasks();
    successMessage.value = result.failed.length
      ? `已终止 ${result.succeededTaskIds.length} 个任务，${result.failed.length} 个未成功。`
      : `已终止 ${result.succeededTaskIds.length} 个任务。`;
    ElMessage.success(successMessage.value);
  } catch (error) {
    if (error === "cancel") {
      return;
    }
    ElMessage.error(error instanceof Error ? error.message : "批量终止任务失败");
  } finally {
    actionLoading.value = false;
  }
}

async function deleteSingle(task: AdminTaskListItem) {
  try {
    await ElMessageBox.confirm(`确认删除任务"${task.title || task.id}"吗？删除后不可恢复。`, "删除任务", {
      confirmButtonText: "删除",
      cancelButtonText: "取消",
      type: "warning",
    });
    actionLoading.value = true;
    successMessage.value = "";
    await deleteAdminTask(task.id);
    selectedTasks.value = selectedTasks.value.filter((item) => item.id !== task.id);
    await loadTasks();
    successMessage.value = "任务已删除。";
    ElMessage.success("任务已删除");
  } catch (error) {
    if (error === "cancel") {
      return;
    }
    ElMessage.error(error instanceof Error ? error.message : "删除任务失败");
  } finally {
    actionLoading.value = false;
  }
}

async function deleteSelected() {
  const taskIds = selectedTasks.value.map((task) => task.id);
  if (taskIds.length === 0) {
    ElMessage.warning("请选择要删除的任务");
    return;
  }
  try {
    await ElMessageBox.confirm(`确认删除选中的 ${taskIds.length} 个任务吗？删除后不可恢复。`, "批量删除任务", {
      confirmButtonText: "批量删除",
      cancelButtonText: "取消",
      type: "warning",
    });
    actionLoading.value = true;
    successMessage.value = "";
    const result = await bulkDeleteAdminTasks(taskIds);
    const failedIds = new Set(result.failed.map((item) => item.taskId));
    selectedTasks.value = result.failed.length ? selectedTasks.value.filter((task) => failedIds.has(task.id)) : [];
    await loadTasks();
    successMessage.value = result.failed.length
      ? `已删除 ${result.succeededTaskIds.length} 个任务，${result.failed.length} 个未成功。`
      : `已删除 ${result.succeededTaskIds.length} 个任务。`;
    ElMessage.success(successMessage.value);
  } catch (error) {
    if (error === "cancel") {
      return;
    }
    ElMessage.error(error instanceof Error ? error.message : "批量删除任务失败");
  } finally {
    actionLoading.value = false;
  }
}

function resetFilters() {
  filters.q = "";
  filters.status = "";
  filters.sort = "updated_desc";
  currentPage.value = 1;
  void loadTasks();
}

onMounted(() => {
  void loadTasks();
});
</script>

<style scoped>
.task-page__summary {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.task-page > *,
.task-page .surface-card,
.task-page__summary,
.task-page__summary-card {
  min-width: 0;
  max-width: 100%;
}

.task-page__summary-card {
  border-radius: var(--jd-radius-card);
}

.task-page__summary-card :deep(.el-card__body) {
  display: grid;
  gap: 8px;
  padding: 16px;
}

.task-page__summary-card p {
  margin: 0;
  color: var(--jd-text-soft);
  font-size: 0.88rem;
}

.task-page__summary-card strong {
  font-family: inherit;
  font-size: 1.8rem;
  line-height: 1.05;
}

.task-page__summary-card span {
  color: var(--jd-text-soft);
  font-size: 0.92rem;
}

.task-page__toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 16px;
}

.task-page__toolbar-spacer {
  flex: 1 1 auto;
  min-width: 0;
}

.task-page__toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.task-page__filters {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 10px;
  margin-bottom: 14px;
  padding: 12px;
  border: 1px solid var(--jd-border);
  border-radius: var(--jd-radius-card);
  background: var(--jd-surface-muted);
}

.task-page__filters-action {
  margin-left: auto;
}

.task-page__alert {
  margin-bottom: 16px;
}

.task-page__table {
  width: 100%;
}

.task-page__task-cell,
.task-page__owner-cell,
.task-page__status-cell,
.task-page__meta-cell,
.task-page__progress-cell {
  display: grid;
  gap: 6px;
}

.task-page__task-cell strong,
.task-page__owner-cell strong,
.task-page__progress-head strong {
  color: var(--jd-text);
}

.task-page__task-cell span,
.task-page__owner-cell span,
.task-page__status-cell span,
.task-page__meta-cell span,
.task-page__progress-head span {
  color: var(--jd-text-soft);
  font-size: 0.88rem;
}

.task-page__progress-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.task-page__action-cell {
  display: flex;
  align-items: center;
  gap: 4px;
}

.task-page__muted-action {
  color: var(--jd-text-soft);
  display: inline-flex;
  justify-content: center;
  min-width: 32px;
  font-size: 0.86rem;
}

.task-page__pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--jd-border);
}

.task-page__detail-panel {
  padding: 14px 18px 18px;
  background: var(--jd-surface-muted);
}

.task-page__detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.task-page__detail-section {
  min-width: 0;
  padding: 14px;
  border: 1px solid var(--jd-border);
  border-radius: var(--jd-radius-card);
  background: var(--jd-surface);
}

.task-page__detail-section--wide {
  grid-column: 1 / -1;
}

.task-page__detail-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}

.task-page__detail-section-head h3 {
  margin: 0;
  color: var(--jd-text);
  font-size: 0.94rem;
  font-weight: 850;
}

.task-page__detail-progress {
  margin-bottom: 12px;
}

.task-page__detail-progress-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.task-page__detail-progress-head strong {
  color: var(--jd-text);
  font-size: 1.12rem;
}

.task-page__detail-progress-head span,
.task-page__detail-empty {
  color: var(--jd-text-soft);
  font-size: 0.86rem;
}

.task-page__detail-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 12px;
  margin: 0;
}

.task-page__detail-list--compact {
  margin-top: 12px;
}

.task-page__detail-list--params {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.task-page__detail-list div {
  min-width: 0;
  padding: 8px 10px;
  border: 1px solid var(--jd-border);
  border-radius: 8px;
  background: var(--jd-surface-muted);
}

.task-page__detail-list dt {
  margin: 0 0 4px;
  color: var(--jd-text-soft);
  font-size: 0.78rem;
  font-weight: 780;
}

.task-page__detail-list dd {
  margin: 0;
  color: var(--jd-text);
  font-size: 0.88rem;
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.task-page__detail-text {
  margin-top: 12px;
  padding: 10px 12px;
  border: 1px solid var(--jd-border);
  border-radius: 8px;
  background: var(--jd-surface-muted);
}

.task-page__detail-text strong {
  display: block;
  color: var(--jd-text);
  font-size: 0.82rem;
  font-weight: 850;
}

.task-page__detail-text p {
  max-height: 120px;
  margin: 6px 0 0;
  overflow: auto;
  color: var(--jd-text-soft);
  font-size: 0.88rem;
  line-height: 1.65;
  overflow-wrap: anywhere;
}

.task-page__detail-json {
  margin-top: 12px;
}

.task-page__detail-json pre {
  max-height: 260px;
  margin: 0;
  overflow: auto;
  color: var(--jd-text);
  font-size: 0.78rem;
  line-height: 1.55;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.task-page__detail-loading,
.task-page__detail-empty {
  min-height: 80px;
}

@media (max-width: 1200px) {
  .task-page__summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .task-page__detail-list--params {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .task-page__summary {
    grid-template-columns: 1fr;
  }

  .task-page__toolbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .task-page__toolbar-actions {
    width: 100%;
  }

  .task-page__toolbar-actions :deep(.el-button) {
    flex: 1;
  }

  .task-page__detail-panel {
    padding: 12px;
  }

  .task-page__detail-grid,
  .task-page__detail-list,
  .task-page__detail-list--params {
    grid-template-columns: 1fr;
  }
}
</style>
