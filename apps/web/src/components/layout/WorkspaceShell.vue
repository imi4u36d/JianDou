<template>
  <div class="workspace-shell">
    <div class="workspace-shell__aurora workspace-shell__aurora-left" aria-hidden="true"></div>
    <div class="workspace-shell__aurora workspace-shell__aurora-right" aria-hidden="true"></div>

    <aside class="workspace-sidebar" :class="{ 'workspace-sidebar-open': sidebarOpen }">
      <div class="workspace-sidebar__top">
        <div class="sidebar-avatar">
          <span>{{ avatarInitials }}</span>
        </div>

        <nav class="sidebar-nav">
          <RouterLink
            v-for="item in navItems"
            :key="item.to"
            class="sidebar-nav__item"
            :class="{ 'sidebar-nav__item-active': isActive(item.to) }"
            :to="item.to"
          >
            <span class="sidebar-nav__icon" v-html="item.icon"></span>
            <span>{{ item.label }}</span>
          </RouterLink>
        </nav>
      </div>

      <section class="sidebar-dev">
        <div class="sidebar-dev__line"></div>
        <label class="sidebar-dev__toggle">
          <span>开发者模式</span>
          <input v-model="developerSettings.enabled" type="checkbox" />
          <span class="sidebar-dev__switch" :class="{ 'sidebar-dev__switch-on': developerSettings.enabled }"></span>
        </label>
        <label v-if="developerSettings.enabled" class="sidebar-dev__option">
          <input v-model="developerSettings.stopBeforeVideoGeneration" type="checkbox" />
          <div>
            <strong>视频生成前停止</strong>
            <small>{{ developerNote }}</small>
          </div>
        </label>

        <div class="sidebar-user-card">
          <div class="sidebar-user-card__header">
            <div class="sidebar-user-card__avatar">{{ avatarInitials }}</div>
            <div>
              <p class="sidebar-user-card__name">{{ currentUser?.displayName || "未登录" }}</p>
              <p class="sidebar-user-card__meta">{{ currentUser?.username || "-" }} · {{ currentUser?.role || "-" }}</p>
            </div>
          </div>
          <div class="sidebar-user-card__actions">
            <RouterLink
              v-if="isAdmin"
              class="sidebar-user-card__link"
              to="/admin/tasks"
            >
              管理端
            </RouterLink>
            <button class="sidebar-user-card__logout" type="button" @click="handleLogout">
              退出登录
            </button>
          </div>
        </div>
      </section>
    </aside>

    <div v-if="sidebarOpen" class="workspace-sidebar-mask" @click="sidebarOpen = false"></div>

    <div class="workspace-main">
      <header class="workspace-mobile-bar">
        <button class="shell-ghost-btn" type="button" @click="sidebarOpen = true">菜单</button>
        <p class="workspace-mobile-bar__title">{{ currentTitle }}</p>
        <span class="workspace-mobile-bar__placeholder"></span>
      </header>

      <header class="workspace-header">
        <h1 class="workspace-header__title">{{ currentTitle }}</h1>
        <div class="workspace-header__actions">
          <div class="workspace-header__user">
            <span class="workspace-header__user-name">{{ currentUser?.displayName || currentUser?.username }}</span>
            <span class="workspace-header__user-role">{{ currentUser?.role }}</span>
          </div>
          <div class="workspace-brand">
            <div class="workspace-brand__mark">
              <span class="workspace-brand__mark-j">j</span>
              <span class="workspace-brand__mark-d">d</span>
            </div>
            <span>煎豆工作台</span>
          </div>
        </div>
      </header>

      <main class="workspace-content">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 工作区组件。
 */
