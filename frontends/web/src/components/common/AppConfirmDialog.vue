<template>
  <Transition name="app-confirm-fade">
    <div v-if="open" class="app-confirm" role="dialog" aria-modal="true" @click.self="emit('cancel')">
      <div class="app-confirm__panel">
        <div class="app-confirm__icon" :class="`app-confirm__icon-${tone}`" aria-hidden="true">
          <IconWarning v-if="tone === 'danger'" size="sm" />
          <IconInfo v-else size="sm" />
        </div>
        <div class="app-confirm__body">
          <h3>{{ title }}</h3>
          <p>{{ message }}</p>
        </div>
        <div class="app-confirm__actions">
          <button type="button" class="app-confirm__cancel" @click="emit('cancel')">{{ cancelText }}</button>
          <button type="button" class="app-confirm__confirm" :class="`app-confirm__confirm-${tone}`" @click="emit('confirm')">
            {{ confirmText }}
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { IconInfo, IconWarning } from "@/components/icons";

withDefaults(defineProps<{
  open: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  tone?: "danger" | "primary";
}>(), {
  confirmText: "确认",
  cancelText: "取消",
  tone: "danger",
});

const emit = defineEmits<{
  confirm: [];
  cancel: [];
}>();
</script>

<style scoped>
.app-confirm {
  position: fixed;
  inset: 0;
  z-index: 1500;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(10, 10, 20, 0.25);
  backdrop-filter: blur(40px) saturate(2.0);
}

.app-confirm__panel {
  position: relative;
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr);
  gap: 14px;
  width: min(420px, 100%);
  padding: 16px;
  border: 1px solid rgba(255, 255, 255, 0.7);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(40px) saturate(1.8);
  -webkit-backdrop-filter: blur(40px) saturate(1.8);
  box-shadow: 0 22px 56px rgba(0, 0, 0, 0.12), inset 0 1px 0 rgba(255, 255, 255, 0.95);
}

.app-confirm__icon {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 13px;
}

.app-confirm__icon-danger {
  background: rgba(251, 113, 133, 0.15);
  color: var(--accent-danger);
}

.app-confirm__icon-primary {
  background: rgba(99, 102, 241, 0.12);
  color: var(--accent-blue);
}

.app-confirm__body {
  display: grid;
  gap: 7px;
  min-width: 0;
}

.app-confirm__body h3,
.app-confirm__body p {
  margin: 0;
}

.app-confirm__body h3 {
  color: var(--text-strong);
  font-size: 0.98rem;
  font-weight: 850;
  line-height: 1.35;
}

.app-confirm__body p {
  color: var(--text-body);
  font-size: 0.86rem;
  line-height: 1.65;
  overflow-wrap: anywhere;
}

.app-confirm__actions {
  grid-column: 1 / -1;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 4px;
}

.app-confirm__cancel,
.app-confirm__confirm {
  min-height: 38px;
  padding: 0 15px;
  border: 0;
  border-radius: var(--radius-sm);
  font-size: 0.84rem;
  font-weight: 820;
  cursor: pointer;
  transition: transform 160ms ease, box-shadow 160ms ease;
}

.app-confirm__cancel:active,
.app-confirm__confirm:active {
  transform: scale(0.97);
}

.app-confirm__cancel {
  background: rgba(0, 0, 0, 0.04);
  color: var(--text-body);
}

.app-confirm__cancel:hover {
  background: rgba(255, 255, 255, 0.55);
}

.app-confirm__confirm {
  color: #fff;
}

.app-confirm__confirm-danger {
  background: linear-gradient(135deg, #fb7185, #e54865);
  box-shadow: 0 8px 20px rgba(251, 113, 133, 0.25);
}

.app-confirm__confirm-primary {
  background: var(--bg-accent);
  box-shadow: 0 8px 20px rgba(99, 102, 241, 0.2);
}

.app-confirm-fade-enter-active,
.app-confirm-fade-leave-active {
  transition: opacity 160ms ease;
}

.app-confirm-fade-enter-active .app-confirm__panel,
.app-confirm-fade-leave-active .app-confirm__panel {
  transition: transform 180ms cubic-bezier(0.22, 1, 0.36, 1);
}

.app-confirm-fade-enter-from,
.app-confirm-fade-leave-to {
  opacity: 0;
}

.app-confirm-fade-enter-from .app-confirm__panel,
.app-confirm-fade-leave-to .app-confirm__panel {
  transform: translateY(8px) scale(0.985);
}

@media (max-width: 640px) {
  .app-confirm {
    align-items: end;
    padding: 14px;
  }

  .app-confirm__panel {
    width: 100%;
    border-radius: var(--radius-lg);
    padding: 26px 16px 14px;
  }

  .app-confirm__panel::before {
    content: "";
    position: absolute;
    top: 10px;
    left: 50%;
    width: 38px;
    height: 4px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.2);
    transform: translateX(-50%);
  }

  .app-confirm__actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }
}
</style>
