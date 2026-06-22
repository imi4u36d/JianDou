<template>
  <div class="workspace-shell">
    <aside class="workspace-sidebar">
      <div class="sidebar-brand">
        <img alt="煎豆 Logo" src="/brand/jiandou-mark.svg" />
      </div>

      <nav class="sidebar-nav">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          class="sidebar-nav__item"
          :class="{ 'sidebar-nav__item-active': isActive(item.to) }"
          :to="item.to"
        >
          <span class="sidebar-nav__icon"><component :is="iconComponentMap[item.icon]" /></span>
          <span class="sidebar-nav__label">{{ item.label }}</span>
        </RouterLink>
      </nav>

      <div class="sidebar-bottom">
        <div class="sidebar-credits" :title="creditTitle">
          <span class="sidebar-credits__label">积分</span>
          <span class="sidebar-credits__value">{{ creditValue }}</span>
        </div>
        <div ref="accountMenuRef" class="sidebar-account" @keydown.escape="closeUserMenu">
          <button
            class="sidebar-account__trigger"
            type="button"
            aria-label="用户信息"
            :aria-expanded="userMenuOpen"
            @click.stop="toggleUserMenu"
          >
            <span class="sidebar-account__avatar">{{ avatarInitials }}</span>
            <span v-if="currentUser" class="sidebar-account__status" aria-hidden="true"></span>
          </button>

          <div v-if="userMenuOpen" class="sidebar-user-popover" @click.stop>
            <div class="sidebar-user-popover__header">
              <div class="sidebar-user-popover__avatar">{{ avatarInitials }}</div>
              <div>
                <p class="sidebar-user-popover__name">{{ accountTitle }}</p>
                <p class="sidebar-user-popover__meta">{{ accountMeta }}</p>
              </div>
            </div>
            <div class="sidebar-user-popover__actions">
              <a v-if="isAdmin" class="sidebar-user-popover__link" :href="adminPortalUrl">管理</a>
              <button v-if="currentUser" class="sidebar-user-popover__link" type="button" @click="keyDialogOpen = true; closeUserMenu()">Key</button>
              <button v-if="currentUser" class="sidebar-user-popover__logout" type="button" @click="handleLogout">退出</button>
              <RouterLink v-else class="sidebar-user-popover__link" to="/login" @click="closeUserMenu">登录</RouterLink>
            </div>
          </div>
        </div>
      </div>
    </aside>

    <div class="workspace-main">
      <header class="workspace-topbar">
        <h2 class="workspace-topbar__title">{{ currentTitle }}</h2>
        <div class="workspace-topbar__right">
          <span v-if="currentUser" class="workspace-topbar__user">{{ currentUser.displayName || currentUser.username }}</span>
        </div>
      </header>

      <main class="workspace-content">
        <RouterView />
      </main>
    </div>
    <KeyManagementDialog v-model="keyDialogOpen" />
  </div>
</template>

