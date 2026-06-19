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
  background: rgba(15, 20, 25, 0.34);
  backdrop-filter: blur(10px);
}

.app-confirm__panel {
  position: relative;
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr);
  gap: 14px;
  width: min(420px, 100%);
  padding: 16px;
  border: 1px solid rgba(15, 20, 25, 0.08);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow:
    0 22px 56px rgba(15, 20, 25, 0.16),
    0 2px 8px rgba(18, 28, 33, 0.04);
}

.app-confirm__icon {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 13px;
}

.app-confirm__icon-danger {
  background: #fff4f6;
  color: var(--accent-danger);
}

.app-confirm__icon-primary {
  background: #effcff;
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
  border-radius: 12px;
  font-size: 0.84rem;
  font-weight: 820;
  cursor: pointer;
}

.app-confirm__cancel {
  background: #f3f6f8;
  color: var(--text-body);
}

.app-confirm__confirm {
  color: #fff;
}

.app-confirm__confirm-danger {
  background: linear-gradient(135deg, #ff6b5f, #e54865);
}

.app-confirm__confirm-primary {
  background: var(--bg-accent);
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
    border-radius: 22px;
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
    background: rgba(15, 20, 25, 0.16);
    transform: translateX(-50%);
  }

  .app-confirm__actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }
}
</style>
