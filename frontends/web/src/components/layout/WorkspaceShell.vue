<template>
  <div class="workspace-shell">
    <aside class="workspace-sidebar liquid-glass">
      <div class="workspace-sidebar__top">
        <div class="workspace-sidebar__topbar">
          <div class="sidebar-brand">
            <img alt="煎豆 Logo" class="sidebar-brand__logo" src="/brand/jiandou-mark.svg" />
          </div>
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
      </div>

      <section class="sidebar-account-zone">
        <div class="sidebar-credit-card" :title="creditTitle">
          <span class="sidebar-credit-card__label">积分</span>
          <strong>{{ creditValue }}</strong>
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
              <a
                v-if="isAdmin"
                class="sidebar-user-popover__link"
                :href="adminPortalUrl"
              >
                管理
              </a>
              <button
                v-if="currentUser"
                class="sidebar-user-popover__link sidebar-user-popover__link--btn"
                type="button"
                @click="keyDialogOpen = true; closeUserMenu()"
              >
                Key
              </button>
              <button v-if="currentUser" class="sidebar-user-popover__logout" type="button" @click="handleLogout">
                退出
              </button>
              <RouterLink v-else class="sidebar-user-popover__link" to="/login" @click="closeUserMenu">
                登录
              </RouterLink>
            </div>
          </div>
        </div>
      </section>
    </aside>

    <div class="workspace-main">
      <main class="workspace-content glass">
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
import { iconComponentMap } from "@/components/icons";
import type { IconName } from "@/components/icons";
import KeyManagementDialog from "@/components/KeyManagementDialog.vue";

const route = useRoute();
const router = useRouter();
const authState = useAuthSessionState();
const adminPortalUrl = getRuntimeConfig().adminBaseUrl;

const navItems: { to: string; label: string; icon: IconName }[] = [
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
  position: relative;
  z-index: 1;
  display: flex;
  height: 100vh;
  min-height: 100vh;
  background: transparent;
  color: var(--text-strong);
  overflow: hidden;
}

.workspace-sidebar {
  position: relative;
  z-index: 30;
  height: 100%;
  width: 56px;
  flex: 0 0 56px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 20px 6px 18px;
  border-right: 1px solid rgba(255, 255, 255, 0.6);
  background: transparent;
}

.workspace-sidebar__top {
  display: grid;
  gap: clamp(76px, 14vh, 150px);
  justify-items: center;
}

.workspace-sidebar__topbar {
  display: grid;
  place-items: center;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 15px;
  transition:
    background 180ms ease,
    box-shadow 180ms ease,
    transform 180ms ease;
}

.sidebar-brand:hover {
  background: rgba(255, 255, 255, 0.6);
  box-shadow:
    0 8px 24px rgba(0, 0, 0, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
  transform: translateY(-1px);
}

.sidebar-brand__logo {
  display: block;
  width: 29px;
  height: 29px;
  flex: 0 0 29px;
  object-fit: contain;
}

.sidebar-nav {
  display: grid;
  gap: 14px;
  justify-items: center;
}

.sidebar-nav__item {
  position: relative;
  display: grid;
  justify-items: center;
  align-content: center;
  align-items: center;
  gap: 5px;
  width: 44px;
  min-height: 50px;
  padding: 4px 2px;
  border-radius: 14px;
  color: var(--text-body);
  border: 0;
  background: transparent;
  transition:
    color 180ms ease,
    background 180ms ease,
    box-shadow 180ms ease,
    transform 180ms ease;
}

.sidebar-nav__item:hover {
  transform: translateY(-1px);
  color: var(--accent-blue);
  background: rgba(255, 255, 255, 0.5);
}

.sidebar-nav__item-active {
  color: var(--accent-blue);
  background: rgba(255, 255, 255, 0.7);
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.1);
}

.sidebar-nav__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 25px;
  height: 25px;
  color: currentColor;
  transition: transform 180ms ease;
}

.sidebar-nav__icon :deep(svg) {
  width: 100%;
  height: 100%;
  aspect-ratio: 1 / 1;
}

.sidebar-nav__icon :deep(.icon__fill) {
  fill: currentColor;
  opacity: 0;
  transition: opacity 180ms ease;
}

.sidebar-nav__item-active .sidebar-nav__icon :deep(.icon__fill) {
  opacity: 1;
}

