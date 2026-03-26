<template>
  <section class="space-y-6">
    <PageHeader
      eyebrow="Admin Task"
      :title="task?.title || '任务详情'"
      description="管理侧只关注处理动作、异常原因和日志，不再承载创作型交互。"
    >
      <div class="flex flex-wrap gap-2">
        <button :class="adminSecondaryButton" :disabled="actionLoading" type="button" @click="cloneTaskToWorkbench">
          复制到前台
        </button>
        <button v-if="task?.status === 'FAILED'" :class="adminWarningButton" :disabled="actionLoading" type="button" @click="retryTaskAction">
          失败重试
        </button>
        <button :class="adminDangerButton" :disabled="actionLoading || runningTask" type="button" @click="deleteTaskAction">
          删除
        </button>
      </div>
    </PageHeader>

    <div v-if="errorMessage" class="rounded-[24px] border border-rose-500/20 bg-rose-500/10 p-4 text-sm text-rose-100">
      {{ errorMessage }}
    </div>

    <div v-if="loading" class="rounded-[24px] border border-white/10 bg-white/[0.04] p-8 text-sm text-slate-300">
      正在读取任务详情...
    </div>

    <template v-else-if="task">
      <div class="grid gap-6 xl:grid-cols-[minmax(0,0.96fr)_minmax(0,1.04fr)]">
        <section class="grid gap-4 rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(13,19,38,0.94),rgba(8,14,28,0.92))] p-5 shadow-[0_24px_70px_rgba(0,0,0,0.3)]">
          <div class="grid gap-3 sm:grid-cols-2">
            <article class="rounded-[22px] border border-white/8 bg-slate-950/55 p-4">
              <p class="text-[11px] uppercase tracking-[0.28em] text-slate-500">状态</p>
              <p class="mt-2 text-lg font-semibold text-white">{{ task.status }}</p>
              <p class="mt-1 text-sm text-slate-400">进度 {{ task.progress }}%</p>
            </article>
            <article class="rounded-[22px] border border-white/8 bg-slate-950/55 p-4">
              <p class="text-[11px] uppercase tracking-[0.28em] text-slate-500">平台 / 比例</p>
              <p class="mt-2 text-lg font-semibold text-white">{{ task.platform }}</p>
              <p class="mt-1 text-sm text-slate-400">{{ task.aspectRatio }}</p>
            </article>
            <article class="rounded-[22px] border border-white/8 bg-slate-950/55 p-4">
              <p class="text-[11px] uppercase tracking-[0.28em] text-slate-500">输出</p>
              <p class="mt-2 text-lg font-semibold text-white">{{ task.completedOutputCount ?? 0 }} / {{ task.outputCount }}</p>
              <p class="mt-1 text-sm text-slate-400">{{ task.minDurationSeconds }}-{{ task.maxDurationSeconds }} 秒</p>
            </article>
            <article class="rounded-[22px] border border-white/8 bg-slate-950/55 p-4">
              <p class="text-[11px] uppercase tracking-[0.28em] text-slate-500">素材</p>
              <p class="mt-2 break-all text-sm font-semibold text-white">{{ task.sourceFileName }}</p>
              <p class="mt-1 text-sm text-slate-400">{{ task.source?.originalFileName || "未关联原始资产名" }}</p>
            </article>
          </div>

          <article class="rounded-[22px] border border-white/8 bg-white/[0.04] p-4">
            <div class="flex flex-wrap items-center gap-2">
              <span class="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-[11px] uppercase tracking-[0.22em] text-slate-200">规划方式</span>
              <span class="text-xs text-slate-500">{{ planningSummary.label }}</span>
            </div>
            <p class="mt-3 text-base font-semibold text-white">{{ planningSummary.title }}</p>
            <p class="mt-1 text-sm leading-6 text-slate-300">{{ planningSummary.detail }}</p>
          </article>

          <div v-if="task.errorMessage" class="rounded-[22px] border border-rose-500/20 bg-rose-500/10 p-4 text-sm text-rose-100">
            {{ task.errorMessage }}
          </div>

          <div v-if="task.plan?.length" class="rounded-[22px] border border-white/8 bg-white/[0.04] p-4">
            <p class="text-[11px] uppercase tracking-[0.28em] text-slate-500">规划方案</p>
            <div class="mt-3 grid gap-3">
              <article v-for="clip in task.plan" :key="clip.clipIndex" class="rounded-2xl border border-white/8 bg-slate-950/55 p-4">
                <div class="flex items-start justify-between gap-3">
                  <div class="min-w-0">
                    <p class="break-words text-sm font-semibold text-white">#{{ clip.clipIndex }} {{ clip.title }}</p>
                    <p class="mt-1 break-words text-sm leading-6 text-slate-300">{{ clip.reason }}</p>
                  </div>
                  <span class="shrink-0 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs text-slate-200">{{ clip.durationSeconds.toFixed(1) }}s</span>
                </div>
                <p class="mt-3 text-xs text-slate-400">{{ clip.startSeconds.toFixed(1) }}s - {{ clip.endSeconds.toFixed(1) }}s</p>
              </article>
            </div>
          </div>
        </section>

        <section class="grid gap-4 rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(13,19,38,0.92),rgba(8,14,28,0.9))] p-5 shadow-[0_24px_70px_rgba(0,0,0,0.28)]">
          <div class="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p class="text-[11px] uppercase tracking-[0.32em] text-sky-300/80">Trace</p>
              <h3 class="mt-2 text-lg font-semibold text-white">任务日志</h3>
              <p class="mt-1 text-sm text-slate-400">默认只看摘要，展开后再读完整事件流。</p>
            </div>
            <div class="flex flex-wrap gap-2">
              <button :class="adminSecondaryButton" type="button" @click="refresh">
                刷新
              </button>
              <button :class="adminGhostButton" type="button" @click="traceExpanded = !traceExpanded">
                {{ traceExpanded ? "收起日志" : "展开日志" }}
              </button>
            </div>
          </div>

          <article :class="traceFocusToneClass" class="rounded-[22px] border p-4">
            <div class="flex flex-wrap items-center gap-2 text-[11px] uppercase tracking-[0.24em] text-slate-500">
              <span>当前重点</span>
              <span>{{ traceFocus?.timestamp ? formatTime(traceFocus.timestamp) : "暂无日志" }}</span>
            </div>
            <p class="mt-3 text-sm font-semibold text-white">{{ traceFocus?.message || "还没有可展示的关键事件" }}</p>
            <p v-if="traceFocus" class="mt-1 break-all font-mono text-[11px] text-slate-500">{{ traceFocus.event }}</p>
          </article>

          <div v-if="!traceExpanded" class="grid gap-3">
            <article v-for="entry in tracePreview" :key="`${entry.timestamp}-${entry.event}`" class="rounded-[22px] border border-white/8 bg-slate-950/55 p-4">
              <div class="flex flex-wrap items-center gap-2 text-[11px] uppercase tracking-[0.24em] text-slate-500">
                <span>{{ entry.level }}</span>
                <span>{{ entry.stage }}</span>
                <span>{{ formatTime(entry.timestamp) }}</span>
              </div>
              <p class="mt-3 text-sm font-semibold text-white">{{ entry.message }}</p>
            </article>
          </div>

          <div v-else class="grid gap-3">
            <article v-for="entry in orderedTraceEvents" :key="`${entry.timestamp}-${entry.event}`" class="rounded-[22px] border border-white/8 bg-slate-950/55 p-4">
              <div class="flex flex-wrap items-center gap-2 text-[11px] uppercase tracking-[0.24em] text-slate-500">
                <span>{{ entry.level }}</span>
                <span>{{ entry.stage }}</span>
                <span>{{ formatTime(entry.timestamp) }}</span>
              </div>
              <p class="mt-3 text-sm font-semibold text-white">{{ entry.message }}</p>
              <p class="mt-2 break-all font-mono text-[11px] text-slate-500">{{ entry.event }}</p>
            </article>
          </div>

          <div v-if="traceEvents.length === 0" class="rounded-[22px] border border-dashed border-white/10 bg-white/[0.03] p-4 text-sm text-slate-400">
            当前没有日志。
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
import PageHeader from "@/components/PageHeader.vue";
import type { TaskDetail, TaskTraceEvent } from "@/types";

const route = useRoute();
const router = useRouter();
const task = ref<TaskDetail | null>(null);
const traceEvents = ref<TaskTraceEvent[]>([]);
const loading = ref(true);
const actionLoading = ref(false);
const errorMessage = ref("");
const traceExpanded = ref(false);

const adminSecondaryButton = "btn-secondary";
const adminGhostButton = "btn-ghost";
const adminWarningButton = "btn-warning";
const adminDangerButton = "btn-danger";

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
const tracePreview = computed(() => orderedTraceEvents.value.slice(0, 3));
const traceFocusToneClass = computed(() => {
  if (!traceFocus.value) {
    return "border-white/8 bg-white/[0.04]";
  }
  if (traceFocus.value.level === "ERROR") {
    return "border-rose-400/20 bg-rose-500/10";
  }
  if (traceFocus.value.level === "WARN") {
    return "border-amber-400/20 bg-amber-500/10";
  }
  return "border-sky-400/20 bg-sky-500/10";
});

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
