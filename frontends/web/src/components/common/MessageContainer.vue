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
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(40px) saturate(1.8);
  -webkit-backdrop-filter: blur(40px) saturate(1.8);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.7);
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
  background: rgba(74, 222, 128, 0.15);
  color: var(--accent-lime);
}

.message-toast--error .message-toast__icon {
  background: rgba(251, 113, 133, 0.15);
  color: var(--accent-danger);
}

.message-toast--warning .message-toast__icon {
  background: rgba(251, 191, 36, 0.15);
  color: var(--accent-warning);
}

.message-toast--info .message-toast__icon {
  background: rgba(99, 102, 241, 0.15);
  color: var(--accent-blue);
}

.message-toast__content {
  flex: 1;
  min-width: 0;
  font-size: 0.86rem;
  font-weight: 600;
  color: var(--text-strong);
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
  color: var(--text-muted);
  font-size: 1.1rem;
  line-height: 1;
  cursor: pointer;
}

.message-toast__close:hover {
  background: rgba(255, 255, 255, 0.1);
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
    border-radius: var(--radius-md);
  }
}
</style>
