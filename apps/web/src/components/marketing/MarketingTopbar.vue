<template>
  <header class="marketing-topbar">
    <RouterLink class="marketing-brand" to="/">
      <img alt="煎豆 Logo" class="marketing-brand__logo" src="/brand/jiandou-mark.svg" />
      <span>煎豆工作台</span>
    </RouterLink>

    <nav class="marketing-topbar__nav" aria-label="主导航">
      <a
        v-if="props.scrollSections"
        class="marketing-topbar__link"
        :class="{ 'marketing-topbar__link-active': props.activePage === 'home' }"
        href="#top"
        @click.prevent="emitSection('top')"
      >
        首页
      </a>
      <RouterLink
        v-else
        class="marketing-topbar__link"
        :class="{ 'marketing-topbar__link-active': props.activePage === 'home' }"
        to="/"
      >
        首页
      </RouterLink>
      <RouterLink
        class="marketing-topbar__link"
        :class="{ 'marketing-topbar__link-active': props.activePage === 'docs' }"
        to="/docs"
      >
        使用文档
      </RouterLink>
      <a
        v-if="props.scrollSections"
        class="marketing-topbar__link"
        href="#features"
        @click.prevent="emitSection('features')"
      >
        产品能力
      </a>
      <RouterLink v-else class="marketing-topbar__link" :to="{ path: '/', hash: '#features' }">
        产品能力
      </RouterLink>
      <a
        v-if="props.scrollSections"
        class="marketing-topbar__link"
        href="#solutions"
        @click.prevent="emitSection('solutions')"
      >
        解决方案
      </a>
      <RouterLink v-else class="marketing-topbar__link" :to="{ path: '/', hash: '#solutions' }">
        解决方案
      </RouterLink>
    </nav>

    <div class="marketing-topbar__actions">
      <a
        class="marketing-topbar__github"
        :href="props.githubRepoUrl"
        target="_blank"
        rel="noreferrer"
        aria-label="打开 GitHub 仓库"
        title="GitHub"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path
            d="M12 2C6.48 2 2 6.59 2 12.25c0 4.53 2.87 8.37 6.84 9.72.5.1.66-.22.66-.49 0-.24-.01-1.03-.01-1.86-2.78.62-3.37-1.21-3.37-1.21-.46-1.19-1.11-1.51-1.11-1.51-.91-.64.07-.62.07-.62 1 .07 1.53 1.06 1.53 1.06.9 1.57 2.35 1.12 2.93.86.09-.67.35-1.12.64-1.38-2.22-.26-4.56-1.14-4.56-5.08 0-1.12.39-2.03 1.03-2.75-.1-.26-.45-1.31.1-2.73 0 0 .84-.28 2.75 1.05A9.3 9.3 0 0 1 12 6.84c.85 0 1.71.12 2.51.36 1.91-1.33 2.75-1.05 2.75-1.05.55 1.42.2 2.47.1 2.73.64.72 1.03 1.63 1.03 2.75 0 3.95-2.35 4.82-4.58 5.07.36.32.68.95.68 1.92 0 1.38-.01 2.49-.01 2.83 0 .27.18.59.67.49A10.29 10.29 0 0 0 22 12.25C22 6.59 17.52 2 12 2Z"
          />
        </svg>
      </a>
      <RouterLink class="marketing-topbar__primary" to="/generate">立即开始</RouterLink>
    </div>
  </header>
</template>

<script setup lang="ts">
type ActivePage = "home" | "docs";

const props = withDefaults(defineProps<{
  activePage: ActivePage;
  githubRepoUrl?: string;
  scrollSections?: boolean;
}>(), {
  githubRepoUrl: "https://github.com/imi4u36d/JianDou",
  scrollSections: false
});

const emit = defineEmits<{
  sectionRequest: [sectionId: string];
}>();

function emitSection(sectionId: string) {
  emit("sectionRequest", sectionId);
}
</script>

<style scoped>
.marketing-topbar {
  position: sticky;
  top: 18px;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  min-height: 76px;
  padding: 16px 24px;
  overflow: hidden;
  border: 1px solid rgba(157, 138, 201, 0.18);
  border-radius: 30px;
  background: rgba(255, 255, 255, 0.72);
  box-shadow:
    0 18px 60px rgba(104, 83, 134, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.76);
  backdrop-filter: blur(18px);
}

.marketing-brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-family: "Manrope", "Inter", "PingFang SC", sans-serif;
  font-size: 0.96rem;
  font-weight: 800;
  color: #2a2d3a;
}

.marketing-brand__logo {
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
  filter: drop-shadow(0 6px 14px rgba(112, 96, 255, 0.16));
}

.marketing-topbar__nav,
.marketing-topbar__actions {
  display: inline-flex;
  align-items: center;
  gap: 12px;
}

.marketing-topbar__nav {
  gap: 20px;
  font-size: 0.9rem;
  color: #505461;
}

.marketing-topbar__link {
  position: relative;
  display: inline-flex;
  align-items: center;
  min-height: 40px;
  font-weight: 700;
  color: inherit;
  transition:
    color 160ms ease,
    transform 160ms ease;
}

.marketing-topbar__link:hover,
.marketing-topbar__link-active {
  color: #8a57e7;
}

.marketing-topbar__link-active::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  bottom: -12px;
  height: 2px;
  border-radius: 999px;
  background: linear-gradient(90deg, #a65cff, #5fddff);
}

.marketing-topbar__github {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 14px;
  color: #2a2d3a;
  background: rgba(255, 255, 255, 0.86);
  box-shadow:
    0 12px 24px rgba(85, 90, 120, 0.1),
    inset 0 0 0 1px rgba(157, 147, 196, 0.18);
  transition:
    color 160ms ease,
    box-shadow 160ms ease,
    transform 160ms ease;
}

.marketing-topbar__github svg {
  width: 20px;
  height: 20px;
  fill: currentColor;
}

.marketing-topbar__github:hover {
  transform: translateY(-1px);
  color: #8a57e7;
  box-shadow:
    0 14px 28px rgba(110, 89, 255, 0.16),
    inset 0 0 0 1px rgba(138, 87, 231, 0.18);
}

.marketing-topbar__primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 42px;
  padding: 0 20px;
  border-radius: 999px;
  font-size: 0.88rem;
  font-weight: 800;
  color: #fff;
  background: linear-gradient(135deg, #ae69ff, #6e59ff 42%, #59d6ff 100%);
  box-shadow: 0 12px 28px rgba(140, 105, 255, 0.28);
  transition:
    transform 160ms ease,
    box-shadow 160ms ease,
    background 160ms ease;
}

.marketing-topbar__primary:hover {
  transform: translateY(-1px);
}

@media (max-width: 960px) {
  .marketing-topbar {
    top: 10px;
    flex-wrap: wrap;
    justify-content: center;
    padding: 18px;
  }
}

@media (max-width: 640px) {
  .marketing-topbar__nav,
  .marketing-topbar__actions {
    width: 100%;
    flex-wrap: wrap;
    justify-content: center;
  }

  .marketing-topbar__primary {
    width: auto;
    flex: 1 1 auto;
  }

  .marketing-topbar__github {
    flex: 0 0 42px;
  }
}
</style>
