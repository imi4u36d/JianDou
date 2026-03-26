<template>
  <section class="space-y-6">
    <PageHeader
      eyebrow="Admin System"
      title="系统状态"
      description="集中查看模型配置、规划能力和最近系统日志。"
    />

    <div class="grid gap-6 xl:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
      <ModelStatusStrip />

      <section class="surface-panel p-5">
        <div class="flex items-end justify-between gap-3">
          <div>
            <p class="text-xs uppercase tracking-[0.24em] text-slate-500">Admin Trace</p>
            <h3 class="mt-2 text-lg font-semibold text-white">最近关键日志</h3>
          </div>
          <button class="btn-secondary btn-sm" type="button" @click="loadTraces">
            刷新
          </button>
        </div>

        <div class="mt-4 grid gap-3">
          <article v-for="entry in traces" :key="`${entry.taskId}-${entry.timestamp}-${entry.event}`" class="surface-tile bg-slate-950/55 p-4">
            <div class="flex flex-wrap items-center gap-2 text-[11px] uppercase tracking-[0.24em] text-slate-500">
              <span>{{ entry.level }}</span>
              <span>{{ entry.stage }}</span>
              <span>{{ formatTime(entry.timestamp) }}</span>
            </div>
            <p class="mt-3 text-sm font-semibold text-white">{{ entry.taskTitle || entry.taskId }}</p>
            <p class="mt-1 text-sm text-slate-300">{{ entry.message }}</p>
          </article>
          <div v-if="traces.length === 0" class="surface-tile border-dashed p-4 text-sm text-slate-400">
            当前没有日志。
          </div>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { fetchAdminTraces } from "@/api/admin";
import ModelStatusStrip from "@/components/ModelStatusStrip.vue";
import PageHeader from "@/components/PageHeader.vue";
import type { AdminTraceEvent } from "@/types";

const traces = ref<AdminTraceEvent[]>([]);

function formatTime(value: string) {
  return new Date(value).toLocaleString();
}

async function loadTraces() {
  traces.value = await fetchAdminTraces({ limit: 16 });
}

onMounted(async () => {
  await loadTraces();
});
</script>
