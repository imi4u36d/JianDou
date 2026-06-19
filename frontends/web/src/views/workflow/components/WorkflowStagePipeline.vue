<script setup lang="ts">
interface StageItem {
  key: string;
  index: number;
  label: string;
  status: string;
  count: string;
  ready: boolean;
}

defineProps<{
  stages: StageItem[];
  activeStage: string;
}>();

const emit = defineEmits<{
  switch: [stage: string];
}>();
</script>

<template>
  <nav class="workflow-stage-pipeline" aria-label="阶段流水线">
    <button
      v-for="stage in stages"
      :key="stage.key"
      type="button"
      class="workflow-stage-step"
      :class="{
        'workflow-stage-step-active': activeStage === stage.key,
        'workflow-stage-step-ready': stage.ready,
      }"
      @click="emit('switch', stage.key)"
    >
      <span class="workflow-stage-step__index">{{ stage.index }}</span>
      <span class="workflow-stage-step__text">
        <strong>{{ stage.label }}</strong>
      </span>
      <span class="workflow-stage-step__count">{{ stage.count }}</span>
    </button>
  </nav>
</template>

<style scoped>
.workflow-stage-pipeline {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
  min-width: 0;
}

.workflow-stage-step {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  min-height: 48px;
  padding: 8px 10px;
  border: 1px solid rgba(0, 169, 187, 0.1);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.76);
  color: var(--text-body);
  text-align: left;
  cursor: pointer;
  transition:
    transform 180ms ease,
    border-color 180ms ease,
    background 180ms ease,
    box-shadow 180ms ease,
    color 180ms ease;
}

.workflow-stage-step:hover,
.workflow-stage-step-active {
  transform: translateY(-1px);
  border-color: rgba(27, 124, 255, 0.22);
  background: linear-gradient(135deg, rgba(239, 252, 255, 0.96), rgba(237, 245, 255, 0.92));
  color: var(--accent-blue);
  box-shadow: 0 12px 24px rgba(27, 124, 255, 0.08);
}

.workflow-stage-step__index {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #effcff;
  color: currentColor;
  font-size: 0.76rem;
  font-weight: 900;
}

.workflow-stage-step__text {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.workflow-stage-step__text strong,
.workflow-stage-step__text small {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workflow-stage-step__text strong {
  color: var(--text-strong);
  font-size: 0.82rem;
}

.workflow-stage-step__text small,
.workflow-stage-step__count {
  color: var(--text-muted);
  font-size: 0.72rem;
}

.workflow-stage-step-ready .workflow-stage-step__count {
  color: var(--accent-blue);
}

@media (max-width: 1180px) {
  .workflow-stage-pipeline {
    grid-template-columns: repeat(5, minmax(132px, 1fr));
    overflow-x: auto;
    padding-bottom: 4px;
  }
}
</style>
