<template>
  <div class="mb-6 flex flex-col gap-2">
    <p class="text-xs uppercase tracking-[0.3em] text-orange-300">{{ eyebrow }}</p>
    <div class="flex flex-col gap-2 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <h2 class="text-2xl font-semibold text-white">{{ title }}</h2>
        <p class="mt-1 text-sm leading-6 text-slate-300">{{ description }}</p>
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

