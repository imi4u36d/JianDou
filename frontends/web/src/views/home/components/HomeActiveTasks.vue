<template>
  <section v-if="tasks.length" class="home-active-tasks" aria-label="进行中的任务">
    <RouterLink
      v-for="task in tasks"
      :key="task.id"
      class="home-active-task-card"
      :to="{ name: 'image-tasks', query: { selected: task.id } }"
    >
      <div class="home-active-task-card__top">
        <span class="home-active-task-card__type">{{ task.aspectRatio || "生成任务" }}</span>
        <span class="home-active-task-card__status">{{ formatTaskStatus(task.status) }}</span>
      </div>
      <h2>{{ task.title }}</h2>
      <p>{{ activeTaskStageLabel(task) }}</p>
      <div class="home-active-task-card__progress" aria-hidden="true">
        <span :style="{ width: `${activeTaskProgress(task)}%` }"></span>
      </div>
      <div class="home-active-task-card__meta">
        <span>{{ activeTaskProgress(task) }}%</span>
        <span>{{ formatActiveTaskTime(task.updatedAt || task.createdAt) }}</span>
      </div>
    </RouterLink>
  </section>
</template>

<script setup lang="ts">
import { RouterLink } from "vue-router";
import { formatTaskStatus } from "@/utils/task";
import type { TaskListItem } from "@/types";
import { activeTaskProgress, activeTaskStageLabel, formatActiveTaskTime } from "@/features/home/active-task-presenters";

defineProps<{ tasks: TaskListItem[] }>();
</script>

<style scoped src="./home-active-tasks.css"></style>
