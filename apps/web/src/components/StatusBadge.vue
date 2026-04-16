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
  --badge-color: rgba(255, 255, 255, 0.56);
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.35rem 0.9rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.15em;
  background: rgba(9, 12, 18, 0.84);
  color: var(--badge-color);
  text-transform: uppercase;
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.05),
    0 10px 20px rgba(0, 0, 0, 0.22);
}

.status-dot {
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 50%;
  background: var(--badge-color);
  box-shadow: 0 0 14px rgba(255, 255, 255, 0.16);
}

.status-completed {
  --badge-color: #68e0b0;
}

.status-failed {
  --badge-color: #ff8fa9;
}

.status-running {
  --badge-color: #6ed5ff;
}

.status-paused {
  --badge-color: #ffce72;
}

.status-idle {
  --badge-color: rgba(255, 255, 255, 0.56);
}
</style>