import { computed, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { logoutAndClearSession, useAuthSessionState } from "@/auth/session";
import { loadDeveloperSettings, saveDeveloperSettings } from "@/workbench/developer-settings";

const route = useRoute();
const router = useRouter();
const authState = useAuthSessionState();

const navItems = [
  {
    to: "/workspace",
    label: "工作台",
    icon: `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M3 11.5 12 4l9 7.5" />
        <path d="M5.5 10.5V20h13V10.5" />
      </svg>
    `,
  },
  {
    to: "/generate",
    label: "文本生成",
    icon: `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M7 3.5h7l4 4V20a1.5 1.5 0 0 1-1.5 1.5h-9A1.5 1.5 0 0 1 6 20V5A1.5 1.5 0 0 1 7.5 3.5Z" />
        <path d="M14 3.5V8h4" />
        <path d="M9 12h6" />
        <path d="M9 16h6" />
      </svg>
    `,
  },
  {
    to: "/tasks",
    label: "任务管理",
    icon: `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <rect x="4" y="4" width="6" height="6" rx="1.5" />
        <rect x="14" y="4" width="6" height="6" rx="1.5" />
        <rect x="4" y="14" width="6" height="6" rx="1.5" />
        <rect x="14" y="14" width="6" height="6" rx="1.5" />
      </svg>
    `,
  },
  {
    to: "/settings",
    label: "设置",
    icon: `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <circle cx="12" cy="12" r="3.2" />
        <path d="M19.4 15a1 1 0 0 0 .2 1.1l.1.1a1.2 1.2 0 0 1 0 1.7l-1.2 1.2a1.2 1.2 0 0 1-1.7 0l-.1-.1a1 1 0 0 0-1.1-.2 1 1 0 0 0-.6.9V20a1.2 1.2 0 0 1-1.2 1.2h-1.7A1.2 1.2 0 0 1 11 20v-.2a1 1 0 0 0-.6-.9 1 1 0 0 0-1.1.2l-.1.1a1.2 1.2 0 0 1-1.7 0l-1.2-1.2a1.2 1.2 0 0 1 0-1.7l.1-.1a1 1 0 0 0 .2-1.1 1 1 0 0 0-.9-.6H4A1.2 1.2 0 0 1 2.8 13v-2A1.2 1.2 0 0 1 4 9.8h.2a1 1 0 0 0 .9-.6 1 1 0 0 0-.2-1.1L4.8 8A1.2 1.2 0 0 1 4.8 6.3l1.2-1.2a1.2 1.2 0 0 1 1.7 0l.1.1a1 1 0 0 0 1.1.2 1 1 0 0 0 .6-.9V4A1.2 1.2 0 0 1 10.7 2.8h1.7A1.2 1.2 0 0 1 13.6 4v.2a1 1 0 0 0 .6.9 1 1 0 0 0 1.1-.2l.1-.1a1.2 1.2 0 0 1 1.7 0l1.2 1.2a1.2 1.2 0 0 1 0 1.7l-.1.1a1 1 0 0 0-.2 1.1 1 1 0 0 0 .9.6h.2A1.2 1.2 0 0 1 21.2 11v2a1.2 1.2 0 0 1-1.2 1.2h-.2a1 1 0 0 0-.9.8Z" />
      </svg>
    `,
  },
];

const sidebarOpen = ref(false);
const developerSettings = reactive(loadDeveloperSettings());

const currentUser = computed(() => authState.user.value);
const isAdmin = computed(() => authState.isAdmin.value);
const avatarInitials = computed(() => {
  const source = currentUser.value?.displayName || currentUser.value?.username || "JD";
  return source.slice(0, 2).toUpperCase();
});

function isActive(target: string) {
  return route.path === target || route.path.startsWith(`${target}/`);
}

const currentTitle = computed(() => {
  const metaTitle = route.meta?.title;
  return typeof metaTitle === "string" && metaTitle.trim() ? metaTitle : "煎豆工作台";
});

const developerNote = computed(() => {
  if (developerSettings.stopBeforeVideoGeneration) {
    return "任务会创建并完成分析与编排，但不会进入图片和视频生成。";
  }
  return "保持完整生成链路启用。";
});

async function handleLogout() {
  await logoutAndClearSession();
  await router.replace("/login");
}

watch(
  () => route.fullPath,
  () => {
    sidebarOpen.value = false;
  },
);

watch(
  developerSettings,
  (value) => {
    saveDeveloperSettings({ ...value });
  },
  { deep: true },
);
</script>

<style scoped>
.workspace-shell {
  position: relative;
  display: flex;
  height: 100vh;
  min-height: 100vh;
  background:
    radial-gradient(circle at top left, rgba(78, 208, 255, 0.12), transparent 24%),
    radial-gradient(circle at bottom left, rgba(164, 83, 255, 0.18), transparent 28%),
    radial-gradient(circle at 84% 84%, rgba(72, 198, 255, 0.12), transparent 24%),
    #06070b;
  color: var(--text-strong);
  overflow: hidden;
}

.workspace-shell__aurora {
  position: absolute;
  border-radius: 999px;
  filter: blur(84px);
  opacity: 0.45;
  pointer-events: none;
}

.workspace-shell__aurora-left {
  left: -140px;
  top: -60px;
  width: 320px;
  height: 320px;
  background: rgba(78, 208, 255, 0.2);
}

.workspace-shell__aurora-right {
  right: -120px;
  bottom: 60px;
  width: 300px;
  height: 300px;
  background: rgba(164, 83, 255, 0.18);
}

.workspace-sidebar {
  position: relative;
  z-index: 2;
  height: 100%;
  width: 264px;
  flex: 0 0 264px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 22px 18px 26px;
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  background: linear-gradient(180deg, rgba(9, 11, 17, 0.92), rgba(5, 7, 11, 0.84));
  backdrop-filter: blur(24px);
}

.workspace-sidebar__top {
  display: grid;
  gap: 28px;
}

.sidebar-avatar {
  width: 42px;
  height: 42px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  background:
    linear-gradient(135deg, rgba(132, 82, 255, 0.9), rgba(76, 219, 255, 0.88));
  box-shadow:
    0 0 0 2px rgba(255, 255, 255, 0.06),
    0 16px 34px rgba(97, 104, 255, 0.24);
}

.sidebar-avatar span {
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: #fff;
}

.sidebar-nav {
  display: grid;
  gap: 10px;
}

.sidebar-nav__item {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 52px;
  padding: 0 14px;
  border-radius: 14px;
  color: var(--text-muted);
  border: 1px solid transparent;
  transition:
    color 180ms ease,
    border-color 180ms ease,
    background 180ms ease,
    box-shadow 180ms ease,
    transform 180ms ease;
}

.sidebar-nav__item:hover {
  transform: translateY(-1px);
  color: rgba(255, 255, 255, 0.92);
}

.sidebar-nav__item-active {
  color: #fff;
  border-color: rgba(255, 255, 255, 0.08);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.04));
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.06),
    0 10px 24px rgba(0, 0, 0, 0.28);
}

