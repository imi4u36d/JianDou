<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from "vue";

interface StageItem {
  key: string;
  index: number;
  label: string;
  status: string;
  count: string;
  ready: boolean;
}

const props = defineProps<{
  stages: StageItem[];
  activeStage: string;
}>();

const emit = defineEmits<{
  switch: [stage: string];
}>();

const pipelineRef = ref<HTMLElement | null>(null);

async function revealActiveStage() {
  await nextTick();
  const activeStep = pipelineRef.value?.querySelector<HTMLElement>('[aria-current="step"]');
  if (activeStep && typeof activeStep.scrollIntoView === "function") {
    activeStep.scrollIntoView({ block: "nearest", inline: "center" });
  }
}

watch(() => props.activeStage, revealActiveStage);
onMounted(revealActiveStage);
</script>

<template>
  <section class="workflow-stage-pipeline-shell" aria-label="创作进度">
    <span class="workflow-stage-pipeline__hint" aria-hidden="true">左右滑动查看 5 个阶段</span>
    <nav ref="pipelineRef" class="workflow-stage-pipeline" aria-label="阶段流水线">
      <button
        v-for="stage in stages"
        :key="stage.key"
        type="button"
        class="workflow-stage-step"
        :class="{
          'workflow-stage-step-active': activeStage === stage.key,
          'workflow-stage-step-ready': stage.ready,
        }"
        :aria-current="activeStage === stage.key ? 'step' : undefined"
        @click="emit('switch', stage.key)"
      >
        <span class="workflow-stage-step__index">{{ stage.index }}</span>
        <span class="workflow-stage-step__text">
          <strong>{{ stage.label }}</strong>
        </span>
        <span class="workflow-stage-step__count">{{ stage.count }}</span>
      </button>
    </nav>
  </section>
</template>

<style scoped>
.workflow-stage-pipeline-shell {
  position: relative;
  min-width: 0;
}

.workflow-stage-pipeline__hint {
  display: none;
}

.workflow-stage-pipeline {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0;
  flex: 0 0 auto;
  min-width: 0;
  min-height: 70px;
  align-items: stretch;
  padding: 10px 4px 0;
  scroll-padding-inline: 8px;
  scroll-snap-type: x proximity;
  overscroll-behavior-inline: contain;
  scrollbar-width: none;
}

.workflow-stage-pipeline::-webkit-scrollbar {
  display: none;
}

.workflow-stage-step {
  position: relative;
  display: grid;
  grid-template-columns: 1fr;
  justify-items: center;
  align-content: start;
  gap: 8px;
  box-sizing: border-box;
  min-height: 60px;
  padding: 0 8px 10px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--text-body);
  text-align: center;
  cursor: pointer;
  scroll-snap-align: center;
  transition:
    color 180ms ease;
}

.workflow-stage-step:not(:last-child)::after {
  content: "";
  position: absolute;
  z-index: 0;
  top: 15px;
  left: calc(50% + 20px);
  width: calc(100% - 40px);
  height: 1px;
  background: #dfe3eb;
}

.workflow-stage-step:hover {
  color: var(--accent-blue);
}

.workflow-stage-step:focus-visible {
  outline: 2px solid color-mix(in srgb, var(--accent-blue) 42%, transparent);
  outline-offset: -2px;
}

.workflow-stage-step-active {
  color: var(--accent-blue);
}

.workflow-stage-step__index {
  display: grid;
  place-items: center;
  position: relative;
  z-index: 1;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  border: 1px solid #dfe3eb;
  background: #fff;
  color: var(--text-muted);
  font-size: 0.76rem;
  font-weight: 600;
  transition:
    border-color 180ms ease,
    background 180ms ease,
    box-shadow 180ms ease,
    color 180ms ease,
    transform 180ms ease;
}

.workflow-stage-step:hover .workflow-stage-step__index {
  border-color: color-mix(in srgb, var(--accent-blue) 45%, #dfe3eb);
  color: var(--accent-blue);
  transform: translateY(-1px);
}

.workflow-stage-step-active .workflow-stage-step__index {
  border-color: var(--accent-blue);
  background: var(--accent-blue);
  color: #fff;
  box-shadow: 0 0 0 5px color-mix(in srgb, var(--accent-blue) 12%, transparent);
}

.workflow-stage-step-ready:not(.workflow-stage-step-active) .workflow-stage-step__index {
  border-color: color-mix(in srgb, var(--accent-blue) 32%, #dfe3eb);
  background: var(--bg-accent-soft, #f0f0ff);
  color: var(--accent-blue);
}

.workflow-stage-step-ready:not(:last-child)::after {
  background: color-mix(in srgb, var(--accent-blue) 38%, #dfe3eb);
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
  font-size: 0.8rem;
  font-weight: 600;
  line-height: 1.35;
  text-align: center;
  transition: color 180ms ease;
}

.workflow-stage-step:hover .workflow-stage-step__text strong,
.workflow-stage-step-active .workflow-stage-step__text strong {
  color: var(--accent-blue);
}

.workflow-stage-step__text small,
.workflow-stage-step__count {
  color: var(--text-muted);
  font-size: 0.72rem;
}

.workflow-stage-step__count {
  display: none;
}

.workflow-stage-step-ready .workflow-stage-step__count {
  color: var(--accent-blue);
}

@media (max-width: 1180px) {
  .workflow-stage-pipeline-shell::after {
    content: "";
    position: absolute;
    z-index: 2;
    right: 0;
    bottom: 0;
    width: 28px;
    height: 70px;
    pointer-events: none;
    background: linear-gradient(90deg, transparent, var(--workspace-surface, #fff));
  }

  .workflow-stage-pipeline__hint {
    display: block;
    margin: 0 4px -2px 0;
    color: var(--text-muted);
    font-size: 0.7rem;
    line-height: 1.4;
    text-align: right;
  }

  .workflow-stage-pipeline {
    grid-template-columns: repeat(5, minmax(112px, 1fr));
    overflow-x: auto;
  }
}

@media (max-width: 640px) {
  .workflow-stage-pipeline {
    grid-template-columns: repeat(5, minmax(104px, 1fr));
    padding-top: 9px;
  }

  .workflow-stage-step {
    min-height: 58px;
    padding-inline: 6px;
  }
}
</style>
