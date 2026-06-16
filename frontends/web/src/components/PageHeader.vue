<template>
  <div class="page-header mb-6 page-header-surface">
    <p class="page-header-eyebrow">{{ eyebrow }}</p>
    <div class="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
      <div class="max-w-3xl">
        <h2 class="page-header-title">{{ title }}</h2>
        <p class="page-header-description">{{ description }}</p>
      </div>
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 页面Header组件。
 */
defineProps<{
  eyebrow: string;
  title: string;
  description: string;
}>();

</script>

<style scoped>
.page-header-surface {
  position: relative;
  overflow: hidden;
  padding: 1.35rem 1.5rem;
  border-radius: 24px;
  border: 1px solid var(--surface-border);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02)),
    var(--bg-surface);
  box-shadow: var(--shadow-panel);
}

.page-header-surface::after {
  content: "";
  position: absolute;
  inset: auto 1.5rem 0;
  height: 1px;
  background: linear-gradient(90deg, rgba(176, 92, 255, 0.34), rgba(78, 219, 255, 0.08), rgba(255, 255, 255, 0));
}

.page-header-surface::before {
  content: "";
  position: absolute;
  inset: auto auto -3.4rem 70%;
  width: 14rem;
  height: 9rem;
  border-radius: 999px;
  background: radial-gradient(circle, rgba(78, 219, 255, 0.16), transparent 70%);
  filter: blur(20px);
}

.page-header-eyebrow {
  margin: 0 0 0.35rem;
  font-size: 0.78rem;
  letter-spacing: 0.3em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.page-header-title {
  margin: 0;
  font-size: clamp(1.5rem, 2.8vw, 2.4rem);
  color: var(--text-strong);
  letter-spacing: -0.05em;
}

.page-header-description {
  margin: 0.35rem 0 0;
  color: var(--text-body);
  max-width: 60ch;
}
</style>