.sidebar-nav__icon {
  display: inline-flex;
  width: 20px;
  height: 20px;
  color: currentColor;
}

.sidebar-nav__icon :deep(svg) {
  width: 20px;
  height: 20px;
}

.sidebar-dev {
  display: grid;
  gap: 16px;
}

.sidebar-dev__line {
  height: 1px;
  background: linear-gradient(90deg, rgba(255, 255, 255, 0.16), rgba(255, 255, 255, 0));
}

.sidebar-dev__toggle {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  color: rgba(255, 255, 255, 0.72);
  font-size: 0.82rem;
}

.sidebar-dev__toggle input,
.sidebar-dev__option input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.sidebar-dev__switch {
  position: relative;
  width: 42px;
  height: 24px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.18);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08);
  transition: background 180ms ease;
}

.sidebar-dev__switch::after {
  content: "";
  position: absolute;
  top: 3px;
  left: 3px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.9);
  transition: transform 180ms ease;
}

.sidebar-dev__switch-on {
  background: linear-gradient(90deg, rgba(164, 83, 255, 0.9), rgba(69, 215, 255, 0.9));
}

.sidebar-dev__switch-on::after {
  transform: translateX(18px);
}

.sidebar-dev__option {
  display: grid;
  gap: 4px;
  padding: 14px 14px 14px 18px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.04);
}

