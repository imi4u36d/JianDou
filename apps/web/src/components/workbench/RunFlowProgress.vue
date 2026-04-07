<template>
  <section class="flow-card">
    <div class="flow-head">
      <div>
        <p class="flow-kicker">Workflow</p>
        <h3 class="flow-title">{{ title }}</h3>
        <p class="flow-summary">{{ summary }}</p>
      </div>
      <div class="flow-metrics">
        <span class="flow-chip">{{ status }}</span>
        <span class="flow-chip">总耗时 {{ totalElapsedLabel }}</span>
        <span class="flow-chip">当前节点 {{ currentStepElapsedLabel }}</span>
      </div>
    </div>

    <div class="flow-track" :style="{ '--flow-accent': accent }">
      <div class="flow-track-bar">
        <div class="flow-track-fill" :style="{ width: `${clampedProgress}%` }"></div>
      </div>
      <div class="flow-track-labels">
        <span>0%</span>
        <span>{{ clampedProgress }}%</span>
        <span>100%</span>
      </div>
    </div>

    <div v-if="errorMessage" class="flow-error">
      <strong>错误提示</strong>
      <p>{{ errorMessage }}</p>
    </div>

    <ol class="flow-steps">
      <li v-for="(step, index) in resolvedSteps" :key="step.key" class="flow-step" :class="`flow-step-${step.state}`">
        <div class="flow-step-index" :style="{ '--flow-accent': accent }">
          <span>{{ index + 1 }}</span>
        </div>
        <div class="flow-step-body">
          <div class="flow-step-top">
            <strong>{{ step.label }}</strong>
            <span class="flow-step-state">{{ step.stateLabel }}</span>
          </div>
          <p>{{ step.hint }}</p>
          <small>{{ step.timeLabel }}</small>
        </div>
      </li>
    </ol>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { AgentRunEvent } from "@/types";

export interface FlowStepSpec {
  key: string;
  label: string;
  hint: string;
  stagePatterns: string[];
}

type FlowStepState = "done" | "current" | "pending" | "error";

const props = defineProps<{
  title: string;
  summary: string;
  status: string;
  progress: number;
  startedAt?: string | null;
  finishedAt?: string | null;
  createdAt?: string | null;
  errorMessage?: string | null;
  events: AgentRunEvent[];
  steps: FlowStepSpec[];
  accent?: string;
}>();

const clampedProgress = computed(() => Math.max(0, Math.min(100, Math.round(props.progress || 0))));
const accent = computed(() => props.accent || "#2563eb");

function toMs(value?: string | null) {
  if (!value) {
    return null;
  }
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? null : parsed;
}

function formatDuration(ms: number | null) {
  if (ms === null || !Number.isFinite(ms) || ms < 0) {
    return "0s";
  }
  const totalSeconds = Math.max(0, Math.round(ms / 1000));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  if (hours > 0) {
    return `${hours}h ${minutes}m ${seconds}s`;
  }
  if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  }
  return `${seconds}s`;
}

function stageMatches(step: FlowStepSpec, stage: string) {
  const normalizedStage = stage.toLowerCase();
  return step.stagePatterns.some((pattern) => normalizedStage.includes(pattern.toLowerCase()));
}

const resolvedSteps = computed(() => {
  const startedAtMs = toMs(props.startedAt) ?? toMs(props.createdAt) ?? Date.now();
  const finishedAtMs = toMs(props.finishedAt);
  const nowMs = finishedAtMs ?? Date.now();
  const eventList = props.events ?? [];
  const errorEvent = [...eventList].reverse().find((item) => (item.level || "").toLowerCase() === "error");

  const stepStarts = props.steps.map((step) => {
    const matchedEvents = eventList.filter((event) => stageMatches(step, event.stage));
    const firstEventMs = matchedEvents.length ? toMs(matchedEvents[0]?.timestamp) : null;
    const lastEventMs = matchedEvents.length ? toMs(matchedEvents[matchedEvents.length - 1]?.timestamp) : null;
    return {
      step,
      matchedEvents,
      firstEventMs: firstEventMs ?? null,
      lastEventMs: lastEventMs ?? null,
    };
  });

  const errorIndex = errorEvent ? props.steps.findIndex((step) => stageMatches(step, errorEvent.stage)) : -1;
  const currentIndex = (() => {
    if (errorIndex >= 0) {
      return errorIndex;
    }
    const lastMatched = stepStarts.map((entry, index) => ({ index, matched: entry.matchedEvents.length })).filter((item) => item.matched > 0).pop();
    if (lastMatched) {
      return lastMatched.index;
    }
    return props.status.toLowerCase() === "failed" ? props.steps.length - 1 : 0;
  })();

  return stepStarts.map((entry, index) => {
    let state: FlowStepState = "pending";
    if (errorIndex >= 0 && index === errorIndex) {
      state = "error";
    } else if (errorIndex >= 0 && index < errorIndex) {
      state = "done";
    } else if (props.status.toLowerCase() === "completed" || props.status.toLowerCase() === "succeeded") {
      state = "done";
    } else if (index < currentIndex) {
      state = "done";
    } else if (index === currentIndex) {
      state = "current";
    }

    const startMs = entry.firstEventMs ?? (index === 0 ? startedAtMs : stepStarts[index - 1]?.lastEventMs ?? startedAtMs);
    const elapsedMs = state === "pending" ? 0 : Math.max(0, nowMs - startMs);
    const stateLabel = state === "done" ? "已完成" : state === "current" ? "进行中" : state === "error" ? "错误" : "待执行";
    const timeLabel = state === "pending" ? "等待开始" : `已用 ${formatDuration(elapsedMs)}`;

    return {
      ...entry.step,
      state,
      stateLabel,
      timeLabel,
    };
  });
});

