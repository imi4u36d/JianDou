<template>
  <div class="workflow-stage-empty" :class="{ 'workflow-stage-empty-compact': compact }" role="status">
    <span class="workflow-stage-empty__icon" aria-hidden="true">
      <IconEmpty size="lg" />
    </span>
    <div class="workflow-stage-empty__copy">
      <strong>{{ title }}</strong>
      <p v-if="description">{{ description }}</p>
    </div>
    <div v-if="$slots.action" class="workflow-stage-empty__action">
      <slot name="action" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { IconEmpty } from "@/components/icons";

withDefaults(
  defineProps<{
    title: string;
    description?: string;
    compact?: boolean;
  }>(),
  {
    description: "",
    compact: false,
  },
);
</script>

<style scoped>
.workflow-stage-empty {
  display: grid;
  justify-items: center;
  align-content: center;
  gap: 12px;
  min-height: 176px;
  padding: 28px 22px;
  border: 1px dashed rgba(99, 102, 241, 0.2);
  border-radius: 12px;
  background: radial-gradient(circle at 50% 0, rgba(99, 102, 241, 0.08), transparent 52%), var(--bg-subtle, #f8f9fb);
  text-align: center;
}

.workflow-stage-empty-compact {
  min-height: 132px;
  padding-block: 20px;
}

.workflow-stage-empty__icon {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border: 1px solid rgba(99, 102, 241, 0.14);
  border-radius: 12px;
  background: #fff;
  color: var(--accent-blue);
  box-shadow: 0 6px 18px rgba(44, 51, 73, 0.06);
}

.workflow-stage-empty__copy {
  display: grid;
  justify-items: center;
  gap: 5px;
  max-width: 420px;
}

.workflow-stage-empty__copy strong {
  color: var(--text-strong);
  font-size: 0.94rem;
  font-weight: 600;
}

.workflow-stage-empty__copy p {
  margin: 0;
  color: var(--text-muted);
  font-size: 0.82rem;
  line-height: 1.6;
}

.workflow-stage-empty__action {
  display: flex;
  justify-content: center;
}

@media (max-width: 640px) {
  .workflow-stage-empty {
    min-height: 150px;
    padding: 22px 16px;
  }

  .workflow-stage-empty-compact {
    min-height: 120px;
  }
}
</style>
