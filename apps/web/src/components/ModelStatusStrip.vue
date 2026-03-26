<template>
  <section class="rounded-xl border border-slate-200 bg-white shadow-sm">
    <div class="flex flex-wrap items-end justify-between gap-3 border-b border-slate-200 px-4 py-3">
      <div>
        <h3 class="text-base font-semibold text-slate-900">模型与规划能力</h3>
        <p class="mt-1 text-sm text-slate-600">只读配置检查，不触发真实模型调用。</p>
      </div>
      <button class="inline-flex items-center rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50" type="button" @click="loadHealth">
        刷新
      </button>
    </div>

    <div v-if="loading" class="px-4 py-8 text-sm text-slate-500">正在读取运行时状态...</div>
    <div v-else-if="errorMessage" class="m-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
      {{ errorMessage }}
    </div>
    <div v-else-if="health" class="p-4">
      <div class="mb-3 flex flex-wrap items-center gap-2">
        <span :class="health.runtime.model.ready ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-amber-200 bg-amber-50 text-amber-700'" class="rounded-md border px-2.5 py-1 text-xs font-medium">
          {{ health.runtime.model.ready ? "模型配置就绪" : "模型配置未完成" }}
        </span>
        <span class="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs text-slate-700">{{ health.runtime.execution_mode }}</span>
        <span class="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs text-slate-700">{{ health.runtime.model.provider }}</span>
      </div>

      <div class="overflow-x-auto rounded-lg border border-slate-200">
        <table class="min-w-full text-sm">
          <tbody>
            <tr class="border-b border-slate-200">
              <td class="w-48 bg-slate-50 px-3 py-2 text-xs font-medium text-slate-500">主模型</td>
              <td class="px-3 py-2 text-slate-900">{{ health.runtime.model.primary_model }}</td>
            </tr>
            <tr class="border-b border-slate-200">
              <td class="bg-slate-50 px-3 py-2 text-xs font-medium text-slate-500">回退模型</td>
              <td class="px-3 py-2 text-slate-900">{{ health.runtime.model.fallback_model || "未配置" }}</td>
            </tr>
            <tr class="border-b border-slate-200">
              <td class="bg-slate-50 px-3 py-2 text-xs font-medium text-slate-500">视觉模型</td>
              <td class="px-3 py-2 text-slate-900">{{ health.runtime.model.vision_model || "未配置" }}</td>
            </tr>
            <tr class="border-b border-slate-200">
              <td class="bg-slate-50 px-3 py-2 text-xs font-medium text-slate-500">Endpoint Host</td>
              <td class="px-3 py-2 break-all text-slate-900">{{ health.runtime.model.endpoint_host || "未配置" }}</td>
            </tr>
            <tr class="border-b border-slate-200">
              <td class="bg-slate-50 px-3 py-2 text-xs font-medium text-slate-500">温度 / Max Tokens</td>
              <td class="px-3 py-2 text-slate-900">{{ health.runtime.model.temperature }} / {{ health.runtime.model.max_tokens }}</td>
            </tr>
            <tr>
              <td class="bg-slate-50 px-3 py-2 text-xs font-medium text-slate-500">API Key</td>
              <td class="px-3 py-2 text-slate-900">{{ health.runtime.model.api_key_present ? "已配置" : "缺失" }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="mt-4 overflow-x-auto rounded-lg border border-slate-200">
        <table class="min-w-full text-sm">
          <thead class="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th class="px-3 py-2 text-left font-medium">能力项</th>
              <th class="px-3 py-2 text-left font-medium">状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in capabilityRows" :key="item.key" class="border-t border-slate-200">
              <td class="px-3 py-2 text-slate-700">{{ item.label }}</td>
              <td class="px-3 py-2">
                <span :class="item.enabled ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-700'" class="rounded px-2 py-0.5 text-xs font-medium">
                  {{ item.enabled ? "已启用" : "未启用" }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="health.runtime.model.config_errors.length" class="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700">
        配置问题：{{ health.runtime.model.config_errors.join(" / ") }}
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { fetchHealth } from "@/api/health";
import type { HealthResponse } from "@/types";

const health = ref<HealthResponse | null>(null);
const loading = ref(true);
const errorMessage = ref("");

const capabilityRows = computed(() => {
  if (!health.value) {
    return [];
  }
  const c = health.value.runtime.planning_capabilities;
  return [
    { key: "timed_transcript", label: "带时间戳字幕优先", enabled: c.timed_transcript_supported },
    { key: "transcript_semantic", label: "字幕语义规划", enabled: c.transcript_semantic_planning },
    { key: "visual_content", label: "视频内容理解", enabled: c.visual_content_analysis },
    { key: "visual_event", label: "视觉事件识别", enabled: c.visual_event_reasoning },
    { key: "fusion", label: "字幕+视频融合", enabled: c.subtitle_visual_fusion },
    { key: "audio_peak", label: "音频峰值信号", enabled: c.audio_peak_signal },
    { key: "scene_boundary", label: "镜头切换边界", enabled: c.scene_boundary_signal },
    { key: "timeline", label: "融合时间轴规划", enabled: c.fusion_timeline_planning },
    { key: "fallback", label: "启发式回退", enabled: c.fallback_heuristic_enabled },
  ];
});

async function loadHealth() {
  loading.value = true;
  errorMessage.value = "";
  try {
    health.value = await fetchHealth();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "读取运行时状态失败";
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void loadHealth();
});
</script>
