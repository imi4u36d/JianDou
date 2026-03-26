<template>
  <div class="relative min-h-screen overflow-x-hidden text-white">
    <div class="pointer-events-none absolute inset-0 z-0 bg-[radial-gradient(circle_at_12%_8%,rgba(96,165,250,0.18),transparent_22%),radial-gradient(circle_at_86%_10%,rgba(245,158,11,0.14),transparent_20%),radial-gradient(circle_at_50%_100%,rgba(29,78,216,0.14),transparent_28%),linear-gradient(180deg,rgba(8,17,31,0.96)_0%,rgba(8,24,43,0.96)_42%,rgba(5,13,24,0.98)_100%)]"></div>
    <div class="pointer-events-none absolute inset-0 z-0 opacity-[0.07]" style="background-image: linear-gradient(rgba(148,163,184,0.18) 1px, transparent 1px), linear-gradient(90deg, rgba(148,163,184,0.18) 1px, transparent 1px); background-size: 48px 48px;"></div>
    <div class="pointer-events-none absolute inset-x-0 top-0 z-0 h-48 bg-[linear-gradient(180deg,rgba(255,255,255,0.05),transparent)] opacity-70"></div>
    <RouterView />
  </div>
</template>

<script setup lang="ts"></script>
