<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="create-task-dialog-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-task-dialog-title"
      @click.self="requestClose"
      @keydown.esc.stop.prevent="requestClose"
    >
      <div class="create-task-dialog">
        <header class="create-task-dialog__head">
          <h2 id="create-task-dialog-title">开始新任务</h2>
        </header>
        <button type="button" class="create-task-dialog__close" aria-label="关闭" @click="requestClose">
          <IconClose size="sm" />
        </button>

        <form class="create-task-dialog__body" @submit.prevent="submitTask">
          <label class="create-field">
            <span>标题</span>
            <input ref="titleInputRef" v-model="taskTitle" required placeholder="任务名称" />
          </label>
          <label class="create-field">
            <span>灵感创作</span>
            <textarea v-model="taskPrompt" rows="6" placeholder="描述你要生成的视频内容"></textarea>
          </label>
          <label class="create-field">
            <span>画幅</span>
            <AppSelect v-model="taskAspectRatio" :options="aspectRatioOptions" />
          </label>

          <div class="create-task-dialog__footer">
            <span class="create-status-text" :class="{ 'create-status-text--error': isStatusError }">{{ taskStatusText }}</span>
            <button class="jd-button jd-button--primary" type="submit" :disabled="submitting || !taskTitle.trim()">
              <IconLoading v-if="submitting" size="xs" />
              <span>{{ submitting ? "创建中" : "开始" }}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import AppSelect from "@/components/common/AppSelect.vue";
import { IconClose, IconLoading } from "@/components/icons";
import { useCreateTaskDialog } from "@/views/unified/composables/useCreateTaskDialog";

const props = defineProps<{
  open: boolean;
}>();

const emit = defineEmits<{
  close: [];
  created: [id: string];
}>();

const {
  aspectRatioOptions,
  isStatusError,
  requestClose,
  submitTask,
  submitting,
  taskAspectRatio,
  taskPrompt,
  taskStatusText,
  taskTitle,
  titleInputRef,
} = useCreateTaskDialog({
  open: () => props.open,
  close: () => emit("close"),
  created: (id) => emit("created", id),
});
</script>

<style scoped src="./create-task-dialog.css"></style>
