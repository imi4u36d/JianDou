<template>
  <section class="forbidden-view">
    <div class="forbidden-view__card">
      <h1>没有权限</h1>
      <div class="forbidden-view__actions">
        <RouterLink class="forbidden-view__secondary" to="/image-tasks">
          <IconHome size="xs" />
          <span>任务</span>
        </RouterLink>
        <RouterLink class="forbidden-view__primary" to="/image-tasks">
          <IconTask size="xs" />
          <span>任务</span>
        </RouterLink>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { IconHome, IconTask } from "@/components/icons";
</script>

<style scoped>
.forbidden-view {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background: var(--bg-base);
}

.forbidden-view__card {
  width: min(380px, 100%);
  padding: 22px;
  border-radius: 12px;
  border: 1px solid var(--surface-border);
  background: var(--bg-surface);
  box-shadow: 0 16px 40px rgba(16, 24, 40, 0.08);
  text-align: center;
}

.forbidden-view__card h1 {
  margin: 0;
  font-family: inherit;
  font-size: clamp(1.45rem, 3.8vw, 1.9rem);
  letter-spacing: 0;
  color: var(--text-strong);
}

.forbidden-view__card p {
  margin: 16px 0 0;
  color: var(--text-body);
  line-height: 1.8;
}

.forbidden-view__actions {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-top: 20px;
}

.forbidden-view__primary,
.forbidden-view__secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 40px;
  padding: 0 14px;
  border-radius: 10px;
  font-size: 0.88rem;
  font-weight: 800;
  text-decoration: none;
}

.forbidden-view__primary :deep(svg),
.forbidden-view__secondary :deep(svg) {
  width: 14px;
  height: 14px;
}

.forbidden-view__primary {
  background: var(--accent-indigo);
  color: #fff;
  box-shadow: none;
}

.forbidden-view__secondary {
  border: 1px solid var(--surface-border-strong);
  background: var(--bg-surface);
  color: var(--text-strong);
}

.forbidden-view__primary:hover,
.forbidden-view__secondary:hover,
.forbidden-view__primary:focus-visible,
.forbidden-view__secondary:focus-visible {
  transform: translateY(-1px);
  box-shadow: var(--shadow-soft);
}

@media (max-width: 640px) {
  .forbidden-view__actions {
    flex-direction: column;
  }
}
</style>
