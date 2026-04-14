<template>
  <main class="home-view">
    <div class="home-mesh"></div>
    <div class="home-glow home-glow-left"></div>
    <div class="home-glow home-glow-right"></div>
    <div class="home-glow home-glow-center"></div>
    <section class="home-container">
      <HomeHero />
      <div class="home-story-grid">
        <HomeCapabilityHighlights />
        <HomeVideoShowcase />
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import HomeCapabilityHighlights from "@/components/home/HomeCapabilityHighlights.vue";
import HomeHero from "@/components/home/HomeHero.vue";
import HomeVideoShowcase from "@/components/home/HomeVideoShowcase.vue";
</script>

<style scoped>
.home-view {
  position: relative;
  min-height: 100%;
  overflow: hidden;
  padding: clamp(1rem, 2.8vw, 2.1rem);
  background:
    radial-gradient(circle at top left, rgba(255, 214, 209, 0.52), transparent 26%),
    radial-gradient(circle at 82% 16%, rgba(205, 219, 240, 0.48), transparent 24%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.18), transparent 30%);
  color: #1f242c;
}

.home-container {
  position: relative;
  z-index: 1;
  max-width: 1180px;
  margin: 0 auto;
  display: grid;
  gap: 1.25rem;
  animation: fade-up 0.55s ease-out;
}

.home-story-grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: minmax(320px, 0.92fr) minmax(0, 1.08fr);
}

.home-mesh {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  opacity: 0.34;
  background:
    linear-gradient(rgba(255, 255, 255, 0.24) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.24) 1px, transparent 1px);
  background-size: 72px 72px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.35), transparent 86%);
}

.home-glow {
  position: absolute;
  z-index: 0;
  width: 360px;
  height: 360px;
  pointer-events: none;
  filter: blur(26px);
  opacity: 0.28;
}

.home-glow-left {
  top: -110px;
  left: -120px;
  background: radial-gradient(circle, rgba(255, 183, 174, 0.54), transparent 62%);
}

.home-glow-right {
  top: 120px;
  right: -120px;
  background: radial-gradient(circle, rgba(190, 206, 230, 0.62), transparent 64%);
}

.home-glow-center {
  top: 400px;
  left: 42%;
  width: 260px;
  height: 260px;
  background: radial-gradient(circle, rgba(255, 205, 194, 0.42), transparent 66%);
}

@keyframes fade-up {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 1024px) {
  .home-story-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .home-view {
    padding: 0.85rem;
  }

  .home-glow {
    width: 220px;
    height: 220px;
  }

  .home-mesh {
    background-size: 48px 48px;
  }
}
</style>
