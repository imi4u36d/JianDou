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
  gap: 8px;
  flex: 0 0 auto;
  min-width: 0;
  min-height: 54px;
  align-items: stretch;
  padding: 2px 0 4px;
  scrollbar-width: none;
}

.workflow-stage-pipeline::-webkit-scrollbar {
  display: none;
}

.workflow-stage-step {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr) auto;
  gap: 7px;
  align-items: center;
  box-sizing: border-box;
  min-height: 46px;
  padding: 8px 9px;
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 13px;
  background: rgba(0, 0, 0, 0.03);
  color: var(--text-body);
  text-align: left;
  cursor: pointer;
  transition:
    border-color 180ms ease,
    background 180ms ease,
    box-shadow 180ms ease,
    color 180ms ease;
}

.workflow-stage-step:hover,
.workflow-stage-step-active {
  border-color: rgba(99, 102, 241, 0.25);
  background: rgba(99, 102, 241, 0.1);
  color: var(--accent-blue);
  box-shadow: none;
}

.workflow-stage-step__index {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: rgba(99, 102, 241, 0.12);
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
    grid-template-columns: repeat(5, minmax(118px, 1fr));
    overflow-x: auto;
  }
}
</style>
