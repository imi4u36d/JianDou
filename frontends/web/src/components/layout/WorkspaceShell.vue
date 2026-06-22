<template>
  <div class="workspace-shell">
    <aside
      class="workspace-sidebar"
    >
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

        <div class="sidebar-user-card">
          <div class="sidebar-user-card__header">
            <div class="sidebar-user-card__avatar">{{ avatarInitials }}</div>
            <div>
              <p class="sidebar-user-card__name">{{ accountTitle }}</p>
              <p class="sidebar-user-card__meta">{{ accountMeta }}</p>
            </div>
          </div>
          <div class="sidebar-user-card__actions">
            <a
              v-if="isAdmin"
              class="sidebar-user-card__link"
              :href="adminPortalUrl"
            >
              管理
            </a>
            <button
              v-if="currentUser"
              class="sidebar-user-card__link sidebar-user-card__link--btn"
              type="button"
              @click="keyDialogOpen = true"
            >
              Key
            </button>
            <button v-if="currentUser" class="sidebar-user-card__logout" type="button" @click="handleLogout">
              退出
            </button>
            <RouterLink v-else class="sidebar-user-card__link" to="/login">
              登录
            </RouterLink>
          </div>
        </div>
      </section>
    </aside>

    <div class="workspace-main">
    <header class="workspace-topbar">
      <h2>{{ currentTitle }}</h2>
      <div class="workspace-topbar__right">
        <span v-if="currentUser" class="workspace-topbar__user">{{ currentUser.displayName || currentUser.username }}</span>
        <span class="workspace-topbar__credits" :title="creditTitle">{{ creditValue }}</span>
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
.workspace-shell{position:relative;display:flex;height:100vh;min-height:100vh;background:var(--bg-base);color:var(--text-primary);overflow:hidden}
.workspace-sidebar{width:72px;flex:0 0 72px;display:flex;flex-direction:column;align-items:center;padding:16px 0 20px;background:var(--bg-surface);border-right:1px solid var(--border-subtle);z-index:30;gap:4px}
.workspace-sidebar__top{display:grid;gap:24px;justify-items:center}
.workspace-sidebar__topbar{display:grid;place-items:center}
.sidebar-brand{width:40px;height:40px;border-radius:var(--radius-md);background:linear-gradient(135deg,var(--accent-indigo),var(--accent-blue));display:grid;place-items:center;box-shadow:0 4px 12px rgba(79,70,229,0.25);transition:transform 120ms ease}
.sidebar-brand:hover{transform:translateY(-1px)}
.sidebar-brand__logo{width:22px;height:22px;object-fit:contain;filter:brightness(0) invert(1)}
.sidebar-nav{display:grid;gap:4px;justify-items:center}
.sidebar-nav__item{display:flex;flex-direction:column;align-items:center;gap:4px;width:44px;min-height:50px;padding:8px 0;border-radius:var(--radius-md);color:var(--text-muted);transition:all 120ms ease;position:relative}
.sidebar-nav__item:hover{color:var(--text-primary);background:var(--bg-muted)}
.sidebar-nav__item-active{color:var(--accent-indigo);background:var(--bg-accent-soft)}
.sidebar-nav__item-active::before{content:"";position:absolute;left:-14px;top:50%;transform:translateY(-50%);width:3px;height:20px;border-radius:0 3px 3px 0;background:var(--accent-indigo)}
.sidebar-nav__icon{display:inline-flex;align-items:center;justify-content:center;width:20px;height:20px;color:currentColor}
.sidebar-nav__icon :deep(svg){width:100%;height:100%}
.sidebar-nav__label{font-size:10px;font-weight:600;color:currentColor;text-align:center;line-height:1}
.sidebar-account-zone{display:grid;justify-items:center;gap:12px}
.sidebar-credit-card{display:grid;place-items:center;width:44px;min-height:44px;padding:4px 2px;border-radius:var(--radius-full);background:var(--bg-accent-soft);color:var(--accent-indigo);text-align:center}
.sidebar-credit-card__label{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)}
.sidebar-credit-card strong{display:block;max-width:38px;overflow:hidden;font-size:12px;font-weight:800;line-height:1.1;text-overflow:ellipsis;white-space:nowrap}
.sidebar-account{position:relative}
.sidebar-account__trigger{display:grid;place-items:center;width:40px;height:40px;border:0;border-radius:50%;background:transparent;color:var(--text-primary);cursor:pointer;transition:background 120ms ease}
.sidebar-account__trigger:hover{background:var(--bg-muted)}
.sidebar-account__avatar{display:grid;place-items:center;width:34px;height:34px;border-radius:50%;background:linear-gradient(135deg,var(--accent-indigo),var(--accent-blue));color:#fff;font-weight:800;font-size:11px}
.sidebar-account__status{position:absolute;right:5px;bottom:5px;width:9px;height:9px;border:2px solid var(--bg-surface);border-radius:50%;background:var(--accent-emerald)}
.sidebar-user-popover{position:absolute;left:52px;bottom:0;z-index:50;display:grid;gap:12px;width:240px;padding:14px;border:1px solid var(--border-subtle);border-radius:var(--radius-lg);background:var(--bg-surface);box-shadow:var(--shadow-xl)}
.sidebar-user-popover__header{display:flex;align-items:center;gap:12px;min-width:0}
.sidebar-user-popover__avatar{display:grid;place-items:center;width:38px;height:38px;flex:0 0 38px;border-radius:50%;background:linear-gradient(135deg,var(--accent-indigo),var(--accent-blue));color:#fff;font-weight:800;font-size:12px}
.sidebar-user-popover__name{margin:0;color:var(--text-primary);font-size:14px;font-weight:700;max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sidebar-user-popover__meta{margin:4px 0 0;color:var(--text-muted);font-size:11px;max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sidebar-user-popover__actions{display:flex;gap:8px}
.sidebar-user-popover__link,.sidebar-user-popover__logout{flex:1;min-height:34px;display:inline-flex;align-items:center;justify-content:center;padding:0 12px;border-radius:var(--radius-md);border:0;background:var(--bg-muted);color:var(--text-primary);font-size:12px;font-weight:700;cursor:pointer;text-decoration:none}
.sidebar-user-popover__logout{background:rgba(244,63,94,0.06);color:var(--accent-rose)}
.sidebar-user-card{display:none}
.workspace-main{position:relative;z-index:1;flex:1;min-width:0;min-height:0;display:flex;flex-direction:column;overflow:hidden}
.workspace-topbar{display:flex;align-items:center;justify-content:space-between;gap:14px;min-height:52px;padding:0 24px;border-bottom:1px solid var(--border-subtle);background:var(--bg-surface);flex-shrink:0}
.workspace-topbar h2{margin:0;color:var(--text-primary);font-size:15px;font-weight:700}
.workspace-topbar__right{display:flex;align-items:center;gap:12px;color:var(--text-muted);font-size:12px}
.workspace-topbar__user{color:var(--text-primary);font-weight:600}
.workspace-topbar__credits{min-width:56px;padding:2px 12px;border-radius:var(--radius-full);background:var(--bg-accent-soft);color:var(--accent-indigo);font-weight:700;text-align:center;font-size:12px}
.workspace-content{padding:24px 28px;flex:1;min-width:0;min-height:0;overflow:auto;background:var(--bg-base)}
</style>
