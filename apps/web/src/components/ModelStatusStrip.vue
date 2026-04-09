<template>
  <section class="admin-panel model-status-strip overflow-hidden">
    <div class="admin-panel-header">
      <div>
        <h3 class="text-base font-semibold text-slate-900">模型与规划能力</h3>
        <p class="mt-1 text-sm text-slate-600">只读配置检查，不触发真实模型调用。</p>
      </div>
      <button class="admin-btn-secondary" type="button" @click="loadHealth">
        刷新
      </button>
    </div>

    <div v-if="loading" class="px-5 py-8 text-sm text-slate-500">正在读取运行时状态...</div>
    <div v-else-if="errorMessage" class="m-5 admin-alert-error">
      {{ errorMessage }}
    </div>
    <div v-else-if="health" class="p-5">
      <div class="mb-3 flex flex-wrap items-center gap-2">
        <span :class="health.runtime.model.ready ? 'admin-chip admin-chip-success' : 'admin-chip admin-chip-warn'">
          {{ health.runtime.model.ready ? "模型配置就绪" : "模型配置未完成" }}
        </span>
        <span class="admin-chip">{{ health.runtime.execution_mode }}</span>
        <span class="admin-chip">{{ health.runtime.model.provider }}</span>
      </div>

      <div class="grid gap-4 xl:grid-cols-2">
        <section class="space-y-3">
          <div>
            <p class="admin-eyebrow">Model Config</p>
            <h4 class="mt-1 text-sm font-semibold text-slate-900">模型配置</h4>
          </div>
          <div class="admin-table-wrap h-full">
            <table class="admin-table">
              <tbody>
                <tr class="border-b border-slate-200">
                  <td class="w-48 bg-slate-50 text-xs font-medium text-slate-500">主模型</td>
                  <td class="text-slate-900">{{ health.runtime.model.primary_model }}</td>
                </tr>
                <tr class="border-b border-slate-200">
                  <td class="bg-slate-50 text-xs font-medium text-slate-500">文本分析模型</td>
                  <td class="text-slate-900">{{ health.runtime.model.text_analysis_model || health.runtime.model.primary_model }}</td>
                </tr>
                <tr class="border-b border-slate-200">
                  <td class="bg-slate-50 text-xs font-medium text-slate-500">回退模型</td>
                  <td class="text-slate-900">{{ health.runtime.model.fallback_model || "未配置" }}</td>
                </tr>
                <tr class="border-b border-slate-200">
                  <td class="bg-slate-50 text-xs font-medium text-slate-500">视觉模型</td>
                  <td class="text-slate-900">{{ health.runtime.model.vision_model || "未配置" }}</td>
                </tr>
                <tr class="border-b border-slate-200">
                  <td class="bg-slate-50 text-xs font-medium text-slate-500">Endpoint Host</td>
                  <td class="break-all text-slate-900">{{ health.runtime.model.endpoint_host || "未配置" }}</td>
                </tr>
                <tr class="border-b border-slate-200">
                  <td class="bg-slate-50 text-xs font-medium text-slate-500">温度 / Max Tokens</td>
                  <td class="text-slate-900">{{ health.runtime.model.temperature }} / {{ health.runtime.model.max_tokens }}</td>
                </tr>
                <tr>
                  <td class="bg-slate-50 text-xs font-medium text-slate-500">API Key</td>
                  <td class="text-slate-900">{{ health.runtime.model.api_key_present ? "已配置" : "缺失" }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="space-y-3">
          <div>
            <p class="admin-eyebrow">Capabilities</p>
            <h4 class="mt-1 text-sm font-semibold text-slate-900">规划能力</h4>
          </div>
          <div class="admin-table-wrap h-full">
            <table class="admin-table">
              <thead>
                <tr>
                  <th>能力项</th>
                  <th>状态</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in capabilityRows" :key="item.key">
                  <td>{{ item.label }}</td>
                  <td>
                    <span :class="item.enabled ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-700'" class="rounded px-2 py-0.5 text-xs font-medium">
                      {{ item.enabled ? "已启用" : "未启用" }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <div v-if="health.runtime.model.config_errors.length" class="mt-4 admin-alert-warn">
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

<style scoped>
.model-status-strip :deep(.admin-table-wrap) {
  border-radius: 1rem;
  border: 1px solid #dbe4ee;
  background: #f8fafc;
}

.model-status-strip :deep(.admin-table th) {
  background: #f1f5f9;
}

.model-status-strip :deep(.admin-table td),
.model-status-strip :deep(.admin-table th) {
  border-color: #e2e8f0;
}
</style>
