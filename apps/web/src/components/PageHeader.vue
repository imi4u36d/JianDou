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
  background-color: #E0E5EC;
  padding: 1.25rem;
  border-radius: 28px;
  box-shadow: 18px 18px 34px rgba(145, 164, 186, 0.45), -12px -12px 28px rgba(255, 255, 255, 0.9);
}

.page-header-eyebrow {
  margin: 0 0 0.35rem;
  font-size: 0.78rem;
  letter-spacing: 0.3em;
  text-transform: uppercase;
  color: #5f6573;
}

.page-header-title {
  margin: 0;
  font-size: clamp(1.5rem, 2.8vw, 2.4rem);
  color: #1f242c;
}

.page-header-description {
  margin: 0.35rem 0 0;
  color: #4c5262;
}
</style>
