<template>
  <Teleport to="body">
    <div class="message-container" role="status" aria-live="polite">
      <TransitionGroup name="message-slide">
        <div v-for="entry in entries" :key="entry.id" class="message-toast" :class="`message-toast--${entry.type}`">
          <span class="message-toast__icon">
            <IconSuccess v-if="entry.type === 'success'" size="sm" />
            <IconError v-else-if="entry.type === 'error'" size="sm" />
            <IconWarning v-else-if="entry.type === 'warning'" size="sm" />
            <IconInfo v-else size="sm" />
          </span>
          <span class="message-toast__content">{{ entry.content }}</span>
          <button type="button" class="message-toast__close" aria-label="关闭" @click="remove(entry.id)"><IconClose size="xs" /></button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { useMessage } from "@/composables/useMessage";
import { IconSuccess, IconError, IconWarning, IconInfo, IconClose } from "@/components/icons";

const { entries, remove } = useMessage();
</script>

<style scoped>
.message-container {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
  max-width: min(420px, calc(100vw - 32px));
}

.message-toast {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 44px;
  padding: 10px 14px 10px 16px;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(15, 20, 25, 0.12);
  border: 1px solid rgba(15, 20, 25, 0.06);
  pointer-events: auto;
}

.message-toast__icon {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  font-size: 0.78rem;
  font-weight: 800;
}

.message-toast--success .message-toast__icon {
  background: rgba(34, 197, 94, 0.12);
  color: #16a34a;
}

.message-toast--error .message-toast__icon {
  background: rgba(229, 72, 101, 0.12);
  color: var(--accent-danger, #e54865);
}

.message-toast--warning .message-toast__icon {
  background: rgba(217, 137, 0, 0.12);
  color: var(--accent-warning, #d98900);
}

.message-toast--info .message-toast__icon {
  background: rgba(46, 125, 255, 0.12);
  color: #2e7dff;
}

.message-toast__content {
  flex: 1;
  min-width: 0;
  font-size: 0.86rem;
  font-weight: 600;
  color: var(--text-strong, #102842);
  overflow-wrap: anywhere;
}

.message-toast__close {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--text-muted, #9aa5ad);
  font-size: 1.1rem;
  line-height: 1;
  cursor: pointer;
}

.message-toast__close:hover {
  background: rgba(15, 20, 25, 0.06);
}

.message-slide-enter-active,
.message-slide-leave-active {
  transition: opacity 200ms ease, transform 200ms ease;
}

.message-slide-enter-from,
.message-slide-leave-to {
  opacity: 0;
  transform: translateX(24px);
}

.message-slide-move {
  transition: transform 200ms ease;
}

.message-slide-leave-active {
  position: absolute;
  right: 0;
}

@media (max-width: 640px) {
  .message-container {
    top: 64px;
    right: 12px;
    left: 12px;
    max-width: none;
  }

  .message-toast {
    width: 100%;
    padding: 10px 10px 10px 12px;
    border-radius: 14px;
  }
}
</style>
