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
  background:
    radial-gradient(circle at top right, rgba(255, 183, 174, 0.28), transparent 28%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.86), rgba(255, 255, 255, 0.42)),
    var(--bg-surface);
  padding: 1.35rem;
  border-radius: 28px;
  border: 1px solid var(--surface-border);
  box-shadow: var(--shadow-raise);
}

.page-header-surface::after {
  content: "";
  position: absolute;
  inset: auto 1.25rem 0;
  height: 1px;
  background: linear-gradient(90deg, rgba(197, 108, 115, 0.24), rgba(197, 108, 115, 0));
}

.page-header-eyebrow {
  margin: 0 0 0.35rem;
  font-size: 0.78rem;
  letter-spacing: 0.3em;
  text-transform: uppercase;
  color: #6f7988;
}

.page-header-title {
  margin: 0;
  font-size: clamp(1.5rem, 2.8vw, 2.4rem);
  color: var(--text-strong);
  letter-spacing: -0.04em;
}

.page-header-description {
  margin: 0.35rem 0 0;
  color: var(--text-body);
  max-width: 60ch;
}
</style>
