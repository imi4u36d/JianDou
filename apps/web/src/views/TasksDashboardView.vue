<template>
  <section class="tasks-dashboard-view space-y-5">
    <header class="surface-panel p-5 md:p-6">
      <p class="text-xs font-semibold uppercase tracking-[0.26em] text-slate-500">AI Video</p>
      <div class="mt-2 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 class="text-3xl font-semibold tracking-[-0.03em] text-slate-900">任务管理</h1>
          <p class="mt-2 max-w-3xl text-sm text-slate-600">
            左侧筛选任务，右侧默认查看全部任务卡片，点击后在当前页展开详情。
          </p>
        </div>
        <span class="surface-chip">最近刷新 {{ lastRefreshLabel }}</span>
      </div>
    </header>

    <div v-if="loadError" class="surface-tile border border-rose-200 bg-rose-50/90 p-4 text-sm text-rose-700">
      {{ loadError }}
    </div>

    <div class="layout-grid">
      <TaskSidebarLite
        :keyword="keyword"
        :status="status"
        :platform="platform"
        :platform-options="platformOptions"
        :loading="tasksLoading"
        :metrics="metrics"
        :result-count="filteredTasks.length"
        @update:keyword="keyword = $event"
        @update:status="status = $event"
        @update:platform="platform = $event"
        @refresh="refreshAll"
      />

      <div class="space-y-5">
        <section class="surface-panel p-5 md:p-6">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">任务卡片</p>
              <h2 class="mt-1 text-2xl font-semibold tracking-[-0.03em] text-slate-900">
                {{ filteredTasks.length ? `共 ${filteredTasks.length} 个任务` : "暂无匹配任务" }}
              </h2>
            </div>
            <div class="flex flex-wrap gap-2">
              <span class="surface-chip">总任务 {{ tasks.length }}</span>
              <span v-if="selectedTask" class="surface-chip">当前展开 {{ selectedTask.title }}</span>
            </div>
          </div>

          <div v-if="tasksLoading && !tasks.length" class="surface-tile mt-4 p-5 text-sm text-slate-600">
            正在加载任务...
          </div>
          <div v-else-if="!filteredTasks.length" class="surface-tile mt-4 p-5 text-sm text-slate-600">
            没有匹配的任务，调整左侧筛选后再试。
          </div>
          <div v-else class="task-grid mt-5">
            <TaskCard
              v-for="task in filteredTasks"
              :key="task.id"
              :busy="managingTaskId === task.id"
              :task="task"
              :selectable="true"
              :selected="selectedTaskId === task.id"
              :show-clone-action="false"
              :show-retry-action="task.sourceKind === 'task'"
              :show-delete-action="task.sourceKind === 'task'"
              @select="handleSelectTask(task)"
              @retry="handleRetry(task)"
              @delete="handleDelete(task)"
            />
          </div>
        </section>

        <TaskDetailPanelLite
          :task="selectedTask"
          :trace="selectedTrace"
          :storage-base-url="storageBaseUrl"
          :loading="detailLoading"
          :trace-loading="traceLoading"
        />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { fetchAgentRun, fetchAgentRuns } from "@/api/agents";
import { getRuntimeConfig } from "@/api/runtime-config";
import { deleteTask, fetchTask, fetchTaskTrace, fetchTasks, retryTask } from "@/api/tasks";
import TaskCard from "@/components/TaskCard.vue";
import TaskDetailPanelLite from "@/components/tasks-lite/TaskDetailPanelLite.vue";
import TaskSidebarLite from "@/components/tasks-lite/TaskSidebarLite.vue";
import type {
  AgentRunArtifact,
  AgentRunDetail,
  AgentRunEvent,
  AgentRunStatus,
  AgentRunSummary,
  TaskDetail,
  TaskListItem,
  TaskMaterial,
  TaskOutput,
  TaskStatus,
  TaskTraceEvent,
} from "@/types";
import { getTaskLifecycleGroup } from "@/utils/task";

type DashboardTaskListItem = TaskListItem & {
  sourceKind: "task" | "agent-run";
};

type DashboardTaskDetail = TaskDetail & {
  sourceKind: "task" | "agent-run";
  remoteTaskId?: string | null;
};

const route = useRoute();
const router = useRouter();

const tasks = ref<DashboardTaskListItem[]>([]);
const selectedTaskId = ref("");
const selectedTask = ref<DashboardTaskDetail | null>(null);
const selectedTrace = ref<TaskTraceEvent[]>([]);
const tasksLoading = ref(false);
const detailLoading = ref(false);
const traceLoading = ref(false);
const loadError = ref("");
const keyword = ref("");
const status = ref<TaskStatus | "all">("all");
const platform = ref<string | "all">("all");
const lastRefreshAt = ref("");
const managingTaskId = ref("");

