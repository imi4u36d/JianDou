<template>
  <section class="detail-stage-card" :class="{ 'detail-stage-card-image': imageMode }" aria-label="任务阶段">
    <div v-if="imageMode && stages.length" class="detail-stage-steps">
      <template v-for="(stage, index) in stages" :key="stage.key">
        <div
          class="detail-stage-step"
          :class="[`detail-stage-step-${stage.state}`, `detail-stage-step-icon-${stage.iconState}`]"
        >
          <span class="detail-stage-step__icon" aria-hidden="true">
            <IconCheck v-if="stage.iconState === 'done'" size="xs" />
            <IconRefresh v-else-if="stage.iconState === 'active'" size="xs" />
            <span v-else-if="stage.iconState === 'paused'" class="detail-stage-step__pause"></span>
            <IconWarning v-else-if="stage.iconState === 'failed'" size="xs" />
          </span>
          <span class="detail-stage-step__copy">
            <strong>{{ stage.label }}</strong>
            <small>
              <span>{{ stage.stateLabel }}</span>
              <span v-if="stage.durationLabel" class="detail-stage-step__duration">{{ stage.durationLabel }}</span>
            </small>
          </span>
        </div>
        <span v-if="index < stages.length - 1" class="detail-stage-step__chevron" aria-hidden="true">›</span>
      </template>
    </div>
    <div v-else-if="stages.length" class="detail-stage-line">
      <div
        v-for="stage in stages"
        :key="stage.key"
        class="detail-stage-line__item"
        :class="`detail-stage-line__item-${stage.state}`"
      >
        <span class="detail-stage-line__dot" :class="stageStateClass(stage.state)" aria-hidden="true"></span>
        <span class="detail-stage-line__copy">
          <strong>{{ stage.label }}</strong>
          <small>{{ stage.stateLabel }}</small>
        </span>
      </div>
    </div>
    <div v-else class="detail-stage-empty">
      <span class="detail-stage-empty__icon" aria-hidden="true"><IconEmpty size="sm" /></span>
      <strong>暂无阶段信息</strong>
      <small>任务开始处理后，阶段进度会显示在这里。</small>
    </div>
  </section>
</template>

<script setup lang="ts">
import { IconCheck, IconEmpty, IconRefresh, IconWarning } from "@/components/icons";
import {
  stageStateClass,
  type TaskStageDisplayItem,
} from "../features/task-detail-presenters";

defineProps<{
  stages: TaskStageDisplayItem[];
  imageMode: boolean;
}>();
</script>

<style scoped src="./task-stage-timeline.css"></style>
