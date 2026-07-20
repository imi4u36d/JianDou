<template>
  <div class="page-shell admin-layout">
    <aside class="surface-card admin-layout__aside" aria-label="管理端导航">
      <div class="admin-layout__brand">
        <div class="admin-layout__brand-mark">
          <img alt="煎豆 Logo" class="admin-layout__brand-logo" src="/brand/jiandou-mark.svg" />
        </div>
        <div>
          <h1>JianDou</h1>
          <p>管理后台</p>
        </div>
      </div>

      <el-menu :default-active="activeMenu" class="admin-layout__menu" router aria-label="管理功能">
        <el-menu-item index="/admin">
          <el-icon><DataAnalysis /></el-icon>
          <span>概览</span>
        </el-menu-item>
        <el-menu-item index="/admin/tasks">
          <el-icon><Tickets /></el-icon>
          <span>任务</span>
        </el-menu-item>
        <el-menu-item index="/admin/users">
          <el-icon><UserFilled /></el-icon>
          <span>用户</span>
        </el-menu-item>
        <el-menu-item index="/admin/invites">
          <el-icon><Ticket /></el-icon>
          <span>邀请码</span>
        </el-menu-item>
        <el-menu-item index="/admin/credits">
          <el-icon><Coin /></el-icon>
          <span>积分</span>
        </el-menu-item>
        <el-menu-item index="/admin/system">
          <el-icon><Setting /></el-icon>
          <span>系统</span>
        </el-menu-item>
      </el-menu>

      <div class="admin-layout__aside-footer">
        <div class="admin-layout__profile">
          <strong>{{ currentUser?.username }}</strong>
          <span>{{ currentUser?.username }} · {{ currentUser?.role }}</span>
        </div>
        <div class="admin-layout__footer-actions">
          <el-button plain @click="goToWorkspace"> 工作台 </el-button>
          <el-button plain @click="handleLogout"> 退出 </el-button>
        </div>
      </div>
    </aside>

    <section class="admin-layout__main">
      <header class="surface-card admin-layout__header" aria-label="当前页面">
        <div>
          <h2>{{ currentTitle }}</h2>
          <p>运营与系统管理</p>
        </div>
        <div class="admin-layout__header-meta">
          <span>{{ currentUser?.username }}</span>
          <el-tag effect="plain" type="success">{{ currentUser?.role || "ADMIN" }}</el-tag>
        </div>
      </header>

      <main class="admin-layout__content">
        <RouterView />
      </main>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { logoutAndClearSession, useAuthSessionState } from "@/auth/session";

const route = useRoute();
const router = useRouter();
const authState = useAuthSessionState();

const currentUser = computed(() => authState.user.value);
const activeMenu = computed(() => {
  if (route.path === "/admin" || route.path.startsWith("/admin/")) {
    // Highlight the correct menu item based on the sub-path
    for (const prefix of ["/admin/tasks", "/admin/users", "/admin/invites", "/admin/credits", "/admin/system"]) {
      if (route.path.startsWith(prefix)) {
        return prefix;
      }
    }
    return "/admin";
  }
  return route.path;
});
const currentTitle = computed(() => {
  const title = route.meta.title;
  return typeof title === "string" && title.trim() ? title : "管理系统";
});

function goToWorkspace() {
  router.push("/image-tasks");
}

async function handleLogout() {
  await logoutAndClearSession();
  await router.replace("/login");
}
</script>

<style scoped>
.admin-layout {
  position: relative;
  display: grid;
  grid-template-columns: 176px minmax(0, 1fr);
  grid-template-rows: 1fr;
  gap: 0;
  padding: 0;
  height: 100vh;
  overflow: hidden;
  background: var(--jd-bg);
}

.admin-layout__aside {
  align-self: stretch;
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 18px 10px 14px;
  border-radius: 0;
  border-width: 0 1px 0 0;
  box-shadow: none;
  overflow-y: auto;
}

.admin-layout__brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 52px;
  padding: 2px 12px 12px;
  border-bottom: 0;
}

.admin-layout__brand-mark {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: 9px;
  background: transparent;
}

.admin-layout__brand-logo {
  width: 30px;
  height: 30px;
}

