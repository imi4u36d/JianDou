<template>
  <Transition name="home-toast-slide">
    <div v-if="taskId" class="home-task-toast" role="status">
      <span class="home-task-toast__icon" aria-hidden="true"><IconCheck size="sm" /></span>
      <span class="home-task-toast__body">
        <strong>任务已提交</strong>
        <small>正在生成，可查看进度</small>
      </span>
      <RouterLink :to="{ name: 'image-tasks', query: { selected: taskId } }">查看任务</RouterLink>
      <button type="button" aria-label="关闭任务提示" @click="emit('dismiss')">
        <IconClose size="xs" />
      </button>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { RouterLink } from "vue-router";
import { IconCheck, IconClose } from "@/components/icons";

defineProps<{ taskId: string }>();
const emit = defineEmits<{ dismiss: [] }>();
</script>

<style scoped src="./home-task-toast.css"></style>
