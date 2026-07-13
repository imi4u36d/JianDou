<template>
  <h1
    class="home-brand-play"
    :class="{
      'home-brand-play-focused': focused,
      'home-brand-play-active': active,
      'home-brand-play-submitting': submitting,
    }"
    aria-label="JianDou 图片生成工作台"
  >
    <span class="home-brand-play__stage" aria-hidden="true">
      <span class="home-brand-play__halo"></span>
      <svg class="home-brand-play__mark" viewBox="0 0 128 128" role="presentation" focusable="false">
        <defs>
          <linearGradient id="home-brand-gradient" x1="31" y1="29" x2="97" y2="99" gradientUnits="userSpaceOnUse">
            <stop stop-color="#8b5cf6" />
            <stop offset="0.5" stop-color="#6366f1" />
            <stop offset="1" stop-color="#3b82f6" />
          </linearGradient>
          <linearGradient id="home-brand-gloss" x1="30" y1="32" x2="106" y2="65" gradientUnits="userSpaceOnUse">
            <stop stop-color="#c4b5fd" />
            <stop offset="1" stop-color="#ffffff" stop-opacity="0.36" />
          </linearGradient>
        </defs>
        <g class="home-brand-play__letter home-brand-play__letter-j">
          <path class="home-brand-play__logo-shadow" d="M27 39C32.7 34 43.2 33.5 49.5 38.8" />
          <path
            class="home-brand-play__logo-shadow"
            d="M44 37C45.2 51.2 44.7 64.5 41.5 75C37.4 88.6 27.9 95.3 18.5 90.5"
          />
          <path class="home-brand-play__logo-stroke" d="M27 39C32.7 34 43.2 33.5 49.5 38.8" />
          <path
            class="home-brand-play__logo-stroke"
            d="M44 37C45.2 51.2 44.7 64.5 41.5 75C37.4 88.6 27.9 95.3 18.5 90.5"
          />
          <path class="home-brand-play__logo-gloss" d="M31 38.5C35.1 36.7 42 36.8 46.4 39" />
          <g class="home-brand-play__face home-brand-play__face-j">
            <circle cx="35.4" cy="47.4" r="2" />
            <circle cx="44.6" cy="47.8" r="2" />
            <path d="M35.5 54.5C38.4 57 42.7 57 45.5 54.5" />
          </g>
        </g>
        <g class="home-brand-play__letter home-brand-play__letter-d">
          <path
            class="home-brand-play__logo-fill-shadow"
            fill-rule="evenodd"
            clip-rule="evenodd"
            d="M77 32H87C105.7 32 116 44.5 116 64C116 83.5 105.7 96 87 96H77C70.9 96 67 92.1 67 86V42C67 35.9 70.9 32 77 32ZM84 48V80H87C96.4 80 101.4 74.1 101.4 64C101.4 53.9 96.4 48 87 48H84Z"
          />
          <path
            class="home-brand-play__logo-fill"
            fill-rule="evenodd"
            clip-rule="evenodd"
            d="M77 30H87C105.7 30 116 42.5 116 62C116 81.5 105.7 94 87 94H77C70.9 94 67 90.1 67 84V40C67 33.9 70.9 30 77 30ZM84 46V78H87C96.4 78 101.4 72.1 101.4 62C101.4 51.9 96.4 46 87 46H84Z"
          />
          <path class="home-brand-play__logo-gloss" d="M77 40C79.4 36.7 84.2 35.2 89.2 35.5" />
          <g class="home-brand-play__face home-brand-play__face-d">
            <circle cx="88.7" cy="60" r="1.8" />
            <circle cx="96.2" cy="60" r="1.8" />
            <path d="M88.6 67C91.2 69.4 95.3 69.4 97.9 67" />
          </g>
        </g>
      </svg>
      <span class="home-brand-play__collision"></span>
      <span class="home-brand-play__burst">
        <span class="home-brand-play__spark home-brand-play__spark-1"></span>
        <span class="home-brand-play__spark home-brand-play__spark-2"></span>
        <span class="home-brand-play__spark home-brand-play__spark-3"></span>
        <span class="home-brand-play__spark home-brand-play__spark-4"></span>
        <span class="home-brand-play__spark home-brand-play__spark-5"></span>
        <span class="home-brand-play__spark home-brand-play__spark-6"></span>
        <span class="home-brand-play__spark home-brand-play__spark-7"></span>
        <span class="home-brand-play__spark home-brand-play__spark-8"></span>
      </span>
      <span class="home-brand-play__fall">
        <span class="home-brand-play__fall-dot home-brand-play__fall-dot-1"></span>
        <span class="home-brand-play__fall-dot home-brand-play__fall-dot-2"></span>
        <span class="home-brand-play__fall-dot home-brand-play__fall-dot-3"></span>
        <span class="home-brand-play__fall-dot home-brand-play__fall-dot-4"></span>
        <span class="home-brand-play__fall-dot home-brand-play__fall-dot-5"></span>
        <span class="home-brand-play__fall-dot home-brand-play__fall-dot-6"></span>
      </span>
    </span>
  </h1>
</template>

<script setup lang="ts">
defineProps<{
  focused: boolean;
  active: boolean;
  submitting: boolean;
}>();
</script>

<style scoped src="./home-brand-play.css"></style>
