<template>
  <Teleport to="body">
    <Transition name="task-prompt-dialog-fade">
      <div
        v-if="open"
        class="task-prompt-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="task-prompt-dialog-title"
        @click.self="$emit('close')"
        @keydown.esc.stop.prevent="$emit('close')"
      >
        <section class="task-prompt-dialog__panel">
          <header class="task-prompt-dialog__header">
            <div>
              <h3 id="task-prompt-dialog-title">使用的提示词</h3>
              <p>{{ title || "当前任务" }}</p>
            </div>
            <button
              ref="closeButton"
              class="task-prompt-dialog__close"
              type="button"
              aria-label="关闭提示词"
              title="关闭"
              @click="$emit('close')"
            >
              <IconClose size="sm" />
            </button>
          </header>
          <div class="task-prompt-dialog__content" :class="{ 'task-prompt-dialog__content-empty': !prompt }">
            <pre v-if="prompt">{{ prompt }}</pre>
            <p v-else>暂无提示词</p>
          </div>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from "vue";
import { IconClose } from "@/components/icons";

const props = defineProps<{ open: boolean; title: string; prompt: string }>();
defineEmits<{ close: [] }>();
const closeButton = ref<HTMLButtonElement | null>(null);

watch(
  () => props.open,
  async (open) => {
    if (!open) return;
    await nextTick();
    closeButton.value?.focus({ preventScroll: true });
  },
  { immediate: true },
);
</script>

<style scoped src="./task-prompt-dialog.css"></style>
