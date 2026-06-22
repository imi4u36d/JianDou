<template>
  <div class="app-glass-bg" aria-hidden="true"></div>
</template>

<style scoped>
.app-glass-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  background: var(--bg-base);
  pointer-events: none;
}
</style>
