<template>
  <section class="progress-card p-6">
    <div class="progress-orb progress-orb-cyan" aria-hidden="true"></div>
    <div class="progress-orb progress-orb-emerald" aria-hidden="true"></div>

    <div class="card-head">
      <div>
        <p class="eyebrow">任务进度</p>
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
/**
 * 任务进度组件。
 */
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
  background:
    radial-gradient(circle at top right, rgba(255, 183, 174, 0.24), transparent 26%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.88), rgba(255, 255, 255, 0.42)),
    var(--bg-surface);
  color: var(--text-strong);
  border: 1px solid var(--surface-border);
  box-shadow: var(--shadow-raise);
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
  background: rgba(255, 183, 174, 0.28);
}

.progress-orb-emerald {
  bottom: -2.5rem;
  left: -2rem;
  width: 9rem;
  height: 9rem;
  background: rgba(194, 212, 235, 0.18);
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
  color: var(--text-muted);
}

.card-head h2 {
  margin: 0.25rem 0 0;
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-strong);
}

.status-pill {
  --status-color: #8b97a8;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
  padding: 0.32rem 0.8rem;
  background: rgba(255, 255, 255, 0.74);
  color: var(--status-color);
  border: 1px solid var(--surface-border);
  box-shadow: none;
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
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.84), rgba(255, 255, 255, 0.34)),
    var(--bg-surface);
  border: 1px solid var(--surface-border);
  box-shadow: var(--shadow-pressed);
}

.progress-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  color: var(--text-strong);
  font-size: 0.92rem;
}

.progress-track {
  width: 100%;
  height: 10px;
  border-radius: 999px;
  background: rgba(197, 208, 223, 0.52);
  box-shadow: inset 0 0 0 1px rgba(141, 157, 180, 0.08);
}

.progress-bar {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #c56c73, #ffb7ae);
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
  gap: 0.6rem;
}

.result-shell {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 0.6rem;
  padding: 1rem;
  border-radius: 26px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.84), rgba(255, 255, 255, 0.34)),
    var(--bg-surface);
  border: 1px solid var(--surface-border);
  box-shadow: var(--shadow-pressed);
}

.result-title {
  margin: 0;
  color: var(--text-strong);
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
  color: var(--text-body);
  background: rgba(255, 255, 255, 0.66);
  border: 1px solid var(--surface-border);
  box-shadow: none;
}

.empty-shell {
  padding: 1.1rem;
  border-radius: 26px;
  color: var(--text-body);
  text-align: center;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.78), rgba(255, 255, 255, 0.26)),
    var(--bg-surface);
  border: 1px dashed var(--surface-border-strong);
  box-shadow: var(--shadow-pressed);
}
</style>