.sidebar-nav__item-active .sidebar-nav__icon :deep(.icon__detail) {
  stroke: #fff;
  fill: #fff;
}

.sidebar-nav__item:hover .sidebar-nav__icon,
.sidebar-nav__item-active .sidebar-nav__icon {
  transform: scale(1.04);
}

.sidebar-nav__label {
  display: inline-block;
  max-width: 42px;
  overflow: visible;
  white-space: normal;
  color: currentColor;
  font-size: 0.74rem;
  font-weight: 500;
  line-height: 1;
  letter-spacing: 0;
  text-align: center;
}

.sidebar-account-zone {
  display: grid;
  justify-items: center;
  gap: 14px;
}

.sidebar-credit-card {
  display: grid;
  place-items: center;
  align-content: center;
  width: 44px;
  min-height: 44px;
  padding: 4px 2px;
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: var(--radius-full);
  background: rgba(255, 255, 255, 0.5);
  color: var(--text-strong);
  text-align: center;
}

.sidebar-credit-card__label {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
}

.sidebar-credit-card strong {
  display: block;
  max-width: 38px;
  overflow: hidden;
  color: var(--accent-blue);
  font-size: 0.76rem;
  font-weight: 850;
  line-height: 1.1;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-account {
  position: relative;
}

.sidebar-account__trigger {
  position: relative;
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--text-strong);
  cursor: pointer;
  transition:
    background 180ms ease,
    transform 180ms ease;
}

.sidebar-account__trigger:hover,
.sidebar-account__trigger[aria-expanded="true"] {
  background: rgba(255, 255, 255, 0.6);
  box-shadow:
    0 8px 24px rgba(0, 0, 0, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
  transform: translateY(-1px);
}

.sidebar-account__avatar,
.sidebar-user-popover__avatar {
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: linear-gradient(135deg, #6366f1 0%, #818cf8 54%, #a78bfa 100%);
  color: #fff;
  font-weight: 800;
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.4),
    0 4px 12px rgba(99, 102, 241, 0.2);
}

.sidebar-account__avatar {
  width: 34px;
  height: 34px;
  font-size: 0.72rem;
}

.sidebar-account__status {
  position: absolute;
  right: 7px;
  bottom: 7px;
  width: 9px;
  height: 9px;
  border: 2px solid rgba(255, 255, 255, 0.9);
  border-radius: 50%;
  background: #16a34a;
}

.sidebar-user-popover {
  position: absolute;
  left: 52px;
  bottom: 0;
  z-index: 50;
  display: grid;
  gap: 14px;
  width: 252px;
  padding: 14px;
  border: 1px solid rgba(255, 255, 255, 0.7);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(40px) saturate(1.8);
  -webkit-backdrop-filter: blur(40px) saturate(1.8);
  box-shadow: 0 18px 46px rgba(0, 0, 0, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.95);
}

.sidebar-user-popover__header {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.sidebar-user-popover__avatar {
  width: 42px;
  height: 42px;
  flex: 0 0 42px;
  font-size: 0.74rem;
}

.sidebar-user-popover__name,
.sidebar-user-popover__meta {
  max-width: 164px;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-user-popover__name {
  color: var(--text-strong);
  font-size: 0.92rem;
  font-weight: 800;
}

.sidebar-user-popover__meta {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 0.76rem;
}

.sidebar-user-popover__actions {
  display: flex;
  gap: 8px;
}

.sidebar-user-popover__link,
.sidebar-user-popover__logout {
  flex: 1;
  min-height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 12px;
  border-radius: 14px;
  border: 0;
  background: rgba(0, 0, 0, 0.04);
  color: var(--text-strong);
  font-size: 0.8rem;
  font-weight: 800;
  cursor: pointer;
  transition: background 160ms ease, transform 160ms ease;
}

.sidebar-user-popover__link:hover,
.sidebar-user-popover__logout:hover {
  background: rgba(0, 0, 0, 0.08);
  transform: translateY(-1px);
}

.sidebar-user-popover__logout {
  background: rgba(229, 72, 101, 0.08);
  color: var(--accent-coral);
}

.sidebar-user-popover__logout:hover {
  background: rgba(229, 72, 101, 0.14);
}

.sidebar-user-popover__link--btn {
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

.workspace-content {
  padding: 0;
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow: auto;
}

</style>