.sidebar-dev__option strong {
  font-size: 0.82rem;
  color: rgba(255, 255, 255, 0.88);
}

.sidebar-dev__option small {
  color: rgba(255, 255, 255, 0.58);
  line-height: 1.55;
}

.sidebar-user-card {
  display: grid;
  gap: 14px;
  padding: 16px;
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.04);
}

.sidebar-user-card__header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.sidebar-user-card__avatar {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(255, 169, 77, 0.9), rgba(71, 193, 255, 0.88));
  color: #06111a;
  font-size: 0.76rem;
  font-weight: 800;
}

.sidebar-user-card__name {
  margin: 0;
  color: #fff;
  font-size: 0.9rem;
  font-weight: 700;
}

.sidebar-user-card__meta {
  margin: 4px 0 0;
  color: rgba(255, 255, 255, 0.56);
  font-size: 0.76rem;
}

.sidebar-user-card__actions {
  display: flex;
  gap: 10px;
}

.sidebar-user-card__link,
.sidebar-user-card__logout {
  flex: 1;
  min-height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.84);
  font-size: 0.8rem;
  font-weight: 700;
}

.sidebar-user-card__logout {
  cursor: pointer;
}

.workspace-main {
  position: relative;
  z-index: 1;
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.workspace-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  min-height: 68px;
  padding: 0 28px 0 46px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.workspace-header__title {
  margin: 0;
  font-size: clamp(1.3rem, 1.6vw, 1.9rem);
  font-weight: 700;
  letter-spacing: -0.04em;
  color: #f5f7fb;
}

.workspace-header__actions {
  display: flex;
  align-items: center;
  gap: 14px;
}

.workspace-header__user {
  display: grid;
  justify-items: end;
  gap: 2px;
}

.workspace-header__user-name {
  color: rgba(255, 255, 255, 0.9);
  font-size: 0.84rem;
  font-weight: 700;
}

.workspace-header__user-role {
  color: rgba(255, 255, 255, 0.5);
  font-size: 0.74rem;
}

.workspace-brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: rgba(255, 255, 255, 0.92);
  font-size: 0.86rem;
  font-weight: 500;
}

.workspace-brand__mark {
  display: inline-flex;
  align-items: flex-end;
  gap: 1px;
  font-size: 1.2rem;
  font-weight: 800;
  line-height: 1;
}

.workspace-brand__mark-j {
  color: #a55bff;
}

.workspace-brand__mark-d {
  color: #55d9ff;
}

.workspace-content {
  flex: 1;
  min-width: 0;
  min-height: 0;
  padding: 22px 28px 28px 46px;
  overflow: hidden;
}

.workspace-mobile-bar {
  display: none;
}

.workspace-sidebar-mask {
  position: fixed;
  inset: 0;
  z-index: 20;
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(6px);
}

.shell-ghost-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 36px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.84);
}

.workspace-mobile-bar__title {
  margin: 0;
  color: rgba(255, 255, 255, 0.92);
  font-size: 0.92rem;
  font-weight: 700;
}

.workspace-mobile-bar__placeholder {
  width: 56px;
}

@media (max-width: 1024px) {
  .workspace-sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    transform: translateX(-100%);
    transition: transform 180ms ease;
  }

  .workspace-sidebar-open {
    transform: translateX(0);
  }

  .workspace-mobile-bar {
    position: sticky;
    top: 0;
    z-index: 10;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    min-height: 56px;
    padding: 10px 18px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    background: rgba(6, 8, 13, 0.92);
    backdrop-filter: blur(20px);
  }

  .workspace-header {
    display: none;
  }

  .workspace-content {
    padding: 18px;
  }
}
</style>