let pollTimer: ReturnType<typeof setInterval> | null = null;

const storageBaseUrl = computed(() => getRuntimeConfig().storageBaseUrl);

function asRecord(value: unknown) {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

function asString(value: unknown) {
  return typeof value === "string" ? value.trim() : "";
}

function asNumber(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function extractTaskIdFromText(value: unknown) {
  if (typeof value !== "string" || !value.trim()) {
    return "";
  }
  const markerMatch = value.match(/\[seeddance_task_id=([^\]]+)\]/i);
  if (markerMatch?.[1]) {
    return markerMatch[1].trim();
  }
  const genericMatch = value.match(/\btask[_\s-]*id[:=\s]+([A-Za-z0-9._:-]+)/i);
  if (genericMatch?.[1]) {
    return genericMatch[1].trim();
  }
  return "";
}

function isAgentRunId(taskId: string) {
  return taskId.startsWith("run_");
}

function agentRunStatusToTaskStatus(statusValue: AgentRunStatus): TaskStatus {
  switch (statusValue) {
    case "completed":
      return "COMPLETED";
    case "failed":
      return "FAILED";
    case "running":
      return "RENDERING";
    case "queued":
    case "idle":
    default:
      return "PENDING";
  }
}

function agentEventToTraceItem(event: AgentRunEvent): TaskTraceEvent {
  return {
    timestamp: event.timestamp,
    level: event.level.toUpperCase(),
    stage: event.stage,
    event: event.event,
    message: event.message,
    payload: event.payload ?? {},
  };
}

function pickAgentRunError(detail: AgentRunDetail) {
  const outputError = asString(detail.output?.error);
  if (outputError) {
    return outputError;
  }
  const monitorError = asString(detail.monitor?.error);
  if (monitorError) {
    return monitorError;
  }
  const reversedEvents = [...detail.events].reverse();
  return reversedEvents.find((item) => item.level === "error")?.message ?? "";
}

function pickAgentRunRemoteTaskId(detail: AgentRunDetail) {
  const monitor = asRecord(detail.monitor) ?? {};
  const output = asRecord(detail.output) ?? {};
  const fromMonitor = asString(monitor.lastSeeddanceTaskId) || asString(monitor.taskId);
  if (fromMonitor) {
    return fromMonitor;
  }
  const fromOutput = asString(output.taskId) || extractTaskIdFromText(output.error);
  if (fromOutput) {
    return fromOutput;
  }
  const reversedEvents = [...detail.events].reverse();
  for (const item of reversedEvents) {
    const payload = asRecord(item.payload) ?? {};
    const payloadTaskId = asString(payload.taskId) || asString(payload.task_id);
    if (payloadTaskId) {
      return payloadTaskId;
    }
    const details = asRecord(payload.details) ?? {};
    const detailTaskId = asString(details.taskId) || asString(details.task_id);
    if (detailTaskId) {
      return detailTaskId;
    }
    const fromMessage = extractTaskIdFromText(item.message);
    if (fromMessage) {
      return fromMessage;
    }
  }
  return extractTaskIdFromText(pickAgentRunError(detail));
}

function buildAgentOutputs(detail: AgentRunDetail): TaskOutput[] {
  const output = asRecord(detail.output) ?? {};
  const defaultDuration = Math.max(0, Math.round(asNumber(output.durationSeconds) ?? 0));
  const videoArtifacts = detail.artifacts.filter((artifact) => {
    const kind = (artifact.kind || "").toLowerCase();
    const mimeType = (artifact.mimeType || "").toLowerCase();
    return Boolean(artifact.url) && (kind.includes("video") || mimeType.startsWith("video/"));
  });
  return videoArtifacts.map((artifact, index) => {
    const json = asRecord(artifact.json) ?? {};
    const durationSeconds = Math.max(0, Math.round(asNumber(json.durationSeconds) ?? defaultDuration));
    return {
      id: `${detail.id}-${artifact.kind}-${index}`,
      clipIndex: index + 1,
      title: artifact.label || `结果 ${index + 1}`,
      reason: artifact.kind === "stitched-video" ? detail.summary : "AI 剧生成片段",
      startSeconds: 0,
      endSeconds: durationSeconds,
      durationSeconds,
      previewUrl: artifact.url || "",
      downloadUrl: artifact.url || "",
    };
  });
}

function buildAgentMaterials(detail: AgentRunDetail): TaskMaterial[] {
  return detail.artifacts
    .filter((artifact) => {
      const kind = (artifact.kind || "").toLowerCase();
      const mimeType = (artifact.mimeType || "").toLowerCase();
      return Boolean(artifact.url) && (kind.includes("video") || kind.includes("image") || mimeType.startsWith("video/") || mimeType.startsWith("image/"));
    })
    .map((artifact, index) => mapArtifactToMaterial(detail.id, artifact, index));
}

function mapArtifactToMaterial(runId: string, artifact: AgentRunArtifact, index: number): TaskMaterial {
  const kind = (artifact.kind || "").toLowerCase();
  const mimeType = (artifact.mimeType || "").toLowerCase();
  return {
    id: `${runId}-material-${index}`,
    kind: "output",
    mediaType: kind.includes("image") || mimeType.startsWith("image/") ? "image" : "video",
    title: artifact.label || `素材 ${index + 1}`,
    fileUrl: artifact.url || "",
    previewUrl: artifact.url || "",
    mimeType: artifact.mimeType || null,
  };
}

function extractAgentStoryboard(detail: AgentRunDetail) {
  const markdownArtifact = detail.artifacts.find((artifact) => artifact.kind === "markdown" && artifact.text);
  if (markdownArtifact?.text) {
    return markdownArtifact.text;
  }
  const output = asRecord(detail.output) ?? {};
  return asString(output.scriptMarkdown) || asString(output.outputText) || null;
}

function buildAgentRunListItem(run: AgentRunSummary): DashboardTaskListItem {
  return {
    id: run.id,
    title: run.title,
    status: agentRunStatusToTaskStatus(run.status),
    platform: run.agentId === "ai-drama" ? "AI 剧" : "Agent",
    progress: run.progress,
    outputCount: Math.max(0, run.artifactCount),
    createdAt: run.createdAt,
    updatedAt: run.updatedAt,
    sourceFileName: run.sourceLabel,
    retryCount: 0,
    startedAt: run.startedAt ?? null,
    finishedAt: run.finishedAt ?? null,
    completedOutputCount: run.status === "completed" ? Math.max(0, run.artifactCount) : 0,
    sourceKind: "agent-run",
  };
}

function buildAgentRunDetail(detail: AgentRunDetail): DashboardTaskDetail {
  const input = asRecord(detail.input) ?? {};
  const output = asRecord(detail.output) ?? {};
  const directorDecision = asRecord(output.directorDecision) ?? {};
  const totalDurationSeconds = Math.max(
    0,
    Math.round(asNumber(output.totalDurationSeconds) ?? asNumber(output.durationSeconds) ?? asNumber(input.totalDurationSeconds) ?? 0)
  );
  const textFileName = asString(input.textFileName) || "TXT 小说";
  const outputs = buildAgentOutputs(detail);
  const transcriptPreview = asString(input.text);
  const remoteTaskId = pickAgentRunRemoteTaskId(detail);
  return {
    ...buildAgentRunListItem(detail),
    sourceKind: "agent-run",
    sourceFileName: textFileName,
    sourceFileNames: textFileName ? [textFileName] : [],
    sourceAssetIds: asString(input.textAssetId) ? [asString(input.textAssetId)] : [],
    aspectRatio: asString(output.aspectRatio) || asString(input.aspectRatio) || "",
    minDurationSeconds: totalDurationSeconds,
    maxDurationSeconds: totalDurationSeconds,
    introTemplate: asString(output.introTemplate) || asString(directorDecision.introTemplate),
    outroTemplate: asString(output.outroTemplate) || asString(directorDecision.outroTemplate),
    creativePrompt: detail.summary,
    errorMessage: pickAgentRunError(detail) || null,
    transcriptPreview: transcriptPreview || (textFileName ? `[TXT] ${textFileName}` : null),
    hasTranscript: Boolean(transcriptPreview || textFileName),
    hasTimedTranscript: false,
    transcriptCueCount: 0,
    storyboardScript: extractAgentStoryboard(detail),
    materials: buildAgentMaterials(detail),
    outputs,
    outputCount: outputs.length,
    completedOutputCount: outputs.length,
    remoteTaskId: remoteTaskId || null,
  };
}

function sortByUpdatedAtDesc(items: DashboardTaskListItem[]) {
  return items.slice().sort((left, right) => new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime());
}

const platformOptions = computed(() => {
  return Array.from(new Set(tasks.value.map((task) => task.platform).filter(Boolean))).sort();
});

const filteredTasks = computed(() => {
  const q = keyword.value.trim().toLowerCase();
  return tasks.value.filter((task) => {
    if (status.value !== "all" && task.status !== status.value) {
      return false;
    }
    if (platform.value !== "all" && task.platform !== platform.value) {
      return false;
    }
    if (!q) {
      return true;
    }
    return [task.id, task.title, task.platform, task.sourceFileName ?? ""].join(" ").toLowerCase().includes(q);
  });
});

const metrics = computed(() => {
  let running = 0;
  let completed = 0;
  let failed = 0;
  for (const task of tasks.value) {
    const group = getTaskLifecycleGroup(task.status);
    if (group === "running") {
      running += 1;
    } else if (group === "completed") {
      completed += 1;
    } else if (group === "failed") {
      failed += 1;
    }
  }
  return {
    total: tasks.value.length,
    running,
    completed,
    failed,
  };
});

const lastRefreshLabel = computed(() => {
  if (!lastRefreshAt.value) {
    return "尚未刷新";
  }
  const date = new Date(lastRefreshAt.value);
  if (Number.isNaN(date.getTime())) {
    return lastRefreshAt.value;
  }
  return date.toLocaleTimeString("zh-CN", { hour12: false });
});

async function loadTasks() {
  tasksLoading.value = true;
  loadError.value = "";
  try {
    const [taskList, agentRuns] = await Promise.all([fetchTasks(), fetchAgentRuns("ai-drama")]);
    tasks.value = sortByUpdatedAtDesc([
      ...taskList.map((item) => ({ ...item, sourceKind: "task" as const })),
      ...agentRuns.map((item) => buildAgentRunListItem(item)),
    ]);
    lastRefreshAt.value = new Date().toISOString();

    if (selectedTaskId.value && !tasks.value.some((item) => item.id === selectedTaskId.value)) {
      selectedTaskId.value = "";
    }
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : "加载任务失败";
  } finally {
    tasksLoading.value = false;
  }
}

async function loadSelectedTask(taskId: string) {
  if (!taskId) {
    selectedTask.value = null;
    selectedTrace.value = [];
    return;
  }
  detailLoading.value = true;
  traceLoading.value = true;
  loadError.value = "";
  try {
    if (isAgentRunId(taskId)) {
      const detail = await fetchAgentRun(taskId);
      selectedTask.value = buildAgentRunDetail(detail);
      selectedTrace.value = detail.events.map((item) => agentEventToTraceItem(item)).slice().reverse();
      return;
    }
    const [task, trace] = await Promise.all([fetchTask(taskId), fetchTaskTrace(taskId, 80)]);
    selectedTask.value = { ...task, sourceKind: "task" };
    selectedTrace.value = trace.slice().reverse();
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : "加载任务详情失败";
  } finally {
    detailLoading.value = false;
    traceLoading.value = false;
  }
}

async function refreshAll() {
  await loadTasks();
  if (selectedTaskId.value) {
    await loadSelectedTask(selectedTaskId.value);
  }
}

function handleSelectTask(task: DashboardTaskListItem) {
  selectedTaskId.value = task.id;
}

async function handleRetry(task: DashboardTaskListItem) {
  if (task.sourceKind !== "task") {
    return;
  }
  managingTaskId.value = task.id;
  loadError.value = "";
  try {
    await retryTask(task.id);
    selectedTaskId.value = task.id;
    await refreshAll();
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : "任务重试失败";
  } finally {
    managingTaskId.value = "";
  }
}

async function handleDelete(task: DashboardTaskListItem) {
  if (task.sourceKind !== "task") {
    return;
  }
  const ok = window.confirm(`确认删除任务“${task.title}”吗？`);
  if (!ok) {
    return;
  }
  managingTaskId.value = task.id;
  loadError.value = "";
  try {
    await deleteTask(task.id);
    if (selectedTaskId.value === task.id) {
      selectedTaskId.value = "";
    }
    await refreshAll();
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : "任务删除失败";
  } finally {
    managingTaskId.value = "";
  }
}

function startPolling() {
  stopPolling();
  pollTimer = setInterval(async () => {
    await refreshAll();
  }, 8000);
}

function stopPolling() {
  if (!pollTimer) {
    return;
  }
  clearInterval(pollTimer);
  pollTimer = null;
}

watch(selectedTaskId, async (taskId) => {
  const query = { ...route.query };
  if (taskId) {
    query.selected = taskId;
  } else {
    delete query.selected;
  }
  router.replace({ query });
  await loadSelectedTask(taskId);
});

watch(
  () => route.query.selected,
  (value) => {
    const nextTaskId = typeof value === "string" ? value : "";
    if (nextTaskId !== selectedTaskId.value) {
      selectedTaskId.value = nextTaskId;
    }
  }
);

onMounted(async () => {
  const initialSelected = typeof route.query.selected === "string" ? route.query.selected : "";
  selectedTaskId.value = initialSelected;
  await refreshAll();
  startPolling();
});

onUnmounted(() => {
  stopPolling();
});
</script>

<style scoped>
.tasks-dashboard-view {
  animation: view-enter 0.44s ease;
}

.layout-grid {
  display: grid;
  gap: 1rem;
  align-items: start;
}

.task-grid {
  display: grid;
  gap: 1rem;
}

@media (min-width: 1100px) {
  .layout-grid {
    grid-template-columns: minmax(300px, 340px) minmax(0, 1fr);
  }

  .task-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (min-width: 1500px) {
  .task-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@keyframes view-enter {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