.admin-layout__eyebrow {
  margin: 0 0 4px;
  color: var(--jd-text-soft);
  font-size: 0.78rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.admin-layout__brand h1,
.admin-layout__header h2 {
  margin: 0;
  font-family: inherit;
}

.admin-layout__brand h1 {
  font-size: 0.96rem;
  font-weight: 760;
  line-height: 1.15;
}

.admin-layout__brand p,
.admin-layout__header p {
  margin: 3px 0 0;
  color: var(--jd-text-soft);
  font-size: 0.76rem;
  line-height: 1.3;
}

.admin-layout__menu {
  flex: 1;
  min-height: 240px;
}

.admin-layout__menu :deep(.el-menu-item) {
  height: 46px;
  min-height: 46px;
  margin: 4px 2px;
  padding: 0 14px !important;
  border-radius: 9px;
  color: #5d6675;
  font-size: 0.9rem;
  font-weight: 560;
  transition: color 160ms ease, background-color 160ms ease;
}

.admin-layout__menu :deep(.el-menu-item .el-icon) {
  margin-right: 11px;
  color: #687386;
  font-size: 19px;
}

.admin-layout__menu :deep(.el-menu-item:hover) {
  color: var(--jd-text);
  background: #f6f7fa;
}

.admin-layout__menu :deep(.el-menu-item.is-active) {
  color: #4f55e7;
  background: #f0f0ff;
  font-weight: 700;
}

.admin-layout__menu :deep(.el-menu-item.is-active .el-icon) {
  color: #4f55e7;
}

.admin-layout__aside-footer {
  display: grid;
  gap: 10px;
  padding: 12px 4px 2px;
  border-top: 1px solid var(--jd-border);
}

.admin-layout__profile {
  display: grid;
  gap: 4px;
}

.admin-layout__profile span {
  color: var(--jd-text-soft);
  overflow: hidden;
  font-size: 0.76rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.admin-layout__footer-actions {
  display: flex;
  gap: 8px;
}

.admin-layout__footer-actions .el-button {
  flex: 1;
  min-width: 0;
  min-height: 32px;
  padding: 6px 8px;
  font-size: 0.78rem;
}

.admin-layout__main {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.admin-layout__header {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 82px;
  padding: 14px 24px;
  border-width: 0 0 1px;
  border-radius: 0;
  box-shadow: none;
}

.admin-layout__header-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 10px 7px 12px;
  border: 1px solid var(--jd-border);
  border-radius: 10px;
  background: #fff;
  color: var(--jd-text-soft);
  font-size: 0.82rem;
  white-space: nowrap;
}

.admin-layout__content {
  flex: 1;
  min-height: 0;
  padding: 18px 22px 24px;
  border-radius: 0;
  overflow-y: auto;
  border: 0;
  background: #f7f8fa;
  box-shadow: none;
}

@media (max-width: 1100px) {
  .admin-layout {
    grid-template-columns: 1fr;
  }

  .admin-layout__aside {
    max-width: 100%;
    min-width: 0;
    gap: 12px;
    padding: 12px;
    border-width: 0 0 1px;
    border-radius: 0;
    overflow-y: visible;
  }

  .admin-layout__brand {
    min-height: 40px;
    padding: 0 4px;
  }

  .admin-layout__brand-mark {
    width: 40px;
    height: 40px;
  }

  .admin-layout__brand-logo {
    width: 28px;
    height: 28px;
  }

  .admin-layout__menu {
    display: flex;
    width: 100%;
    min-height: 0;
    overflow-x: auto;
    padding: 2px 0;
  }

  .admin-layout__menu :deep(.el-menu-item) {
    flex: 0 0 auto;
    min-height: 40px;
    margin: 0 4px;
    padding: 0 12px;
    border-radius: var(--jd-radius-control);
  }

  .admin-layout__aside-footer {
    display: none;
  }
}

@media (max-width: 768px) {
  .admin-layout {
    padding: 0;
    gap: 0;
  }

  .admin-layout__header {
    align-items: flex-start;
    flex-direction: column;
    min-height: 0;
    padding: 14px;
  }

  .admin-layout__header h2 {
    font-size: 1.2rem;
  }

  .admin-layout__content {
    padding: 12px;
  }

  .admin-layout__header-meta {
    width: 100%;
    justify-content: space-between;
  }
}
</style>