const totalElapsedLabel = computed(() => {
  const startedAtMs = toMs(props.startedAt) ?? toMs(props.createdAt);
  const finishedAtMs = toMs(props.finishedAt) ?? Date.now();
  return formatDuration(startedAtMs !== null ? finishedAtMs - startedAtMs : null);
});

const currentStepElapsedLabel = computed(() => {
  const current = resolvedSteps.value.find((step) => step.state === "current" || step.state === "error")
    ?? resolvedSteps.value[resolvedSteps.value.length - 1];
  return current?.timeLabel || "0s";
});
</script>

<style scoped>
.flow-card {
  border: 1px solid #e7e1d7;
  border-radius: 1.5rem;
  background:
    radial-gradient(circle at top left, rgba(37, 99, 235, 0.06), transparent 30%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(250, 247, 242, 0.96));
  box-shadow: 0 18px 44px rgba(15, 23, 42, 0.08);
  padding: 1rem;
  animation: flow-rise 320ms ease;
}

.flow-head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 0.9rem;
}

.flow-kicker {
  margin: 0;
  color: #7d8592;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.28em;
  text-transform: uppercase;
}

.flow-title {
  margin: 0.3rem 0 0;
  color: #24303f;
  font-size: 1.1rem;
}

.flow-summary {
  margin: 0.45rem 0 0;
  color: #667085;
  line-height: 1.7;
  font-size: 0.9rem;
}

.flow-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  align-items: flex-start;
}

.flow-chip {
  border: 1px solid #dde4ee;
  border-radius: 999px;
  background: #fff;
  padding: 0.34rem 0.62rem;
  color: #425466;
  font-size: 0.72rem;
  font-weight: 700;
}

.flow-track {
  margin-top: 1rem;
}

.flow-track-bar {
  position: relative;
  height: 0.6rem;
  overflow: hidden;
  border-radius: 999px;
  background: #e9edf4;
}

.flow-track-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, color-mix(in srgb, var(--flow-accent) 90%, #ffffff), color-mix(in srgb, var(--flow-accent) 55%, #94a3b8));
  transition: width 240ms ease;
}

.flow-track-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 0.4rem;
  color: #8b94a3;
  font-size: 0.7rem;
}

.flow-error {
  margin-top: 0.9rem;
  border: 1px solid rgba(239, 68, 68, 0.18);
  border-radius: 1rem;
  background: rgba(254, 242, 242, 0.92);
  padding: 0.8rem 0.9rem;
  color: #9f1239;
}

.flow-error strong {
  display: block;
  margin-bottom: 0.25rem;
}

.flow-error p {
  margin: 0;
  line-height: 1.65;
}

.flow-steps {
  display: grid;
  gap: 0.75rem;
  margin: 1rem 0 0;
  padding: 0;
  list-style: none;
}

.flow-step {
  display: grid;
  grid-template-columns: 2.4rem minmax(0, 1fr);
  gap: 0.8rem;
  align-items: start;
  border: 1px solid #e7e1d7;
  border-radius: 1.1rem;
  background: rgba(255, 255, 255, 0.96);
  padding: 0.85rem;
  transition:
    transform 180ms ease,
    border-color 180ms ease,
    box-shadow 180ms ease,
    background 180ms ease;
}

.flow-step:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
}

.flow-step-done {
  border-color: rgba(37, 99, 235, 0.18);
  background: rgba(248, 250, 255, 0.95);
}

.flow-step-current {
  border-color: color-mix(in srgb, var(--flow-accent) 36%, #dbe3ef);
  box-shadow: 0 14px 28px rgba(37, 99, 235, 0.1);
}

.flow-step-error {
  border-color: rgba(239, 68, 68, 0.22);
  background: rgba(255, 248, 248, 0.98);
}

.flow-step-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.4rem;
  height: 2.4rem;
  border-radius: 0.9rem;
  background: color-mix(in srgb, var(--flow-accent) 10%, #f8fafc);
  color: color-mix(in srgb, var(--flow-accent) 82%, #24303f);
  font-weight: 800;
}

.flow-step-current .flow-step-index {
  box-shadow: 0 0 0 6px color-mix(in srgb, var(--flow-accent) 10%, transparent);
  animation: flow-pulse 1.6s ease-in-out infinite;
}

.flow-step-error .flow-step-index {
  background: rgba(239, 68, 68, 0.08);
  color: #ef4444;
}

.flow-step-body {
  display: grid;
  gap: 0.3rem;
}

.flow-step-top {
  display: flex;
  justify-content: space-between;
  gap: 0.65rem;
}

.flow-step-body strong {
  color: #24303f;
  font-size: 0.94rem;
}

.flow-step-state {
  border-radius: 999px;
  border: 1px solid #dbe4ee;
  background: #fff;
  padding: 0.18rem 0.45rem;
  color: #5b6778;
  font-size: 0.68rem;
  text-transform: uppercase;
}

.flow-step-body p {
  margin: 0;
  color: #667085;
  line-height: 1.6;
  font-size: 0.82rem;
}

.flow-step-body small {
  color: #8b94a3;
  font-size: 0.74rem;
}

@keyframes flow-rise {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes flow-pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.04);
  }
}

@media (max-width: 720px) {
  .flow-head {
    grid-template-columns: 1fr;
  }

  .flow-step {
    grid-template-columns: 2.2rem minmax(0, 1fr);
  }
}
</style>