<script setup lang="ts">
/**
 * 工作区组件。
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { fetchCreditSummary } from "@/api/credits";
import { getRuntimeConfig } from "@/api/runtime-config";
import { logoutAndClearSession, useAuthSessionState } from "@/auth/session";
import type { CreditSummary } from "@/types";
import { IconClose, iconComponentMap } from "@/components/icons";
import type { IconName } from "@/components/icons";
import KeyManagementDialog from "@/components/KeyManagementDialog.vue";

const route = useRoute();
const router = useRouter();
const authState = useAuthSessionState();
const adminPortalUrl = getRuntimeConfig().adminBaseUrl;

const navItems: { to: string; label: string; icon: IconName }[] = [
  { to: "/workspace", label: "工作", icon: "home" },
  { to: "/workflows", label: "阶段", icon: "workflow" },
  { to: "/tasks", label: "任务", icon: "task" },
  { to: "/materials", label: "素材", icon: "material" },
];

const sidebarOpen = ref(false);
const userMenuOpen = ref(false);
const keyDialogOpen = ref(false);
const accountMenuRef = ref<HTMLElement | null>(null);
const credits = ref<CreditSummary | null>(null);
const creditsLoading = ref(false);

const currentUser = computed(() => authState.user.value);
const isAdmin = computed(() => authState.isAdmin.value);
const avatarInitials = computed(() => {
  const source = currentUser.value?.displayName || currentUser.value?.username || "JD";
  return source.slice(0, 2).toUpperCase();
});
const roleLabel = computed(() => {
  if (currentUser.value?.role === "ADMIN") {
    return "管理员";
  }
  if (currentUser.value?.role === "USER") {
    return "普通用户";
  }
  return "未登录";
});
const accountTitle = computed(() => currentUser.value?.displayName || currentUser.value?.username || "未登录");
const accountMeta = computed(() => {
  if (!currentUser.value) {
    return "未登录";
  }
  return roleLabel.value;
});
const creditValue = computed(() => {
  if (!currentUser.value) {
    return "--";
  }
  if (creditsLoading.value && !credits.value) {
    return "--";
  }
  if (!credits.value) {
    return "--";
  }
  if (credits.value.exempt) {
    return "免扣";
  }
  return formatCreditBalance(credits.value.balance ?? 0);
});
const creditTitle = computed(() => {
  if (!currentUser.value) {
    return "登录后查看积分余额";
  }
  if (credits.value?.exempt) {
    return "当前账号积分免扣";
  }
  return `剩余积分：${creditValue.value}`;
});
function isActive(target: string) {
  return route.path === target || route.path.startsWith(`${target}/`);
}

const currentTitle = computed(() => {
  const metaTitle = route.meta?.title;
  const title = typeof metaTitle === "string" && metaTitle.trim() ? metaTitle : "煎豆工作台";
  return title.replace(/\s*·\s*煎豆$/, "").replace(/管理$/, "");
});

function toggleUserMenu() {
  userMenuOpen.value = !userMenuOpen.value;
}

function closeUserMenu() {
  userMenuOpen.value = false;
}

function formatCreditBalance(value: number) {
  return Number.isInteger(value) ? String(value) : value.toFixed(2).replace(/\.?0+$/, "");
}

async function loadCredits() {
  if (!authState.isAuthenticated.value) {
    credits.value = null;
    return;
  }
  creditsLoading.value = true;
  try {
    credits.value = await fetchCreditSummary();
  } catch {
    credits.value = null;
  } finally {
    creditsLoading.value = false;
  }
}

function handleDocumentPointerDown(event: PointerEvent) {
  if (!userMenuOpen.value) {
    return;
  }
  const target = event.target;
  if (!(target instanceof Node) || accountMenuRef.value?.contains(target)) {
    return;
  }
  closeUserMenu();
}

async function handleLogout() {
  closeUserMenu();
  await logoutAndClearSession();
  await router.replace("/login");
}

onMounted(() => {
  void loadCredits();
  document.addEventListener("pointerdown", handleDocumentPointerDown);
});

onBeforeUnmount(() => {
  document.removeEventListener("pointerdown", handleDocumentPointerDown);
});

watch(
  () => route.fullPath,
  () => {
    sidebarOpen.value = false;
    userMenuOpen.value = false;
    void loadCredits();
  },
);

watch(
  () => authState.isAuthenticated.value,
  () => {
    void loadCredits();
  },
);
</script>


<style scoped>
.workspace-shell {
  display: flex;
  height: 100vh;
  min-height: 100vh;
  background: var(--bg-base);
  overflow: hidden;
}

.workspace-sidebar {
  width: 72px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 0 20px;
  background: var(--bg-surface);
  border-right: 1px solid var(--border-subtle);
  z-index: 20;
  gap: 4px;
}

.sidebar-brand {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--accent-indigo), var(--accent-blue));
  display: grid;
  place-items: center;
  margin-bottom: 24px;
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.25);
}

.sidebar-brand img {
  width: 22px;
  height: 22px;
  filter: brightness(0) invert(1);
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
  padding: 0 12px;
}

.sidebar-nav__item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 10px 0;
  border-radius: 10px;
  color: var(--text-muted);
  transition: all 120ms ease;
  position: relative;
  text-decoration: none;
}

.sidebar-nav__item:hover {
  color: var(--text-primary);
  background: var(--bg-muted);
}

.sidebar-nav__item-active {
  color: var(--accent-indigo);
  background: var(--bg-accent-soft);
}

.sidebar-nav__item-active::before {
  content: "";
  position: absolute;
  left: -12px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 20px;
  border-radius: 0 3px 3px 0;
  background: var(--accent-indigo);
}

.sidebar-nav__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
}

.sidebar-nav__icon :deep(svg) {
  width: 100%;
  height: 100%;
}

.sidebar-nav__label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.02em;
  max-width: 42px;
  overflow: visible;
  white-space: normal;
  text-align: center;
  line-height: 1;
}

.sidebar-bottom {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 0 12px;
}

.sidebar-credits {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 8px 0;
}

.sidebar-credits__label {
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
}

.sidebar-credits__value {
  font-size: 13px;
  font-weight: 800;
  color: var(--accent-emerald);
}

.sidebar-account {
  position: relative;
}

.sidebar-account__trigger {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--accent-rose), var(--accent-violet));
  color: #fff;
  font-size: 11px;
  font-weight: 800;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  position: relative;
}

.sidebar-account__trigger:hover {
  box-shadow: var(--shadow-md);
}

.sidebar-account__status {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--accent-emerald);
  border: 2px solid var(--bg-surface);
}

.sidebar-user-popover {
  position: absolute;
  left: 48px;
  bottom: 0;
  z-index: 50;
  display: grid;
  gap: 12px;
  width: 240px;
  padding: 14px;
  border: 1px solid var(--border-subtle);
  border-radius: 16px;
  background: var(--bg-surface);
  box-shadow: var(--shadow-xl);
}

.sidebar-user-popover__header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.sidebar-user-popover__avatar {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--accent-rose), var(--accent-violet));
  color: #fff;
  font-size: 11px;
  font-weight: 800;
  flex-shrink: 0;
}

.sidebar-user-popover__name {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-user-popover__meta {
  margin: 2px 0 0;
  font-size: 11px;
  color: var(--text-muted);
}

.sidebar-user-popover__actions {
  display: flex;
  gap: 6px;
}

.sidebar-user-popover__link,
.sidebar-user-popover__logout {
  flex: 1;
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 10px;
  border-radius: 8px;
  border: 0;
  background: var(--bg-muted);
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  text-decoration: none;
}

.sidebar-user-popover__logout {
  background: rgba(244, 63, 94, 0.08);
  color: var(--accent-rose);
}

.sidebar-user-popover__link:hover {
  background: var(--bg-accent-soft);
  color: var(--accent-indigo);
}

.workspace-main {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.workspace-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  min-height: 56px;
  padding: 0 28px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-surface);
  flex-shrink: 0;
}

.workspace-topbar__title {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.workspace-topbar__right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.workspace-topbar__user {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.workspace-content {
  flex: 1;
  min-width: 0;
  min-height: 0;
  padding: 24px 28px;
  overflow: auto;
}
</style>
