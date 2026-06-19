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
        <el-tag type="info" effect="light">{{ health.runtime.execution_mode }}</el-tag>
        <el-tag type="info" effect="light">{{ health.runtime.model.provider || "未指定" }}</el-tag>
      </div>

      <div class="model-status-strip__grid">
        <div>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="主模型">{{ health.runtime.model.primary_model || "未配置" }}</el-descriptions-item>
            <el-descriptions-item label="文本分析模型">{{ health.runtime.model.text_analysis_model || "未配置" }}</el-descriptions-item>
            <el-descriptions-item label="Endpoint Host">{{ health.runtime.model.endpoint_host || "未配置" }}</el-descriptions-item>
            <el-descriptions-item label="温度 / Max Tokens">{{ health.runtime.model.temperature }} / {{ health.runtime.model.max_tokens }}</el-descriptions-item>
            <el-descriptions-item label="API Key">{{ health.runtime.model.api_key_present ? "已配置" : "缺失" }}</el-descriptions-item>
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

      <el-alert v-if="health.runtime.model.config_errors.length" class="model-status-strip__alert" :title="'配置问题：' + health.runtime.model.config_errors.join(' / ')" type="warning" show-icon />
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { Refresh } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { fetchHealth } from "@/api/health";
import type { HealthResponse } from "@/types";

const health = ref<HealthResponse | null>(null);
const loading = ref(true);

const capabilityRows = computed(() => {
  if (!health.value) return [];
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

<style scoped>
.model-status-strip {
  min-width: 0;
}

.model-status-strip__toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.model-status-strip__section-title {
  margin: 0;
  color: var(--jd-text);
  font-family: inherit;
  font-weight: 850;
}

.model-status-strip__toolbar-spacer {
  flex: 1 1 auto;
  min-width: 0;
}

.model-status-strip__empty {
  display: grid;
  place-items: center;
  min-height: 96px;
  color: var(--jd-text-soft);
  font-size: 0.88rem;
}

.model-status-strip__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.model-status-strip__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.model-status-strip__section-title {
  margin-bottom: 10px;
  font-size: 0.92rem;
}

.model-status-strip__alert {
  margin-top: 16px;
}

@media (max-width: 960px) {
  .model-status-strip__grid {
    grid-template-columns: 1fr;
  }
}
</style>
