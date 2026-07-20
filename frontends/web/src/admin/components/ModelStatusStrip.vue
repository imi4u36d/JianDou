<template>
  <el-card class="surface-card model-status-strip" shadow="never">
    <template #header>
      <div class="model-status-strip__toolbar">
        <span class="model-status-strip__toolbar-spacer" aria-hidden="true"></span>
        <el-button :icon="Refresh" :loading="loading" @click="loadHealth">刷新</el-button>
      </div>
    </template>

    <div v-if="!health" class="model-status-strip__empty">加载中</div>
    <div v-else>
      <div class="model-status-strip__tags">
        <el-tag :type="health.runtime.model.ready ? 'success' : 'danger'" effect="light">
          {{ health.runtime.model.ready ? "模型就绪" : "模型未就绪" }}
        </el-tag>
        <el-tag type="info" effect="light">{{ executionMode }}</el-tag>
        <el-tag type="info" effect="light">{{ health.runtime.model.provider || "未指定" }}</el-tag>
      </div>

      <div class="model-status-strip__grid">
        <div>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="主模型">{{ modelPrimaryModel || "未配置" }}</el-descriptions-item>
            <el-descriptions-item label="文本分析模型">{{ modelTextAnalysisModel || "未配置" }}</el-descriptions-item>
            <el-descriptions-item label="Endpoint Host">{{ modelEndpointHost || "未配置" }}</el-descriptions-item>
            <el-descriptions-item label="温度 / Max Tokens">{{ health.runtime.model.temperature }} / {{ modelMaxTokens }}</el-descriptions-item>
            <el-descriptions-item label="API Key">{{ modelApiKeyPresent ? "已配置" : "缺失" }}</el-descriptions-item>
          </el-descriptions>
        </div>

        <div>
          <h4 class="model-status-strip__section-title">规划能力</h4>
          <el-table :data="capabilityRows" stripe size="small">
            <el-table-column label="能力项" prop="label" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.enabled ? 'success' : 'info'" effect="light" size="small">
                  {{ row.enabled ? "已启用" : "未启用" }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <el-alert v-if="modelConfigErrors.length" class="model-status-strip__alert" :title="'配置问题：' + modelConfigErrors.join(' / ')" type="warning" show-icon />
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { Refresh } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { fetchHealth } from "@/api/health";
import type { HealthPlanningCapabilities, HealthResponse } from "@/types";

const health = ref<HealthResponse | null>(null);
const loading = ref(true);

const executionMode = computed(() => health.value?.runtime.execution_mode ?? health.value?.runtime.executionMode ?? "");
const modelPrimaryModel = computed(() => health.value?.runtime.model.primary_model ?? health.value?.runtime.model.primaryModel ?? "");
const modelTextAnalysisModel = computed(() => health.value?.runtime.model.text_analysis_model ?? health.value?.runtime.model.textAnalysisModel ?? "");
const modelEndpointHost = computed(() => health.value?.runtime.model.endpoint_host ?? health.value?.runtime.model.endpointHost ?? "");
const modelApiKeyPresent = computed(() => Boolean(health.value?.runtime.model.api_key_present ?? health.value?.runtime.model.apiKeyPresent));
const modelMaxTokens = computed(() => health.value?.runtime.model.max_tokens ?? health.value?.runtime.model.maxTokens ?? 0);
const modelConfigErrors = computed(() => health.value?.runtime.model.config_errors ?? health.value?.runtime.model.configErrors ?? []);

const capabilityRows = computed(() => {
  if (!health.value) return [];
  const c: Partial<HealthPlanningCapabilities> =
    health.value.runtime.planning_capabilities ?? health.value.runtime.planningCapabilities ?? {};
  const enabled = (
    snakeKey: keyof HealthPlanningCapabilities,
    camelKey: keyof HealthPlanningCapabilities,
  ) => Boolean(c[snakeKey] ?? c[camelKey]);
  return [
    { key: "timed_transcript", label: "带时间戳字幕优先", enabled: enabled("timed_transcript_supported", "timedTranscriptSupported") },
    { key: "transcript_semantic", label: "字幕语义规划", enabled: enabled("transcript_semantic_planning", "transcriptSemanticPlanning") },
    { key: "visual_content", label: "视频内容理解", enabled: enabled("visual_content_analysis", "visualContentAnalysis") },
    { key: "visual_event", label: "视觉事件识别", enabled: enabled("visual_event_reasoning", "visualEventReasoning") },
    { key: "fusion", label: "字幕+视频融合", enabled: enabled("subtitle_visual_fusion", "subtitleVisualFusion") },
    { key: "audio_peak", label: "音频峰值信号", enabled: enabled("audio_peak_signal", "audioPeakSignal") },
    { key: "scene_boundary", label: "镜头切换边界", enabled: enabled("scene_boundary_signal", "sceneBoundarySignal") },
    { key: "timeline", label: "融合时间轴规划", enabled: enabled("fusion_timeline_planning", "fusionTimelinePlanning") },
  ];
});

async function loadHealth() {
  loading.value = true;
  try {
    health.value = await fetchHealth();
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "读取运行时状态失败");
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void loadHealth();
});
</script>

<style scoped src="./model-status-strip.css"></style>
