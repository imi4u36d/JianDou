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
        <small>{{ stage.status }}</small>
      </span>
      <span class="workflow-stage-step__count">{{ stage.count }}</span>
    </button>
  </nav>
</template>
