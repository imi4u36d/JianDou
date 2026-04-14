<template>
  <span :class="['status-badge', statusClass]">
    <span class="status-dot"></span>
    <span>{{ label }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { TaskStatus } from "@/types";
import { formatTaskStatus } from "@/utils/task";

const props = defineProps<{
  status: TaskStatus;
}>();

const label = computed(() => formatTaskStatus(props.status));

const statusClass = computed(() => {
  switch (props.status) {
    case "COMPLETED":
      return "status-completed";
    case "FAILED":
      return "status-failed";
    case "RENDERING":
      return "status-running";
    case "PLANNING":
      return "status-running";
    case "ANALYZING":
      return "status-running";
    case "PAUSED":
      return "status-paused";
    default:
      return "status-idle";
  }
});
</script>

<style scoped>
.status-badge {
  --badge-color: #8b97a8;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.35rem 0.9rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.15em;
  background: #E0E5EC;
  color: var(--badge-color);
  text-transform: uppercase;
  box-shadow:
    4px 4px 8px rgba(147, 157, 174, 0.35),
    -4px -4px 8px rgba(255, 255, 255, 0.9);
}

.status-dot {
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 50%;
  background: var(--badge-color);
  box-shadow:
    inset 1px 1px 3px rgba(255, 255, 255, 0.8),
    inset -1px -1px 3px rgba(0, 0, 0, 0.1);
}

.status-completed {
  --badge-color: #7e9d8d;
}

.status-failed {
  --badge-color: #b37d87;
}

.status-running {
  --badge-color: #c9878e;
}

.status-paused {
  --badge-color: #b79b79;
}

.status-idle {
  --badge-color: #8b97a8;
}
</style>
