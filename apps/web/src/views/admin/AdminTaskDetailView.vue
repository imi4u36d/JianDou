<template>
  <section class="admin-page admin-task-detail-view">
    <div class="admin-panel px-5 py-5">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="admin-heading-block">
          <p class="admin-eyebrow">Task Detail</p>
          <h2 class="admin-title">任务详情</h2>
          <p class="admin-subtitle">面向运维的任务生成诊断视图：状态、参数、进度、日志。</p>
        </div>
        <div class="admin-action-row">
          <button v-if="task?.status === 'FAILED'" :class="warningButtonClass" :disabled="actionLoading" type="button" @click="retryTaskAction">失败重试</button>
          <button :class="dangerButtonClass" :disabled="actionLoading || runningTask" type="button" @click="deleteTaskAction">删除</button>
        </div>
      </div>
    </div>

    <div v-if="errorMessage" class="admin-alert-error">
      {{ errorMessage }}
    </div>

    <div v-if="loading" class="admin-panel px-4 py-8 text-sm text-slate-500">
      正在读取任务详情...
    </div>

    <template v-else-if="task">
      <div class="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <section class="admin-panel overflow-hidden">
          <div class="admin-panel-header">
            <h3 class="text-base font-semibold text-slate-900">基础信息</h3>
          </div>
          <div class="grid gap-3 p-5 sm:grid-cols-2">
            <article class="admin-panel-soft p-4">
              <p class="text-xs uppercase tracking-wide text-slate-500">任务标题</p>
              <p class="mt-1 text-sm font-medium text-slate-900">{{ task.title }}</p>
            </article>
            <article class="admin-panel-soft p-4">
              <p class="text-xs uppercase tracking-wide text-slate-500">状态</p>
              <p class="mt-1 text-sm font-medium text-slate-900">{{ task.status }} · {{ task.progress }}%</p>
            </article>
            <article class="admin-panel-soft p-4">
              <p class="text-xs uppercase tracking-wide text-slate-500">比例</p>
              <p class="mt-1 text-sm font-medium text-slate-900">{{ task.aspectRatio }}</p>
            </article>
            <article class="admin-panel-soft p-4">
              <p class="text-xs uppercase tracking-wide text-slate-500">已生成结果</p>
              <p class="mt-1 text-sm font-medium text-slate-900">{{ task.completedOutputCount ?? task.outputs?.length ?? 0 }} 条</p>
            </article>
            <article class="admin-panel-soft p-4">
              <p class="text-xs uppercase tracking-wide text-slate-500">时长区间</p>
              <p class="mt-1 text-sm font-medium text-slate-900">{{ task.minDurationSeconds }} - {{ task.maxDurationSeconds }} 秒</p>
            </article>
            <article class="admin-panel-soft p-4">
              <p class="text-xs uppercase tracking-wide text-slate-500">源文件</p>
              <p class="mt-1 break-all text-sm font-medium text-slate-900">{{ task.sourceFileName }}</p>
            </article>
          </div>

          <div class="border-t border-slate-200/80 px-5 py-4">
            <h4 class="text-sm font-semibold text-slate-900">任务摘要</h4>
            <p class="mt-1 text-sm text-slate-700">{{ planningSummary.title }}</p>
            <p class="mt-1 text-xs text-slate-500">{{ planningSummary.detail }}</p>
          </div>

          <div v-if="task.errorMessage" class="border-t border-slate-200/80 px-5 py-4">
            <div class="admin-alert-error">
              {{ task.errorMessage }}
            </div>
          </div>

          <div v-if="task.plan?.length" class="border-t border-slate-200/80 p-5">
            <div class="mb-2 flex items-center justify-between">
              <h4 class="text-sm font-semibold text-slate-900">任务计划</h4>
              <span class="admin-chip">{{ task.plan.length }} 条</span>
            </div>
            <div class="admin-table-wrap">
              <table class="admin-table">
                <thead>
                  <tr>
                    <th>序号</th>
                    <th>标题</th>
                    <th>时长</th>
                    <th>时间窗</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="clip in task.plan" :key="clip.clipIndex">
                    <td>#{{ clip.clipIndex }}</td>
                    <td>
                      <p class="font-medium text-slate-900">{{ clip.title }}</p>
                      <p class="mt-0.5 text-xs text-slate-500">{{ clip.reason }}</p>
                    </td>
                    <td>{{ clip.durationSeconds.toFixed(1) }}s</td>
                    <td>{{ clip.startSeconds.toFixed(1) }}s - {{ clip.endSeconds.toFixed(1) }}s</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <section class="admin-panel overflow-hidden">
          <div class="admin-panel-header">
            <div>
              <h3 class="text-base font-semibold text-slate-900">任务日志</h3>
              <p class="mt-1 text-sm text-slate-600">默认显示最新摘要，可展开完整事件流。</p>
            </div>
            <div class="flex flex-wrap gap-2">
              <button :class="secondaryButtonClass" type="button" @click="refresh">刷新</button>
              <button :class="ghostButtonClass" type="button" @click="traceExpanded = !traceExpanded">{{ traceExpanded ? "收起日志" : "展开日志" }}</button>
            </div>
          </div>

          <div class="space-y-4 p-5">
            <article class="admin-panel-soft p-4">
              <p class="text-xs uppercase tracking-wide text-slate-500">当前重点</p>
              <p class="mt-1 text-sm font-medium text-slate-900">{{ traceFocus?.message || "暂无日志" }}</p>
              <p class="mt-1 text-xs text-slate-500">{{ traceFocus?.timestamp ? formatTime(traceFocus.timestamp) : "" }}</p>
            </article>

            <div v-if="traceEvents.length === 0" class="admin-empty">
              当前没有日志。
            </div>

            <div v-else class="admin-table-wrap">
              <table class="admin-table">
                <thead>
                  <tr>
                    <th>时间</th>
                    <th>级别</th>
                    <th>阶段</th>
                    <th>消息</th>
                    <th>事件</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="entry in traceExpanded ? orderedTraceEvents : tracePreview"
                    :key="`${entry.timestamp}-${entry.event}`"
                  >
                    <td class="text-xs text-slate-500">{{ formatTime(entry.timestamp) }}</td>
                    <td>
                      <span :class="logLevelClass(entry.level)" class="rounded px-2 py-0.5 text-xs font-medium">{{ entry.level }}</span>
                    </td>
                    <td>{{ entry.stage }}</td>
                    <td>{{ entry.message }}</td>
                    <td class="break-all text-xs text-slate-500">{{ entry.event }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { deleteAdminTask, fetchAdminTask, fetchAdminTaskTrace, retryAdminTask } from "@/api/admin";
import type { TaskDetail, TaskTraceEvent } from "@/types";

const route = useRoute();
const router = useRouter();
const task = ref<TaskDetail | null>(null);
const traceEvents = ref<TaskTraceEvent[]>([]);
const loading = ref(true);
const actionLoading = ref(false);
const errorMessage = ref("");
const traceExpanded = ref(false);

const ghostButtonClass = "admin-btn-ghost";
const secondaryButtonClass = "admin-btn-secondary";
const warningButtonClass = "admin-btn-warning";
const dangerButtonClass = "admin-btn-danger";

const taskId = computed(() => String(route.params.id || ""));
const runningTask = computed(() => Boolean(task.value && (task.value.status === "ANALYZING" || task.value.status === "PLANNING" || task.value.status === "RENDERING")));

const planningSummary = computed(() => {
  if (!task.value?.plan?.length) {
    return {
      label: "未生成计划",
      title: "当前还没有任务计划",
      detail: "任务如果失败或仍在处理中，计划可能尚未生成。"
    };
  }
  if (task.value.hasTimedTranscript) {
    return {
      label: "时间轴输入",
      title: "当前任务包含时间轴文本输入",
      detail: "系统会优先依据时间轴文本与阶段信号推进生成。"
    };
  }
  return {
    label: "任务生成",
    title: "当前任务使用标准生成链路",
    detail: "系统按分析、编排、渲染阶段持续推进。"
  };
});

const orderedTraceEvents = computed(() => [...traceEvents.value].reverse());
const traceFocus = computed(() => orderedTraceEvents.value[0] ?? null);
const tracePreview = computed(() => orderedTraceEvents.value.slice(0, 5));

function logLevelClass(level: string) {
  if (level === "ERROR") {
    return "bg-rose-100 text-rose-700";
  }
  if (level === "WARN") {
    return "bg-amber-100 text-amber-700";
  }
  return "bg-slate-100 text-slate-700";
}

function formatTime(value: string) {
  return new Date(value).toLocaleString();
}

async function loadTask() {
  task.value = await fetchAdminTask(taskId.value);
}

async function loadTrace() {
  traceEvents.value = await fetchAdminTaskTrace(taskId.value, 500);
}

async function refresh() {
  loading.value = true;
  errorMessage.value = "";
  try {
    await Promise.all([loadTask(), loadTrace()]);
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "读取任务详情失败";
  } finally {
    loading.value = false;
  }
}

async function retryTaskAction() {
  actionLoading.value = true;
  try {
    await retryAdminTask(taskId.value);
    await refresh();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "重试失败";
  } finally {
    actionLoading.value = false;
  }
}

async function deleteTaskAction() {
  if (!window.confirm(`确认删除任务“${task.value?.title || taskId.value}”吗？`)) {
    return;
  }
  actionLoading.value = true;
  try {
    await deleteAdminTask(taskId.value);
    router.push("/admin/tasks");
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "删除失败";
  } finally {
    actionLoading.value = false;
  }
}

watch(taskId, () => {
  traceExpanded.value = false;
  void refresh();
}, { immediate: true });
</script>

<style scoped>
.admin-task-detail-view :deep(.admin-panel) {
  border: 1px solid #dbe4ee;
  border-radius: 1.25rem;
  background: #ffffff;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
}

.admin-task-detail-view :deep(.admin-panel-soft) {
  border: 1px solid #dbe4ee;
  background: #f8fafc;
}

.admin-task-detail-view :deep(.admin-table th) {
  background: #f1f5f9;
}
</style>
