<template>
  <section class="surface-panel progress-card p-6">
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

    <div class="surface-tile progress-shell p-4">
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

    <div v-if="props.outputUrl" class="surface-tile result-shell p-4">
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

    <div v-else class="surface-tile empty-shell p-6">
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
  overflow: hidden;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.9), rgba(245, 249, 255, 0.78)),
    radial-gradient(circle at top right, rgba(56, 189, 248, 0.12), transparent 28%);
}

.progress-orb {
  position: absolute;
  border-radius: 999px;
  filter: blur(22px);
  opacity: 0.42;
  pointer-events: none;
}

.progress-orb-cyan {
  top: -3rem;
  right: -2rem;
  width: 11rem;
  height: 11rem;
  background: rgba(56, 189, 248, 0.16);
}

.progress-orb-emerald {
  bottom: -2.4rem;
  left: -1.8rem;
  width: 9rem;
  height: 9rem;
  background: rgba(16, 185, 129, 0.12);
}

.card-head {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}

.eyebrow {
  margin: 0;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: #5f7895;
}

.card-head h2 {
  margin: 0.25rem 0 0;
  font-family: "Sora", "PingFang SC", sans-serif;
  font-size: 1.25rem;
  font-weight: 750;
  color: #0f2744;
}

.status-pill {
  border-radius: 999px;
  font-size: 0.76rem;
  font-weight: 700;
  padding: 0.28rem 0.65rem;
}

.status-idle {
  background: #e2e8f0;
  color: #334155;
}

.status-running {
  background: #dbeafe;
  color: #1d4ed8;
}

.status-paused {
  background: #fef3c7;
  color: #b45309;
}

.status-completed {
  background: #dcfce7;
  color: #15803d;
}

.status-failed {
  background: #fee2e2;
  color: #b91c1c;
}

.progress-shell {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 0.6rem;
  border: 1px solid rgba(109, 139, 177, 0.12);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.8), rgba(245, 249, 255, 0.72)),
    radial-gradient(circle at top left, rgba(56, 189, 248, 0.08), transparent 30%);
}

.progress-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  color: #1f334b;
  font-size: 0.9rem;
}

.progress-track {
  width: 100%;
  height: 9px;
  background: rgba(148, 163, 184, 0.22);
  border-radius: 999px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #3166ff, #5bc7d9);
  transition: width 240ms ease;
}

.progress-message {
  margin: 0;
  color: #43546a;
  font-size: 0.85rem;
}

.progress-meta {
  margin: 0;
  color: #718198;
  font-size: 0.75rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.7rem;
}

.result-shell {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 0.6rem;
  border: 1px solid rgba(109, 139, 177, 0.12);
}

.result-title {
  margin: 0;
  color: #334155;
  font-size: 0.84rem;
  font-weight: 600;
}

.result-video {
  width: 100%;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.26);
  background: #020617;
  max-height: 360px;
}

.result-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.result-meta span {
  border-radius: 999px;
  padding: 0.22rem 0.55rem;
  font-size: 0.73rem;
  color: #3b4f68;
  border: 1px solid rgba(148, 163, 184, 0.34);
  background: rgba(255, 255, 255, 0.68);
}

.empty-shell {
  position: relative;
  z-index: 1;
  font-size: 0.86rem;
  color: #64748b;
  text-align: center;
  border: 1px dashed rgba(109, 139, 177, 0.22);
}
</style>
