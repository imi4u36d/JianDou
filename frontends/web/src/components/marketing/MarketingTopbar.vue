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
        <IconGitHub />
      </a>
      <RouterLink class="marketing-topbar__primary" to="/workspace">立即开始</RouterLink>
    </div>
  </header>
</template>

<script setup lang="ts">
import { IconGitHub } from "@/components/icons";

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
  top: 16px;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  min-height: 64px;
  padding: 10px 12px 10px 18px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  background: rgba(12, 13, 15, 0.76);
  box-shadow: 0 18px 70px rgba(0, 0, 0, 0.28);
  backdrop-filter: blur(20px);
}

.marketing-brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-family: inherit;
  font-size: 0.96rem;
  font-weight: 800;
  color: #fff8e7;
}

.marketing-brand__logo {
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
  filter: drop-shadow(0 8px 18px rgba(242, 211, 122, 0.12));
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
  color: #aaa69b;
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
  color: #fff8e7;
}

.marketing-topbar__link-active::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  bottom: -12px;
  height: 2px;
  border-radius: 2px;
  background: #f2d37a;
}

.marketing-topbar__github {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 8px;
  color: #fff8e7;
  background: rgba(255, 255, 255, 0.06);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08);
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
  color: #f2d37a;
  box-shadow: inset 0 0 0 1px rgba(242, 211, 122, 0.22);
}

.marketing-topbar__primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 42px;
  padding: 0 20px;
  border-radius: 8px;
  font-size: 0.88rem;
  font-weight: 800;
  color: #11120f;
  background: #f2d37a;
  box-shadow: 0 12px 28px rgba(242, 211, 122, 0.12);
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
