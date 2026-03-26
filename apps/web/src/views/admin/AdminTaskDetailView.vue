<template>
  <section class="space-y-4">
    <div class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div class="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 class="text-lg font-semibold text-slate-900">任务详情</h2>
          <p class="mt-1 text-sm text-slate-600">面向运维的任务诊断视图：状态、参数、方案、日志。</p>
        </div>
        <div class="flex flex-wrap gap-2">
          <button :class="secondaryButtonClass" :disabled="actionLoading" type="button" @click="cloneTaskToWorkbench">复制到前台</button>
          <button v-if="task?.status === 'FAILED'" :class="warningButtonClass" :disabled="actionLoading" type="button" @click="retryTaskAction">失败重试</button>
          <button :class="dangerButtonClass" :disabled="actionLoading || runningTask" type="button" @click="deleteTaskAction">删除</button>
        </div>
      </div>
    </div>

    <div v-if="errorMessage" class="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
      {{ errorMessage }}
    </div>

    <div v-if="loading" class="rounded-lg border border-slate-200 bg-white px-4 py-8 text-sm text-slate-500">
      正在读取任务详情...
    </div>

    <template v-else-if="task">
      <div class="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <section class="rounded-xl border border-slate-200 bg-white shadow-sm">
          <div class="border-b border-slate-200 px-4 py-3">
            <h3 class="text-base font-semibold text-slate-900">基础信息</h3>
          </div>
          <div class="grid gap-3 p-4 sm:grid-cols-2">
            <article class="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p class="text-xs uppercase tracking-wide text-slate-500">任务标题</p>
              <p class="mt-1 text-sm font-medium text-slate-900">{{ task.title }}</p>
            </article>
            <article class="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p class="text-xs uppercase tracking-wide text-slate-500">状态</p>
              <p class="mt-1 text-sm font-medium text-slate-900">{{ task.status }} · {{ task.progress }}%</p>
            </article>
            <article class="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p class="text-xs uppercase tracking-wide text-slate-500">平台 / 比例</p>
              <p class="mt-1 text-sm font-medium text-slate-900">{{ task.platform }} · {{ task.aspectRatio }}</p>
            </article>
            <article class="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p class="text-xs uppercase tracking-wide text-slate-500">输出</p>
              <p class="mt-1 text-sm font-medium text-slate-900">{{ task.completedOutputCount ?? 0 }} / {{ task.outputCount }}</p>
            </article>
            <article class="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p class="text-xs uppercase tracking-wide text-slate-500">时长区间</p>
              <p class="mt-1 text-sm font-medium text-slate-900">{{ task.minDurationSeconds }} - {{ task.maxDurationSeconds }} 秒</p>
            </article>
            <article class="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p class="text-xs uppercase tracking-wide text-slate-500">源文件</p>
              <p class="mt-1 break-all text-sm font-medium text-slate-900">{{ task.sourceFileName }}</p>
            </article>
          </div>

          <div class="border-t border-slate-200 px-4 py-3">
            <h4 class="text-sm font-semibold text-slate-900">规划摘要</h4>
            <p class="mt-1 text-sm text-slate-700">{{ planningSummary.title }}</p>
            <p class="mt-1 text-xs text-slate-500">{{ planningSummary.detail }}</p>
          </div>

          <div v-if="task.errorMessage" class="border-t border-slate-200 px-4 py-3">
            <div class="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {{ task.errorMessage }}
            </div>
          </div>

          <div v-if="task.plan?.length" class="border-t border-slate-200 p-4">
            <div class="mb-2 flex items-center justify-between">
              <h4 class="text-sm font-semibold text-slate-900">规划方案</h4>
              <span class="text-xs text-slate-500">{{ task.plan.length }} 条</span>
            </div>
            <div class="overflow-x-auto rounded-lg border border-slate-200">
              <table class="min-w-full text-sm">
                <thead class="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th class="px-3 py-2 text-left font-medium">序号</th>
                    <th class="px-3 py-2 text-left font-medium">标题</th>
                    <th class="px-3 py-2 text-left font-medium">时长</th>
                    <th class="px-3 py-2 text-left font-medium">时间窗</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="clip in task.plan" :key="clip.clipIndex" class="border-t border-slate-200">
                    <td class="px-3 py-2 text-slate-700">#{{ clip.clipIndex }}</td>
                    <td class="px-3 py-2">
                      <p class="font-medium text-slate-900">{{ clip.title }}</p>
                      <p class="mt-0.5 text-xs text-slate-500">{{ clip.reason }}</p>
                    </td>
                    <td class="px-3 py-2 text-slate-700">{{ clip.durationSeconds.toFixed(1) }}s</td>
                    <td class="px-3 py-2 text-slate-700">{{ clip.startSeconds.toFixed(1) }}s - {{ clip.endSeconds.toFixed(1) }}s</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <section class="rounded-xl border border-slate-200 bg-white shadow-sm">
          <div class="flex flex-wrap items-end justify-between gap-3 border-b border-slate-200 px-4 py-3">
            <div>
              <h3 class="text-base font-semibold text-slate-900">任务日志</h3>
              <p class="mt-1 text-sm text-slate-600">默认显示最新摘要，可展开完整事件流。</p>
            </div>
            <div class="flex flex-wrap gap-2">
              <button :class="secondaryButtonClass" type="button" @click="refresh">刷新</button>
              <button :class="ghostButtonClass" type="button" @click="traceExpanded = !traceExpanded">{{ traceExpanded ? "收起日志" : "展开日志" }}</button>
            </div>
          </div>

          <div class="space-y-3 p-4">
            <article class="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p class="text-xs uppercase tracking-wide text-slate-500">当前重点</p>
              <p class="mt-1 text-sm font-medium text-slate-900">{{ traceFocus?.message || "暂无日志" }}</p>
              <p class="mt-1 text-xs text-slate-500">{{ traceFocus?.timestamp ? formatTime(traceFocus.timestamp) : "" }}</p>
            </article>

            <div v-if="traceEvents.length === 0" class="rounded-lg border border-dashed border-slate-300 px-3 py-6 text-center text-sm text-slate-500">
              当前没有日志。
            </div>

            <div v-else class="overflow-x-auto rounded-lg border border-slate-200">
              <table class="min-w-full text-sm">
                <thead class="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th class="px-3 py-2 text-left font-medium">时间</th>
                    <th class="px-3 py-2 text-left font-medium">级别</th>
                    <th class="px-3 py-2 text-left font-medium">阶段</th>
                    <th class="px-3 py-2 text-left font-medium">消息</th>
                    <th class="px-3 py-2 text-left font-medium">事件</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="entry in traceExpanded ? orderedTraceEvents : tracePreview"
                    :key="`${entry.timestamp}-${entry.event}`"
                    class="border-t border-slate-200"
                  >
                    <td class="px-3 py-2 text-xs text-slate-500">{{ formatTime(entry.timestamp) }}</td>
                    <td class="px-3 py-2">
                      <span :class="logLevelClass(entry.level)" class="rounded px-2 py-0.5 text-xs font-medium">{{ entry.level }}</span>
                    </td>
                    <td class="px-3 py-2 text-slate-700">{{ entry.stage }}</td>
                    <td class="px-3 py-2 text-slate-700">{{ entry.message }}</td>
                    <td class="px-3 py-2 break-all text-xs text-slate-500">{{ entry.event }}</td>
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
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { cloneAdminTask, deleteAdminTask, fetchAdminTask, fetchAdminTaskTrace, retryAdminTask } from "@/api/admin";
import type { TaskDetail, TaskTraceEvent } from "@/types";

