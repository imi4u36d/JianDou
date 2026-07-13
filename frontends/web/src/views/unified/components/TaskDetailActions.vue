<template>
  <div
    class="detail-actions detail-actions-card"
    :class="{ 'detail-actions-card-image': imageMode }"
    aria-label="任务操作"
  >
    <button class="jd-button jd-button--sm" type="button" :disabled="loading" @click="$emit('refresh')">
      <IconRefresh size="xs" />刷新
    </button>
    <button class="jd-button jd-button--sm" type="button" :disabled="loading" @click="$emit('prompt')">
      <IconText size="xs" />提示词
    </button>
    <button
      v-if="task?.status === 'FAILED' || task?.status === 'COMPLETED'"
      class="jd-button jd-button--sm jd-button--primary"
      type="button"
      :disabled="commandDisabled"
      @click="task && $emit('retry', task)"
    >
      <IconRefresh size="xs" />{{ task.status === "FAILED" ? "重试" : "重新生成" }}
    </button>
    <button
      v-if="task && ['PENDING', 'ANALYZING', 'PLANNING'].includes(task.status)"
      class="jd-button jd-button--sm"
      type="button"
      :disabled="commandDisabled"
      @click="$emit('pause', task)"
    >
      <span class="jd-button__pause" aria-hidden="true"></span>暂停
    </button>
    <button
      v-if="task?.status === 'PAUSED'"
      class="jd-button jd-button--sm jd-button--primary"
      type="button"
      :disabled="commandDisabled"
      @click="task && $emit('continue', task)"
    >
      <IconRefresh size="xs" />继续
    </button>
    <button
      v-if="task && ['PENDING', 'ANALYZING', 'PLANNING', 'RENDERING'].includes(task.status)"
      class="jd-button jd-button--sm jd-button--warning"
      type="button"
      :disabled="commandDisabled"
      @click="$emit('terminate', task)"
    >
      <IconWarning size="xs" />终止
    </button>
    <button
      v-if="task"
      class="jd-button jd-button--sm jd-button--danger"
      type="button"
      :disabled="commandDisabled"
      @click="$emit('delete', task)"
    >
      <IconDelete size="xs" />删除
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { IconDelete, IconRefresh, IconText, IconWarning } from "@/components/icons";
import type { TaskListItem } from "@/types";

const props = defineProps<{
  task: TaskListItem | null;
  loading: boolean;
  managingTaskId: string;
  imageMode: boolean;
}>();

defineEmits<{
  refresh: [];
  prompt: [];
  retry: [task: TaskListItem];
  pause: [task: TaskListItem];
  continue: [task: TaskListItem];
  terminate: [task: TaskListItem];
  delete: [task: TaskListItem];
}>();

const commandDisabled = computed(() =>
  props.loading || Boolean(props.task && props.managingTaskId === props.task.id),
);
</script>

<style scoped src="./task-detail-actions.css"></style>
