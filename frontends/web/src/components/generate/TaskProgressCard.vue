<template>
  <section class="progress-card">
    <div class="card-head">
      <div>
        <h2>进度</h2>
      </div>
      <span :class="['status-pill', `status-${props.state.status}`]">
        {{ statusLabel }}
      </span>
    </div>

    <div class="progress-shell">
      <div class="progress-top">
        <strong>{{ props.state.stage }}</strong>
        <span>{{ props.state.progress }}%</span>
      </div>
      <div class="progress-track">
        <div class="progress-bar" :style="{ width: `${props.state.progress}%` }"></div>
      </div>
      <p class="progress-message">{{ props.state.message }}</p>
      <p class="progress-meta">
        <span v-if="props.taskId" :title="props.taskId">#{{ compactTaskId }}</span>
        <span v-if="props.traceCount">追 {{ props.traceCount }}</span>
        <span v-if="props.elapsedLabel">{{ props.elapsedLabel }}</span>
        <span>{{ props.state.updatedAt }}</span>
      </p>
    </div>

    <div v-if="props.outputUrl" class="result-shell">
      <p class="result-title">{{ props.resultTitle || "结果" }}</p>
      <video
        :src="props.outputUrl"
        :poster="props.posterUrl || undefined"
        controls
        playsinline
        preload="metadata"
        class="result-video"
      ></video>
      <div class="result-meta">
        <span v-for="item in props.resultMeta" :key="item">{{ item }}</span>
      </div>
    </div>

    <div v-else class="empty-shell" aria-hidden="true">
      <IconVideo size="md" />
    </div>
  </section>
</template>

<script setup lang="ts">
/**
 * 任务进度组件。
 */
import { computed } from "vue";
import { IconVideo } from "@/components/icons";
import type { TaskProgressCardProps } from "./types";

const props = defineProps<TaskProgressCardProps>();

const statusLabel = computed(() => {
  if (props.state.status === "completed") {
    return "已完成";
  }
  if (props.state.status === "failed") {
    return "失败";
  }
  if (props.state.status === "running") {
    return "进行中";
  }
  if (props.state.status === "paused") {
    return "已暂停";
  }
  return "待开始";
});

const compactTaskId = computed(() => {
  const value = props.taskId || "";
  if (value.length <= 14) {
    return value;
  }
  return `${value.slice(0, 6)}...${value.slice(-5)}`;
});

</script>

<style scoped>
.progress-card {
  position: relative;
  display: grid;
  gap: 14px;
  padding: 18px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.82);
  color: var(--text-strong);
  border: 1px solid rgba(15, 20, 25, 0.07);
  box-shadow:
    0 12px 30px rgba(27, 124, 255, 0.045),
    inset 0 1px 0 rgba(255, 255, 255, 0.86);
  backdrop-filter: blur(18px);
}

.card-head {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.card-head h2 {
  margin: 0;
  font-size: 1rem;
  font-weight: 820;
  color: var(--text-strong);
}

.status-pill {
  --status-color: #8b97a8;
  border-radius: 999px;
  min-height: 26px;
  font-size: 0.74rem;
  font-weight: 800;
  padding: 0 9px;
  background: rgba(248, 250, 252, 0.9);
  color: var(--status-color);
  border: 1px solid var(--surface-border);
  box-shadow: none;
}

.status-idle {
  --status-color: #8b97a8;
}

.status-running {
  --status-color: #2563eb;
}

.status-paused {
  --status-color: #b45309;
}

.status-completed {
  --status-color: #059669;
}

.status-failed {
  --status-color: #e11d48;
}

.progress-shell {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 8px;
  padding: 12px 0 0;
  border-top: 1px solid rgba(15, 20, 25, 0.06);
  border-radius: 0;
  background: transparent;
  border-left: 0;
  border-right: 0;
  border-bottom: 0;
  box-shadow: none;
}

.progress-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  color: var(--text-strong);
  font-size: 0.92rem;
}

.progress-track {
  width: 100%;
  height: 6px;
  border-radius: 999px;
  background: rgba(15, 20, 25, 0.08);
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--accent-cyan), var(--accent-blue));
  transition: width 240ms ease;
}

.progress-message {
  margin: 0;
  color: var(--text-body);
  font-size: 0.85rem;
}

.progress-meta {
  margin: 0;
  color: var(--text-muted);
  font-size: 0.75rem;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  min-width: 0;
}

.progress-meta span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-shell {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 10px;
  padding: 12px 0 0;
  border-top: 1px solid rgba(15, 20, 25, 0.06);
  border-radius: 0;
  background: transparent;
  border-left: 0;
  border-right: 0;
  border-bottom: 0;
  box-shadow: none;
}

.result-title {
  margin: 0;
  color: var(--text-strong);
  font-size: 0.88rem;
  font-weight: 820;
}

.result-video {
  width: 100%;
  border-radius: 12px;
  background: #01040a;
  max-height: 360px;
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.14);
}

.result-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.result-meta span {
  border-radius: 999px;
  min-height: 26px;
  padding: 0 9px;
  font-size: 0.73rem;
  color: var(--text-body);
  background: rgba(255, 255, 255, 0.66);
  border: 1px solid rgba(15, 20, 25, 0.06);
  box-shadow: none;
}

.empty-shell {
  display: grid;
  place-items: center;
  min-height: 96px;
  padding: 0;
  border-radius: 12px;
  color: var(--text-muted);
  text-align: center;
  background: rgba(248, 250, 252, 0.52);
  border: 1px dashed rgba(15, 20, 25, 0.1);
  box-shadow: none;
}

.empty-shell :deep(svg) {
  width: 24px;
  height: 24px;
}
</style>