const route = useRoute();
const router = useRouter();
const task = ref<TaskDetail | null>(null);
const traceEvents = ref<TaskTraceEvent[]>([]);
const loading = ref(true);
const actionLoading = ref(false);
const errorMessage = ref("");
const traceExpanded = ref(false);

const secondaryButtonClass =
  "inline-flex items-center rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-50";
const ghostButtonClass =
  "inline-flex items-center rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-600 transition hover:bg-slate-50 disabled:opacity-50";
const warningButtonClass =
  "inline-flex items-center rounded-md border border-amber-300 bg-amber-50 px-3 py-1.5 text-sm font-medium text-amber-700 transition hover:bg-amber-100 disabled:opacity-50";
const dangerButtonClass =
  "inline-flex items-center rounded-md border border-rose-300 bg-rose-50 px-3 py-1.5 text-sm font-medium text-rose-700 transition hover:bg-rose-100 disabled:opacity-50";

const taskId = computed(() => String(route.params.id || ""));
const runningTask = computed(() => Boolean(task.value && (task.value.status === "ANALYZING" || task.value.status === "PLANNING" || task.value.status === "RENDERING")));

const planningSummary = computed(() => {
  if (!task.value?.plan?.length) {
    return {
      label: "未生成方案",
      title: "当前还没有规划方案",
      detail: "任务如果已经失败或仍在处理中，方案可能尚未落地。"
    };
  }
  if (task.value.hasTimedTranscript) {
    return {
      label: "语义 + 四信号",
      title: "当前方案优先参考时间轴字幕与多信号融合",
      detail: "这批切点会优先靠近对白边界、音频卡点、镜头切换和视觉事件。"
    };
  }
  return {
    label: "多信号规划",
    title: "当前方案来自融合规划链路",
    detail: "如果没有时间轴字幕，系统会更多依赖视觉事件、音频峰值和镜头切换。"
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

async function cloneTaskToWorkbench() {
  const draft = await cloneAdminTask(taskId.value);
  router.push({ path: "/tasks/new", query: { cloneFrom: draft.sourceTaskId } });
}

watch(taskId, () => {
  traceExpanded.value = false;
  void refresh();
}, { immediate: true });

onMounted(async () => {
  await refresh();
});
</script>
