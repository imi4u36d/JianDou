<template>
  <section class="progress-card p-6">
    <div class="progress-orb progress-orb-cyan" aria-hidden="true"></div>
    <div class="progress-orb progress-orb-emerald" aria-hidden="true"></div>

    <div class="card-head">
      <div>
        <p class="eyebrow">Task Progress</p>
        <h2>实时进度</h2>
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
        <span v-if="props.taskId">任务ID：{{ props.taskId }}</span>
        <span v-if="props.traceCount">追踪事件：{{ props.traceCount }}</span>
        <span v-if="props.elapsedLabel">{{ props.elapsedLabel }}</span>
        <span>更新时间：{{ props.state.updatedAt }}</span>
      </p>
    </div>

    <div v-if="props.outputUrl" class="result-shell">
      <p class="result-title">{{ props.resultTitle || "生成结果" }}</p>
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

    <div v-else class="empty-shell">
      任务执行后，这里会显示实时进度和生成成品预览。
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
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
</script>

<style scoped>
.progress-card {
  position: relative;
  display: grid;
  gap: 1rem;
  padding: 1.5rem;
  border-radius: 32px;
  background: #E0E5EC;
  color: #1f2a37;
  box-shadow:
    20px 20px 40px rgba(138, 148, 164, 0.45),
    -20px -20px 40px rgba(255, 255, 255, 0.95);
}

.progress-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(28px);
  opacity: 0.35;
  pointer-events: none;
}

.progress-orb-cyan {
  top: -2rem;
  right: -1.5rem;
  width: 10rem;
  height: 10rem;
  background: rgba(255, 156, 156, 0.24);
}

.progress-orb-emerald {
  bottom: -2.5rem;
  left: -2rem;
  width: 9rem;
  height: 9rem;
  background: rgba(255, 156, 156, 0.18);
}

.card-head {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.eyebrow {
  margin: 0;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: #5f6b7c;
}

.card-head h2 {
  margin: 0.25rem 0 0;
  font-size: 1.25rem;
  font-weight: 700;
  color: #1f2a37;
}

.status-pill {
  --status-color: #8b97a8;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
  padding: 0.32rem 0.8rem;
  background: #E7EBF2;
  color: var(--status-color);
  box-shadow:
    2px 2px 6px rgba(138, 148, 164, 0.3),
    -2px -2px 6px rgba(255, 255, 255, 0.9);
  text-transform: uppercase;
  letter-spacing: 0.12em;
}

.status-idle {
  --status-color: #8b97a8;
}

.status-running {
  --status-color: #c9878e;
}

.status-paused {
  --status-color: #b79b79;
}

.status-completed {
  --status-color: #7e9d8d;
}

.status-failed {
  --status-color: #b37d87;
}

.progress-shell {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 0.4rem;
  padding: 1rem;
  border-radius: 26px;
  background: #E7EBF2;
  box-shadow:
    inset 6px 6px 14px rgba(138, 148, 164, 0.35),
    inset -6px -6px 14px rgba(255, 255, 255, 0.8);
}

.progress-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  color: #1f2a37;
  font-size: 0.92rem;
}

.progress-track {
  width: 100%;
  height: 10px;
  border-radius: 999px;
  background: #E0E5EC;
  box-shadow:
    inset 2px 2px 6px rgba(138, 148, 164, 0.25),
    inset -2px -2px 6px rgba(255, 255, 255, 0.9);
}

.progress-bar {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(255, 156, 156, 0.4), #ffd3d3);
  transition: width 240ms ease;
}

.progress-message {
  margin: 0;
  color: #5c6774;
  font-size: 0.85rem;
}

.progress-meta {
  margin: 0;
  color: #5a6370;
  font-size: 0.75rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.result-shell {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 0.6rem;
  padding: 1rem;
  border-radius: 26px;
  background: #E7EBF2;
  box-shadow:
    inset 6px 6px 14px rgba(138, 148, 164, 0.25),
    inset -6px -6px 14px rgba(255, 255, 255, 0.9);
}

.result-title {
  margin: 0;
  color: #1f2a37;
  font-size: 0.88rem;
  font-weight: 600;
}

.result-video {
  width: 100%;
  border-radius: 18px;
  background: #01040a;
  max-height: 360px;
  box-shadow:
    6px 6px 16px rgba(15, 23, 42, 0.25),
    -6px -6px 16px rgba(255, 255, 255, 0.2);
}

.result-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.result-meta span {
  border-radius: 999px;
  padding: 0.28rem 0.6rem;
  font-size: 0.73rem;
  color: #3b4f68;
  background: #E0E5EC;
  box-shadow:
    inset 2px 2px 6px rgba(255, 255, 255, 0.9),
    inset -2px -2px 6px rgba(138, 148, 164, 0.2);
}

.empty-shell {
  padding: 1.1rem;
  border-radius: 26px;
  color: #5c6774;
  text-align: center;
  background: #E0E5EC;
  box-shadow:
    inset 6px 6px 14px rgba(138, 148, 164, 0.25),
    inset -6px -6px 14px rgba(255, 255, 255, 0.9);
}
</style>
