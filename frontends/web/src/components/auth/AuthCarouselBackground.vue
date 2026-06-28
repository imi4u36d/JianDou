<template>
  <div class="auth-carousel-bg" aria-hidden="true">
    <div class="auth-carousel-bg__fallback" :style="{ backgroundImage: `url(${fallbackSlide})` }"></div>
    <div
      v-for="slide in visibleSlides"
      :key="slide.src"
      class="auth-carousel-bg__slide"
      :class="{ 'is-active': slide.index === activeIndex }"
      :style="{
        backgroundImage: `url(${slide.src})`,
        transitionDuration: `${transitionMs}ms`
      }"
    ></div>
    <div class="auth-carousel-bg__overlay"></div>
    <div class="auth-carousel-bg__vignette"></div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

type AuthCarouselBackgroundProps = {
  slides?: string[];
  intervalMs?: number;
  transitionMs?: number;
};

const props = withDefaults(defineProps<AuthCarouselBackgroundProps>(), {
  slides: () => [
    "/login-bg/cycle-01.webp",
    "/login-bg/cycle-02.webp",
    "/login-bg/cycle-03.webp",
    "/login-bg/cycle-04.webp"
  ],
  intervalMs: 6000,
  transitionMs: 1200
});

const activeIndex = ref(0);
const prefersReducedMotion = ref(false);
const loadedSlideIndexes = ref<Set<number>>(new Set([0]));
const slidesToUse = computed(() =>
  props.slides.filter((slide) => typeof slide === "string" && slide.trim().length > 0),
);
const fallbackSlide = computed(() => (slidesToUse.value.length ? slidesToUse.value[0] : "/login-bg/cycle-01.webp"));
const hasMultipleSlides = computed(() => slidesToUse.value.length > 1);
const visibleSlides = computed(() =>
  slidesToUse.value
    .map((src, index) => ({ src, index }))
    .filter((slide) => loadedSlideIndexes.value.has(slide.index)),
);

let timerId: ReturnType<typeof setInterval> | null = null;
let preloadTimerId: ReturnType<typeof setTimeout> | null = null;
let motionMatcher: MediaQueryList | null = null;
let preloadCursor = 1;
const preloadImages: HTMLImageElement[] = [];

function clearTimer() {
  if (timerId) {
    clearInterval(timerId);
    timerId = null;
  }
}

function clearPreloadTimer() {
  if (preloadTimerId) {
    clearTimeout(preloadTimerId);
    preloadTimerId = null;
  }
}

function markSlideLoaded(index: number) {
  if (loadedSlideIndexes.value.has(index)) {
    return;
  }
  const nextLoadedIndexes = new Set(loadedSlideIndexes.value);
  nextLoadedIndexes.add(index);
  loadedSlideIndexes.value = nextLoadedIndexes;
}

function advanceSlide() {
  const loadedIndexes = [...loadedSlideIndexes.value]
    .filter((index) => index < slidesToUse.value.length)
    .sort((a, b) => a - b);

  if (loadedIndexes.length < 2) {
    activeIndex.value = loadedIndexes[0] ?? 0;
    return;
  }

  const currentLoadedPosition = loadedIndexes.indexOf(activeIndex.value);
  const nextPosition = currentLoadedPosition === -1 ? 0 : (currentLoadedPosition + 1) % loadedIndexes.length;
  activeIndex.value = loadedIndexes[nextPosition];
}

function startTimer() {
  clearTimer();
  if (hasMultipleSlides.value && loadedSlideIndexes.value.size > 1 && !prefersReducedMotion.value) {
    timerId = setInterval(() => {
      advanceSlide();
    }, props.intervalMs);
  }
}

function preloadNextSlide() {
  clearPreloadTimer();
  if (prefersReducedMotion.value || preloadCursor >= slidesToUse.value.length) {
    return;
  }

  const slideIndex = preloadCursor;
  preloadCursor += 1;
  const image = new Image();
  preloadImages.push(image);

  image.onload = () => {
    markSlideLoaded(slideIndex);
    startTimer();
    preloadTimerId = setTimeout(preloadNextSlide, 350);
  };
  image.onerror = () => {
    preloadTimerId = setTimeout(preloadNextSlide, 350);
  };
  image.src = slidesToUse.value[slideIndex];
}

function schedulePreload() {
  clearPreloadTimer();
  if (!hasMultipleSlides.value || prefersReducedMotion.value) {
    return;
  }
  preloadTimerId = setTimeout(preloadNextSlide, 450);
}

function resetSlides() {
  activeIndex.value = 0;
  preloadCursor = 1;
  loadedSlideIndexes.value = slidesToUse.value.length ? new Set([0]) : new Set();
  preloadImages.forEach((image) => {
    image.onload = null;
    image.onerror = null;
  });
  preloadImages.length = 0;
  schedulePreload();
  startTimer();
}

function onReducedMotionChange(event?: MediaQueryListEvent) {
  prefersReducedMotion.value = event ? event.matches : window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (prefersReducedMotion.value) {
    activeIndex.value = 0;
    clearPreloadTimer();
  } else {
    schedulePreload();
  }
  startTimer();
}

onMounted(() => {
  motionMatcher = window.matchMedia("(prefers-reduced-motion: reduce)");
  onReducedMotionChange();
  if (motionMatcher.addEventListener) {
    motionMatcher.addEventListener("change", onReducedMotionChange);
  } else {
    motionMatcher.addListener(onReducedMotionChange);
  }
  resetSlides();
});

onBeforeUnmount(() => {
  clearTimer();
  clearPreloadTimer();
  preloadImages.forEach((image) => {
    image.onload = null;
    image.onerror = null;
  });
  preloadImages.length = 0;
  if (!motionMatcher) {
    return;
  }
  if (motionMatcher.removeEventListener) {
    motionMatcher.removeEventListener("change", onReducedMotionChange);
  } else {
    motionMatcher.removeListener(onReducedMotionChange);
  }
  motionMatcher = null;
});

watch([hasMultipleSlides, () => props.intervalMs, () => loadedSlideIndexes.value.size], () => {
  startTimer();
});

watch(() => slidesToUse.value.join("\n"), () => {
  resetSlides();
});
</script>

<style scoped>
.auth-carousel-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
  background:
    radial-gradient(circle at 24% 18%, rgba(255, 255, 255, 0.05) 0%, rgba(0, 0, 0, 0) 34%),
    var(--bg-base);
}

.auth-carousel-bg__fallback,
.auth-carousel-bg__slide {
  position: absolute;
  inset: 0;
  background-size: cover;
  background-position: center;
}

.auth-carousel-bg__fallback {
  filter: saturate(1.2) brightness(0.72);
}

.auth-carousel-bg__slide {
  opacity: 0;
  transition: opacity ease-in-out;
  will-change: opacity;
}

.auth-carousel-bg__slide.is-active {
  opacity: 1;
}

.auth-carousel-bg__overlay {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(180deg, rgba(6, 10, 16, 0.24) 0%, rgba(6, 10, 16, 0.38) 100%),
    linear-gradient(75deg, rgba(99, 102, 241, 0.2), rgba(0, 0, 0, 0));
}

.auth-carousel-bg__vignette {
  position: absolute;
  inset: -15%;
  background:
    radial-gradient(40% 65% at 50% 48%, rgba(255, 255, 255, 0.06), rgba(0, 0, 0, 0.58)),
    linear-gradient(145deg, rgba(16, 18, 28, 0.3), rgba(4, 6, 12, 0.82));
  filter: blur(0.2px);
}
</style>
