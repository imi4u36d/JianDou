<template>
  <div class="app-shell">
    <aside class="app-sidebar" :class="{ 'app-sidebar-open': sidebarOpen }">
      <div class="app-sidebar__header">
        <RouterLink class="brand-mark" to="/">
          <span class="brand-mark__icon">A</span>
          <span>
            <strong>AI Cut</strong>
            <small>Text to Video</small>
          </span>
        </RouterLink>
        <button class="shell-icon-btn lg:hidden" type="button" @click="sidebarOpen = false">
          关闭
        </button>
      </div>

      <nav class="app-sidebar__nav">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          class="nav-link"
          :class="{ 'nav-link-active': isActive(item.to) }"
          :to="item.to"
        >
          <span class="nav-link__label">{{ item.label }}</span>
          <small>{{ item.desc }}</small>
        </RouterLink>
      </nav>

      <section class="sidebar-panel sidebar-panel-compact">
        <div class="sidebar-panel__head">
          <div>
            <p class="eyebrow">Developer</p>
            <h3>开发者模式</h3>
          </div>
        </div>
        <label class="developer-toggle">
          <div>
            <strong>启用开发者模式</strong>
            <small>显示调试型流水线控制，默认不会影响普通生成。</small>
          </div>
          <input v-model="developerSettings.enabled" class="developer-toggle__input" type="checkbox" />
        </label>
        <label v-if="developerSettings.enabled" class="developer-option">
          <input v-model="developerSettings.stopBeforeVideoGeneration" type="checkbox" />
          <div>
            <strong>在关键帧前停止</strong>
            <small>AI 剧会完成文本分析与编排准备，但不会开始关键帧与视频生成。</small>
          </div>
        </label>
        <p class="sidebar-note">
          {{ developerNote }}
        </p>
      </section>
    </aside>

    <div v-if="sidebarOpen" class="app-sidebar-mask" @click="sidebarOpen = false"></div>

    <div class="app-shell__main">
      <header class="mobile-bar">
        <button class="shell-icon-btn" type="button" @click="sidebarOpen = true">
          菜单
        </button>
        <RouterLink class="mobile-bar__brand" to="/">AI Cut</RouterLink>
        <span class="shell-icon-btn shell-icon-btn-placeholder" aria-hidden="true">占位</span>
      </header>

      <main class="app-shell__content">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { loadDeveloperSettings, saveDeveloperSettings } from "@/workbench/developer-settings";

const route = useRoute();

const navItems = [
  { to: "/", label: "官网首页", desc: "能力展示与案例" },
  { to: "/generate", label: "TXT 小说生成", desc: "上传或粘贴小说正文生成视频" },
  { to: "/tasks", label: "任务管理", desc: "查询任务状态与结果" },
];

const sidebarOpen = ref(false);
const developerSettings = reactive(loadDeveloperSettings());

function isActive(target: string) {
  return target === "/" ? route.path === "/" : route.path.startsWith(target);
}

const developerNote = computed(() => {
  if (!developerSettings.enabled) {
    return "关闭时页面保持默认的一键生成体验。";
  }
  if (developerSettings.stopBeforeVideoGeneration) {
    return "当前会在关键帧文生图之前停止，方便先检查分析和编排结果。";
  }
  return "开发者模式已开启，但不会提前停止任务。";
});

watch(
  () => route.fullPath,
  () => {
    sidebarOpen.value = false;
  }
);

watch(
  developerSettings,
  (value) => {
    saveDeveloperSettings({ ...value });
  },
  { deep: true }
);
</script>

<style scoped>
.sidebar-panel-compact {
  flex: 0 0 auto;
}

.developer-toggle,
.developer-option {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.85rem;
  border: 1px solid rgba(125, 151, 187, 0.16);
  border-radius: 1rem;
  background: rgba(255, 255, 255, 0.66);
  padding: 0.9rem;
}

.developer-toggle strong,
.developer-option strong {
  display: block;
  color: #18324d;
  font-size: 0.88rem;
}

.developer-toggle small,
.developer-option small {
  display: block;
  margin-top: 0.22rem;
  color: #6b7f94;
  line-height: 1.5;
}

.developer-toggle__input,
.developer-option input {
  margin-top: 0.2rem;
  width: 1rem;
  height: 1rem;
  accent-color: #1d4ed8;
}
</style>
