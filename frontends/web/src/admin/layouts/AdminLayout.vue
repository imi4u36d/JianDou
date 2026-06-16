<template>
  <div class="page-shell admin-layout">
    <div class="admin-layout__aurora admin-layout__aurora-left" aria-hidden="true"></div>
    <div class="admin-layout__aurora admin-layout__aurora-right" aria-hidden="true"></div>

    <aside class="surface-card admin-layout__aside">
      <div class="admin-layout__brand">
        <div class="admin-layout__brand-mark">
          <img alt="煎豆 Logo" class="admin-layout__brand-logo" src="/brand/jiandou-mark.svg" />
        </div>
        <div>
          <p class="admin-layout__eyebrow">Admin Console</p>
          <h1>JianDou 管理系统</h1>
        </div>
      </div>

      <el-menu :default-active="activeMenu" class="admin-layout__menu" router>
        <el-menu-item index="/">
          <el-icon><DataAnalysis /></el-icon>
          <span>首页概览</span>
        </el-menu-item>
        <el-menu-item index="/tasks">
          <el-icon><Tickets /></el-icon>
          <span>任务管理</span>
        </el-menu-item>
        <el-menu-item index="/users">
          <el-icon><UserFilled /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
        <el-menu-item index="/invites">
          <el-icon><Ticket /></el-icon>
          <span>邀请码管理</span>
        </el-menu-item>
        <el-menu-item index="/credits">
          <el-icon><Coin /></el-icon>
          <span>积分管理</span>
        </el-menu-item>
        <el-menu-item index="/system">
          <el-icon><Setting /></el-icon>
          <span>系统配置</span>
        </el-menu-item>
      </el-menu>

      <div class="admin-layout__aside-footer">
        <div class="admin-layout__profile">
          <strong>{{ currentUser?.displayName || currentUser?.username }}</strong>
          <span>{{ currentUser?.username }} · {{ currentUser?.role }}</span>
        </div>
        <el-button plain @click="handleLogout">
          退出登录
        </el-button>
      </div>
    </aside>

    <section class="admin-layout__main">
      <header class="surface-card admin-layout__header">
        <div>
          <p class="admin-layout__eyebrow">Secure Area</p>
          <h2>{{ currentTitle }}</h2>
        </div>
        <div class="admin-layout__header-meta">
          <span>仅管理员可访问</span>
          <el-tag type="warning" effect="plain">Admin Only</el-tag>
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
  if (route.path === "/") {
    return "/";
  }
  if (route.path.startsWith("/tasks")) {
    return "/tasks";
  }
  if (route.path.startsWith("/users")) {
    return "/users";
  }
  if (route.path.startsWith("/invites")) {
    return "/invites";
  }
  if (route.path.startsWith("/credits")) {
    return "/credits";
  }
  return route.path;
});
const currentTitle = computed(() => {
  const title = route.meta.title;
  return typeof title === "string" && title.trim() ? title : "管理系统";
});

async function handleLogout() {
  await logoutAndClearSession();
  await router.replace("/login");
}
</script>

<style scoped>
.admin-layout {
  position: relative;
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 24px;
  padding: 24px;
}

.admin-layout__aurora {
  position: fixed;
  width: 320px;
  height: 320px;
  border-radius: 999px;
  filter: blur(96px);
  opacity: 0.4;
  pointer-events: none;
}

.admin-layout__aurora-left {
  top: -120px;
  left: -80px;
  background: rgba(196, 107, 47, 0.24);
}

.admin-layout__aurora-right {
  right: -80px;
  bottom: -120px;
  background: rgba(47, 122, 136, 0.22);
}

.admin-layout__aside {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 24px 18px 18px;
  border-radius: 28px;
}

.admin-layout__brand {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 6px 10px;
}

.admin-layout__brand-mark {
  display: grid;
  place-items: center;
  width: 54px;
  height: 54px;
  border-radius: 18px;
  background: linear-gradient(135deg, rgba(196, 107, 47, 0.18), rgba(47, 122, 136, 0.18));
}

.admin-layout__brand-logo {
  width: 34px;
  height: 34px;
  filter: drop-shadow(0 0 12px rgba(98, 136, 255, 0.18));
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

.admin-layout__menu {
  flex: 1;
  min-height: 240px;
}

.admin-layout__aside-footer {
  display: grid;
  gap: 12px;
  padding: 16px 10px 8px;
  border-top: 1px solid rgba(23, 32, 42, 0.08);
}

.admin-layout__profile {
  display: grid;
  gap: 4px;
}

.admin-layout__profile span {
  color: var(--jd-text-soft);
  font-size: 0.92rem;
}

.admin-layout__main {
  min-width: 0;
}

.admin-layout__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 24px;
  border-radius: 24px;
}

.admin-layout__header-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--jd-text-soft);
  font-size: 0.94rem;
}

.admin-layout__content {
  padding-top: 20px;
}

@media (max-width: 1100px) {
  .admin-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .admin-layout {
    padding: 16px;
    gap: 16px;
  }

  .admin-layout__header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
