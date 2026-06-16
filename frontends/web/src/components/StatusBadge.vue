<template>
  <span :class="['status-badge', statusClass]">
    <span class="status-dot"></span>
    <span>{{ label }}</span>
  </span>
</template>

<script setup lang="ts">
/**
 * 状态组件。
 */
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
  --badge-color: var(--text-muted);
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.35rem 0.9rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.15em;
  background: #f5f8fa;
  color: var(--badge-color);
  text-transform: uppercase;
  border: 1px solid rgba(15, 20, 25, 0.06);
  box-shadow: none;
}

.status-dot {
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 50%;
  background: var(--badge-color);
}

.status-completed {
  --badge-color: #1b9f63;
}

.status-failed {
  --badge-color: #d73555;
}

.status-running {
  --badge-color: var(--accent-cyan);
}

.status-paused {
  --badge-color: #b7791f;
}

.status-idle {
  --badge-color: var(--text-muted);
}
</style>
